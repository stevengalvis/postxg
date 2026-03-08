import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

url = "https://api.openai.com/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "gpt-4o-mini",
    "messages": [
        {
            "role": "user",
            "content": "In one sentence, why was Chelsea vs Wrexham controversial last night?"
        }
    ]
}

response = requests.post(url, headers=headers, json=payload)
data = response.json()
print(data['choices'][0]['message']['content'])