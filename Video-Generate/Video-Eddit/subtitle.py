import os
import subprocess
import imageio_ffmpeg
import sys

sys.stdout.reconfigure(encoding='utf-8')
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))

INPUT_VIDEO = os.path.join(PROJECT_ROOT, "Output", "final_tiktok_edit.mp4")
FINAL_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "Final-Video")
os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)

OUTPUT_VIDEO = os.path.join(FINAL_OUTPUT_DIR, "final_tiktok_subtitled.mp4")
TEMP_ASS = os.path.join(FINAL_OUTPUT_DIR, "temp_subs.ass")

# Precise timed subtitle blocks: (Start_Seconds, End_Seconds, Text)
# This guarantees 100% manual sync with your voiceover audio.
SUBTITLE_TIMINGS = [
    (0.0,  1.8,  "Wake up!"),
    (1.8,  4.2,  "You are standing right on the edge of greatness,"),
    (4.2,  7.5,  "but you are letting comfort destroy your future!"),
    (7.5,  10.5, "Choose right now, are you going to fold like paper,"),
    (10.5, 13.8, "or are you going to stand up and fight for your life?"),
    (13.8, 16.5, "It is time to run and work!"),
    (16.5, 20.0, "You can do it! You are a champion!")
]

def generate_minimal_white_ass(timings, output_path):
    # Professional Minimalist ASS Template:
    # - Clean White Text (&H00FFFFFF)
    # - Smaller Font Size (48) for that sleek look
    # - Subtle Outline/Shadow so it remains readable
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass_lines = [ass_header]
    
    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int(round((seconds - int(seconds)) * 100))
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    for start_sec, end_sec, text in timings:
        start_time = format_time(start_sec)
        end_time = format_time(end_sec)
        
        # \fad(120,120) for smooth minimal fade transitions
        # \pos(360,780) places it cleanly in the lower-middle section
        animated_text = f"{{\\fad(120,120)\\pos(360,780)\\b1}}{text}"
        
        ass_lines.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{animated_text}")
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ass_lines))

def add_subtitles():
    if not os.path.exists(INPUT_VIDEO):
        print(f"Error: Input video not found at {INPUT_VIDEO}")
        return

    print("🎨 Generating clean minimal white subtitles...")
    generate_minimal_white_ass(SUBTITLE_TIMINGS, TEMP_ASS)
    
    print("🎞️ Burning subtitles into video via FFmpeg...")
    cmd = [
        FFMPEG, "-y",
        "-i", INPUT_VIDEO,
        "-vf", "subtitles=temp_subs.ass",
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "final_tiktok_subtitled.mp4"
    ]
    
    subprocess.run(cmd, check=True, cwd=FINAL_OUTPUT_DIR)
    
    if os.path.exists(TEMP_ASS):
        os.remove(TEMP_ASS)
        
    print(f"✨ Subtitled video ready at: {OUTPUT_VIDEO}")

if __name__ == "__main__":
    add_subtitles()