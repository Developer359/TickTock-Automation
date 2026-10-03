import os
from elevenlabs.client import ElevenLabs
from elevenlabs.core import ApiError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../Video-Data/Voiceovers"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# George Voice ID
CLONED_VOICE_ID = "LcVcltBiweqv2E4ipKan"

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# 💡 Formatting: ALL CAPS + [shouts] + ALL EXCLAMATION MARKS
MOTIVATIONAL_PROMPT = (
    "[shouts at the top of his lungs, screaming violently] "
    "LISTEN TO ME!!! WAKE UP!!! "
    "YOU ARE STANDING RIGHT ON THE EDGE OF GREATNESS BUT YOU ARE LETTING COMFORT DESTROY YOUR FUTURE!!! "
    "[screaming in pure rage] CHOOSE RIGHT NOW!!! "
    "ARE YOU GOING TO FOLD LIKE PAPER OR ARE YOU GOING TO STAND UP AND FIGHT FOR YOUR LIFE!!! "
    "IT IS TIME TO RUN!!! IT IS TIME TO WORK!!! YOU CAN DO IT!!! GET UP AND PROVE THEM WRONG!!!"
)

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "elevenlabs_intense_quote.mp3")

def generate_intense_voiceover():
    print("Generating max-intensity screaming voiceover...")
    
    try:
        audio_stream = client.text_to_speech.convert(
            voice_id=CLONED_VOICE_ID,
            text=MOTIVATIONAL_PROMPT,
            model_id="eleven_v3",  # 👈 Switch to eleven_v3 for true emotion/screaming support
            voice_settings={
                "stability": 0.15,        # 👈 Lower stability forces high emotional volatility & vocal cracking
                "similarity_boost": 0.75,
                "style": 1.0,             # 👈 Max style exaggeration for raw delivery
                "use_speaker_boost": True
            }
        )

        with open(OUTPUT_FILE, "wb") as f:
            for chunk in audio_stream:
                if chunk:
                    f.write(chunk)

        print(f"✓ Audio generated: {OUTPUT_FILE}")

    except ApiError as e:
        print(f"Error details: {e.body}")

if __name__ == "__main__":
    generate_intense_voiceover()