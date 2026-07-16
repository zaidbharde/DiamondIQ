from markupsafe import escape


CUTS = ["Fair", "Good", "Very Good", "Premium", "Ideal"]
COLORS = ["D", "E", "F", "G", "H", "I", "J"]
CLARITIES = ["I1", "SI2", "SI1", "VS2", "VS1", "VVS2", "VVS1", "IF"]

NUMERIC_RULES = {
    "carat": {"label": "Carat", "min": 0.1, "max": 5.0},
    "depth": {"label": "Depth", "min": 40.0, "max": 80.0},
    "table": {"label": "Table", "min": 40.0, "max": 80.0},
    "x": {"label": "X dimension", "min": 1.0, "max": 15.0},
    "y": {"label": "Y dimension", "min": 1.0, "max": 15.0},
    "z": {"label": "Z dimension", "min": 0.5, "max": 10.0},
}


def sanitize_payload(payload):
    data = {}
    errors = {}

    for field, rule in NUMERIC_RULES.items():
        raw_value = payload.get(field, "")
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            errors[field] = f"{rule['label']} must be a number."
            continue

        if value < rule["min"] or value > rule["max"]:
            errors[field] = f"{rule['label']} must be between {rule['min']} and {rule['max']}."
        else:
            data[field] = round(value, 3)

    cut = str(escape(payload.get("cut", ""))).strip()
    color = str(escape(payload.get("color", ""))).strip()
    clarity = str(escape(payload.get("clarity", ""))).strip()

    if cut not in CUTS:
        errors["cut"] = "Choose a valid cut grade."
    else:
        data["cut"] = cut

    if color not in COLORS:
        errors["color"] = "Choose a valid color grade."
    else:
        data["color"] = color

    if clarity not in CLARITIES:
        errors["clarity"] = "Choose a valid clarity grade."
    else:
        data["clarity"] = clarity

    return data, errors
