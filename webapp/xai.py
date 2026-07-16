"""Deterministic Explainable AI module.

Provides feature-level explanations for every prediction using
deterministic rules (no external ML explainability library required).
"""

CUT_SCORE = {"Fair": 1, "Good": 2, "Very Good": 3, "Premium": 4, "Ideal": 5}
COLOR_SCORE = {"J": 1, "I": 2, "H": 3, "G": 4, "F": 5, "E": 6, "D": 7}
CLARITY_SCORE = {
    "I1": 1, "SI2": 2, "SI1": 3, "VS2": 4,
    "VS1": 5, "VVS2": 6, "VVS1": 7, "IF": 8,
}


def analyze_features(inputs, prediction_price):
    """Analyze features and return positive factors, negative factors,
    and most influential features ranked by impact.

    Returns:
        dict with keys:
        - positive_factors: list of {feature, reason, impact}
        - negative_factors: list of {feature, reason, impact}
        - most_influential: list of {feature, impact_percent}
    """
    positive = []
    negative = []
    contributions = _compute_contributions(inputs, prediction_price)
    contributions.sort(key=lambda c: c["impact"], reverse=True)

    for c in contributions:
        feature = c["feature"]
        impact = c["impact"]
        score = c["score"]

        if score >= 5:
            if feature == "Carat weight":
                positive.append({
                    "feature": "Carat Weight",
                    "reason": f"At {inputs['carat']} ct, the weight is a strong value driver",
                    "impact": round(impact, 2),
                })
            elif feature == "Cut grade":
                positive.append({
                    "feature": "Cut Grade",
                    "reason": f"The {inputs['cut']} cut grade enhances light performance and value",
                    "impact": round(impact, 2),
                })
            elif feature == "Color grade":
                positive.append({
                    "feature": "Color Grade",
                    "reason": f"{inputs['color']} color grade is above average and commands a premium",
                    "impact": round(impact, 2),
                })
            elif feature == "Clarity grade":
                positive.append({
                    "feature": "Clarity Grade",
                    "reason": f"{inputs['clarity']} clarity indicates a clean stone",
                    "impact": round(impact, 2),
                })
            elif feature == "Proportions":
                positive.append({
                    "feature": "Proportions",
                    "reason": "Balanced depth and table proportions maximize brilliance",
                    "impact": round(impact, 2),
                })
            elif feature == "Dimensions":
                positive.append({
                    "feature": "Dimensions",
                    "reason": "Favorable dimensions contribute to visual appeal",
                    "impact": round(impact, 2),
                })

    # Negative factors (features with low scores)
    for c in contributions:
        if c["score"] < 5 and c["score"] > 0:
            feature = c["feature"]
            impact = c["impact"]
            if feature == "Carat weight":
                negative.append({
                    "feature": "Carat Weight",
                    "reason": f"At {inputs['carat']} ct, the weight is below premium thresholds",
                    "impact": round(impact, 2),
                })
            elif feature == "Cut grade":
                negative.append({
                    "feature": "Cut Grade",
                    "reason": f"The {inputs['cut']} cut grade limits potential value",
                    "impact": round(impact, 2),
                })
            elif feature == "Color grade":
                negative.append({
                    "feature": "Color Grade",
                    "reason": f"{inputs['color']} color grade is standard rather than premium",
                    "impact": round(impact, 2),
                })
            elif feature == "Clarity grade":
                negative.append({
                    "feature": "Clarity Grade",
                    "reason": f"{inputs['clarity']} clarity has visible characteristics",
                    "impact": round(impact, 2),
                })
            elif feature == "Proportions":
                negative.append({
                    "feature": "Proportions",
                    "reason": "Depth and table proportions fall outside ideal ranges",
                    "impact": round(impact, 2),
                })
            elif feature == "Dimensions":
                negative.append({
                    "feature": "Dimensions",
                    "reason": "Dimensions are modest compared to larger stones",
                    "impact": round(impact, 2),
                })

    # Most influential features ranked
    total = sum(c["impact"] for c in contributions) or 1
    most_influential = [
        {"feature": c["feature"], "impact_percent": round(c["impact"] / total * 100, 1)}
        for c in contributions
    ]

    return {
        "positive_factors": positive,
        "negative_factors": negative,
        "most_influential": most_influential,
        "total_impact": round(prediction_price, 2),
    }


def _compute_contributions(inputs, prediction):
    """Replicate the contribution logic from ml_service.py to keep XAI self-contained."""
    carat = min(inputs["carat"] / 3.0, 1.0) * 44
    dimensions = min((inputs["x"] + inputs["y"] + inputs["z"]) / 30.0, 1.0) * 16
    cut = CUT_SCORE.get(inputs["cut"], 1) / 5 * 14
    color = COLOR_SCORE.get(inputs["color"], 1) / 7 * 12
    clarity = CLARITY_SCORE.get(inputs["clarity"], 1) / 8 * 12
    proportions = 8 if 58 <= inputs["depth"] <= 64 and 53 <= inputs["table"] <= 60 else 4
    values = {
        "Carat weight": carat,
        "Dimensions": dimensions,
        "Cut grade": cut,
        "Color grade": color,
        "Clarity grade": clarity,
        "Proportions": proportions,
    }
    total = sum(values.values()) or 1
    return [
        {"feature": key, "score": round(value / total * 100, 1), "impact": round(prediction * value / total, 2)}
        for key, value in values.items()
    ]
