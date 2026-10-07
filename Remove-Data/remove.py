import os
import sys
import json
import urllib.request
import ssl

sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv

# ── Load env ───────────────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    # If run in GitHub Actions, they might be in environment variables directly
    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_KEY"):
        print("❌ SUPABASE_URL or SUPABASE_KEY not found in env.")
        sys.exit(1)
    else:
        SUPABASE_URL = os.environ.get("SUPABASE_URL").rstrip("/")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

SSL_CTX = ssl.create_default_context()

def _supabase_req(method, path, payload=None):
    url = f"{SUPABASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            body = resp.read().decode()
            return {"status": resp.status, "body": json.loads(body) if body else {}}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "body": exc.read().decode()}

def clean_storage_bucket(bucket_name: str, prefix: str = ""):
    print(f"\n🗑️  Cleaning Storage Bucket: '{bucket_name}' (prefix: '{prefix}')")
    
    # 1. List all files in the bucket
    list_path = f"/storage/v1/object/list/{bucket_name}"
    payload = {"prefix": prefix, "limit": 1000, "offset": 0}
    
    res = _supabase_req("POST", list_path, payload)
    if res["status"] != 200:
        print(f"  ❌ Failed to list bucket files [{res['status']}]: {res['body']}")
        return
        
    files = res["body"]
    if not files:
        print("  ✅ Bucket is already empty.")
        return
        
    # Extract file paths (skip empty folders represented by placeholder files)
    file_paths = []
    for f in files:
        name = f.get("name")
        if name and name != ".emptyFolderPlaceholder":
            if prefix:
                file_paths.append(f"{prefix}/{name}".strip("/"))
            else:
                file_paths.append(name.strip("/"))
            
    if not file_paths:
        print("  ✅ Bucket has no files to delete.")
        return
        
    print(f"  ... found {len(file_paths)} files. Deleting...")
    
    # 2. Delete the files
    delete_path = f"/storage/v1/object/{bucket_name}"
    del_payload = {"prefixes": file_paths}
    del_res = _supabase_req("DELETE", delete_path, del_payload)
    
    if del_res["status"] == 200:
        print(f"  ✅ Successfully deleted {len(file_paths)} files.")
    else:
        print(f"  ❌ Failed to delete files [{del_res['status']}]: {del_res['body']}")

def reset_id_sequence(table_name: str) -> bool:
    """
    Try to reset the auto-increment ID sequence back to 1 after a DELETE.
    Uses the Supabase RPC endpoint for the custom truncate function.
    Returns True if sequence was successfully reset.
    """
    # ── Attempt 1: call the pre-created truncate RPC ───────────────────────────
    rpc_res = _supabase_req("POST", "/rest/v1/rpc/truncate_social_media_automation")
    if rpc_res["status"] in (200, 201, 204):
        print("  ✅  ID sequence reset to 1 via TRUNCATE RPC.")
        return True

    # ── Attempt 2: try a generic reset_sequence RPC ────────────────────────────
    rpc_res2 = _supabase_req(
        "POST",
        "/rest/v1/rpc/reset_table_sequence",
        {"table_name": table_name}
    )
    if rpc_res2["status"] in (200, 201, 204):
        print("  ✅  ID sequence reset to 1 via reset_sequence RPC.")
        return True

    return False


def clean_table(table_name: str):
    print(f"\n\U0001f5d1\ufe0f  Cleaning Table: '{table_name}'")

    # ── Strategy 1: TRUNCATE + RESTART IDENTITY via RPC ───────────────────────
    print("  ... attempting TRUNCATE (resets ID to 1) ...")
    rpc_res = _supabase_req("POST", "/rest/v1/rpc/truncate_social_media_automation")

    if rpc_res["status"] in (200, 201, 204):
        print("  ✅  Table truncated. ID sequence restarted from 1!")
        return

    print(f"  ⚠️   TRUNCATE RPC not found [{rpc_res['status']}] — falling back to DELETE ...")

    # ── Strategy 2: DELETE all rows ────────────────────────────────────────────
    del_res = _supabase_req("DELETE", f"/rest/v1/{table_name}?id=gt.0")

    if del_res["status"] not in (200, 201, 204):
        print(f"  ❌  Failed to delete rows [{del_res['status']}]: {del_res['body']}")
        return

    print("  ✅  All rows deleted.")

    # ── Strategy 3: Reset sequence after DELETE ────────────────────────────────
    seq_reset = reset_id_sequence(table_name)

    if not seq_reset:
        # ── One-time setup instructions ────────────────────────────────────────
        print()
        print("  ╔══════════════════════════════════════════════════════════╗")
        print("  ║   ⚠️  ID SEQUENCE NOT RESET — ONE-TIME SETUP NEEDED      ║")
        print("  ╠══════════════════════════════════════════════════════════╣")
        print("  ║  Run this SQL ONCE in Supabase → SQL Editor:            ║")
        print("  ║                                                          ║")
        print("  ║  CREATE OR REPLACE FUNCTION                              ║")
        print("  ║    truncate_social_media_automation()                    ║")
        print("  ║  RETURNS void LANGUAGE sql AS $$                         ║")
        print(f"  ║    TRUNCATE TABLE \"{table_name}\" RESTART IDENTITY;  ║")
        print("  ║  $$;                                                     ║")
        print("  ║                                                          ║")
        print("  ║  After that, this script will ALWAYS reset IDs to 1!    ║")
        print("  ╚══════════════════════════════════════════════════════════╝")
        print()


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     SUPABASE CLEANUP SCRIPT (Runs Locally or GitHub)     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    
    # Clean the bucket for videos
    clean_storage_bucket("tiktok-videos", prefix="")
    clean_storage_bucket("tiktok-videos", prefix="uploads")
    
    # Clean the table
    clean_table("SocialMedia-Automation")
    
    print("\n✅ Cleanup script completed.\n")

if __name__ == "__main__":
    main()
