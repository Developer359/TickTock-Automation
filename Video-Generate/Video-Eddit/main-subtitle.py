"""
main-subtitle.py
────────────────
Pipeline orchestrator for the Video-Eddit stage.

Runs the two editing steps in strict order:

  STEP 1 ─ trim.py     →  assemble raw video (voice + music + background)
                           and save to  Output/
  STEP 2 ─ subtitle.py →  burn animated subtitles into every video in Output/
                           and save to  Final-Video/

The script exits immediately with code 1 if any step fails.
"""

import sys
import time
import os

# ── Make sure sibling modules resolve correctly ────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import trim     as trim_mod
import subtitle as subtitle_mod


# ── Helpers ───────────────────────────────────────────────────────────────────

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


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main() -> None:
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║      TickTock Automation — Video-Eddit Pipeline          ║")
    print("╚══════════════════════════════════════════════════════════╝")

    steps = [
        (1, "Trim & Assemble Videos   →  Output/",      trim_mod.run_batch),
        (2, "Burn Subtitles           →  Final-Video/", subtitle_mod.main),
    ]

    for number, title, fn in steps:
        try:
            run_step(number, title, fn)
        except SystemExit as exc:
            # Propagate intentional exits (e.g. from trim.py error handling)
            code = exc.code if exc.code is not None else 1
            print(f"\n✗ Pipeline stopped at Step {number} ({title})")
            print(f"  Process exited with code {code}")
            sys.exit(int(code))
        except Exception as exc:
            print(f"\n✗ Pipeline stopped at Step {number} ({title})")
            print(f"  Error: {exc}")
            sys.exit(1)

    print("╔══════════════════════════════════════════════════════════╗")
    print("║         ✓  Both steps completed successfully!            ║")
    print("║         📁  Final videos are in  Final-Video/            ║")
    print("╚══════════════════════════════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
