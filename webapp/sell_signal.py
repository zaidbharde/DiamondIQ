from .database import list_predictions
from .quality_score import CLARITY_SCORE


GOOD_QUALITY_THRESHOLD = 65
MIN_COMPARABLES = 3
DELTA_THRESHOLD = 10


def clarity_band(clarity):
    score = CLARITY_SCORE.get(clarity, 0)
    if score <= 3:
        return "included"
    if score <= 5:
        return "near_eye_clean"
    return "high_clarity"


def get_sell_signal(inputs, predicted_price, quality_score, database_path):
    """Return a relative sell/hold/wait signal from local prediction history.

    This intentionally does not use live market data. It compares the current
    valuation against similar predictions already saved by this app.
    """
    history = list_predictions(database_path, page=1, per_page=100000)["items"]
    target_band = clarity_band(inputs["clarity"])

    comparable = [
        item
        for item in history
        if item.get("inputs", {}).get("cut") == inputs["cut"]
        and item.get("inputs", {}).get("color") == inputs["color"]
        and clarity_band(item.get("inputs", {}).get("clarity")) == target_band
        and item.get("price") is not None
    ]

    if len(comparable) < MIN_COMPARABLES:
        return {
            "signal": "insufficient_data",
            "comparable_count": len(comparable),
            "comparable_avg_price": None,
            "delta_pct": None,
            "reasoning": (
                "Not enough similar predictions in your history yet to make "
                "a relative sell or hold call."
            ),
        }

    avg_price = sum(float(item["price"]) for item in comparable) / len(comparable)
    delta_pct = ((float(predicted_price) - avg_price) / avg_price) * 100 if avg_price else 0

    if quality_score < GOOD_QUALITY_THRESHOLD:
        signal = "wait"
        reasoning = (
            f"Quality score is {quality_score}/100, below the good threshold, "
            "so waiting or reviewing the stone is the safer relative signal."
        )
    elif delta_pct >= DELTA_THRESHOLD:
        signal = "sell_now"
        reasoning = (
            f"Priced {round(delta_pct, 1)}% above similar diamonds in your "
            "prediction history - favorable relative valuation."
        )
    elif abs(delta_pct) <= DELTA_THRESHOLD:
        signal = "hold"
        reasoning = (
            f"Priced within {round(abs(delta_pct), 1)}% of similar diamonds "
            "in your prediction history - a neutral relative valuation."
        )
    else:
        signal = "wait"
        reasoning = (
            f"Priced {round(abs(delta_pct), 1)}% below similar diamonds in "
            "your prediction history - waiting may be more sensible."
        )

    return {
        "signal": signal,
        "comparable_count": len(comparable),
        "comparable_avg_price": round(avg_price, 2),
        "delta_pct": round(delta_pct, 1),
        "reasoning": reasoning,
    }
