"""
main-video-data.py
──────────────────
Pipeline orchestrator — runs the three data-generation steps in order:

  1. quotes.py  →  generate 3 motivational quotes & save to Eddit-data JSON files
  2. voice.py   →  generate voiceovers & save audio paths into Eddit-data JSON files
  3. video.py   →  pick a strict-random background video per category & save to Eddit-data JSON files

Stop immediately if any step raises an exception.
"""

import sys
import time

# ── Make sure imports resolve correctly regardless of how this script is run ──
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import quotes as quotes_mod
import voice  as voice_mod
import video  as video_mod


def separator(title: str) -> None:
    line = "─" * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(f"{line}\n")


def run_step(step_number: int, title: str, fn) -> None:
    separator(f"STEP {step_number}: {title}")
    start = time.time()
    fn()
    elapsed = time.time() - start
    print(f"\n✓ Step {step_number} completed in {elapsed:.1f}s\n")


def main() -> None:
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║         TickTock Automation — Video Data Pipeline        ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # ── Step 1: Generate quotes ───────────────────────────────────────────
    def step_quotes():
        print("[*] Generating 3 motivational quotes (Gym / Mindset / Hardwork)...")
        data = quotes_mod.generate_quotes()
        quotes_mod.save_to_json(data)

    # ── Step 2: Generate voiceovers ───────────────────────────────────────
    def step_voice():
        voice_mod.generate_voiceovers()

    # ── Step 3: Pick background videos ───────────────────────────────────
    def step_video():
        print("[*] Attaching background videos (strict random per category)...\n")
        video_mod.attach_videos()

    steps = [
        (1, "Generate Quotes  →  Eddit-data JSON",        step_quotes),
        (2, "Generate Voiceovers  →  Eddit-data JSON",    step_voice),
        (3, "Select Background Videos  →  Eddit-data JSON", step_video),
    ]

    for number, title, fn in steps:
        try:
            run_step(number, title, fn)
        except Exception as exc:
            print(f"\n✗ Pipeline stopped at Step {number} ({title})")
            print(f"  Error: {exc}")
            sys.exit(1)

    print("╔══════════════════════════════════════════════════════════╗")
    print("║           ✓  All 3 steps completed successfully!         ║")
    print("╚══════════════════════════════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
