import os
import sys
from skills.get_grok_news import get_grok_news
from skills.get_yt_transcripts import get_yt_transcripts
from skills.generate_brief import generate_brief

RESEARCH_FILE = "research/latest.txt"

def save_to_research(label: str, content: str):
    os.makedirs("research", exist_ok=True)
    with open(RESEARCH_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'═' * 40}\n")
        f.write(f"{label}\n")
        f.write(f"{'═' * 40}\n")
        f.write(content)
        f.write("\n")

def read_research() -> str:
    if not os.path.exists(RESEARCH_FILE):
        return ""
    with open(RESEARCH_FILE, "r", encoding="utf-8") as f:
        return f.read()

def reset_research():
    if os.path.exists(RESEARCH_FILE):
        os.remove(RESEARCH_FILE)

def run():
    print("\n🎙️  PostXG — Video Research & Script Generator\n")

    # Step 1 — Research topic
    topic = input("What do you want to research? (press enter to skip Grok)\n> ").strip()

    if topic:
        reset_research()
        print("\n>>> Calling Grok...")
        result = get_grok_news(topic)
        print("\n" + "═" * 40)
        print("GROK RESULTS")
        print("═" * 40)
        print(result)
        save_to_research(f"GROK SEARCH — {topic}", result)

        # Allow multiple Grok searches
        while True:
            choice = input("\nHappy with research?\n[1] Yes continue\n[2] Search again\n> ").strip()
            if choice == "1":
                break
            elif choice == "2":
                follow_up = input("\nWhat else do you want to search?\n> ").strip()
                if follow_up:
                    existing = read_research()
                    print("\n>>> Calling Grok again...")
                    result = get_grok_news(follow_up, context=existing)
                    print("\n" + "═" * 40)
                    print("GROK FOLLOW UP")
                    print("═" * 40)
                    print(result)
                    save_to_research(f"GROK SEARCH 2 — {follow_up}", result)
    else:
        print("Skipping Grok.")
        if not os.path.exists(RESEARCH_FILE):
            reset_research()

    # Step 2 — YouTube transcripts
    video_input = input("\nAdd YouTube video IDs? (paste IDs separated by spaces or press enter to skip)\n> ").strip()
    if video_input:
        video_ids = video_input.split()
        print("\n>>> Pulling transcripts...")
        for vid in video_ids:
            transcript = get_yt_transcripts([vid])
            print(f"✓ Got transcript for {vid}")
            save_to_research(f"YOUTUBE TRANSCRIPT — {vid}", transcript)

    # Step 3 — Write direction
    research = read_research()
    if not research:
        print("\nNo research found. Please run a search or add video IDs first.")
        return

    print("\n" + "═" * 40)
    print("RESEARCH SAVED — ready to write")
    print("═" * 40)

    direction = input("\nWhat do you want to say about this?\n> ").strip()
    if not direction:
        print("No direction given. Exiting.")
        return

    format_choice = input("\nLong form, short, or both?\n[1] Long form\n[2] Short\n[3] Both\n> ").strip()
    fmt = "long"
    if format_choice == "2":
        fmt = "short"
    elif format_choice == "3":
        fmt = "both"

    print("\n>>> Writing your script...")
    output = generate_brief(research, direction, fmt)

    print("\n" + "═" * 60)
    print(output)
    print("═" * 60)

if __name__ == "__main__":
    run()
