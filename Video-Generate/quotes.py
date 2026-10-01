import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

# Initialize client (it will now correctly pick up GEMINI_API_KEY from environment)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Rest of your code remains the same...

# Define Structured Schema
class QuoteItem(BaseModel):
    id: int
    quote: str = Field(description="A powerful, emotional, heart-touching motivational quote.")
    hook: str = Field(description="A 3-5 word high-impact opening line to hook the viewer on TikTok.")
    category: str = Field(description="The theme of the quote (e.g., Resilience, Discipline, Self-Growth, Heartbreak).")
    search_keywords: list[str] = Field(description="3 key search terms to find matching background videos/music.")

class QuotesContainer(BaseModel):
    quotes: list[QuoteItem]

SYSTEM_PROMPT = """
You are a master of human psychology and raw, relatable motivation. 

Your job is to generate short, extremely simple, and deeply relatable quotes that immediately hit the viewer's core emotions and give them instant confidence.

Rules for writing the quotes:
1. EXTREMELY SIMPLE WORDS: Use everyday spoken English. Avoid complex metaphors or poetic phrases like "building an empire" or "heaviest silent battles".
2. DEEP PSYCHOLOGICAL TRUTH: Speak directly to feelings everyone experiences—feeling tired, being misunderstood, working in silence, needing self-respect, and proving oneself right.
3. INSTANT CONFIDENCE & POWER: Every quote must end with a turn that makes the reader feel strong, confident, and unstoppable right now.
4. MAXIMUM 2 SHORT SENTENCES: Keep it ultra-short (10 to 18 words total) so anyone scrolling on TikTok can read and feel it in 2 seconds.

Examples of the exact tone required:
- "Stop explaining yourself. Let your success make all the noise."
- "You are not tired of working. You are tired of not seeing results. Keep going."
- "The best revenge is improving yourself so much that they become a distant memory."
- "Work in silence. Let them think you failed until you show up winning."
"""

def generate_quotes(count: int = 5) -> dict:
    prompt = f"Generate {count} unique, deeply moving, and raw heart-touching motivational quotes."
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",  # Recommended active Flash model tier
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=QuotesContainer,
            temperature=0.8,
        ),
    )
    
    # Parse returned structured JSON string into dictionary
    data = json.loads(response.text)
    return data

def save_to_json(data: dict, filename: str = "video-content.json") -> None:
    # Read existing data if file exists and is not empty, then append or overwrite
    output_path = os.path.join(os.path.dirname(__file__), filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Successfully generated and saved {len(data.get('quotes', []))} quotes to {output_path}")

if __name__ == "__main__":
    quotes_data = generate_quotes(count=5)
    save_to_json(quotes_data)