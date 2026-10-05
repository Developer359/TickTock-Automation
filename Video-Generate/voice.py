import os
import requests
from dotenv import load_dotenv

# Load environment variables from the root .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../Video-Data/Voiceovers"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Pulls FISH_API_KEY securely from your .env file
FISH_API_KEY = os.getenv("FISH_API_KEY")

# Voice Model ID for "Commanding Male Motivator"
REFERENCE_ID = "01b443ee064347eda7bb83feb923226d"

MOTIVATIONAL_PROMPT = (
    "Wake up! You are standing right on the edge of greatness, "
    "but you are letting comfort destroy your future! Choose right now! "
    "Are you going to fold like paper, or are you going to stand up and fight for your life? "
    "It is time to run and work! You can do it! You are a champion! You are a warrior! You are a conqueror! "
)

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "fishaudio_intense_quote.mp3")

def generate_voiceover():
    if not FISH_API_KEY:
        print("Error: FISH_API_KEY not found in environment variables or .env file.")
        return

    url = "https://api.fish.audio/v1/tts"
    
    headers = {
        "Authorization": f"Bearer {FISH_API_KEY}",
        "Content-Type": "application/json",
        "model": "s2.1-pro-free"
    }
    
    payload = {
        "text": MOTIVATIONAL_PROMPT,
        "reference_id": REFERENCE_ID,
        "format": "mp3"
    }

    print("Generating voiceover via Fish Audio (s2.1-pro-free)...")
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        with open(OUTPUT_FILE, "wb") as f:
            f.write(response.content)
        print(f"✓ Saved successfully: {OUTPUT_FILE}")
    else:
        print(f"Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    generate_voiceover()