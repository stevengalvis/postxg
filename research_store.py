import os
from datetime import date

RESEARCH_FILE = "research/latest.txt"
EXTRACTED_FILE = "research/extracted.txt"
SEPARATOR = '═' * 40

# moving these functions here
# list_sources
# remove_sources
# get_strongest_angle

def save_to_research(label: str, content: str, source_type: str = "UNKNOWN"):
    os.makedirs(os.path.dirname(RESEARCH_FILE), exist_ok=True)
    with open(RESEARCH_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{SEPARATOR}\n")
        f.write(f"SOURCE: {source_type}\n")
        f.write(f"LABEL: {label}\n")
        f.write(f"{SEPARATOR}\n")
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
    
    with open (RESEARCH_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    header = {}

    for line in lines[:5]:
        if line.startswith("TOPIC:"):
            header["topic"]=line.replace("TOPI:", "").strip()
        if line.startswith("DATE:"):
            header["date"] = line.replace("DATE:", "").strip()

    return header

def set_research_header(topic: str):
    os.makedirs(os.path.dirname(RESEARCH_FILE), exist_ok=True)
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

def get_strongest_angle() -> str:
    if not os.path.exists(EXTRACTED_FILE):
        return ""
    
    with open(EXTRACTED_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    for line in content.split("\n"):
        if line.startswith("Strongest angle:"):
            return line.replace("Strongest angle:", "").strip()
    
    return ""






def _parse_source_blocks(content: str) -> list[dict]:
    blocks = content.split(SEPARATOR)
    sources = []
    idx = 1

    i = 1
    while i < len(blocks) - 1:
        meta_block = blocks[i].strip()
        content_block = blocks[i+1].strip()

        lines = meta_block.split("\n")

        source = None
        label = None

        for line in lines:
            if line.startswith("SOURCE:"):
                source = line.replace("SOURCE:", "").strip()
            if line.startswith("LABEL:"):
                label = line.replace("LABEL:", "").strip()

        if source or label:
            sources.append({
                "index": idx,
                "source": source,
                "label": label,
                "meta_block": meta_block,
                "content_block": content_block
            })
            idx += 1
        
        i +=2
    return sources



def list_sources() -> list[dict]:
    if not os.path.exists(RESEARCH_FILE):
        return []
    
    with open(RESEARCH_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    sources = _parse_source_blocks(content)

    return [
        {
            "index": s["index"],
            "source": s["source"],
            "label": s["label"]
        }
        for s in sources
    ]

def remove_sources(indices: list[int]):
    if not os.path.exists(RESEARCH_FILE):
        return

    with open(RESEARCH_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    sources = _parse_source_blocks(content)

    #keep only sources not in indices
    remaining = [s for s in sources if s["index"] not in indices]

    if not remaining:
        print("No sources left after removal. Aborting")
        return

    with open(RESEARCH_FILE, "w", encoding="utf-8") as f:
        for s in remaining:
           f.write(f"{SEPARATOR}\n")
           f.write(s["meta_block"] + "\n")
           f.write(f"{SEPARATOR}\n")
           f.write(s["content_block"] + "\n\n")
