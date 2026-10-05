import os
import json
import requests
import re
from dotenv import load_dotenv

# Load environment variables from the root .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../Video-Data/Voiceovers"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

CONTENT_JSON_PATH = os.path.join(SCRIPT_DIR, "../Video-Data/video-content.json")

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

    if not os.path.exists(CONTENT_JSON_PATH):
        print(f"Error: {CONTENT_JSON_PATH} not found. Please run quotes.py first.")
        return

    with open(CONTENT_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    quotes = data.get("quotes", [])
    if not quotes:
        print("No quotes found in video-content.json")
        return

    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {FISH_API_KEY}",
        "Content-Type": "application/json",
        "model": "s2.1-pro-free"
    }

    for quote_item in quotes:
        category = quote_item.get("category", "Uncategorized")
        text = quote_item.get("quote", "")
        
        if not text:
            continue

        filename = f"{sanitize_filename(category)}_audio.mp3"
        output_file = os.path.join(OUTPUT_DIR, filename)

        payload = {
            "text": text,
            "reference_id": REFERENCE_ID,
            "format": "mp3"
        }

        print(f"Generating voiceover for category '{category}'...")
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            print(f"✓ Saved successfully: {output_file}")
        else:
            print(f"Error {response.status_code} for '{category}': {response.text}")

if __name__ == "__main__":
    generate_voiceovers()