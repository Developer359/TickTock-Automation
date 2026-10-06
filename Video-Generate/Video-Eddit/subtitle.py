import os
import re
import sys
import json
import subprocess

import imageio_ffmpeg

# ─────────────────────────────────────────────
#  Encoding fix for Windows terminals
# ─────────────────────────────────────────────
sys.stdout.reconfigure(encoding="utf-8")

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# ─────────────────────────────────────────────
#  Project Paths  (auto-detected)
# ─────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))          # …/Video-Eddit/
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))          # …/TickTock-Automation/

OUTPUT_DIR       = os.path.join(PROJECT_ROOT, "Output")
EDDIT_DATA_DIR   = os.path.join(PROJECT_ROOT, "Eddit-data")
FINAL_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "Final-Video")

os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────
#  ASS Color Constants  (ASS = BGR hex)
# ─────────────────────────────────────────────
COLOR_WHITE     = "&H00E5E5E5"   # soft white   — base text
COLOR_RED       = "&H000000FF"   # vivid red    — primary power-word highlight
COLOR_YELLOW    = "&H0000EFFF"   # electric yellow — secondary accent

# ─────────────────────────────────────────────
#  Keyword → highlight color maps
# ─────────────────────────────────────────────
PRIMARY_KEYWORDS = {
    "wake","up","stop","now","fight","rise","break","destroy",
    "fear","weak","dead","die","pain","suffer","fail","lose",
    "quit","excuses","comfort","trap","wasted","scared","late",
    "criminal","mindset","power","win","champion","warrior",
    "hustle","grind","hunger","fire","god","elite","king",
    "never","don't","failed","hurts","price","loss","lesson",
}

SECONDARY_KEYWORDS = {
    "work","run","build","stand","push","move","act","do",
    "start","go","change","grow","learn","create","earn",
    "believe","dream","achieve","succeed","focus","discipline",
    "heart","soul","life","future","purpose","greatness","forward",
    "winning","paid","use","move","quit","can",
}

# ─────────────────────────────────────────────
#  Emoji injection map
# ─────────────────────────────────────────────
EMOJI_MAP = {
    "fire":     "🔥",
    "grow":     "📈",
    "growth":   "📈",
    "forward":  "📈",
    "die":      "💀",
    "dead":     "💀",
    "champion": "🏆",
    "king":     "👑",
    "elite":    "🗿",
    "mindset":  "🗿",
    "warrior":  "⚔️",
    "wake":     "⚡",
    "hustle":   "💪",
    "grind":    "💪",
    "can":      "💪",
    "money":    "💰",
    "earn":     "💰",
    "heart":    "❤️",
    "dream":    "✨",
    "pain":     "😤",
    "hurts":    "😤",
    "lesson":   "📖",
}


# ══════════════════════════════════════════════════════════════════════════════
#  AUDIO ANALYSIS — Perfect Sync via Silence Detection
# ══════════════════════════════════════════════════════════════════════════════

def get_audio_duration(audio_path: str) -> float:
    """Return total duration of an audio file in seconds."""
    cmd    = [FFMPEG, "-i", audio_path]
    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    match  = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr)
    if match:
        h, m, s = match.groups()
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 15.0


def detect_speech_segments(audio_path: str,
                            noise_db: float = -35.0,
                            min_silence_dur: float = 0.25) -> list:
    """
    Run FFmpeg silencedetect on the voiceover audio and return a list of
    speech segment tuples:  [(start_sec, end_sec), ...]

    noise_db          : silence threshold in dB  (louder = more segments)
    min_silence_dur   : minimum pause to count as silence gap (seconds)

    The segments returned are the *non-silent* (spoken) regions.
    """
    cmd = [
        FFMPEG, "-i", audio_path,
        "-af", f"silencedetect=noise={noise_db}dB:d={min_silence_dur}",
        "-f", "null", "-",
    ]
    result = subprocess.run(
        cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8"
    )
    output = result.stderr

    total_duration = get_audio_duration(audio_path)

    # Parse silence boundaries
    silence_starts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", output)]
    silence_ends   = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)",   output)]

    # Build speech segments from the gaps between silences
    speech_segments = []
    speech_start    = 0.0

    for s_start, s_end in zip(silence_starts, silence_ends):
        if s_start > speech_start + 0.05:         # meaningful gap
            speech_segments.append((speech_start, s_start))
        speech_start = s_end

    # Trailing speech after last silence
    if speech_start < total_duration - 0.1:
        speech_segments.append((speech_start, total_duration))

    # If nothing detected (constant speech), fall back to whole duration
    if not speech_segments:
        speech_segments = [(0.0, total_duration)]

    return speech_segments


def merge_short_segments(segments: list, min_dur: float = 0.8) -> list:
    """
    Merge adjacent speech segments that are shorter than min_dur seconds
    into the next segment so every subtitle block has reasonable screen time.
    """
    if not segments:
        return segments

    merged = [list(segments[0])]
    for start, end in segments[1:]:
        dur = merged[-1][1] - merged[-1][0]
        if dur < min_dur:
            merged[-1][1] = end       # extend previous
        else:
            merged.append([start, end])

    return [(s, e) for s, e in merged]


# ══════════════════════════════════════════════════════════════════════════════
#  QUOTE CHUNKING — Map words → speech segments
# ══════════════════════════════════════════════════════════════════════════════

def map_time_to_real_audio(t_speech: float, segments: list) -> float:
    """Map a time offset within the concatenated speech back to real audio timestamps."""
    accum = 0.0
    for s, e in segments:
        dur = e - s
        if t_speech <= accum + dur:
            return s + (t_speech - accum)
        accum += dur
    return segments[-1][1] if segments else 0.0


def split_quote_proportionally(quote: str, segments: list, words_per_chunk: int = 4) -> list:
    """
    Distribute words proportionally across the detected speech segments based on character count.
    Returns: list of (t_start, t_end, chunk_text)
    """
    words = quote.split()
    total_chars = sum(len(w) for w in words)
    total_speech_time = sum(e - s for s, e in segments) if segments else 0.0

    word_timings = []
    current_speech_time = 0.0

    # 1. Map every word to a start/end time in the real audio
    for word in words:
        char_len = len(word)
        ratio = char_len / total_chars if total_chars > 0 else 0
        word_duration = ratio * total_speech_time
        
        start_t = map_time_to_real_audio(current_speech_time, segments)
        current_speech_time += word_duration
        end_t = map_time_to_real_audio(current_speech_time, segments)
        
        word_timings.append({"word": word, "start": start_t, "end": end_t})

    # 2. Group words into chunks
    timings = []
    for i in range(0, len(word_timings), words_per_chunk):
        chunk_words = word_timings[i : i + words_per_chunk]
        chunk_str = " ".join(cw["word"] for cw in chunk_words)
        
        # Determine chunk boundaries
        t_start = chunk_words[0]["start"]
        t_end   = chunk_words[-1]["end"]
        timings.append((t_start, t_end, chunk_str))

    return timings


# ══════════════════════════════════════════════════════════════════════════════
#  ASS FILE GENERATION — Viral Aesthetic Style
# ══════════════════════════════════════════════════════════════════════════════

def format_time(seconds: float) -> str:
    """Float seconds → ASS timestamp string  H:MM:SS.cs"""
    seconds = max(0.0, seconds)
    h   = int(seconds // 3600)
    m   = int((seconds % 3600) // 60)
    s   = int(seconds % 60)
    cs  = min(int(round((seconds - int(seconds)) * 100)), 99)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def colorize_word(word: str) -> str:
    """Apply ASS inline color override tags to a single word."""
    clean  = re.sub(r"[^a-zA-Z0-9']", "", word).lower()
    emoji  = EMOJI_MAP.get(clean, "")

    if clean in PRIMARY_KEYWORDS:
        styled = f"{{\\c{COLOR_RED}&\\b1}}{word}{{\\c{COLOR_WHITE}&\\b0}}"
    elif clean in SECONDARY_KEYWORDS:
        styled = f"{{\\c{COLOR_YELLOW}&}}{word}{{\\c{COLOR_WHITE}&}}"
    else:
        styled = word

    return styled + (" " + emoji if emoji else "")


def build_ass_text(raw_text: str) -> str:
    """
    Colorize all words then auto-wrap into lines of MAX 4 words each,
    capped at 3 lines so text never touches screen borders on 720px canvas.
    Original \\n splits are ignored — we re-wrap from scratch.
    """
    MAX_WORDS_PER_LINE = 4
    MAX_LINES          = 3

    # Flatten all words from any existing line breaks
    all_words = []
    for segment in raw_text.split("\n"):
        all_words.extend(segment.split())

    # Colorize each word
    colored = [colorize_word(w) for w in all_words]

    # Chunk into lines of MAX_WORDS_PER_LINE
    lines = [
        " ".join(colored[i : i + MAX_WORDS_PER_LINE])
        for i in range(0, len(colored), MAX_WORDS_PER_LINE)
    ]

    # If we exceed MAX_LINES, merge the overflow into the last allowed line
    if len(lines) > MAX_LINES:
        overflow_words = colored[MAX_WORDS_PER_LINE * (MAX_LINES - 1) :]
        lines = lines[: MAX_LINES - 1] + [" ".join(overflow_words)]

    return r"\N".join(lines)


def generate_ass_file(timings: list, output_path: str) -> None:
    """
    Write a complete .ass file from a list of (start_sec, end_sec, text) tuples.
    Style: viral TikTok aesthetic — centered lower-third, fade, multi-color.
    """
    ass_header = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,42,&H00E5E5E5,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0.5,0,1,2.5,1.2,5,30,30,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [ass_header]

    for start_sec, end_sec, raw_text in timings:
        start_ts   = format_time(start_sec)
        end_ts     = format_time(end_sec)
        styled_body = build_ass_text(raw_text)

        # \fad(120,80)  → 120 ms fade-in, 80 ms fade-out
        # \pos(360,750) → horizontally centered, lower-middle position
        # \an5          → center-aligned anchor
        prefix    = r"{\fad(120,80)\pos(360,750)\an5}"
        full_text = prefix + styled_body

        lines.append(
            f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{full_text}"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"    ✅ ASS file written  ({len(timings)} subtitle events)")


# ══════════════════════════════════════════════════════════════════════════════
#  FFMPEG BURN-IN
# ══════════════════════════════════════════════════════════════════════════════

def burn_subtitles(input_video: str, output_video: str, ass_path: str) -> None:
    """Burn .ass file into video via FFmpeg using libass renderer."""
    out_dir = os.path.dirname(output_video)
    os.makedirs(out_dir, exist_ok=True)

    # Forward-slash + escape colon for Windows path inside filtergraph
    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

    cmd = [
        FFMPEG, "-y",
        "-i", input_video,
        "-vf", f"ass='{ass_escaped}'",
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf",    "18",
        "-pix_fmt","yuv420p",
        output_video,
    ]

    print("    🎞️  Burning subtitles with FFmpeg ...")
    subprocess.run(cmd, check=True)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN BATCH PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def process_video(video_filename: str) -> None:
    """
    Full pipeline for a single video:
      1. Load matching JSON → quote + voice_path
      2. Run silencedetect on the voiceover → real speech timestamps
      3. Split quote into chunks matching speech segments
      4. Generate .ass file with viral aesthetic styling
      5. Burn subtitles into video → save to Final-Video/
    """
    base_name  = os.path.splitext(video_filename)[0]
    json_path  = os.path.join(EDDIT_DATA_DIR, f"{base_name}.json")

    if not os.path.exists(json_path):
        print(f"  ⚠️  No JSON found for {video_filename} — skipping.")
        return

    # ── Load JSON ────────────────────────────────────────────────────────────
    with open(json_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"  ❌  JSON parse error ({json_path}): {e}")
            return

    quote      = data.get("quote", "").strip()
    voice_path = data.get("voice_path", "").strip()

    if not quote:
        print(f"  ⚠️  Empty quote in {json_path} — skipping.")
        return

    input_video  = os.path.join(OUTPUT_DIR,       video_filename)
    output_video = os.path.join(FINAL_OUTPUT_DIR,  video_filename)
    temp_ass     = os.path.join(FINAL_OUTPUT_DIR, f"{base_name}_temp.ass")

    print(f"\n🎬  {video_filename}")
    print(f"    Quote   : {quote[:70]}{'...' if len(quote) > 70 else ''}")

    # ── Detect speech segments from voiceover audio ───────────────────────────
    if voice_path and os.path.exists(voice_path):
        print(f"    Audio   : {os.path.basename(voice_path)}")
        print("    🔊  Running silence detection on voiceover ...")

        segments = detect_speech_segments(voice_path, noise_db=-35.0, min_silence_dur=0.25)
        segments = merge_short_segments(segments, min_dur=0.8)

        print(f"    📊  Detected {len(segments)} speech segment(s)")
        num_chunks = len(segments)

    else:
        print("    ⚠️  voice_path not found — falling back to even time split.")
        # Fallback: even split over video duration
        from_ffmpeg = [FFMPEG, "-i", input_video]
        res   = subprocess.run(from_ffmpeg, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
        total = int(match.group(1))*3600 + int(match.group(2))*60 + float(match.group(3)) if match else 15.0
        # Simple 8-chunk even fallback
        num_chunks  = 8
        step        = total / num_chunks
        segments    = [(i * step, (i + 1) * step) for i in range(num_chunks)]

    # ── Map text perfectly to speech timestamps ──────────────────────────────
    raw_timings = split_quote_proportionally(quote, segments, words_per_chunk=4)

    # ── Build final timed subtitle list (apply voice delay) ───────────────────
    # We must add 0.20s because trim.py applies `adelay=200|200` to the voice!
    # Pad each subtitle: start 40 ms early, end 80 ms late → feels snappy
    VOICE_DELAY = 0.20
    PAD_START   = 0.04
    PAD_END     = 0.08

    timings = []
    for t_start, t_end, chunk in raw_timings:
        final_start = max(0.0, t_start + VOICE_DELAY - PAD_START)
        final_end   = t_end + VOICE_DELAY + PAD_END
        timings.append((final_start, final_end, chunk))

    # ── Generate ASS + burn ───────────────────────────────────────────────────
    generate_ass_file(timings, temp_ass)
    burn_subtitles(input_video, output_video, temp_ass)

    # Cleanup temp ASS
    if os.path.exists(temp_ass):
        os.remove(temp_ass)

    print(f"    ✨  Saved → {output_video}")


def main() -> None:
    if not os.path.exists(OUTPUT_DIR):
        print(f"❌  Output directory not found: {OUTPUT_DIR}")
        return

    videos = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".mp4")]
    if not videos:
        print("❌  No .mp4 files found in Output/")
        return

    print(f"📂  Found {len(videos)} video(s) to process\n")

    for video_filename in sorted(videos):
        try:
            process_video(video_filename)
        except subprocess.CalledProcessError as e:
            print(f"  ❌  FFmpeg error on {video_filename}: {e}")
        except Exception as e:
            print(f"  ❌  Unexpected error on {video_filename}: {e}")

    print("\n🎉  All videos processed! Check Final-Video/")


if __name__ == "__main__":
    main()