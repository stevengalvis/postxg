import requests
import os
from dotenv import load_dotenv

load_dotenv()

GROK_API_KEY = os.getenv("GROK_API_KEY")

def get_grok_news(team: str) -> str:
    """
    Fetches latest football news and X/Twitter reactions via Grok API.
    Use this skill to get real-time transfer news and fan reactions.
    Pass a team name to get the latest news about that team.
    """
    response = requests.post(
        "https://api.x.ai/v1/responses",
        headers={
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "grok-4-1-fast",
            "tools": [{"type": "web_search"}, {"type": "x_search"}],
            "input": [
                {
                    "role": "user",
                    "content": f"Latest news, transfer rumours and fan reactions about {team} in the last 48 hours?"
                }
            ]
        }
    )
    print("Status:", response.status_code)
    data = response.json()
    for item in data.get("output", []):
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    return block.get("text", "")
    return "No results found"

if __name__ == "__main__":
    result = get_grok_news("Chelsea FC")
    print(result)
