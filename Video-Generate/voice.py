import os
import json
import requests
import re
from dotenv import load_dotenv

# Load environment variables from the root .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR  = os.path.abspath(os.path.join(SCRIPT_DIR, "../Video-Data/Voiceovers"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Eddit-data directory that quotes.py writes into
EDDIT_DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../Eddit-data"))

# All three per-category JSON files (order doesn't matter)
EDDIT_JSON_FILES = [
    os.path.join(EDDIT_DATA_DIR, "gym-video.json"),
    os.path.join(EDDIT_DATA_DIR, "mindset-video.json"),
    os.path.join(EDDIT_DATA_DIR, "hardwork-video.json"),
]

# Pulls FISH_API_KEY securely from your .env file
FISH_API_KEY = os.getenv("FISH_API_KEY")

# Voice Model ID for "Commanding Male Motivator"
REFERENCE_ID = "01b443ee064347eda7bb83feb923226d"

def sanitize_filename(name):
    # Remove any invalid characters for a filename
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    # Replace spaces with underscores
    name = name.replace(" ", "_").lower()
    return name

def generate_voiceovers():
    if not FISH_API_KEY:
        print("Error: FISH_API_KEY not found in environment variables or .env file.")
        return

    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {FISH_API_KEY}",
        "Content-Type": "application/json",
        "model": "s2.1-pro-free"
    }

    for json_path in EDDIT_JSON_FILES:
        if not os.path.exists(json_path) or os.path.getsize(json_path) == 0:
            print(f"[SKIP] {os.path.basename(json_path)} — not found or empty (run quotes.py first)")
            continue

        with open(json_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"[SKIP] {os.path.basename(json_path)} — invalid JSON")
                continue

        category = data.get("category", "Uncategorized")
        text     = data.get("quote", "")

        if not text:
            print(f"[SKIP] {os.path.basename(json_path)} — no quote text found")
            continue

        filename    = f"{sanitize_filename(category)}_audio.mp3"
        output_file = os.path.join(OUTPUT_DIR, filename)

        payload = {
            "text": text,
            "reference_id": REFERENCE_ID,
            "format": "mp3"
        }

        print(f"Generating voiceover for '{category}'...")
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)

            # Normalise path separators
            normalized_audio_path = output_file.replace("\\", "/")

            # Write the audio path back into the same Eddit-data JSON
            data["voice_path"] = normalized_audio_path
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            print(f"  ✓ Audio saved : {output_file}")
            print(f"  ✓ JSON updated: {os.path.basename(json_path)}")
        else:
            print(f"  ✗ Error {response.status_code} for '{category}': {response.text}")

if __name__ == "__main__":
    generate_voiceovers()