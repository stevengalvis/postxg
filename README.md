# ⚽📊 PostXG — AI Football Content Pipeline

> From raw research to publish-ready briefs in minutes.

**Live demo:** [postxg.streamlit.app](https://postxg.streamlit.app)

---

## What is PostXG?

PostXG is an AI-powered content pipeline for football creators. It takes raw research from live social data, YouTube transcripts, and manual sources and produces structured, publish-ready briefs for any content format: video scripts, talking points, social posts, or written pieces.

Built and used in production.

---

## How it works
```
Grok Search (live social data)
YouTube Transcripts (via Supadata)
Manual Sources (articles, tweets, press conferences)
        ↓
Claude Haiku — Extraction & Structuring
        ↓
Review & Direction
        ↓
Claude Opus — Brief Generation
        ↓
Output: Titles, Hooks, Script, Talking Points, Closing Questions, Description
        ↓
Telegram — Brief delivered to phone
```

---

## Key product decisions

**Model selection at each step**
Haiku for extraction (fast, cheap, structured output), Opus for brief writing (best quality for creative output). Total cost per run: ~10 cents.

**Hallucination guard**
Extraction prompt explicitly forbids assigning roles not stated in research. Caught real errors in testing (e.g. misidentifying a player as a manager from YouTube transcript context).

**Output designed for filming**
Short script has a hard 45-word limit and is broken into individual lines for on-camera reading. Long form includes a Quick Reference section with stats, tweets, and quotes to read directly on camera.

**Source attribution**
Every talking point is tagged [Grok], [YouTube], or [Manual] so the creator knows where each claim came from.

**Deduplication rule**
No stat, quote, or fact appears more than once across the entire output.

**Three interfaces**
Terminal (development), Telegram bot (mobile, always-on via systemd), Streamlit UI (web, shareable).

---

## Tech stack

| Layer | Tool |
|---|---|
| Live research | Grok API |
| YouTube transcripts | Supadata API |
| Extraction | Claude Haiku |
| Brief writing | Claude Opus |
| Notifications | Telegram Bot |
| Web UI | Streamlit |
| Infrastructure | Hetzner VPS, Ubuntu 24.04 |
| Always-on service | systemd |

---

## Cost per run

| Step | Cost |
|---|---|
| Grok search | ~3 cents |
| Haiku extraction | ~0.5 cents |
| Opus brief (both formats) | ~6 cents |
| **Total** | **~10 cents** |

---

## Status

In active use. Two videos produced and published using PostXG output.
