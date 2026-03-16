import os
import re
import sys
import signal
import requests
from datetime import date
from skills.get_grok_news import get_grok_news
from skills.get_yt_transcripts import get_yt_transcripts
from skills.extract import extract_research
from skills.generate_brief import generate_brief

RESEARCH_FILE = "research/latest.txt"
EXTRACTED_FILE = "research/extracted.txt"

def handle_exit(sig, frame):
    print("\n\nExiting PostXG.")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)

def get_video_title(video_id: str) -> str:
    try:
        url = f"https://www.youtube.com/oembed?url=https://youtube.com/watch?v={video_id}&format=json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            title = data.get("title", video_id)
            author = data.get("author_name", "")
            return f"{author} — {title}" if author else title
    except Exception:
        pass
    return video_id

def extract_video_id(input_str: str) -> str:
    input_str = input_str.strip()
    if "youtube.com/watch" in input_str:
        match = re.search(r'v=([a-zA-Z0-9_-]{11})', input_str)
        if match:
            return match.group(1)
    if "youtu.be/" in input_str:
        match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', input_str)
        if match:
            return match.group(1)
    if "youtube.com/shorts/" in input_str:
        match = re.search(r'shorts/([a-zA-Z0-9_-]{11})', input_str)
        if match:
            return match.group(1)
    return input_str

def save_to_research(label: str, content: str, source_type: str = "UNKNOWN"):
    os.makedirs("research", exist_ok=True)
    with open(RESEARCH_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'═' * 40}\n")
        f.write(f"SOURCE: {source_type}\n")
        f.write(f"LABEL: {label}\n")
        f.write(f"{'═' * 40}\n")
        f.write(content)
        f.write("\n")

def read_research() -> str:
    if not os.path.exists(RESEARCH_FILE):
        return ""
    with open(RESEARCH_FILE, "r", encoding="utf-8") as f:
        return f.read()

def get_research_header() -> dict:
    if not os.path.exists(RESEARCH_FILE):
        return {}
    with open(RESEARCH_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    header = {}
    for line in lines[:5]:
        if line.startswith("TOPIC:"):
            header["topic"] = line.replace("TOPIC:", "").strip()
        if line.startswith("DATE:"):
            header["date"] = line.replace("DATE:", "").strip()
    return header

def set_research_header(topic: str):
    os.makedirs("research", exist_ok=True)
    existing = read_research()
    with open(RESEARCH_FILE, "w", encoding="utf-8") as f:
        f.write(f"TOPIC: {topic}\n")
        f.write(f"DATE: {date.today()}\n")
        f.write(existing)

def clear_research():
    if os.path.exists(RESEARCH_FILE):
        os.remove(RESEARCH_FILE)
    if os.path.exists(EXTRACTED_FILE):
        os.remove(EXTRACTED_FILE)

def list_sources() -> list:
    sources = []
    if not os.path.exists(RESEARCH_FILE):
        return sources
    with open(RESEARCH_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    sep = "═" * 40
    blocks = content.split(sep)
    # blocks[0] is the file header; sources are stored as pairs: (metadata_block, content_block)
    i = 1
    while i < len(blocks) - 1:
        meta_block = blocks[i]
        content_block = blocks[i + 1]
        source_type = ""
        label = ""
        for line in meta_block.strip().split("\n"):
            if line.startswith("SOURCE:"):
                source_type = line.replace("SOURCE:", "").strip()
            if line.startswith("LABEL:"):
                label = line.replace("LABEL:", "").strip()
        if source_type and label:
            sources.append({
                "type": source_type,
                "label": label,
                "meta_block": meta_block,
                "content_block": content_block,
            })
        i += 2
    return sources

def remove_sources(indices: list):
    sources = list_sources()
    to_remove = [sources[i] for i in indices if i < len(sources)]
    with open(RESEARCH_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    sep = "═" * 40
    for source in to_remove:
        full_entry = sep + source["meta_block"] + sep + source["content_block"]
        content = content.replace(full_entry, "")
    with open(RESEARCH_FILE, "w", encoding="utf-8") as f:
        f.write(content)

def collect_grok(topic: str, appending: bool = False):
    if not appending:
        clear_research()
        set_research_header(topic)
    existing = read_research()
    print("\n>>> Calling Grok...")
    result = get_grok_news(topic, context=existing if appending else None)
    print("\n" + "═" * 40)
    print("GROK RESULTS")
    print("═" * 40)
    print(result)
    save_to_research(f"Grok search — {topic}", result, "GROK_SEARCH")

    while True:
        choice = input("\nHappy with Grok research?\n[1] Yes continue\n[2] Search again\n> ").strip().lower()
        if choice in ["1", "yes"]:
            break
        elif choice in ["2", "no"]:
            follow_up = input("\nWhat else do you want to search?\n> ").strip()
            if follow_up:
                existing = read_research()
                print("\n>>> Calling Grok again...")
                result = get_grok_news(follow_up, context=existing)
                print("\n" + "═" * 40)
                print("GROK FOLLOW UP")
                print("═" * 40)
                print(result)
                save_to_research(f"Grok search — {follow_up}", result, "GROK_SEARCH")

def collect_transcripts():
    video_input = input("\nAdd YouTube video URLs or IDs? (paste separated by spaces or press enter to skip)\n> ").strip()
    if not video_input:
        return
    raw_inputs = video_input.split()
    video_ids = [extract_video_id(v) for v in raw_inputs]
    print("\n>>> Pulling transcripts...")
    for vid in video_ids:
        try:
            transcript = get_yt_transcripts([vid])
            if transcript and len(transcript) > 100:
                title = get_video_title(vid)
                print(f"✓ {title}")
                save_to_research(f"YouTube — {title}", transcript[:10000], "YOUTUBE_TRANSCRIPT")
            else:
                print(f"✗ No transcript found for {vid}")
        except Exception as e:
            print(f"✗ Failed for {vid}: {e}")

def collect_manual():
    while True:
        manual = input("\nAdd article, tweet, Reddit post or other content? (y/n)\n> ").strip().lower()
        if manual not in ["y", "yes"]:
            break

        print("\nWhat type of source is this?")
        print("[1] Article")
        print("[2] Tweet or tweet thread")
        print("[3] Reddit thread")
        print("[4] Press conference transcript")
        print("[5] Other")
        type_choice = input("> ").strip()

        type_map = {
            "1": "MANUAL_ARTICLE",
            "2": "MANUAL_TWEET",
            "3": "MANUAL_REDDIT",
            "4": "MANUAL_PRESSER",
            "5": "MANUAL_OTHER"
        }
        source_type = type_map.get(type_choice, "MANUAL_OTHER")
        label = input("\nGive it a short label (e.g. Athletic — Laporta interview)\n> ").strip()

        print("\nPaste your content below. Type END on a new line when done:")
        lines = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        content = "\n".join(lines)

        if content:
            save_to_research(label, content, source_type)
            print(f"✓ Saved: {label}")

def collect_research(appending: bool = False):
    print("\nTips for your Grok prompt:")
    print("  All topics — top tweets ranked by engagement with exact likes views and replies, pundit reactions")
    print("  Match only — xG, possession, shots on target, big chances, FotMob ratings, manager quotes, league position, VAR controversy")
    topic = input("\nWhat do you want to research? (press enter to skip Grok)\n> ").strip()

    if topic:
        collect_grok(topic, appending)
    else:
        if not appending:
            topic = input("\nWhat is this research about? (used as topic label)\n> ").strip()
            if topic:
                clear_research()
                set_research_header(topic)

    collect_transcripts()
    collect_manual()

def get_strongest_angle() -> str:
    if not os.path.exists(EXTRACTED_FILE):
        return ""
    with open(EXTRACTED_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    for line in content.split("\n"):
        if line.startswith("Strongest angle:"):
            return line.replace("Strongest angle:", "").strip()
    return ""

def review_extracted():
    while True:
        research = read_research()
        if not research:
            print("\nNo research found.")
            return False

        print("\n>>> Extracting research...")
        extracted = extract_research(research)

        with open(EXTRACTED_FILE, "w", encoding="utf-8") as f:
            f.write(extracted)

        print("\n" + "═" * 60)
        print("EXTRACTED RESEARCH SUMMARY")
        print("═" * 60)
        print(extracted)

        print("\nWhat do you want to do?")
        print("[1] Happy — write the brief")
        print("[2] Add more research")
        print("[3] Remove a source")
        print("[4] Start over")
        choice = input("> ").strip().lower()

        if choice in ["1", "yes", "happy"]:
            return True
        elif choice == "2":
            collect_research(appending=True)
        elif choice == "3":
            sources = list_sources()
            if not sources:
                print("No sources found.")
                continue
            print("\nCurrent sources:")
            for i, s in enumerate(sources):
                print(f"[{i+1}] {s['type']} — {s['label']}")
            to_remove = input("\nWhich sources to remove? (enter numbers separated by spaces)\n> ").strip()
            indices = [int(x) - 1 for x in to_remove.split() if x.isdigit()]
            if indices:
                remove_sources(indices)
                print("Removed. Re-extracting...")
        elif choice == "4":
            clear_research()
            print("Research cleared.")
            return False

def send_telegram(message: str):
    import telegram
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not all([bot_token, chat_id]):
        print("\n⚠ Telegram env vars not set — skipping send.")
        return

    try:
        import asyncio
        bot = telegram.Bot(token=bot_token)
        chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
        async def send_chunks():
            for chunk in chunks:
                await bot.send_message(chat_id=chat_id, text=chunk)
        asyncio.run(send_chunks())
        print("\n✓ Brief sent to Telegram.")
    except Exception as e:
        print(f"\n✗ Telegram send failed: {e}")


def write_output(topic: str):
    if not os.path.exists(EXTRACTED_FILE):
        print("No extracted research found.")
        return

    with open(EXTRACTED_FILE, "r", encoding="utf-8") as f:
        extracted = f.read()

    strongest_angle = get_strongest_angle()

    direction = input("\nWhat do you want to say about this?\n> ").strip()
    if not direction:
        print("No direction given.")
        return

    fmt_input = input("\nLong form, short, or both?\n[1] Long form\n[2] Short\n[3] Both\n> ").strip().lower()
    fmt_map = {
        "1": "long", "long": "long", "long form": "long",
        "2": "short", "short": "short",
        "3": "both", "both": "both"
    }
    fmt = fmt_map.get(fmt_input, "long")

    if strongest_angle:
        full_direction = f"{direction}\n\nSTRONGEST ANGLE FROM RESEARCH: {strongest_angle}"
    else:
        full_direction = direction

    print("\n>>> Generating your brief...")
    output = generate_brief(extracted, full_direction, fmt, topic, fmt)

    print("\n" + "═" * 60)
    print(output)
    print("═" * 60)

    send_telegram(output)

def run():
    print("\n⚽📊  PostXG — Video Research & Brief Generator\n")

    header = get_research_header()

    if header.get("topic"):
        print(f"Active research: \"{header['topic']}\" (saved {header.get('date', 'unknown')})")
        print("\n[1] Continue this research")
        print("[2] Start new topic")
        choice = input("> ").strip().lower()

        if choice in ["2", "new"]:
            clear_research()
            collect_research(appending=False)
        else:
            collect_research(appending=True)
    else:
        collect_research(appending=False)

    research = read_research()
    if not research:
        print("\nNo research collected. Exiting.")
        return

    happy = review_extracted()
    if not happy:
        run()
        return

    header = get_research_header()
    topic = header.get("topic", "football video")
    write_output(topic)

if __name__ == "__main__":
    run()
