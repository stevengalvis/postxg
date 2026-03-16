import os
import re
import asyncio
import textwrap
import threading
import requests
import streamlit as st
from datetime import date

try:
    from skills.get_grok_news import get_grok_news
    from skills.get_yt_transcripts import get_yt_transcripts
    from skills.extract import extract_research
    from skills.generate_brief import generate_brief
except ImportError as _e:
    import streamlit as st
    st.error(f"Failed to import pipeline skills: {_e}")
    st.stop()

RESEARCH_FILE = "research/latest.txt"
EXTRACTED_FILE = "research/extracted.txt"

# ── File helpers (mirrors agent.py) ──────────────────────────────

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
    i = 1
    while i < len(blocks) - 1:
        meta_block = blocks[i]
        content_block = blocks[i + 1]
        source_type = label = ""
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


def get_topic_from_header() -> str:
    if not os.path.exists(RESEARCH_FILE):
        return ""
    with open(RESEARCH_FILE, "r", encoding="utf-8") as f:
        for line in f.readlines()[:5]:
            if line.startswith("TOPIC:"):
                return line.replace("TOPIC:", "").strip()
    return ""


def get_strongest_angle() -> str:
    if not os.path.exists(EXTRACTED_FILE):
        return ""
    with open(EXTRACTED_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    for line in content.split("\n"):
        if line.startswith("Strongest angle:"):
            return line.replace("Strongest angle:", "").strip()
    return ""


def extract_video_id(input_str: str) -> str:
    input_str = input_str.strip()
    if "youtube.com/watch" in input_str:
        m = re.search(r'v=([a-zA-Z0-9_-]{11})', input_str)
        if m:
            return m.group(1)
    if "youtu.be/" in input_str:
        m = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', input_str)
        if m:
            return m.group(1)
    if "youtube.com/shorts/" in input_str:
        m = re.search(r'shorts/([a-zA-Z0-9_-]{11})', input_str)
        if m:
            return m.group(1)
    return input_str


def get_video_title(video_id: str) -> str:
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


def extract_image_urls(text: str) -> list:
    return re.findall(
        r'https?://\S+\.(?:jpg|jpeg|png|gif|webp)(?:\?\S*)?',
        text,
        flags=re.IGNORECASE,
    )


def run_in_thread(fn, *args):
    """Run a blocking function in a thread and return the result."""
    result = {}
    def target():
        try:
            result["value"] = fn(*args)
        except Exception as e:
            result["error"] = str(e)
    t = threading.Thread(target=target)
    t.start()
    t.join()
    if "error" in result:
        raise RuntimeError(result["error"])
    return result.get("value")


# ── State helpers ─────────────────────────────────────────────────

STAGES = [
    "grok_input",
    "grok_review",
    "youtube",
    "manual",
    "extract",
    "direction",
    "output",
]


def init_state():
    defaults = {
        "stage": "grok_input",
        "appending": False,
        "grok_result": None,
        "grok_topic": None,
        "extracted": None,
        "brief": None,
        "status_msg": None,
        "yt_results": None,
        "yt_fetching": False,
        "yt_pending": [],
        "manual_entries": [],   # list of {type, label, content}
        "manual_form_key": 0,
        "adding_manual": False,
        "pending_remove": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def go_to(stage: str):
    st.session_state.stage = stage
    st.session_state.status_msg = None


# ── UI ────────────────────────────────────────────────────────────

st.set_page_config(page_title="PostXG", page_icon="⚽📊", layout="wide")
st.title("⚽📊 PostXG — Research & Brief Generator")
st.caption("AI-powered football content pipeline. From raw research to insightful, smart briefs in minutes.")


init_state()

stage = st.session_state.stage

# Sidebar: progress indicator
with st.sidebar:
    st.markdown("### Pipeline")
    step_labels = {
        "grok_input": "1. Grok Research",
        "grok_review": "2. Review Grok",
        "youtube": "3. YouTube",
        "manual": "4. Manual Sources",
        "extract": "5. Extract & Review",
        "direction": "6. Direction & Format",
        "output": "7. Brief Output",
    }
    for s, label in step_labels.items():
        if s == stage:
            st.markdown(f"**→ {label}**")
        else:
            st.markdown(f"&nbsp;&nbsp;&nbsp;{label}")

    st.divider()
    topic = get_topic_from_header()
    sources = list_sources()
    if topic:
        st.caption(f"Topic: **{topic}**")
    if sources:
        st.caption(f"Sources: {len(sources)}")

    if st.button("🗑️ Clear all research", use_container_width=True):
        clear_research()
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ─────────────────────────────────────────────────────────────────
# Stage: GROK INPUT
# ─────────────────────────────────────────────────────────────────
if stage == "grok_input":
    existing_topic = get_topic_from_header()
    existing_sources = list_sources()

    if existing_topic and existing_sources and not st.session_state.appending:
        st.info(f"**Active research:** \"{existing_topic}\" — {len(existing_sources)} source(s).")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Continue this research", use_container_width=True):
                st.session_state.appending = True
                st.rerun()
        with col2:
            if st.button("Start new topic", use_container_width=True):
                clear_research()
                st.session_state.appending = False
                st.rerun()
        st.divider()

        # Clean summary
        research_date = ""
        with open(RESEARCH_FILE, "r", encoding="utf-8") as _f:
            for _line in _f.readlines()[:5]:
                if _line.startswith("DATE:"):
                    research_date = _line.replace("DATE:", "").strip()
                    break

        st.markdown(f"**Topic:** {existing_topic}")
        if research_date:
            st.markdown(f"**Date:** {research_date}")

        grok_s = [s for s in existing_sources if s["type"] == "GROK_SEARCH"]
        yt_s   = [s for s in existing_sources if s["type"] == "YOUTUBE_TRANSCRIPT"]
        manual_s = [s for s in existing_sources if s["type"] not in ("GROK_SEARCH", "YOUTUBE_TRANSCRIPT")]

        if grok_s:
            st.markdown("**Grok searches:**")
            for s in grok_s:
                st.markdown(f"- {s['label'].removeprefix('Grok search — ')}")
        if yt_s:
            st.markdown("**YouTube videos:**")
            for s in yt_s:
                st.markdown(f"- {s['label'].removeprefix('YouTube — ')}")
        if manual_s:
            st.markdown("**Manual sources:**")
            for s in manual_s:
                st.markdown(f"- {s['label']}")

        with st.expander("View raw research"):
            st.code(read_research(), language=None, height=400)
        st.stop()

    if existing_topic and not existing_sources and not st.session_state.appending:
        st.info("No active research — start a new topic.")

    st.subheader("Grok Research")
    st.caption(
        "Tips: All topics — top tweets ranked by engagement with exact likes/views/replies, pundit reactions\n\n"
        "Match only — xG, possession, shots on target, big chances, FotMob ratings, manager quotes, league position, VAR controversy"
    )

    with st.form("grok_form"):
        topic_input = st.text_area(
            "Topic",
            placeholder="e.g. Arsenal vs Man City, Salah contract, Klopp return...",
            label_visibility="collapsed",
            height=150,
        )
        submitted = st.form_submit_button("Search Grok", use_container_width=True)

    skip_clicked = st.button("Skip →", help="Go straight to YouTube / manual sources")

    if submitted and topic_input.strip():
        with st.spinner("Searching Grok..."):
            try:
                existing = read_research() if st.session_state.appending else None
                if not st.session_state.appending:
                    clear_research()
                    set_research_header(topic_input.strip())
                result = run_in_thread(get_grok_news, topic_input.strip(), existing)
                save_to_research(f"Grok search — {topic_input.strip()}", result, "GROK_SEARCH")
                st.session_state.grok_result = result
                st.session_state.grok_topic = topic_input.strip()
                go_to("grok_review")
                st.rerun()
            except Exception as e:
                st.error(f"Grok search failed: {e}")

    if (submitted and not topic_input.strip()) or skip_clicked:
        if not read_research():
            st.session_state.stage = "grok_nolabel"
            st.rerun()
        else:
            go_to("youtube")
            st.rerun()

    grok_sources = [s for s in list_sources() if s["type"] == "GROK_SEARCH"]
    if grok_sources:
        st.divider()
        for s in grok_sources:
            with st.expander(s["label"].removeprefix("Grok search — "), expanded=len(grok_sources) == 1):
                st.code(s["content_block"].strip(), language=None, height=400)


# ─────────────────────────────────────────────────────────────────
# Stage: GROK — no-label (skip grok but need a topic name)
# ─────────────────────────────────────────────────────────────────
elif stage == "grok_nolabel":
    st.subheader("Topic Label")
    with st.form("label_form"):
        label = st.text_input("What is this research about? (used as topic label)")
        submitted = st.form_submit_button("Continue →")
    if submitted:
        if label.strip():
            clear_research()
            set_research_header(label.strip())
        go_to("youtube")
        st.rerun()


# ─────────────────────────────────────────────────────────────────
# Stage: GROK REVIEW
# ─────────────────────────────────────────────────────────────────
elif stage == "grok_review":
    st.subheader("Grok Results")

    with st.form("grok_review_form"):
        follow_up = st.text_area(
            "Search again with a follow-up query? (leave blank to continue)",
            placeholder="Leave blank if happy with results",
            height=150,
        )
        col1, col2 = st.columns(2)
        with col1:
            happy = st.form_submit_button("✓ Happy — continue →", use_container_width=True)
        with col2:
            again = st.form_submit_button("Search again", use_container_width=True)

    if happy:
        go_to("youtube")
        st.rerun()

    if again and follow_up.strip():
        with st.spinner("Searching Grok again..."):
            try:
                existing = read_research()
                result = run_in_thread(get_grok_news, follow_up.strip(), existing)
                save_to_research(f"Grok search — {follow_up.strip()}", result, "GROK_SEARCH")
                st.session_state.grok_result = result
                st.session_state.grok_topic = follow_up.strip()
                st.rerun()
            except Exception as e:
                st.error(f"Grok follow-up failed: {e}")

    grok_sources = [s for s in list_sources() if s["type"] == "GROK_SEARCH"]
    for s in grok_sources:
        with st.expander(s["label"].removeprefix("Grok search — "), expanded=len(grok_sources) == 1):
            text = s["content_block"].strip()
            st.code(text, language=None, height=400)
            for img_url in extract_image_urls(text):
                try:
                    st.image(img_url)
                except Exception:
                    pass


# ─────────────────────────────────────────────────────────────────
# Stage: YOUTUBE
# ─────────────────────────────────────────────────────────────────
elif stage == "youtube":
    st.subheader("YouTube Transcripts")

    if st.session_state.yt_fetching:
        fetch_errors = []
        with st.spinner("Pulling transcripts..."):
            for vid in st.session_state.yt_pending:
                try:
                    transcript = run_in_thread(get_yt_transcripts, [vid])
                    if transcript and len(transcript) > 100:
                        title = get_video_title(vid)
                        save_to_research(f"YouTube — {title}", transcript[:10000], "YOUTUBE_TRANSCRIPT")
                    else:
                        fetch_errors.append(f"✗ No transcript found for {vid}")
                except Exception as e:
                    fetch_errors.append(f"✗ Failed for {vid}: {e}")
        st.session_state.yt_fetching = False
        st.session_state.yt_pending = []
        st.session_state.yt_results = fetch_errors
        st.rerun()
    else:
        with st.form("yt_form"):
            yt_input = st.text_area(
                "Paste YouTube URLs or video IDs (one per line or space-separated)",
                placeholder="https://youtube.com/watch?v=... or leave blank to skip",
                height=100,
            )
            col1, col2 = st.columns(2)
            with col1:
                fetch = st.form_submit_button("Fetch transcripts", use_container_width=True)
            with col2:
                skip = st.form_submit_button("Skip →", use_container_width=True)

        if fetch and yt_input.strip():
            st.session_state.yt_pending = [extract_video_id(v) for v in yt_input.strip().split()]
            st.session_state.yt_fetching = True
            st.rerun()

        if skip or (fetch and not yt_input.strip()):
            go_to("manual")
            st.rerun()

    # Show any fetch errors
    for err in (st.session_state.yt_results or []):
        st.warning(err)

    # Show fetched videos from research file
    yt_sources = [s for s in list_sources() if s["type"] == "YOUTUBE_TRANSCRIPT"]
    if yt_sources:
        st.divider()
        st.markdown(f"**Fetched videos ({len(yt_sources)}):**")
        for s in yt_sources:
            display_label = s["label"].removeprefix("YouTube — ")
            # Wrap long lines so content flows vertically rather than as one horizontal line
            transcript_text = "\n".join(
                textwrap.fill(line, width=100) if len(line) > 100 else line
                for line in s["content_block"].strip().splitlines()
            )
            with st.expander(display_label, expanded=len(yt_sources) == 1):
                st.code(transcript_text, language=None, height=400)
        st.divider()
        if st.button("Continue to manual sources →"):
            go_to("manual")
            st.rerun()


# ─────────────────────────────────────────────────────────────────
# Stage: MANUAL
# ─────────────────────────────────────────────────────────────────
elif stage == "manual":
    st.subheader("Manual Sources")

    MANUAL_TYPES = {"MANUAL_ARTICLE", "MANUAL_TWEET", "MANUAL_REDDIT", "MANUAL_PRESSER", "MANUAL_OTHER"}

    type_map = {
        "Article": "MANUAL_ARTICLE",
        "Tweet / tweet thread": "MANUAL_TWEET",
        "Reddit thread": "MANUAL_REDDIT",
        "Press conference transcript": "MANUAL_PRESSER",
        "Other": "MANUAL_OTHER",
    }

    with st.form(f"manual_form_{st.session_state.manual_form_key}"):
        source_type_label = st.selectbox("Source type", list(type_map.keys()))
        label = st.text_input("Short label", placeholder="e.g. Athletic — Laporta interview")
        content = st.text_area("Paste content here", height=250)
        col1, col2 = st.columns(2)
        with col1:
            add = st.form_submit_button("Add source", use_container_width=True)
        with col2:
            done = st.form_submit_button("Done → Extract research", use_container_width=True)

    if add:
        if label.strip() and content.strip():
            source_type = type_map[source_type_label]
            save_to_research(label.strip(), content.strip(), source_type)
            st.session_state.manual_entries.append({
                "type": source_type,
                "label": label.strip(),
                "content": content.strip(),
            })
            st.session_state.manual_form_key += 1
            st.rerun()
        else:
            st.warning("Label and content are required.")

    if done:
        go_to("extract")
        st.rerun()

    existing_manual = [s for s in list_sources() if s["type"] in MANUAL_TYPES]
    if existing_manual:
        st.divider()
        st.markdown(f"**Saved sources ({len(existing_manual)}):**")
        for s in existing_manual:
            with st.expander(s["label"], expanded=len(existing_manual) == 1):
                st.code(s["content_block"].strip(), language=None, height=400)


# ─────────────────────────────────────────────────────────────────
# Stage: EXTRACT & REVIEW
# ─────────────────────────────────────────────────────────────────
elif stage == "extract":
    # Process any pending removal before rendering anything
    if st.session_state.pending_remove is not None:
        remove_sources([st.session_state.pending_remove])
        st.session_state.pending_remove = None
        st.session_state.extracted = None
        st.rerun()

    st.subheader("Extracted Research")

    research = read_research()
    if not research or not research.strip():
        st.error("No research found. Please go back and add some research.")
        if st.button("← Start over"):
            go_to("grok_input")
            st.rerun()
        st.stop()

    # Run extraction if we don't have it yet
    if not st.session_state.extracted:
        with st.spinner("Extracting key facts from research..."):
            try:
                extracted = run_in_thread(extract_research, research)
                with open(EXTRACTED_FILE, "w", encoding="utf-8") as f:
                    f.write(extracted)
                st.session_state.extracted = extracted
                st.rerun()
            except Exception as e:
                st.error(f"Extraction failed: {e}")
                st.stop()

    st.code(st.session_state.extracted, language=None, height=400)
    st.divider()

    # Source list for removal
    sources = list_sources()
    if sources:
        st.markdown(f"**Sources ({len(sources)}):**")
        for i, s in enumerate(sources):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{i+1}.** {s['type']} — {s['label']}")
            with col2:
                if st.button("Remove", key=f"rm_{i}"):
                    st.session_state.pending_remove = i
                    st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✓ Happy — write brief →", use_container_width=True):
            go_to("direction")
            st.rerun()
    with col2:
        if st.button("Add more research", use_container_width=True):
            st.session_state.appending = True
            st.session_state.extracted = None
            st.session_state.yt_results = None
            go_to("grok_input")
            st.rerun()
    with col3:
        if st.button("Re-extract", use_container_width=True):
            st.session_state.extracted = None
            st.rerun()


# ─────────────────────────────────────────────────────────────────
# Stage: DIRECTION & FORMAT
# ─────────────────────────────────────────────────────────────────
elif stage == "direction":
    st.subheader("Direction & Format")

    strongest_angle = get_strongest_angle()
    if strongest_angle:
        st.info(f"**Suggested angle from research:** {strongest_angle}")

    with st.form("direction_form"):
        direction = st.text_area(
            "What do you want to say about this?",
            placeholder="Your editorial direction, angle, key argument...",
            height=120,
        )
        fmt = st.radio(
            "Format",
            options=["Long form", "Short", "Both"],
            horizontal=True,
        )
        submitted = st.form_submit_button("Generate brief →")

    if submitted:
        if not direction.strip():
            st.warning("Please enter a direction.")
        else:
            fmt_map = {"Long form": "long", "Short": "short", "Both": "both"}
            fmt_key = fmt_map[fmt]

            full_direction = (
                f"{direction.strip()}\n\nSTRONGEST ANGLE FROM RESEARCH: {strongest_angle}"
                if strongest_angle else direction.strip()
            )

            topic = get_topic_from_header() or "football video"

            with open(EXTRACTED_FILE, "r", encoding="utf-8") as f:
                extracted = f.read()

            with st.spinner("Generating your brief..."):
                try:
                    output = run_in_thread(generate_brief, extracted, full_direction, fmt_key, topic, fmt_key)
                    st.session_state.brief = output
                    go_to("output")
                    st.rerun()
                except Exception as e:
                    st.error(f"Brief generation failed: {e}")


# ─────────────────────────────────────────────────────────────────
# Stage: OUTPUT
# ─────────────────────────────────────────────────────────────────
elif stage == "output":
    st.subheader("Your Brief")

    brief = st.session_state.brief or ""
    st.code(brief, language=None, height=400)

    if st.button("Start new brief →"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
