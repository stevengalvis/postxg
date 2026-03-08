import sys
from skills.get_grok_news import get_grok_news
from skills.get_yt_transcripts import get_yt_transcripts
from skills.generate_brief import generate_brief

def run(team: str, video_ids: list):
    print(f"\n>>> Fetching Grok news for {team}...")
    news = get_grok_news(team)
    print("Done.\n")

    print(f">>> Fetching YouTube transcripts...")
    transcripts = get_yt_transcripts(video_ids)
    print("Done.\n")

    print(f">>> Generating video brief...")
    brief = generate_brief(team, news, transcripts)
    print("Done.\n")

    print("=" * 60)
    print("YOUR VIDEO BRIEF:")
    print("=" * 60)
    print(brief)

if __name__ == "__main__":
    run(
        team="Chelsea FC",
        video_ids=["8-_Pz0-LffA"]
    )
