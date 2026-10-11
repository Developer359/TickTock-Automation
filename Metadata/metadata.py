import os
import sys
import json
import time
import urllib.request
import ssl
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

sys.stdout.reconfigure(encoding="utf-8")

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METADATA_DIR  = os.path.dirname(os.path.abspath(__file__))
METADATA_JSON = os.path.join(METADATA_DIR, "metadata.json")
EDDIT_DIR     = os.path.join(ROOT_DIR, "Eddit-data")

# ── Load env ───────────────────────────────────────────────────────────────────
load_dotenv(os.path.join(ROOT_DIR, ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL   = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY", "")

# ── Gemini client ──────────────────────────────────────────────────────────────
client  = genai.Client(api_key=GEMINI_API_KEY)
SSL_CTX = ssl.create_default_context()

# ── Quote categories we track ──────────────────────────────────────────────────
# Each maps to the Eddit-data JSON that quotes.py produces.
CATEGORY_MAP = {
    "The Wake-Up Call": os.path.join(EDDIT_DIR, "gym-video.json"),
    "Mindset & Psychology": os.path.join(EDDIT_DIR, "mindset-video.json"),
    "Hardwork & Self-Belief": os.path.join(EDDIT_DIR, "hardwork-video.json"),
}


# ── Viral FYP Tags guaranteed on every post ──────────────────────────────────
CORE_FYP_TAGS = [
    "#fyp",
    "#foryou",
    "#foryoupage",
    "#viral",
    "#trending",
    "#fypシ",
]

# ── Pydantic schemas ───────────────────────────────────────────────────────────
class PlatformMeta(BaseModel):
    hook: str = Field(
        description="One viral, punchy, curiosity-driven hook title for TikTok (max 85 chars, emoji OK). "
                    "Start with a power verb, emotional trigger, or harsh truth."
    )
    call_to_action: str = Field(
        description="A high-converting TikTok call-to-action that encourages viewers to SAVE and COMMENT "
                    "(e.g. '📌 Save this for when you need a reminder | Drop a 🔥 if you agree'). Max 85 chars."
    )
    tags: list[str] = Field(
        description="List of 8 to 12 high-performing viral and SEO hashtags for TikTok, including #fyp, #foryou, "
                    "#viral, #trending, plus niche tags like #motivation, #mindset, #discipline, #selfimprovement, "
                    "#success, #motok.",
        min_length=8,
        max_length=15,
    )


class QuoteMeta(BaseModel):
    query_name: str = Field(description="The quote category name, exactly as given.")
    tiktok: PlatformMeta


# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a world-class viral TikTok growth expert and SEO specialist for motivational, discipline, and mindset content.

Your task: Given a quote category and the actual quote, generate viral metadata designed to:
1. Break through TikTok's initial test audience (surpassing 100-200 view plateaus).
2. Land on the TikTok "For You Page" (FYP) and Rank #1 in TikTok Search (TikTok SEO).
3. Maximize viewer Saves, Shares, and Comments — the primary ranking signals for TikTok's algorithm.

Rules
─────
1. HOOK
   • Punchy, emotionally provocative, and relatable (max 85 chars).
   • Uses psychological triggers (urgency, harsh truth, wake-up call, ambition).
   • Example: "Stop playing small: Your comfort zone is destroying your potential ⚠️"

2. CALL TO ACTION (CTA)
   • TikTok's algorithm prioritizes SAVES and COMMENTS above all else.
   • Always include a high-converting action:
     - Saving the video ("📌 Save this for when you need a reminder")
     - Commenting ("Drop a 🔥 if you agree", "Comment 'YES' if you claim this")
     - Following ("Follow for daily discipline 🗿")

3. VIRAL HASHTAGS (TAGS)
   • Every post MUST be optimized for the TikTok For You Page (#fyp, #foryou, #foryoupage, #viral, #trending, #fypシ).
   • Include top-tier multi-billion view niche hashtags (#motivation, #mindset, #discipline, #success, #selfimprovement).
   • Include trending aesthetic / subculture tags (#motok, #grindset, #mentality, #mindsetshift).
   • Every tag must start with '#' and be lowercase.

Output: strict JSON matching the schema. No extra text.
"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_quote(json_path: str) -> str:
    """Read the quote text from an Eddit-data JSON file (may be empty)."""
    if not os.path.exists(json_path) or os.path.getsize(json_path) == 0:
        return ""
    with open(json_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data.get("quote", "")
        except json.JSONDecodeError:
            return ""


def generate_metadata_for(query_name: str, quote: str) -> dict | None:
    """Call Gemini 3.1 to generate viral TikTok metadata for one quote."""
    user_prompt = (
        f'Category: "{query_name}"\n'
        f'Quote: "{quote}"\n\n'
        "Generate viral, high-SEO TikTok metadata with hook, CTA, and trending FYP hashtags as per the schema."
    )

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=QuoteMeta,
                temperature=0.85,
            ),
        )
        parsed = json.loads(response.text)

        # ── Post-process & guarantee viral FYP tags + format caption title ───
        tt = parsed.get("tiktok", {})
        hook = tt.get("hook", "").strip()
        cta  = tt.get("call_to_action", "").strip()

        # Combine Hook + CTA into full title for Buffer / TikTok
        if hook and cta:
            formatted_title = f"{hook}\n\n{cta}"
        elif hook:
            formatted_title = hook
        else:
            formatted_title = tt.get("title", "")

        parsed["tiktok"]["title"] = formatted_title

        # Clean tags from Gemini
        raw_tags = tt.get("tags", [])
        clean_tags = []
        for t in raw_tags:
            t = t.strip().lower()
            if not t.startswith("#"):
                t = f"#{t}"
            if t not in clean_tags:
                clean_tags.append(t)

        # Merge with CORE_FYP_TAGS, guaranteeing FYP tags are first
        final_tags = list(CORE_FYP_TAGS)
        for t in clean_tags:
            if t not in final_tags:
                final_tags.append(t)

        parsed["tiktok"]["tags"] = final_tags[:14]
        return parsed
    except Exception as exc:
        print(f"  ⚠  Gemini error for '{query_name}': {exc}")
        return None


def save_to_json(all_metadata: list[dict]) -> None:
    """Persist all generated metadata to Metadata/metadata.json."""
    with open(METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=4, ensure_ascii=False)
    print(f"\n  💾  Saved metadata.json  ({len(all_metadata)} entries)")


# ── Supabase helpers ───────────────────────────────────────────────────────────

def _supabase_request(method: str, path: str, payload: dict | list | None = None) -> dict:
    url  = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req  = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")

    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            body = resp.read().decode()
            return {"status": resp.status, "body": json.loads(body) if body else []}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        return {"status": exc.code, "body": body}


def push_to_supabase(all_metadata: list[dict]) -> None:
    """
    Insert one row per quote (TikTok) into SocialMedia-Automation.
    Columns: query_name, title, tags (TEXT), platform (TEXT), status='pending'.
    """
    table = "SocialMedia-Automation"
    rows  = []

    for entry in all_metadata:
        query_name = entry.get("query_name", "")
        for platform in ("tiktok",):
            meta = entry.get(platform, {})
            # tags is TEXT in Supabase — join list into space-separated string
            raw_tags = meta.get("tags", [])
            tags_str = " ".join(raw_tags) if isinstance(raw_tags, list) else raw_tags
            rows.append({
                "query_name": query_name,
                "title":      meta.get("title", ""),
                "tags":       tags_str,
                "platform":   platform.capitalize(),   # 'Tiktok'
                "status":     "pending",
            })

    if not rows:
        print("  No rows to insert.")
        return

    result = _supabase_request("POST", table, rows)

    if result["status"] in (200, 201):
        print(f"  Inserted {len(rows)} rows into Supabase '{table}' (status=pending)")
    else:
        print(f"  Supabase insert failed [{result['status']}]: {result['body']}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║    METADATA  —  Viral Title & Tags Generator (Gemini 3.1)   ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    all_metadata: list[dict] = []

    for query_name, json_path in CATEGORY_MAP.items():
        print(f"  ▶  Processing: {query_name}")
        quote = load_quote(json_path)

        if not quote:
            print(f"     ⚠  No quote found in {os.path.basename(json_path)} — skipping\n")
            continue

        print(f'     Quote: "{quote[:80]}{"…" if len(quote) > 80 else ""}"\n')
        meta = generate_metadata_for(query_name, quote)

        if not meta:
            continue

        # Ensure query_name is embedded
        meta["query_name"] = query_name

        all_metadata.append(meta)

        # Pretty-print results
        for platform in ("tiktok",):
            pm = meta.get(platform, {})
            print(f"     [{platform.upper()}]")
            print(f"       Title : {pm.get('title', '')}")
            print(f"       Tags  : {' '.join(pm.get('tags', []))}")
        print()

        time.sleep(0.5)  # gentle rate-limit pause

    if not all_metadata:
        print("  ⚠  No metadata generated. Exiting.")
        return

    # ── Save locally ───────────────────────────────────────────────────────────
    save_to_json(all_metadata)

    # ── Push to Supabase ───────────────────────────────────────────────────────
    print("\n  📡  Pushing to Supabase …")
    push_to_supabase(all_metadata)

    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║       ✓  Metadata stage completed successfully!              ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
