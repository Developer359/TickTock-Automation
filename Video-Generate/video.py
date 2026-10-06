import os
import json
import random
import glob

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
VIDEOS_ROOT    = os.path.abspath(os.path.join(SCRIPT_DIR, "../Video-Data/Videos"))
EDDIT_DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../Eddit-data"))

# Map: video sub-folder name  →  Eddit-data JSON file
FOLDER_JSON_MAP = {
    "Gym":      "gym-video.json",
    "Mindset":  "mindset-video.json",
    "Hardwork": "hardwork-video.json",
}

VIDEO_EXTENSIONS = ("*.mp4", "*.mov", "*.mkv", "*.webm")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_all_videos(folder: str) -> list[str]:
    """Return a sorted list of all video files inside *folder* (non-recursive)."""
    videos = []
    for ext in VIDEO_EXTENSIONS:
        videos.extend(glob.glob(os.path.join(folder, ext)))
    return sorted(set(videos))


def pick_strict_random(all_videos: list[str], used_videos: list[str]) -> tuple[str, list[str]]:
    """
    Pick one video that has NOT been used yet.
    If every video has been used, reset the used list and start a fresh cycle.
    Returns (selected_path, updated_used_list).
    """
    # Normalise all paths to forward-slash for consistent comparison
    all_norm  = [v.replace("\\", "/") for v in all_videos]
    used_norm = [v.replace("\\", "/") for v in used_videos]

    available = [v for v in all_norm if v not in used_norm]

    if not available:
        # All videos used — reset cycle
        print("  [INFO] All videos used. Resetting rotation.")
        used_norm = []
        available = all_norm

    selected = random.choice(available)
    used_norm.append(selected)
    return selected, used_norm


def load_json(path: str) -> dict:
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {}


def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def attach_videos() -> None:
    if not os.path.exists(VIDEOS_ROOT):
        print(f"Error: Videos directory not found at '{VIDEOS_ROOT}'")
        return

    for folder_name, json_filename in FOLDER_JSON_MAP.items():
        folder_path = os.path.join(VIDEOS_ROOT, folder_name)
        json_path   = os.path.join(EDDIT_DATA_DIR, json_filename)

        # ── 1. Gather all videos in this category folder ──────────────────
        if not os.path.exists(folder_path):
            print(f"[SKIP] Folder not found: {folder_path}")
            continue

        all_videos = get_all_videos(folder_path)
        if not all_videos:
            print(f"[SKIP] No video files found in '{folder_path}'")
            continue

        # ── 2. Load the Eddit-data JSON (may already have quote/voice data) ─
        data = load_json(json_path)

        # ── 3. Strict-random selection ─────────────────────────────────────
        used_videos = data.get("used_videos", [])
        selected, updated_used = pick_strict_random(all_videos, used_videos)

        title = os.path.splitext(os.path.basename(selected))[0]

        # ── 4. Write back ──────────────────────────────────────────────────
        data["used_videos"] = updated_used
        data["bg_video"] = {
            "title":     title,
            "file_path": selected   # already normalised to forward-slash
        }

        save_json(json_path, data)

        remaining = len(all_videos) - len(updated_used)
        print(f"[{folder_name}] Selected : {title}")
        print(f"           JSON     : {json_filename}")
        print(f"           Remaining: {remaining} video(s) before next reset")
        print()


if __name__ == "__main__":
    print("[*] Attaching background videos (strict random per category)...\n")
    attach_videos()