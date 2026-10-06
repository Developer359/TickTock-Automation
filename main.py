"""
main.py
───────
Master pipeline orchestrator for TickTock Automation.

Runs ALL stages end-to-end in strict order:

  STAGE 1 ─ Video-Generate/main-video-data.py
             ├─ Step 1 · quotes.py   → generate motivational quotes
             ├─ Step 2 · voice.py    → generate voiceovers
             ├─ Step 3 · video.py    → select background videos
             └─ Step 4 · music.py    → select background music

  STAGE 2 ─ Video-Generate/Video-Eddit/main-subtitle.py
             ├─ Step 1 · trim.py     → assemble raw video  →  Output/
             └─ Step 2 · subtitle.py → burn subtitles      →  Final-Video/

  STAGE 3 ─ Video-Store/store_videos.py
             └─ Step 1 · store_videos.py → handle finalized videos

Stops immediately with exit code 1 if any stage fails.
"""

import sys
import time
import os
import subprocess

# ── Resolve paths ──────────────────────────────────────────────────────────────
ROOT_DIR         = os.path.dirname(os.path.abspath(__file__))
VIDEO_GENERATE   = os.path.join(ROOT_DIR, "Video-Generate")
VIDEO_EDDIT      = os.path.join(VIDEO_GENERATE, "Video-Eddit")

MAIN_VIDEO_DATA  = os.path.join(VIDEO_GENERATE, "main-video-data.py")
MAIN_SUBTITLE    = os.path.join(VIDEO_EDDIT,    "main-subtitle.py")
VIDEO_STORE      = os.path.join(ROOT_DIR, "Video-Store")
STORE_VIDEOS     = os.path.join(VIDEO_STORE, "store_videos.py")

PYTHON = sys.executable   # same Python interpreter that launched this script


# ── Helpers ───────────────────────────────────────────────────────────────────

def banner(text: str) -> None:
    width = 60
    pad   = (width - len(text) - 2) // 2
    print(f"\n╔{'═' * width}╗")
    print(f"║{' ' * pad}  {text}{' ' * (width - pad - len(text) - 2)}║")
    print(f"╚{'═' * width}╝\n")


def separator(title: str) -> None:
    line = "─" * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(f"{line}\n")


def run_stage(stage_number: int, title: str, script_path: str) -> None:
    """
    Spawn the given script in a subprocess using the current Python interpreter.
    Raises SystemExit(1) if the script returns a non-zero exit code.
    """
    separator(f"STAGE {stage_number}: {title}")

    if not os.path.exists(script_path):
        print(f"  ❌  Script not found: {script_path}")
        sys.exit(1)

    print(f"  ▶  Running: {script_path}\n")
    start = time.time()

    result = subprocess.run(
        [PYTHON, script_path],
        cwd=os.path.dirname(script_path),   # run from the script's own directory
    )

    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"\n✗ Stage {stage_number} FAILED ({title})")
        print(f"  Exit code  : {result.returncode}")
        print(f"  Time spent : {elapsed:.1f}s")
        sys.exit(1)

    print(f"\n✓ Stage {stage_number} completed in {elapsed:.1f}s\n")


# ── Master pipeline ───────────────────────────────────────────────────────────

def main() -> None:
    banner("TickTock Automation — Master Pipeline")

    stages = [
        (
            1,
            "Data Generation  (quotes → voice → video → music)",
            MAIN_VIDEO_DATA,
        ),
        (
            2,
            "Video Editing    (trim → subtitle burn-in)",
            MAIN_SUBTITLE,
        ),
        (
            3,
            "Video Storage    (store finalized videos)",
            STORE_VIDEOS,
        ),
    ]

    total_start = time.time()

    for number, title, script in stages:
        run_stage(number, title, script)

    total_elapsed = time.time() - total_start

    print("╔══════════════════════════════════════════════════════════╗")
    print("║        ✓  Full pipeline completed successfully!          ║")
    print(f"║        ⏱  Total time: {total_elapsed:.1f}s{' ' * (34 - len(f'{total_elapsed:.1f}'))}║")
    print("║        📁  Final videos are in  Final-Video/             ║")
    print("╚══════════════════════════════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
