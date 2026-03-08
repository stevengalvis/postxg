import requests
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def generate_brief(team: str, grok_news: str, yt_transcripts: str) -> str:
    """
    Generates a video brief in Steven's voice using Grok news and YouTube transcripts.
    Use this skill after get_grok_news and get_yt_transcripts have been called.
    Returns a teleprompter-ready video script.
    """
    prompt = f"""
You are writing a video brief for a passionate football YouTube channel in the style of Mark Goldbridge — emotional, opinionated, direct, no fluff.

The presenter is a Chelsea/Man United/Liverpool fan who gives hot takes and strong opinions.

Use the following research to write a 3-4 minute video brief with:
- A strong opening hook (1-2 sentences that grab attention)
- 3-4 main talking points with strong opinions
- A closing call to action

GROK NEWS AND FAN REACTIONS:
{grok_news}

YOUTUBE PUNDIT TRANSCRIPTS:
{yt_transcripts}

TEAM: {team}

Write the brief now. Be passionate, be specific, use the actual names and numbers from the research.
"""

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    )
    data = response.json()
    return data["choices"][0]["message"]["content"]


if __name__ == "__main__":
    # Test with dummy data first
    test_news = "Chelsea beat Wrexham 4-2. Joao Pedro hat trick. Diouf transfer link €28m."
    test_transcripts = "Goldbridge said Chelsea need to strengthen in midfield this summer."
    result = generate_brief("Chelsea FC", test_news, test_transcripts)
    print(result)
