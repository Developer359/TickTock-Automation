import os
import sys
import json
import ssl
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────────
# Script is at: Video-Post/Instagram-post/post_instagram.py
# Root is 3 levels up
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

# ── Credentials ────────────────────────────────────────────────────────────────
SUPABASE_URL       = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY       = os.getenv("SUPABASE_KEY", "")
BUFFER_API_KEY     = os.getenv("BUFFER_API_KEY", "")
BUFFER_CHANNEL_ID  = os.getenv("BUFFER_CHANNEL_ID_Instagram", "")

SUPABASE_TABLE     = "SocialMedia-Automation"
SUPABASE_BUCKET    = "tiktok-videos"
BUFFER_GRAPHQL_URL = "https://api.buffer.com/graphql"

SSL_CTX = ssl.create_default_context()


# ╔══════════════════════════════════════════════════════════╗
# ║              SUPABASE  HELPERS                           ║
# ╚══════════════════════════════════════════════════════════╝

def _supabase_req(method: str, path: str, payload=None, extra_headers: dict = None) -> dict:
    url  = f"{SUPABASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req  = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey",        SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type",  "application/json")
    req.add_header("Prefer",        "return=representation")
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            body = resp.read().decode()
            return {"status": resp.status, "body": json.loads(body) if body else []}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        return {"status": exc.code, "body": body}


def fetch_first_pending_instagram() -> dict | None:
    """
    Fetch the very first row from SocialMedia-Automation where:
      platform = 'Instagram'  AND  status = 'pending'
    Ordered by id ASC — always picks the oldest pending entry.
    """
    print("  \U0001f50d  Fetching first pending Instagram metadata from Supabase ...")
    path = (
        f"/rest/v1/{SUPABASE_TABLE}"
        f"?platform=eq.Instagram"
        f"&status=eq.pending"
        f"&order=id.asc"
        f"&limit=1"
    )
    res = _supabase_req("GET", path)
    if res["status"] != 200:
        print(f"  ❌  Failed to query Supabase [{res['status']}]: {res['body']}")
        return None

    rows = res["body"]
    if not rows:
        print("  ⚠️   No pending Instagram posts found in Supabase.")
        return None

    row = rows[0]
    print(f"  ✅  Found row  id={row['id']}  query_name={row.get('query_name', '')}")
    return row


# ── query_name → video filename mapping ───────────────────────────────────────
QUERY_VIDEO_MAP = {
    "The Wake-Up Call":       "gym-video.mp4",
    "Mindset & Psychology":   "mindset-video.mp4",
    "Hardwork & Self-Belief": "hardwork-video.mp4",
}


def get_video_url_for(query_name: str) -> str | None:
    """
    Return the public Supabase Storage URL for the video that matches
    the given query_name. Falls back to the first real file if the
    query_name is unknown.
    """
    file_name = QUERY_VIDEO_MAP.get(query_name)

    if file_name:
        print(f"  \U0001f3ac  Matched query_name '{query_name}' \u2192 {file_name}")
    else:
        print(f"  \u26a0\ufe0f   Unknown query_name '{query_name}', falling back to first video in bucket ...")
        list_path = f"/storage/v1/object/list/{SUPABASE_BUCKET}"
        payload   = {"prefix": "uploads", "limit": 10, "offset": 0,
                     "sortBy": {"column": "created_at", "order": "asc"}}
        res = _supabase_req("POST", list_path, payload)
        if res["status"] != 200:
            print(f"  \u274c  Failed to list bucket [{res['status']}]: {res['body']}")
            return None
        real_files = [f for f in res["body"]
                      if f.get("name") and f["name"] != ".emptyFolderPlaceholder"]
        if not real_files:
            print("  \u26a0\ufe0f   Bucket is empty.")
            return None
        file_name = real_files[0]["name"]

    storage_path = f"uploads/{file_name}"
    public_url   = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{storage_path}"

    print(f"  \u2705  Video file : {file_name}")
    print(f"  \U0001f517  URL       : {public_url}")
    return public_url


def mark_as_posted(row_id: int) -> None:
    """Update the row status to 'posted' in Supabase."""
    print(f"  \U0001f4dd  Marking row id={row_id} as 'posted' in Supabase ...")
    path = f"/rest/v1/{SUPABASE_TABLE}?id=eq.{row_id}"
    res  = _supabase_req("PATCH", path, {"status": "posted"})
    if res["status"] in (200, 201, 204):
        print("  ✅  Status updated to 'posted'.")
    else:
        print(f"  ❌  Failed to update status [{res['status']}]: {res['body']}")


# ╔══════════════════════════════════════════════════════════╗
# ║              BUFFER  HELPERS                             ║
# ╚══════════════════════════════════════════════════════════╝

def post_to_buffer(title: str, tags: str, video_url: str) -> bool:
    """
    Send a createPost mutation to the Buffer GraphQL API.
    Caption = title + blank line + tags.
    Returns True on success, False on failure.
    """
    caption = f"{title}\n\n{tags}"

    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            dueAt
            status
          }
        }
        ... on MutationError {
          message
          __typename
        }
      }
    }
    """

    variables = {
        "input": {
            "text":           caption,
            "channelId":      BUFFER_CHANNEL_ID,
            "schedulingType": "automatic",
            "mode":           "shareNow",
            "metadata": {
                "instagram": {
                    "type": "reel",
                    "shouldShareToFeed": True
                }
            },
            "assets": [
                {
                    "video": {
                        "url": video_url
                    }
                }
            ]
        }
    }

    payload = json.dumps({"query": mutation, "variables": variables}).encode("utf-8")
    req     = urllib.request.Request(BUFFER_GRAPHQL_URL, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {BUFFER_API_KEY}")
    req.add_header("Content-Type",  "application/json")

    print("  \U0001f4f8  Sending post to Buffer (Instagram channel) ...")
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            body   = resp.read().decode()
            result = json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(f"  ❌  Buffer HTTP error [{exc.code}]: {body}")
        return False
    except Exception as exc:
        print(f"  ❌  Buffer request failed: {exc}")
        return False

    # Inspect GraphQL response
    errors = result.get("errors")
    if errors:
        print(f"  ❌  Buffer GraphQL errors: {json.dumps(errors, indent=2)}")
        return False

    create_post = result.get("data", {}).get("createPost", {})

    if create_post.get("__typename") == "MutationError" or "message" in create_post:
        print(f"  ❌  Buffer mutation error: {create_post.get('message')}")
        return False

    post = create_post.get("post", {})
    print(f"  ✅  Post queued successfully!")
    print(f"      Post ID : {post.get('id', 'N/A')}")
    print(f"      Due at  : {post.get('dueAt', 'N/A')}")
    print(f"      Status  : {post.get('status', 'N/A')}")
    return True


# ╔══════════════════════════════════════════════════════════╗
# ║                       MAIN                               ║
# ╚══════════════════════════════════════════════════════════╝

def main() -> None:
    print("╔══════════════════════════════════════════════════════════╗")
    print("║      \U0001f4f8  Instagram Post Script  —  Buffer API            ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    # ── Guard checks ───────────────────────────────────────────────────────────
    missing = []
    if not SUPABASE_URL:      missing.append("SUPABASE_URL")
    if not SUPABASE_KEY:      missing.append("SUPABASE_KEY")
    if not BUFFER_API_KEY:    missing.append("BUFFER_API_KEY")
    if not BUFFER_CHANNEL_ID: missing.append("BUFFER_CHANNEL_ID_Instagram")
    if missing:
        print(f"  ❌  Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    print(f"  \U0001f4e1  Supabase  : {SUPABASE_URL}")
    print(f"  \U0001f4f7  Channel   : {BUFFER_CHANNEL_ID}  (Instagram)\n")

    # ── Step 1: Fetch first pending Instagram metadata ─────────────────────────
    row = fetch_first_pending_instagram()
    if not row:
        print("\n  ℹ️   Nothing to post. Exiting.")
        sys.exit(0)

    row_id     = row["id"]
    title      = row.get("title", "")
    tags       = row.get("tags",  "")
    query_name = row.get("query_name", "")

    print(f"\n  \U0001f4cb  Metadata loaded:")
    print(f"      Query  : {query_name}")
    print(f"      Title  : {title}")
    print(f"      Tags   : {tags}\n")

    # ── Step 2: Get matching video URL from Supabase Storage ──────────────────
    video_url = get_video_url_for(query_name)
    if not video_url:
        print("\n  ❌  No video available. Exiting without posting.")
        sys.exit(1)

    print()

    # ── Step 3: Post to Buffer ─────────────────────────────────────────────────
    success = post_to_buffer(title, tags, video_url)

    if not success:
        print("\n  ❌  Post failed. Status NOT updated.")
        sys.exit(1)

    # ── Step 4: Update Supabase status → 'posted' ──────────────────────────────
    print()
    mark_as_posted(row_id)

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   ✅  Instagram post completed successfully!             ║")
    print("╚══════════════════════════════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
