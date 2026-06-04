KEYWORD_MAP = {
    "Wheel Alignment": ["wheel","align"],
    "Oiling & Greasing": ["oil","grease"],
    "Cleaning & Inspection": ["clean","inspect"],
    "Parts Replacement": ["replace","part"],
    "Battery replaced": ["battery","charge"],
    "Brake Adjustment": ["brake"],
    "Motor Failure": ["motor","engine"],
    "Broken & Needs Welding": ["weld","broken"],
    "Frame Damage": ["frame","dent"],
    "Structural Damage": ["structural"],
    "Accident": ["accident","crash"]
}


VALID_REASONS = [
    "Wheel Alignment",
    "Oiling & Greasing",
    "Cleaning & Inspection",
    "Parts Replacement",
    "Battery replaced",
    "Brake Adjustment",
    "Motor Failure",
    "Broken & Needs Welding",
    "Frame Damage",
    "Structural Damage",
    "Accident"
]


def map_reason(reason):

    if reason in VALID_REASONS:
        return reason

    txt = reason.lower()

    best_reason = "Structural Damage"
    best_score = 0

    for category, keywords in KEYWORD_MAP.items():

        score = sum(
            kw in txt
            for kw in keywords
        )

        if score > best_score:
            best_score = score
            best_reason = category

    return best_reason