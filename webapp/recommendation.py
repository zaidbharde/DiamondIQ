CUT_SCORE = {"Fair": 1, "Good": 2, "Very Good": 3, "Premium": 4, "Ideal": 5}
COLOR_SCORE = {"J": 1, "I": 2, "H": 3, "G": 4, "F": 5, "E": 6, "D": 7}
CLARITY_SCORE = {
    "I1": 1, "SI2": 2, "SI1": 3, "VS2": 4,
    "VS1": 5, "VVS2": 6, "VVS1": 7, "IF": 8,
}


def get_recommendation(inputs):
    """Determine recommendation category using deterministic rules.

    Categories (highest to lowest):
        Luxury Grade     — Ideal cut, D-F color, IF-VVS1 clarity, >=1.5ct
        Premium Diamond   — Premium+ cut, D-G color, VVS2+ clarity, >=1.0ct
        Good Value        — Very Good+ cut, G-H color, SI1+ clarity, >=0.7ct
        Average Market    — Good+ cut, H-J color, SI2+ clarity, >=0.3ct
        Needs Review      — Below thresholds or entry-level
    """
    cut = inputs["cut"]
    color = inputs["color"]
    clarity = inputs["clarity"]
    carat = inputs["carat"]

    cut_val = CUT_SCORE.get(cut, 1)
    color_val = COLOR_SCORE.get(color, 1)
    clarity_val = CLARITY_SCORE.get(clarity, 1)

    # Luxury Grade
    if (
        cut_val >= 5
        and color_val >= 5
        and clarity_val >= 7
        and carat >= 1.5
    ):
        return {"label": "Luxury Grade", "badge": "premium"}

    # Premium Diamond
    if (
        cut_val >= 4
        and color_val >= 4
        and clarity_val >= 6
        and carat >= 1.0
    ):
        return {"label": "Premium Diamond", "badge": "premium"}

    # Good Value
    if (
        cut_val >= 3
        and color_val >= 3
        and clarity_val >= 3
        and carat >= 0.7
    ):
        return {"label": "Good Value", "badge": "good"}

    # Average Market Value
    if (
        cut_val >= 2
        and color_val >= 2
        and clarity_val >= 2
        and carat >= 0.3
    ):
        return {"label": "Average Market Value", "badge": "average"}

    # Needs Professional Review
    return {"label": "Needs Professional Review", "badge": "review"}
