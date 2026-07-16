CUT_SCORE = {"Fair": 1, "Good": 2, "Very Good": 3, "Premium": 4, "Ideal": 5}
COLOR_SCORE = {"J": 1, "I": 2, "H": 3, "G": 4, "F": 5, "E": 6, "D": 7}
CLARITY_SCORE = {
    "I1": 1, "SI2": 2, "SI1": 3, "VS2": 4,
    "VS1": 5, "VVS2": 6, "VVS1": 7, "IF": 8,
}

# Scoring formula (0-100):
#   Cut     (0-30 pts):  (cut_score/5) * 30
#   Color   (0-25 pts):  (color_score/7) * 25
#   Clarity (0-25 pts):  (clarity_score/8) * 25
#   Carat   (0-20 pts):  min(carat/3.0, 1.0) * 20
# Total: max 100 (when Ideal/D/IF/3.0+ct)
WEIGHT_CUT = 30
WEIGHT_COLOR = 25
WEIGHT_CLARITY = 25
WEIGHT_CARAT = 20


def compute_quality_score(inputs):
    """Compute diamond quality score from 0 to 100.

    Based on:
    - Cut (30%): Fair=1 → Ideal=5
    - Color (25%): J=1 → D=7
    - Clarity (25%): I1=1 → IF=8
    - Carat weight (20%): normalized to 3.0 ct maximum
    """
    cut_val = CUT_SCORE.get(inputs["cut"], 1)
    color_val = COLOR_SCORE.get(inputs["color"], 1)
    clarity_val = CLARITY_SCORE.get(inputs["clarity"], 1)
    carat_val = min(inputs["carat"] / 3.0, 1.0)

    score = (
        (cut_val / 5) * WEIGHT_CUT
        + (color_val / 7) * WEIGHT_COLOR
        + (clarity_val / 8) * WEIGHT_CLARITY
        + carat_val * WEIGHT_CARAT
    )
    return round(min(max(score, 0), 100), 1)


def quality_score_explanation(inputs):
    parts = []
    cut_val = CUT_SCORE.get(inputs["cut"], 1)
    color_val = COLOR_SCORE.get(inputs["color"], 1)
    clarity_val = CLARITY_SCORE.get(inputs["clarity"], 1)

    if cut_val >= 4:
        parts.append(f"Cut ({inputs['cut']}, {cut_val}/5) contributes {round((cut_val / 5) * WEIGHT_CUT, 1)} pts")
    elif cut_val <= 2:
        parts.append(f"Cut ({inputs['cut']}, {cut_val}/5) contributes {round((cut_val / 5) * WEIGHT_CUT, 1)} pts — consider upgrading")
    else:
        parts.append(f"Cut ({inputs['cut']}, {cut_val}/5) contributes {round((cut_val / 5) * WEIGHT_CUT, 1)} pts")

    if color_val >= 5:
        parts.append(f"Color ({inputs['color']}, {color_val}/7) contributes {round((color_val / 7) * WEIGHT_COLOR, 1)} pts")
    elif color_val <= 3:
        parts.append(f"Color ({inputs['color']}, {color_val}/7) contributes {round((color_val / 7) * WEIGHT_COLOR, 1)} pts — lower grade")
    else:
        parts.append(f"Color ({inputs['color']}, {color_val}/7) contributes {round((color_val / 7) * WEIGHT_COLOR, 1)} pts")

    if clarity_val >= 6:
        parts.append(f"Clarity ({inputs['clarity']}, {clarity_val}/8) contributes {round((clarity_val / 8) * WEIGHT_CLARITY, 1)} pts")
    elif clarity_val <= 3:
        parts.append(f"Clarity ({inputs['clarity']}, {clarity_val}/8) contributes {round((clarity_val / 8) * WEIGHT_CLARITY, 1)} pts — visible inclusions")
    else:
        parts.append(f"Clarity ({inputs['clarity']}, {clarity_val}/8) contributes {round((clarity_val / 8) * WEIGHT_CLARITY, 1)} pts")

    carat_pct = min(inputs["carat"] / 3.0, 1.0)
    carat_pts = round(carat_pct * WEIGHT_CARAT, 1)
    if inputs["carat"] >= 1.5:
        carat_note = f"Carat ({inputs['carat']} ct) contributes {carat_pts} pts — substantial weight"
    elif inputs["carat"] >= 0.7:
        carat_note = f"Carat ({inputs['carat']} ct) contributes {carat_pts} pts — moderate weight"
    else:
        carat_note = f"Carat ({inputs['carat']} ct) contributes {carat_pts} pts — smaller stone"
    parts.append(carat_note)

    return "Quality Score Breakdown: " + "; ".join(parts)
