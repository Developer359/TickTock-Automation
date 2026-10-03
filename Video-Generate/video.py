import os
import json
import random
import glob

def attach_random_single_bg_video(
    relative_json_path: str = "../Video-Data/video-content.json",
    relative_videos_dir: str = "../Video-Data/Videos"
) -> None:
    # Resolve absolute paths relative to Video-Generate script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.abspath(os.path.join(script_dir, relative_json_path))
    videos_dir = os.path.abspath(os.path.join(script_dir, relative_videos_dir))

    if not os.path.exists(videos_dir):
        print(f"Error: Videos directory not found at '{videos_dir}'")
        return

    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at '{json_path}'")
        return

    # Find all videos inside Video-Data/Videos/
    video_extensions = ("*.mp4", "*.mov", "*.mkv", "*.webm")
    local_videos = []
    
    for ext in video_extensions:
        local_videos.extend(glob.glob(os.path.join(videos_dir, ext)))
        local_videos.extend(glob.glob(os.path.join(videos_dir, "**", ext), recursive=True))

    local_videos = sorted(list(set(local_videos)))

    if not local_videos:
        print(f"No video files found in '{videos_dir}'. Please add .mp4 files.")
        return

    # Load existing video-content.json
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Clean up video_path from individual quotes if present
    quotes = data.get("quotes", [])
    for item in quotes:
        if "video_path" in item:
            del item["video_path"]

    # Remove bg_videos array if previously created
    if "bg_videos" in data:
        del data["bg_videos"]

    # Randomly pick ONE video from the folder
    selected_video = random.choice(local_videos)
    normalized_path = os.path.abspath(selected_video).replace("\\", "/")
    title = os.path.splitext(os.path.basename(selected_video))[0]

    # Store single chosen video under bg_video
    data["bg_video"] = {
        "title": title,
        "file_path": normalized_path
    }

    print(f"Randomly selected video: {title}")

    # Save updated JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Successfully updated 'bg_video' in: {json_path}")

if __name__ == "__main__":
    attach_random_single_bg_video()