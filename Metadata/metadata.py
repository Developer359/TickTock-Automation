"""
metadata.py  ─  Generates viral TikTok & Instagram titles + tags for every
                quote using Gemini 3.1, saves results to metadata.json, then
                inserts each row into the Supabase public."SocialMedia-Automation"
                table with status = 'pending'.

Structure saved per entry
─────────────────────────
{
  "query_name"  : "The Wake-Up Call",
  "tiktok" : {
      "title"  : "...",
      "tags"   : "#tag1 #tag2 ... #tag10"   // 6-10 tags, space-separated text
  },
  "instagram" : {
      "title"  : "...",
      "tags"   : "#tag1 ... #tag10"
  }
}

Supabase table: SocialMedia-Automation
────────────────────────────────────────
  id (auto), title (text), query_name (text), tags (text),
  platform (text), status (text), created_at (auto)
  Two rows inserted per quote: one for TikTok, one for Instagram.
"""

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


# ── Pydantic schemas ───────────────────────────────────────────────────────────
class PlatformMeta(BaseModel):
    title: str = Field(
        description="One viral, trending, SEO-optimised title for the platform (max 100 chars)."
    )
    tags: list[str] = Field(
        description="Between 6 and 10 hashtag strings (include the # symbol). "
                    "Mix trending, niche, and broad tags for maximum reach.",
        min_length=6,
        max_length=10,
    )


class QuoteMeta(BaseModel):
    query_name: str = Field(description="The quote category name, exactly as given.")
    tiktok: PlatformMeta
    instagram: PlatformMeta


# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a viral social-media growth expert specialising in TikTok and Instagram
for motivational / self-improvement content.

Your task: given a quote category name and the actual quote, generate ONE set of
metadata optimised for MAXIMUM viral reach on each platform.

Rules
─────
1. TITLES  
   • TikTok  : short, punchy, hook-driven (emoji OK). Max 100 chars.  
   • Instagram: slightly longer, story-driven, SEO-rich. Max 100 chars.  
   • Both must sound natural and NOT like clickbait.  
   • Start with a power verb or emotional hook word.

2. TAGS (hashtags)  
   • Return 6–10 hashtag strings starting with '#'.  
   • Mix: 2-3 MEGA tags (>10 M posts), 2-3 MID tags (1-10 M), 1-3 NICHE tags.  
   • TikTok  : prioritise trending audio / challenge tags where relevant.  
   • Instagram: prioritise community + niche discovery tags.  
   • NEVER duplicate tags between platforms.

3. SEO  
   • Embed the main keyword (e.g. "motivation", "mindset", "hardwork") naturally  
     in both titles.  
   • Tags must match what real users search for RIGHT NOW in 2025-2026.

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
    """Call Gemini 3.1 to generate TikTok + Instagram metadata for one quote."""
    user_prompt = (
        f'Category: "{query_name}"\n'
        f'Quote: "{quote}"\n\n'
        "Generate viral metadata for TikTok AND Instagram as per the schema."
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
        return json.loads(response.text)
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
    Insert two rows per quote (TikTok + Instagram) into SocialMedia-Automation.
    Columns: query_name, title, tags (TEXT), platform (TEXT), status='pending'.
    """
    table = "SocialMedia-Automation"
    rows  = []

    for entry in all_metadata:
        query_name = entry.get("query_name", "")
        for platform in ("tiktok", "instagram"):
            meta = entry.get(platform, {})
            # tags is TEXT in Supabase — join list into space-separated string
            raw_tags = meta.get("tags", [])
            tags_str = " ".join(raw_tags) if isinstance(raw_tags, list) else raw_tags
            rows.append({
                "query_name": query_name,
                "title":      meta.get("title", ""),
                "tags":       tags_str,
                "platform":   platform.capitalize(),   # 'Tiktok' or 'Instagram'
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
        for platform in ("tiktok", "instagram"):
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
