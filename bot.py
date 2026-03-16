import os
import re
import asyncio
import requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()

from skills.get_grok_news import get_grok_news
from skills.get_yt_transcripts import get_yt_transcripts
from skills.extract import extract_research
from skills.generate_brief import generate_brief

RESEARCH_FILE = "research/latest.txt"
EXTRACTED_FILE = "research/extracted.txt"

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID", ""))

sessions = {}  # chat_id -> session dict


# ── Telegram ──────────────────────────────────────────────────────

async def send(chat_id, text, bot):
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        await bot.send_message(chat_id=chat_id, text=chunk)


# ── Research file helpers ─────────────────────────────────────────

def save_to_research(label, content, source_type="UNKNOWN"):
    os.makedirs("research", exist_ok=True)
    with open(RESEARCH_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'═' * 40}\n")
        f.write(f"SOURCE: {source_type}\n")
        f.write(f"LABEL: {label}\n")
        f.write(f"{'═' * 40}\n")
        f.write(content)
        f.write("\n")


def read_research():
    if not os.path.exists(RESEARCH_FILE):
        return ""
    with open(RESEARCH_FILE, "r", encoding="utf-8") as f:
        return f.read()


def set_research_header(topic):
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


def list_sources():
    sources = []
    if not os.path.exists(RESEARCH_FILE):
        return sources
    with open(RESEARCH_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    sep = "═" * 40
    blocks = content.split(sep)
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


def remove_sources(indices):
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


def get_strongest_angle():
    if not os.path.exists(EXTRACTED_FILE):
        return ""
    with open(EXTRACTED_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    for line in content.split("\n"):
        if line.startswith("Strongest angle:"):
            return line.replace("Strongest angle:", "").strip()
    return ""


def get_topic_from_header():
    if not os.path.exists(RESEARCH_FILE):
        return ""
    with open(RESEARCH_FILE, "r", encoding="utf-8") as f:
        for line in f.readlines()[:5]:
            if line.startswith("TOPIC:"):
                return line.replace("TOPIC:", "").strip()
    return ""


def extract_video_id(input_str):
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


def get_video_title(video_id):
    try:
        url = f"https://www.youtube.com/oembed?url=https://youtube.com/watch?v={video_id}&format=json"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            title = data.get("title", video_id)
            author = data.get("author_name", "")
            return f"{author} — {title}" if author else title
    except Exception:
        pass
    return video_id


# ── Session helpers ───────────────────────────────────────────────

def get_session(chat_id):
    if chat_id not in sessions:
        sessions[chat_id] = {"state": "START"}
    return sessions[chat_id]


def set_state(chat_id, state):
    sessions[chat_id]["state"] = state


# ── Flow helpers ──────────────────────────────────────────────────

async def prompt_grok(chat_id, bot):
    set_state(chat_id, "GROK_TOPIC")
    await send(chat_id,
               "Tips for your Grok prompt:\n"
               "All topics — top tweets ranked by engagement with exact likes views and replies, pundit reactions\n"
               "Match only — xG, possession, shots on target, big chances, FotMob ratings, manager quotes, league position, VAR controversy\n\n"
               "What do you want to research? (or type skip to skip Grok)",
               bot)


async def prompt_youtube(chat_id, bot):
    set_state(chat_id, "YOUTUBE")
    await send(chat_id, "Add YouTube video URLs or IDs? (paste separated by spaces, or type skip)", bot)


async def prompt_manual_ask(chat_id, bot):
    set_state(chat_id, "MANUAL_ASK")
    await send(chat_id, "Add article, tweet, Reddit post or other content? (y/n)", bot)


async def run_extraction(chat_id, bot):
    research = read_research()
    if not research:
        await send(chat_id, "No research found. Starting over.", bot)
        await prompt_grok(chat_id, bot)
        return
    await send(chat_id, "Extracting research...", bot)
    try:
        extracted = await asyncio.to_thread(extract_research, research)
        with open(EXTRACTED_FILE, "w", encoding="utf-8") as f:
            f.write(extracted)
        await send(chat_id, "═" * 40 + "\nEXTRACTED RESEARCH\n" + "═" * 40 + "\n\n" + extracted, bot)
        await prompt_review(chat_id, bot)
    except Exception as e:
        await send(chat_id, f"Extraction failed: {e}", bot)
        await prompt_review(chat_id, bot)


async def prompt_review(chat_id, bot):
    set_state(chat_id, "REVIEW")
    await send(chat_id,
               "What do you want to do?\n"
               "[1] Happy — write the brief\n"
               "[2] Add more research\n"
               "[3] Remove a source\n"
               "[4] Start over",
               bot)


# ── State handlers ────────────────────────────────────────────────

def get_research_summary() -> str:
    if not os.path.exists(RESEARCH_FILE):
        return "No research loaded."
    topic = get_topic_from_header()
    sources = list_sources()
    if not topic and not sources:
        return "No research loaded."
    parts = []
    if topic:
        parts.append(f'"{topic}"')
    if sources:
        parts.append(f"{len(sources)} source{'s' if len(sources) != 1 else ''}")
    return "Research loaded: " + ", ".join(parts)


async def handle_start(chat_id, text, session, bot):
    await send(chat_id, get_research_summary(), bot)
    await prompt_grok(chat_id, bot)


async def handle_grok_topic(chat_id, text, session, bot):
    appending = session.get("appending", False)

    if text.lower() == "skip":
        if appending or read_research():
            await prompt_youtube(chat_id, bot)
        else:
            set_state(chat_id, "TOPIC_LABEL")
            await send(chat_id, "What is this research about? (used as topic label)", bot)
        return

    if not appending:
        clear_research()
        set_research_header(text)
        session["topic"] = text

    existing = read_research() if appending else None
    await send(chat_id, "Searching Grok...", bot)
    try:
        result = await asyncio.to_thread(get_grok_news, text, existing)
        save_to_research(f"Grok search — {text}", result, "GROK_SEARCH")
        await send(chat_id, "═" * 40 + "\nGROK RESULTS\n" + "═" * 40 + "\n\n" + result, bot)
        set_state(chat_id, "GROK_CONFIRM")
        await send(chat_id, "Happy with Grok research?\n[1] Yes continue\n[2] Search again (type follow-up query)", bot)
    except Exception as e:
        await send(chat_id, f"Grok search failed: {e}", bot)
        await prompt_youtube(chat_id, bot)


async def handle_grok_confirm(chat_id, text, session, bot):
    if text.lower() in ["1", "yes"]:
        await prompt_youtube(chat_id, bot)
        return

    # Anything else is a follow-up search query
    existing = read_research()
    await send(chat_id, "Searching Grok again...", bot)
    try:
        result = await asyncio.to_thread(get_grok_news, text, existing)
        save_to_research(f"Grok search — {text}", result, "GROK_SEARCH")
        await send(chat_id, "═" * 40 + "\nGROK FOLLOW UP\n" + "═" * 40 + "\n\n" + result, bot)
        set_state(chat_id, "GROK_CONFIRM")
        await send(chat_id, "Happy with Grok research?\n[1] Yes continue\n[2] Search again (type follow-up query)", bot)
    except Exception as e:
        await send(chat_id, f"Grok search failed: {e}", bot)
        await prompt_youtube(chat_id, bot)


async def handle_topic_label(chat_id, text, session, bot):
    if text:
        clear_research()
        set_research_header(text)
        session["topic"] = text
    await prompt_youtube(chat_id, bot)


def _fetch_transcripts(video_ids):
    """Blocking transcript fetch — runs in a thread."""
    results = []
    for vid in video_ids:
        try:
            transcript = get_yt_transcripts([vid])
            if transcript and len(transcript) > 100:
                title = get_video_title(vid)
                save_to_research(f"YouTube — {title}", transcript[:10000], "YOUTUBE_TRANSCRIPT")
                results.append(f"✓ {title}")
            else:
                results.append(f"✗ No transcript found for {vid}")
        except Exception as e:
            results.append(f"✗ Failed for {vid}: {e}")
    return "\n".join(results)


async def handle_youtube(chat_id, text, session, bot):
    if text.lower() == "skip":
        await prompt_manual_ask(chat_id, bot)
        return

    video_ids = [extract_video_id(v) for v in text.split()]
    await send(chat_id, "Pulling transcripts...", bot)
    result_text = await asyncio.to_thread(_fetch_transcripts, video_ids)
    await send(chat_id, result_text, bot)
    await prompt_manual_ask(chat_id, bot)


async def handle_manual_ask(chat_id, text, session, bot):
    if text.lower() in ["y", "yes"]:
        set_state(chat_id, "MANUAL_TYPE")
        await send(chat_id,
                   "What type of source?\n"
                   "[1] Article\n"
                   "[2] Tweet or tweet thread\n"
                   "[3] Reddit thread\n"
                   "[4] Press conference transcript\n"
                   "[5] Other",
                   bot)
    else:
        await run_extraction(chat_id, bot)


async def handle_manual_type(chat_id, text, session, bot):
    type_map = {
        "1": "MANUAL_ARTICLE",
        "2": "MANUAL_TWEET",
        "3": "MANUAL_REDDIT",
        "4": "MANUAL_PRESSER",
        "5": "MANUAL_OTHER",
    }
    session["manual_type"] = type_map.get(text, "MANUAL_OTHER")
    set_state(chat_id, "MANUAL_LABEL")
    await send(chat_id, "Give it a short label (e.g. Athletic — Laporta interview)", bot)


async def handle_manual_label(chat_id, text, session, bot):
    session["manual_label"] = text
    session["manual_lines"] = []
    set_state(chat_id, "MANUAL_CONTENT")
    await send(chat_id, "Paste your content. Send END on its own line when done.", bot)


async def handle_manual_content(chat_id, text, session, bot):
    if text.strip().upper() == "END":
        content = "\n".join(session.get("manual_lines", []))
        if content:
            save_to_research(session["manual_label"], content, session["manual_type"])
            await send(chat_id, f"✓ Saved: {session['manual_label']}", bot)
        session["manual_lines"] = []
        await prompt_manual_ask(chat_id, bot)
    else:
        session.setdefault("manual_lines", []).append(text)


async def handle_review(chat_id, text, session, bot):
    if text.lower() in ["1", "yes", "happy"]:
        if not os.path.exists(EXTRACTED_FILE):
            await send(chat_id, "No extracted research found. Re-extracting...", bot)
            await run_extraction(chat_id, bot)
            return
        set_state(chat_id, "DIRECTION")
        await send(chat_id, "What do you want to say about this?", bot)

    elif text == "2":
        session["appending"] = True
        await prompt_grok(chat_id, bot)

    elif text == "3":
        sources = list_sources()
        if not sources:
            await send(chat_id, "No sources found.", bot)
            return
        lines = ["Current sources:"]
        for i, s in enumerate(sources):
            lines.append(f"[{i + 1}] {s['type']} — {s['label']}")
        lines.append("\nWhich sources to remove? (numbers separated by spaces)")
        await send(chat_id, "\n".join(lines), bot)
        set_state(chat_id, "REMOVE_SOURCE")

    elif text == "4":
        clear_research()
        session["appending"] = False
        await send(chat_id, "Research cleared.", bot)
        await prompt_grok(chat_id, bot)


async def handle_remove_source(chat_id, text, session, bot):
    indices = [int(x) - 1 for x in text.split() if x.isdigit()]
    if not indices:
        await send(chat_id, "No valid numbers entered. Try again.", bot)
        return
    remove_sources(indices)
    await send(chat_id, "Removed. Re-extracting...", bot)
    await run_extraction(chat_id, bot)


async def handle_direction(chat_id, text, session, bot):
    session["direction"] = text
    set_state(chat_id, "FORMAT")
    await send(chat_id, "Long form, short, or both?\n[1] Long form\n[2] Short\n[3] Both", bot)


async def handle_format(chat_id, text, session, bot):
    fmt_map = {
        "1": "long", "long": "long", "long form": "long",
        "2": "short", "short": "short",
        "3": "both", "both": "both",
    }
    fmt = fmt_map.get(text.lower(), "long")

    direction = session.get("direction", "")
    strongest_angle = get_strongest_angle()
    full_direction = (
        f"{direction}\n\nSTRONGEST ANGLE FROM RESEARCH: {strongest_angle}"
        if strongest_angle else direction
    )

    topic = get_topic_from_header() or session.get("topic", "football video")

    if not os.path.exists(EXTRACTED_FILE):
        await send(chat_id, "No extracted research found.", bot)
        return

    with open(EXTRACTED_FILE, "r", encoding="utf-8") as f:
        extracted = f.read()

    await send(chat_id, "Generating your brief...", bot)
    try:
        output = await asyncio.to_thread(generate_brief, extracted, full_direction, fmt, topic, fmt)
        await send(chat_id, "═" * 40 + "\nYOUR BRIEF\n" + "═" * 40, bot)
        await send(chat_id, output, bot)
    except Exception as e:
        await send(chat_id, f"Brief generation failed: {e}", bot)
    finally:
        set_state(chat_id, "START")
        session["appending"] = False
        await send(chat_id, "Done. Send any message to start a new run.", bot)


# ── Dispatch ──────────────────────────────────────────────────────

HANDLERS = {
    "START":          handle_start,
    "GROK_TOPIC":     handle_grok_topic,
    "GROK_CONFIRM":   handle_grok_confirm,
    "TOPIC_LABEL":    handle_topic_label,
    "YOUTUBE":        handle_youtube,
    "MANUAL_ASK":     handle_manual_ask,
    "MANUAL_TYPE":    handle_manual_type,
    "MANUAL_LABEL":   handle_manual_label,
    "MANUAL_CONTENT": handle_manual_content,
    "REVIEW":         handle_review,
    "REMOVE_SOURCE":  handle_remove_source,
    "DIRECTION":      handle_direction,
    "FORMAT":         handle_format,
}


# ── Entry point ───────────────────────────────────────────────────

async def handle_message(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    chat_id = str(update.effective_chat.id)
    text = (update.message.text or "").strip()

    if not text:
        return

    # Security: only respond to the configured chat ID
    if ALLOWED_CHAT_ID and chat_id != ALLOWED_CHAT_ID:
        return

    session = get_session(chat_id)

    # /start resets from any state
    if text == "/start":
        sessions[chat_id] = {"state": "START"}
        session = sessions[chat_id]
        await send(chat_id, "PostXG ready.", context.bot)

    state = session.get("state", "START")
    handler = HANDLERS.get(state, handle_start)
    await handler(chat_id, text, session, context.bot)


def main():
    if not BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set — bot cannot start.")
    from telegram import Update
    from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    print("PostXG bot polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
