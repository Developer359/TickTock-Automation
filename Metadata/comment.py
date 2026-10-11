import os
import sys
import json
import time
import urllib.request
import urllib.parse
import ssl
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

# ── Gemini Client & SSL Context ────────────────────────────────────────────────
client  = genai.Client(api_key=GEMINI_API_KEY)
SSL_CTX = ssl.create_default_context()

# ── Quote categories we track ──────────────────────────────────────────────────
CATEGORY_MAP = {
    "The Wake-Up Call": os.path.join(EDDIT_DIR, "gym-video.json"),
    "Mindset & Psychology": os.path.join(EDDIT_DIR, "mindset-video.json"),
    "Hardwork & Self-Belief": os.path.join(EDDIT_DIR, "hardwork-video.json"),
}

# ── High-Impact Fallback Comments ──────────────────────────────────────────────
FALLBACK_COMMENTS = {
    "The Wake-Up Call": "Drop a '🔥' if you chose discipline over temporary comfort today.",
    "Mindset & Psychology": "Don't let people who gave up on their dreams talk you out of yours. Agree?",
    "Hardwork & Self-Belief": "Failure is just a lesson you paid for. Comment 'YES' if you're not quitting.",
}

# ── Pydantic Schema ────────────────────────────────────────────────────────────
class CommentResponse(BaseModel):
    query_name: str = Field(description="The category name, exactly as provided.")
    comment: str = Field(
        description="Exactly ONE viral, short, punchy motivational sentence (under 18 words). "
                    "Must inspire viewers and provoke them to reply or drop an emoji."
    )

# ── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a viral social-media growth hacker and psychology expert specializing in TikTok engagement.

Your task: Given a motivational quote and category, generate ONE viral, high-converting pinned comment.

Strict Rules:
1. EXACTLY ONE SENTENCE ONLY: Keep it between 8 and 18 words.
2. HIGH-IMPACT & MOTIVATING: Punchy, raw, empowering, and emotionally resonant.
3. DRIVE ENGAGEMENT: Compel viewers to comment back, share their perspective, or drop a '🔥', '🗿', or 'YES'.
4. NO generic praise: Don't just say 'great video'. Make a statement or pose a bold question related to the quote.

Examples:
- "Drop a '🔥' if you chose discipline over temporary comfort today."
- "Winners focus on winning; losers focus on winners. Drop a '🗿' if you agree."
- "Comment 'YES' if you refuse to stay in your comfort zone another day."
- "Failure is just the price of admission. What lesson made you stronger?"

Output: Strict JSON matching the schema.
"""

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_quote(json_path: str) -> str:
    """Read the quote text from an Eddit-data JSON file."""
    if not os.path.exists(json_path) or os.path.getsize(json_path) == 0:
        return ""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("quote", "")
    except Exception:
        return ""


def generate_comment_for(query_name: str, quote: str) -> str:
    """Call Gemini 3.1 to generate one viral engagement comment."""
    user_prompt = (
        f'Category: "{query_name}"\n'
        f'Quote: "{quote}"\n\n'
        "Generate exactly ONE viral, motivational engagement comment as per the schema."
    )

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=CommentResponse,
                temperature=0.85,
            ),
        )
        parsed = json.loads(response.text)
        comment = parsed.get("comment", "").strip()
        if comment:
            return comment
    except Exception as exc:
        print(f"  ⚠  Gemini error for '{query_name}': {exc}")

    # Fallback if AI generation failed
    return FALLBACK_COMMENTS.get(query_name, "Drop a '🔥' if you are pushing forward today.")


# ── Supabase Helpers ───────────────────────────────────────────────────────────

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
    except Exception as exc:
        return {"status": 500, "body": str(exc)}


def update_supabase_comment(query_name: str, comment_text: str) -> bool:
    """
    Update the 'Comment' column for the matching pending row in SocialMedia-Automation.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("  ⚠️  Supabase credentials missing, skipping database update.")
        return False

    # Find the newest pending row for this query_name
    query_encoded = urllib.parse.quote(query_name)
    path = f"SocialMedia-Automation?query_name=eq.{query_encoded}&platform=eq.Tiktok&status=eq.pending&order=id.desc&limit=1"
    res = _supabase_request("GET", path)

    if res["status"] != 200 or not res["body"]:
        print(f"  ⚠️  No pending row found in Supabase for query_name: '{query_name}'")
        return False

    row_id = res["body"][0]["id"]

    # PATCH the Comment column
    patch_path = f"SocialMedia-Automation?id=eq.{row_id}"
    patch_res  = _supabase_request("PATCH", patch_path, {"Comment": comment_text})

    if patch_res["status"] in (200, 204):
        print(f"  ✅  Supabase row id={row_id} updated with Comment: '{comment_text}'")
        return True
    else:
        print(f"  ❌  Failed to update Supabase row id={row_id} [{patch_res['status']}]: {patch_res['body']}")
        return False


def update_local_metadata_json(comments_by_query: dict[str, str]) -> None:
    """Persist generated comments into Metadata/metadata.json."""
    if not os.path.exists(METADATA_JSON):
        return

    try:
        with open(METADATA_JSON, "r", encoding="utf-8") as f:
            all_meta = json.load(f)

        if isinstance(all_meta, list):
            for entry in all_meta:
                qname = entry.get("query_name", "")
                if qname in comments_by_query and "tiktok" in entry:
                    entry["tiktok"]["comment"] = comments_by_query[qname]

            with open(METADATA_JSON, "w", encoding="utf-8") as f:
                json.dump(all_meta, f, indent=4, ensure_ascii=False)
            print(f"  💾  Updated local metadata.json with viral comments.")
    except Exception as exc:
        print(f"  ⚠️  Could not update local metadata.json: {exc}")


# ── Main ───────────────────────────────────────────────────────────────────────

def generate_and_store_comments() -> dict[str, str]:
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     AI COMMENTS  —  Viral Motivation & Engagement (Gemini)   ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    results: dict[str, str] = {}

    for query_name, json_path in CATEGORY_MAP.items():
        print(f"  ▶  Processing: {query_name}")
        quote = load_quote(json_path)

        if not quote:
            print(f"     ⚠  No quote found in {os.path.basename(json_path)} — using fallback\n")
            comment = FALLBACK_COMMENTS.get(query_name, "Drop a '🔥' if you agree.")
        else:
            print(f'     Quote   : "{quote[:75]}{"…" if len(quote) > 75 else ""}"')
            comment = generate_comment_for(query_name, quote)

        print(f"     Comment : 💬 \"{comment}\"\n")
        results[query_name] = comment

        # Update Supabase Comment column
        update_supabase_comment(query_name, comment)
        time.sleep(0.5)

    # Persist in local metadata.json
    update_local_metadata_json(results)

    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║       ✓  Viral comments generated and stored in Supabase!    ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")
    return results


if __name__ == "__main__":
    generate_and_store_comments()
