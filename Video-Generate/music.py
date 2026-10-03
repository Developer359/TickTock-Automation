import os
import json
import random
import glob

def attach_random_music(
    relative_json_path: str = "../Video-Data/video-content.json", 
    relative_music_dir: str = "../Video-Data/Music"
) -> None:
    # Resolve absolute paths relative to Video-Generate script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.abspath(os.path.join(script_dir, relative_json_path))
    music_dir = os.path.abspath(os.path.join(script_dir, relative_music_dir))

    # Ensure Music folder exists
    if not os.path.exists(music_dir):
        print(f"Error: Music folder not found at '{music_dir}'")
        return

    # Find all MP3 files in Video-Data/Music
    mp3_files = glob.glob(os.path.join(music_dir, "*.mp3"))

    if not mp3_files:
        print(f"No .mp3 files found in '{music_dir}'.")
        return

    # Pick a random MP3
    selected_file = random.choice(mp3_files)
    track_name = os.path.splitext(os.path.basename(selected_file))[0]
    normalized_path = os.path.abspath(selected_file).replace("\\", "/")

    # Read existing Video-Data/video-content.json
    data = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}

    # Attach/Update background music object
    data["bg_music"] = {
        "title": track_name,
        "file_path": normalized_path
    }

    # Save updated JSON file
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Selected Music: {track_name}")
    print(f"Updated {json_path} successfully.")

if __name__ == "__main__":
    attach_random_music()