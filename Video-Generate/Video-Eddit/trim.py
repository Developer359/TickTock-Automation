import os
import subprocess
import json
import sys

# Fix Windows console encoding for emoji output
sys.stdout.reconfigure(encoding='utf-8')

import imageio_ffmpeg

# Use the ffmpeg bundled with moviepy (imageio-ffmpeg)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# Directories based on your project structure
# trim.py is at: TickTock-Automation/Video-Generate/Video-Eddit/trim.py
# Video-Data is at: TickTock-Automation/Video-Data/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))        # .../Video-Eddit
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))    # .../TickTock-Automation

VOICEOVER_PATH = os.path.join(PROJECT_ROOT, "Video-Data", "Voiceovers", "fishaudio_intense_quote.mp3")
MUSIC_DIR      = os.path.join(PROJECT_ROOT, "Video-Data", "Music")
VIDEO_DIR      = os.path.join(PROJECT_ROOT, "Video-Data", "Videos")
OUTPUT_DIR     = os.path.join(PROJECT_ROOT, "Output")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_duration(filepath):
    """Get audio duration using moviepy (ffprobe not bundled with imageio_ffmpeg)."""
    from moviepy import AudioFileClip
    clip = AudioFileClip(filepath)
    duration = clip.duration
    clip.close()
    return duration


def create_tiktok_edit():
    print("🎬 Starting video assembly...")

    # ── 1. Get voiceover duration ────────────────────────────────────────────
    if not os.path.exists(VOICEOVER_PATH):
        print(f"Error: Voiceover not found at {VOICEOVER_PATH}")
        return

    voice_duration = get_duration(VOICEOVER_PATH)
    target_duration = voice_duration + 1.0
    print(f"🎙️ Voiceover duration: {voice_duration:.2f}s | Target: {target_duration:.2f}s")

    # ── 2. Pick first available video & music ────────────────────────────────
    video_files = [f for f in os.listdir(VIDEO_DIR) if f.endswith(('.mp4', '.mov', '.mkv'))]
    music_files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(('.mp3', '.wav', '.m4a'))]

    if not video_files or not music_files:
        print("Error: Missing video or music files in directories.")
        return

    video_path = os.path.join(VIDEO_DIR, video_files[0])
    music_path = os.path.join(MUSIC_DIR, music_files[0])
    output_file = os.path.join(OUTPUT_DIR, "final_tiktok_edit.mp4")

    print(f"📹 Video: {video_files[0]}")
    print(f"🎵 Music: {music_files[0]}")

    # ── 3. Build & run single ffmpeg command ─────────────────────────────────
    # Everything in ONE pass:
    #   input 0 = video (looped with -stream_loop)
    #   input 1 = voiceover mp3
    #   input 2 = background music (looped with -stream_loop)
    #
    # Filter graph:
    #   - Strip original video audio (use only inputs 1 & 2 for audio)
    #   - Delay voiceover by 0.2s
    #   - Duck music to 12% volume
    #   - Mix voice + music together (normalize=0 to prevent auto-quieting)
    #   - Trim everything to target_duration

    filter_complex = (
        # Voiceover: delay 200ms, keep full volume
        "[1:a] adelay=200|200, volume=1.0 [voice]; "
        # Music: duck to 12% volume
        "[2:a] volume=0.12 [music]; "
        # Mix them together — normalize=0 prevents ffmpeg from halving volume
        "[voice][music] amix=inputs=2:duration=longest:normalize=0 [aout]"
    )

    cmd = [
        FFMPEG, "-y",
        # Input 0: video, looped infinitely so it covers target_duration
        "-stream_loop", "-1",
        "-i", video_path,
        # Input 1: voiceover (plays once)
        "-i", VOICEOVER_PATH,
        # Input 2: music, looped infinitely
        "-stream_loop", "-1",
        "-i", music_path,
        # Filter graph for audio mixing
        "-filter_complex", filter_complex,
        # Map: video from input 0, audio from filter output
        "-map", "0:v",
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

    print(f"💾 Rendering final video to {output_file}...")
    print("⏳ This may take a moment...")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ FFmpeg error:\n{result.stderr}")
        return

    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"✨ Video editing completed! → {output_file} ({file_size:.1f} MB)")


if __name__ == "__main__":
    create_tiktok_edit()