import os
import json
import subprocess
import sys

# Fix Windows console encoding for emoji output
sys.stdout.reconfigure(encoding='utf-8')

import imageio_ffmpeg

# Use the ffmpeg bundled with moviepy (imageio-ffmpeg)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))      # .../Video-Eddit
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))      # .../TickTock-Automation

EDDIT_DATA_DIR = os.path.join(PROJECT_ROOT, "Eddit-data")
OUTPUT_DIR     = os.path.join(PROJECT_ROOT, "Output")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_duration(filepath):
    """Get audio duration using moviepy (ffprobe not bundled with imageio_ffmpeg)."""
    from moviepy import AudioFileClip
    clip = AudioFileClip(filepath)
    duration = clip.duration
    clip.close()
    return duration


def create_tiktok_edit(voice_path, music_path, video_path, output_file):
    """
    Exact same ffmpeg logic as trim.py — nothing changed.
    Inputs are passed in instead of being read from fixed directories.
    """
    print("🎬 Starting video assembly...")

    # ── 1. Get voiceover duration ────────────────────────────────────────────
    if not os.path.exists(voice_path):
        print(f"  ❌ Voiceover not found: {voice_path}")
        return False

    if not os.path.exists(music_path):
        print(f"  ❌ Music not found: {music_path}")
        return False

    if not os.path.exists(video_path):
        print(f"  ❌ Video not found: {video_path}")
        return False

    voice_duration  = get_duration(voice_path)
    target_duration = voice_duration + 1.0
    print(f"  🎙️  Voiceover duration: {voice_duration:.2f}s | Target: {target_duration:.2f}s")
    print(f"  📹  Video : {os.path.basename(video_path)}")
    print(f"  🎵  Music : {os.path.basename(music_path)}")


    filter_complex = (
        # Scale and crop the video to exactly 1080x1920 (9:16) for TikTok
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[vout]; "
        # Voiceover: delay 200ms, keep full volume
        "[1:a] adelay=200|200, volume=1.0 [voice]; "
        # Music: duck to 10% volume
        "[2:a] volume=0.10 [music]; "
        # Mix them together — normalize=0 prevents ffmpeg from halving volume
        "[voice][music] amix=inputs=2:duration=longest:normalize=0 [aout]"
    )

    cmd = [
        FFMPEG, "-y",
        # Input 0: video, looped infinitely so it covers target_duration
        "-stream_loop", "-1",
        "-i", video_path,
        # Input 1: voiceover (plays once)
        "-i", voice_path,
        # Input 2: music, looped infinitely
        "-stream_loop", "-1",
        "-i", music_path,
        # Filter graph for video scaling/cropping and audio mixing
        "-filter_complex", filter_complex,
        # Map: video from filter output, audio from filter output
        "-map", "[vout]",
        "-map", "[aout]",
        # Video encoding
        "-c:v", "libx264",
        "-preset", "medium",
        "-b:v", "4000k",
        "-r", "30",
        # Audio encoding
        "-c:a", "aac",
        "-ac", "2",
        "-b:a", "192k",
        "-ar", "44100",
        # Limit total duration
        "-t", str(target_duration),
        # Output
        output_file
    ]

    print(f"  💾  Rendering → {output_file} ...")
    print("  ⏳  This may take a moment...")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ❌  FFmpeg error:\n{result.stderr}")
        return False

    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"  ✨  Done! → {output_file} ({file_size:.1f} MB)")
    return True


# ── Main batch loop ───────────────────────────────────────────────────────────

def run_batch():
    # Collect & sort JSON files so processing order is deterministic
    json_files = sorted(
        f for f in os.listdir(EDDIT_DATA_DIR) if f.endswith(".json")
    )

    if not json_files:
        print("❌ No JSON files found in Eddit-data/")
        return

    total   = len(json_files)
    success = 0
    failed  = 0

    print(f"📂 Found {total} JSON file(s) in {EDDIT_DATA_DIR}")
    print("=" * 60)

    for idx, json_file in enumerate(json_files, start=1):
        json_path = os.path.join(EDDIT_DATA_DIR, json_file)
        stem      = os.path.splitext(json_file)[0]          # e.g. "gym-video"
        output_file = os.path.join(OUTPUT_DIR, f"{stem}.mp4")

        print(f"\n[{idx}/{total}] Processing: {json_file}")
        print("-" * 50)

        # Load JSON
        try:
            with open(json_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as e:
            print(f"  ❌  Failed to read JSON: {e}")
            failed += 1
            continue

        # Extract required fields
        voice_path = data.get("voice_path", "")
        music_path = data.get("bg_music", {}).get("file_path", "")
        video_path = data.get("bg_video", {}).get("file_path", "")

        if not voice_path or not music_path or not video_path:
            print(f"  ❌  Missing required fields in {json_file}. Skipping.")
            failed += 1
            continue

        # Run the exact trim logic
        ok = create_tiktok_edit(
            voice_path  = voice_path,
            music_path  = music_path,
            video_path  = video_path,
            output_file = output_file,
        )

        if ok:
            success += 1
        else:
            failed += 1

        print("-" * 50)

    print("\n" + "=" * 60)
    print(f"🏁 Batch complete — ✅ {success} succeeded  |  ❌ {failed} failed")
    print(f"📁 Output folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    run_batch()
