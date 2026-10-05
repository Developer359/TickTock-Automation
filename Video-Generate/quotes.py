import os
import sys
import json
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# Initialize client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Define Structured Schema
class QuoteItem(BaseModel):
    id: int
    quote: str = Field(description="A powerful, short motivational quote that fits within 20 seconds when spoken aloud (max 40 words).")
    hook: str = Field(description="A 3-5 word high-impact opening line to instantly hook the viewer on TikTok.")
    category: str = Field(description="The category of the quote: 'Gym Motivation', 'Mindset & Psychology', or 'Hardwork & Self-Belief'.")
    search_keyword: str = Field(
        description="Exactly ONE single, highly specific 2-3 word search query for downloading the perfect aesthetic video background (e.g., 'dark gym motivation', 'night city drive', 'lone wolf aesthetic')."
    )

class QuotesContainer(BaseModel):
    quotes: list[QuoteItem]

SYSTEM_PROMPT = """
You are an elite master of human psychology and raw, relatable motivation.

Your ONLY job is to generate 3 quotes — one for each category:
1. GYM MOTIVATION - For people who want to quit, push harder, and break their physical limits.
2. MINDSET & PSYCHOLOGY - Profound psychological truths about self-awareness, letting go, and mental fortitude.
3. HARDWORK & SELF-BELIEF - For people grinding silently, facing doubt, and needing absolute confidence.

STRICT RULES for every quote:
1. NO CLICHÉS: Do NOT use ordinary, overused, or cheesy quotes. Every quote must be highly original, professional, and profound. 
2. DEEPLY RELATABLE: The quote must make the viewer instantly feel understood. It should touch the soul and make them say, "This is exactly how I feel."
3. EASY TO UNDERSTAND: Even though it is profound, the wording must be extremely simple and clear. No complicated metaphors.
4. MAX 40 WORDS: Must be short enough to speak aloud in under 20 seconds. 
5. END WITH POWER: Every quote must end on a commanding, uplifting, and unstoppable note that forces action.
6. PERFECT SEARCH KEYWORD: For `search_keyword`, output EXACTLY ONE ultra-focused 2-3 word query for Pinterest vertical video backgrounds (e.g., 'dark gym motivation', 'night drive aesthetic').

Examples of the exact tone (Profound, Simple, Relatable, Professional):
- "You're not exhausted from working hard. You're exhausted from holding on to the person you used to be. Let them go. Step into who you are now."
- "The people who don't understand your grind will never understand your success. Keep your head down. Let your results introduce you."
- "Pain is just weakness leaving your body. Every time you want to stop, remember why you started. Push."

Generate exactly 3 quotes, one per category.
"""

def generate_quotes() -> dict:
    prompt = """Generate exactly 3 motivational quotes — one per category:
1. Gym Motivation (for people who work out and want to push harder)
2. Mindset & Psychology (deep truth about human psychology and mental strength)
3. Hardwork & Self-Belief (for people grinding silently and doubting themselves)

Each quote must be under 40 words, commanding, simple, and deeply motivating.
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=QuotesContainer,
            temperature=0.9,
        ),
    )

    # Parse returned structured JSON string into dictionary
    data = json.loads(response.text)
    return data


def save_to_json(data: dict) -> None:
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "Video-Data",
        "video-content.json"
    )

    # Load existing content so we preserve bg_music and bg_video keys
    existing = {}
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = {}

    # Only update the quotes section
    existing["quotes"] = data.get("quotes", [])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4, ensure_ascii=False)

    print(f"[OK] Successfully generated and saved {len(existing['quotes'])} quotes to:")
    print(f"   {output_path}")
    print()
    for q in existing["quotes"]:
        print(f"  [{q['category']}]")
        print(f"  Hook: {q['hook']}")
        print(f"  Quote: {q['quote']}")
        print()


if __name__ == "__main__":
    print("[*] Generating 3 motivational quotes (Gym / Mindset / Hardwork)...")
    quotes_data = generate_quotes()
    save_to_json(quotes_data)