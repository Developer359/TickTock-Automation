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


def pick_random_video(all_videos: list[str]) -> str:
    """
    Pick one random video from all available videos.
    Returns the selected path (normalised to forward-slash).
    """
    all_norm = [v.replace("\\", "/") for v in all_videos]
    return random.choice(all_norm)


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

        # ── 3. Random selection ────────────────────────────────────────────
        selected = pick_random_video(all_videos)

        title = os.path.splitext(os.path.basename(selected))[0]

        # ── 4. Write back ──────────────────────────────────────────────────
        data["bg_video"] = {
            "title":     title,
            "file_path": selected   # already normalised to forward-slash
        }

        save_json(json_path, data)

        print(f"[{folder_name}] Selected : {title}")
        print(f"           JSON     : {json_filename}")
        print()


if __name__ == "__main__":
    print("[*] Attaching background videos (strict random per category)...\n")
    attach_videos()