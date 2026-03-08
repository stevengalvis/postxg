import requests
import os
from dotenv import load_dotenv

load_dotenv()

SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")

def get_yt_transcripts(video_ids: list) -> str:
    """
    Fetches transcripts from YouTube videos via Supadata API.
    Use this skill to get pundit opinions and analysis from YouTube videos.
    Pass a list of YouTube video IDs to get their transcripts.
    """
    results = []

    for video_id in video_ids:
        try:
            response = requests.get(
                "https://api.supadata.ai/v1/youtube/transcript",
                headers={"x-api-key": SUPADATA_API_KEY},
                params={"videoId": video_id, "text": True}
            )
            data = response.json()
            content = data.get("content", [])
            if isinstance(content, list):
                text = " ".join([segment.get("text", "") for segment in content])
            else:
                text = content
            results.append(f"VIDEO {video_id}:\n{text}\n")
        except Exception as e:
            results.append(f"VIDEO {video_id}: Error — {e}\n")

    return "\n".join(results)

if __name__ == "__main__":
    test_ids = ["8-_Pz0-LffA"]
    result = get_yt_transcripts(test_ids)
    print(result[:500])
