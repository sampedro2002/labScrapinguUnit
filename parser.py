import re

def parse_number(text):
    if not text:
        return None
    text = text.strip().lower().replace(",", "")
    m = re.match(r"([\d\.]+)([km]?)", text)
    if not m:
        return None
    n = float(m.group(1))
    s = m.group(2)
    if s == "k": n *= 1_000
    elif s == "m": n *= 1_000_000
    return int(n)

def extract_stats(meta):
    meta = meta.replace(",", "")
    out = {}
    for key, pat in {
        "followers": r"([\d\.]+[km]?)\s+(seguidores|followers)",
        "following": r"([\d\.]+[km]?)\s+(siguiendo|following)",
        "posts": r"([\d\.]+[km]?)\s+(publicaciones|posts)"
    }.items():
        m = re.search(pat, meta, re.IGNORECASE)
        out[key] = parse_number(m.group(1)) if m else None
    return out