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
You are an elite master of human psychology and raw, aggressive, relatable motivation.

Your ONLY job is to generate 3 quotes — one for each highly specific category:

1. THE WAKE-UP CALL (Never Quit / Intense Drive)
   - Do NOT use gym terminology (no "weights", "reps", "gym").
   - This is an intense, loud, aggressive wake-up call to not quit, not lose, and not be demotivated.
   - Example tone: "Wake up! You are standing right on the edge of greatness, but you are letting comfort destroy your future! Are you going to fold like paper, or are you going to stand up and fight for your life?"

2. MINDSET (Dealing with Others / Self-Improvement)
   - Do NOT talk about generic human behavior.
   - Focus on how people treat you when you try to improve, how they react to your ambition, and how you must ignore their hate to focus on self-improvement.
   - Example tone: "They will laugh at your boundaries. They will mock your discipline. Let them. Your job isn't to make them comfortable; your job is to build a life they can only watch from the sidelines."

3. HARDWORK (Overcoming Failure / Resilience)
   - Do NOT just say "work hard" or "grind".
   - Focus on FAILURE. Talk about what failure teaches you, that success is painful and not easy, and why you must never give up when failure hits you hard.
   - Example tone: "Failure isn't the end; it's the cost of entry. Every time you fell, you bought a lesson. Success isn't easy, but quitting guarantees you'll never see it. Keep going."

STRICT RULES for every quote:
1. MAX 40 WORDS: Must be short enough to speak aloud in under 20 seconds. 
2. EXTREMELY SIMPLE ENGLISH: Use only the most basic, everyday words. No fancy words, no complex metaphors. A 10-year-old must understand every word instantly.
3. START AND END WITH COMMANDS: Every quote MUST start with a short motivational command (like "Wake up!", "Listen!", "Don't stop!"). It MUST end with an encouraging phrase for the audience like "Just do it!", "Keep going!", "You can do it!", or "Forget the past, move forward!".
4. COMMAND TONE: Use "YOU", "YOUR". Make it loud, commanding, and intense for a voiceover.
5. PERFECT SEARCH KEYWORD: For `search_keyword`, output EXACTLY ONE ultra-focused 2-3 word query for Pinterest vertical video backgrounds (e.g., 'dark aesthetic', 'night drive aesthetic').

Generate exactly 3 quotes, one per category.
"""

def generate_quotes() -> dict:
    prompt = """Generate exactly 3 motivational quotes — one per category:
1. The Wake-Up Call (Intense, loud, don't quit, fight for your future - NO gym words)
2. Mindset (How others treat you when you improve, ignoring hate, self-improvement)
3. Hardwork (Learning from failure, success is hard, don't give up)

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