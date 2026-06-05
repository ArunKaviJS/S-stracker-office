KEYWORD_MAP = {
    "Oiling & Greasing": ["oil", "grease", "lubricant", "lube"],
    "Parts Replacement": ["part", "replace", "replacement"],
    "Broken & Needs Welding": ["weld", "broken", "welding"],
    "Accident": ["accident", "crash", "collision", "damage"],
}

VALID_REASONS = [
    "Oiling & Greasing",
    "Parts Replacement",
    "Broken & Needs Welding",
    "Accident",
]

def map_reason(reason):

    if reason in VALID_REASONS:
        return reason

    # Handle "Others- ..." prefix
    txt = reason.lower()
    if txt.startswith("others-"):
        txt = txt.replace("others-", "").strip()

    best_reason = "Accident"   # default fallback for unmatched
    best_score = 0

    for category, keywords in KEYWORD_MAP.items():
        score = sum(kw in txt for kw in keywords)
        if score > best_score:
            best_score = score
            best_reason = category

    return best_reason