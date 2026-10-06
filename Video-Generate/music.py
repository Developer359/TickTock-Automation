import os
import json
import random
import glob

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
MUSIC_ROOT     = os.path.abspath(os.path.join(SCRIPT_DIR, "../Video-Data/Music"))
EDDIT_DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../Eddit-data"))

# Map: music sub-folder name  →  Eddit-data JSON file
FOLDER_JSON_MAP = {
    "Gym":      "gym-video.json",
    "Mindset":  "mindset-video.json",
    "Hardwork": "hardwork-video.json",
}

MUSIC_EXTENSIONS = ("*.mp3", "*.wav", "*.m4a", "*.aac")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_all_music(folder: str) -> list[str]:
    """Return a sorted list of all music files inside *folder* (non-recursive)."""
    tracks = []
    for ext in MUSIC_EXTENSIONS:
        tracks.extend(glob.glob(os.path.join(folder, ext)))
    return sorted(set(tracks))


def pick_strict_random(all_tracks: list[str], used_tracks: list[str]) -> tuple[str, list[str]]:
    """
    Pick one track that has NOT been used yet.
    If every track has been used, reset the used list and start a fresh cycle.
    Returns (selected_path, updated_used_list).
    """
    # Normalise all paths to forward-slash for consistent comparison
    all_norm  = [t.replace("\\", "/") for t in all_tracks]
    used_norm = [t.replace("\\", "/") for t in used_tracks]

    available = [t for t in all_norm if t not in used_norm]

    if not available:
        # All tracks used — reset cycle
        print("  [INFO] All music tracks used. Resetting rotation.")
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

def attach_music() -> None:
    if not os.path.exists(MUSIC_ROOT):
        print(f"Error: Music directory not found at '{MUSIC_ROOT}'")
        return

    for folder_name, json_filename in FOLDER_JSON_MAP.items():
        folder_path = os.path.join(MUSIC_ROOT, folder_name)
        json_path   = os.path.join(EDDIT_DATA_DIR, json_filename)

        # ── 1. Gather all tracks in this category folder ───────────────────
        if not os.path.exists(folder_path):
            print(f"[SKIP] Folder not found: {folder_path}")
            continue

        all_tracks = get_all_music(folder_path)
        if not all_tracks:
            print(f"[SKIP] No music files found in '{folder_path}'")
            continue

        # ── 2. Load the Eddit-data JSON (may already have video/quote data) ─
        data = load_json(json_path)

        # ── 3. Strict-random selection ─────────────────────────────────────
        used_tracks = data.get("used_music", [])
        selected, updated_used = pick_strict_random(all_tracks, used_tracks)

        title = os.path.splitext(os.path.basename(selected))[0]

        # ── 4. Write back ──────────────────────────────────────────────────
        data["used_music"] = updated_used
        data["bg_music"] = {
            "title":     title,
            "file_path": selected   # already normalised to forward-slash
        }

        save_json(json_path, data)

        remaining = len(all_tracks) - len(updated_used)
        print(f"[{folder_name}] Selected : {title}")
        print(f"           JSON     : {json_filename}")
        print(f"           Remaining: {remaining} track(s) before next reset")
        print()


if __name__ == "__main__":
    print("[*] Attaching background music (strict random per category)...\n")
    attach_music()