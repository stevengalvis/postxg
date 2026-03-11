import requests
import os
from dotenv import load_dotenv
load_dotenv()

GROK_API_KEY = os.getenv("GROK_API_KEY")

def get_grok_news(prompt: str, context: str = None) -> str:
    if context:
        full_prompt = f"Previous research already collected:\n{context}\n\nNew search request: {prompt}\n\nBuild on the previous research. Do not repeat what was already found."
    else:
        full_prompt = prompt

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
                    "content": full_prompt
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
    result = get_grok_news("Chelsea vs PSG Champions League latest news and fan reactions")
    print(result)
