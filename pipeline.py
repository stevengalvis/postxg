from skills.extract import extract_research
from skills.generate_brief import generate_brief
from research_store import read_research, get_strongest_angle, save_to_research, EXTRACTED_FILE
from skills.get_grok_news import get_grok_news


def run_extraction_pipeline() -> str:
    research = read_research()

    if not research:
        raise ValueError("No research found.")

    extracted = extract_research(research)

    with open(EXTRACTED_FILE, "w", encoding="utf-8") as f:
        f.write(extracted)
    
    return extracted

def run_brief_pipeline(extracted: str, direction: str, fmt: str, topic: str) -> str:
    strongest_angle = get_strongest_angle()

    if strongest_angle:
        full_direction = f"{direction}\n\nSTRONGEST ANGLE FROM RESEARCH: {strongest_angle}"
    else:
        full_direction = direction
    
    return generate_brief(extracted, full_direction, fmt, topic, fmt)


def run_grok_research_pipeline(topic: str, appending: bool = False) -> str:
    existing = read_research() if appending else None

    result = get_grok_news(topic, context=existing)

    save_to_researc(
        label=f"Grok search - {topic}",
        content=result,
        source_type="GROK_SEARCH",
    )
    return result
