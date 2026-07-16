import json
from datetime import datetime, timezone

from .quality_score import compute_quality_score, quality_score_explanation
from .recommendation import get_recommendation


def generate_report(prediction_result, inputs, raw_payload=None):
    """Generate the full valuation report dict.

    Args:
        prediction_result: dict from PredictionService.predict()
        inputs: sanitized input dict
        raw_payload: original request payload (may contain _source, _detected,
                     shape, certificate_number)

    Returns:
        dict with all report sections
    """
    payload = raw_payload or {}
    source = payload.get("_source", "manual")
    detected_raw = payload.get("_detected") or "{}"
    try:
        detected = json.loads(detected_raw) if isinstance(detected_raw, str) else detected_raw
    except (TypeError, json.JSONDecodeError):
        detected = {}

    quality = compute_quality_score(inputs)
    recommendation = get_recommendation(inputs)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return {
        "quality_score": quality,
        "quality_explanation": quality_score_explanation(inputs),
        "recommendation": recommendation,
        "ai_explanation": _generate_explanation(
            prediction_result, inputs, source, detected
        ),
        "input_summary": _build_input_summary(inputs, payload, detected),
        "source": source,
        "detected": detected,
        "timestamp": timestamp,
    }


def _generate_explanation(prediction_result, inputs, source, detected):
    price = prediction_result["price"]
    reasons = []

    # Source context
    if source == "certificate":
        reasons.append("based on the uploaded certificate and the provided specifications")
    elif source == "image":
        reasons.append("based on the uploaded diamond image and the provided specifications")
    else:
        reasons.append("based on the provided diamond specifications")

    # Cut
    cut_val = {"Fair": 1, "Good": 2, "Very Good": 3, "Premium": 4, "Ideal": 5}
    if cut_val.get(inputs["cut"], 0) >= 4:
        reasons.append(f"the {inputs['cut']} cut quality is high")
    elif cut_val.get(inputs["cut"], 0) <= 2:
        reasons.append(f"the {inputs['cut']} cut quality is moderate")

    # Color
    color_val = {"D": 7, "E": 6, "F": 5, "G": 4, "H": 3, "I": 2, "J": 1}
    if color_val.get(inputs["color"], 0) >= 5:
        reasons.append(f"the {inputs['color']} color grade is desirable")
    elif color_val.get(inputs["color"], 0) <= 3:
        reasons.append(f"the {inputs['color']} color grade is standard")

    # Clarity
    clarity_val = {"IF": 8, "VVS1": 7, "VVS2": 6, "VS1": 5, "VS2": 4, "SI1": 3, "SI2": 2, "I1": 1}
    if clarity_val.get(inputs["clarity"], 0) >= 6:
        reasons.append(f"clarity grade {inputs['clarity']} indicates few inclusions")
    elif clarity_val.get(inputs["clarity"], 0) <= 3:
        reasons.append(f"clarity grade {inputs['clarity']} has visible inclusions")

    # Carat
    if inputs["carat"] >= 1.5:
        reasons.append("the substantial carat weight adds significant value")
    elif inputs["carat"] >= 0.7:
        reasons.append("the carat weight contributes positively to the valuation")
    else:
        reasons.append("the modest carat weight keeps the price accessible")

    # Detect differences between detected and submitted values
    if detected and source in ("certificate", "image"):
        diffs = []
        for key in ("cut", "color", "clarity", "carat"):
            detected_val = detected.get(key, {}).get("value") if isinstance(detected.get(key), dict) else detected.get(key)
            submitted_val = inputs.get(key)
            if detected_val and submitted_val and str(detected_val) != str(submitted_val):
                diffs.append(f"{key} ({detected_val} → {submitted_val})")
        if diffs:
            reasons.append("some specifications were adjusted after review: " + "; ".join(diffs))

    # Direction
    direction = "higher" if price >= 4500 else "more affordable"

    return (
        f"This valuation is {', '.join(reasons)}. "
        f"The estimated market value of ₹{price:,.2f} reflects a {direction} "
        f"end of the market range."
    )


def _build_input_summary(inputs, payload, detected):
    summary = {}

    for key in ("shape", "carat", "cut", "color", "clarity",
                "depth", "table", "x", "y", "z"):
        val = inputs.get(key)
        if val is not None:
            summary[key] = val

    cert_number = inputs.get("certificate_number") or payload.get("certificate_number")
    if cert_number:
        summary["certificate_number"] = cert_number

    return summary
