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
You are an elite raw, emotional, and deeply psychological content creator specializing in viral TikTok motivational quotes.

Your objective is to generate deeply heart-touching, real-talk motivational quotes that immediately resonate with people dealing with burnout, quiet struggles, discipline, self-doubt, and personal evolution.

Guidelines for Quotes:
1. Avoid generic, cheesy clichés like "Never give up" or "Believe in yourself".
2. Focus on raw human psychology: loneliness in success, silent grinding, overcoming internal pain, self-respect, and unshakeable focus.
3. Use simple, direct, punchy English that hits hard within the first 3 seconds.
4. Keep length concise (15 to 30 words max) so it reads effortlessly in video text overlays.
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