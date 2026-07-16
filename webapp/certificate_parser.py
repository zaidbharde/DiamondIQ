import re

CUT_VALUES = {"fair", "good", "very good", "premium", "ideal"}
COLOR_VALUES = {"d", "e", "f", "g", "h", "i", "j"}
CLARITY_VALUES = {"if", "vvs1", "vvs2", "vs1", "vs2", "si1", "si2", "i1", "i2", "i3"}
FLUOR_VALUES = {"none", "faint", "medium", "strong", "very strong"}
POLISH_VALUES = {"excellent", "very good", "good", "fair", "poor"}
SYMMETRY_VALUES = {"excellent", "very good", "good", "fair", "poor"}


def detect_certificate_type(text_blocks):
    full_text = " ".join(block[0] for block in text_blocks).lower()
    if "gia" in full_text and ("report" in full_text or "grading" in full_text):
        return "GIA"
    if "igi" in full_text:
        return "IGI"
    return "UNKNOWN"


def parse_certificate(text_blocks, cert_type):
    raw = "\n".join(block[0] for block in text_blocks)
    full_text = _normalize_ocr_text(raw)
    result = {
        "fields": {},
        "raw_text": raw,
    }

    parsers = {
        "GIA": _parse_gia,
        "IGI": _parse_igi,
    }

    parser = parsers.get(cert_type)
    if parser:
        result["fields"] = parser(full_text)

    # Fill missing numeric fields from any pattern
    _fill_missing_numeric(full_text, result["fields"])

    return result


def _normalize_ocr_text(text):
    """Fix common OCR artifacts in certificate text.

    Handles:
    - "Cara" + "Weight" -> "Carat Weight"
    - "Clari" + "y" -> "Clarity"
    - "Dept!" + "h" -> "Depth"
    - "Polis" + "h" -> "Polish"
    - "Symmetr" + "y" -> "Symmetry"
    - "Fluor" + "escence" -> "Fluorescence"
    """
    replacements = [
        (r"\bCara\b(?:\s+Weight)?", "Carat"),
        (r"\bClari\s*y\b", "Clarity"),
        (r"\bDept[!1]?\s*h\s*:", "Depth:"),
        (r"\bPolis\s*h\s*:", "Polish:"),
        (r"\bSymmetr\s*y\b", "Symmetry"),
        (r"\bFluor\s*escence\b", "Fluorescence"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _parse_gia(text):
    fields = {}
    lower = text.lower()

    # Certificate number
    m = re.search(r"(?:GIA\s*)?(?:Report\s*)?#?\s*(\d{6,10})", text)
    if m:
        fields["certificate_number"] = {"value": m.group(1), "confidence": _conf_from_match(m, text)}

    # Shape
    m = re.search(
        r"Shape\s*(?:and\s*Cutting\s*Style)?[:\s]*\n?\s*([A-Za-z]+(?:[^\S\n]+[A-Za-z]+)*)",
        text,
        re.IGNORECASE,
    )
    if m:
        fields["shape"] = {"value": m.group(1).strip(), "confidence": _conf_from_match(m, text)}

    # Carat
    m = re.search(r"(?:Carat\s*Weight[:\s]*|Carat\s*)[:\s]*(\d+\.?\d*)\s*(?:carat|ct)", text, re.IGNORECASE)
    if m:
        fields["carat"] = {"value": m.group(1), "confidence": _conf_from_match(m, text)}

    # Color
    m = re.search(r"Color\s*(?:Grade)?[:\s]*\n?\s*([A-Z])", text)
    if m and m.group(1).lower() in COLOR_VALUES:
        fields["color"] = {"value": m.group(1).upper(), "confidence": _conf_from_match(m, text)}

    # Clarity
    m = re.search(r"Clarity\s*(?:Grade)?[:\s]*\n?\s*([A-Za-z0-9]+(?:[^\S\n]+[A-Za-z0-9]+)?)", text)
    if m:
        val = re.sub(r"\s+", "", m.group(1).strip().lower())
        if val in CLARITY_VALUES:
            fields["clarity"] = {"value": val.upper(), "confidence": _conf_from_match(m, text)}

    # Cut
    m = re.search(r"\bCut\b\s*(?:Grade)?[:\s]*\n?\s*([A-Za-z]+(?:[^\S\n]+[A-Za-z]+)?)", text)
    if m:
        val = m.group(1).strip().lower()
        if val in CUT_VALUES:
            fields["cut"] = {"value": val.title(), "confidence": _conf_from_match(m, text)}

    # Depth
    m = re.search(r"(?:Depth|Total Depth)[:\s]*\n?\s*(\d+\.?\d*)\s*%", text, re.IGNORECASE)
    if m:
        fields["depth"] = {"value": m.group(1), "confidence": _conf_from_match(m, text)}

    # Table
    m = re.search(r"Table[:\s]*\n?\s*(\d+\.?\d*)\s*%", text, re.IGNORECASE)
    if m:
        fields["table"] = {"value": m.group(1), "confidence": _conf_from_match(m, text)}

    # Measurements
    m = re.search(
        r"Measurements?[:\s]*\n?\s*(\d+\.?\d*)\s*(?:-|x)\s*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)",
        text,
        re.IGNORECASE,
    )
    if m:
        fields["x"] = {"value": m.group(1), "confidence": _conf_from_match(m, text)}
        fields["y"] = {"value": m.group(2), "confidence": _conf_from_match(m, text)}
        fields["z"] = {"value": m.group(3), "confidence": _conf_from_match(m, text)}

    # Polish
    m = re.search(r"Polish[:\s]*\n?\s*([A-Za-z]+(?:[^\S\n]+[A-Za-z]+)*)", text)
    if m:
        val = m.group(1).strip().lower()
        if val in POLISH_VALUES:
            fields["polish"] = {"value": val.title(), "confidence": _conf_from_match(m, text)}

    # Symmetry
    m = re.search(r"Symmetry[:\s]*\n?\s*([A-Za-z]+(?:[^\S\n]+[A-Za-z]+)*)", text)
    if m:
        val = m.group(1).strip().lower()
        if val in SYMMETRY_VALUES:
            fields["symmetry"] = {"value": val.title(), "confidence": _conf_from_match(m, text)}

    # Fluorescence
    m = re.search(r"Fluorescence[:\s]*\n?\s*([A-Za-z]+(?:[^\S\n]+[A-Za-z]+)*)", text)
    if m:
        val = m.group(1).strip().lower()
        matched = _match_fuzzy(val, FLUOR_VALUES)
        if matched:
            fields["fluorescence"] = {"value": matched.title(), "confidence": _conf_from_match(m, text)}

    return fields


def _parse_igi(text):
    fields = {}
    lower = text.lower()

    # Certificate number
    m = re.search(r"(?:IGI\s*)?(?:Report\s*)?#?\s*(\d{6,10})", text)
    if m:
        fields["certificate_number"] = {"value": m.group(1), "confidence": _conf_from_match(m, text)}

    # Shape
    m = re.search(r"Shape[:\s]*\n?\s*([A-Za-z]+(?:[^\S\n]+[A-Za-z]+)*)", text, re.IGNORECASE)
    if m:
        fields["shape"] = {"value": m.group(1).strip(), "confidence": _conf_from_match(m, text)}

    # Carat
    m = re.search(r"(?:Carat\s*Weight[:\s]*|Carat\s*)[:\s]*(\d+\.?\d*)\s*(?:carat|ct)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"Weight[:\s]*(\d+\.?\d*)\s*(?:carat|ct)", text, re.IGNORECASE)
    if m:
        fields["carat"] = {"value": m.group(1), "confidence": _conf_from_match(m, text)}

    # Color
    m = re.search(r"Color[:\s]*\n?\s*([A-Z])", text)
    if m and m.group(1).lower() in COLOR_VALUES:
        fields["color"] = {"value": m.group(1).upper(), "confidence": _conf_from_match(m, text)}

    # Clarity
    m = re.search(r"Clarity[:\s]*\n?\s*([A-Za-z0-9]+(?:[^\S\n]+[A-Za-z0-9]+)?)", text)
    if m:
        val = re.sub(r"\s+", "", m.group(1).strip().lower())
        if val in CLARITY_VALUES:
            fields["clarity"] = {"value": val.upper(), "confidence": _conf_from_match(m, text)}

    # Cut
    m = re.search(r"\bCut\b[:\s]*\n?\s*([A-Za-z]+(?:[^\S\n]+[A-Za-z]+)?)", text)
    if m:
        val = m.group(1).strip().lower()
        matched = _match_fuzzy(val, CUT_VALUES)
        if matched:
            fields["cut"] = {"value": matched.title(), "confidence": _conf_from_match(m, text)}

    # Depth
    m = re.search(r"Depth[:\s]*\n?\s*(\d+\.?\d*)\s*%", text, re.IGNORECASE)
    if m:
        fields["depth"] = {"value": m.group(1), "confidence": _conf_from_match(m, text)}

    # Table
    m = re.search(r"Table[:\s]*\n?\s*(\d+\.?\d*)\s*%", text, re.IGNORECASE)
    if m:
        fields["table"] = {"value": m.group(1), "confidence": _conf_from_match(m, text)}

    # Measurements
    m = re.search(
        r"Measurements?[:\s]*\n?\s*(\d+\.?\d*)\s*(?:-|x)\s*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)",
        text,
        re.IGNORECASE,
    )
    if m:
        fields["x"] = {"value": m.group(1), "confidence": _conf_from_match(m, text)}
        fields["y"] = {"value": m.group(2), "confidence": _conf_from_match(m, text)}
        fields["z"] = {"value": m.group(3), "confidence": _conf_from_match(m, text)}

    # Polish
    m = re.search(r"Polish[:\s]*\n?\s*([A-Za-z]+(?:[^\S\n]+[A-Za-z]+)*)", text)
    if m:
        val = m.group(1).strip().lower()
        matched = _match_fuzzy(val, POLISH_VALUES)
        if matched:
            fields["polish"] = {"value": matched.title(), "confidence": _conf_from_match(m, text)}

    # Symmetry
    m = re.search(r"Symmetry[:\s]*\n?\s*([A-Za-z]+(?:[^\S\n]+[A-Za-z]+)*)", text)
    if m:
        val = m.group(1).strip().lower()
        matched = _match_fuzzy(val, SYMMETRY_VALUES)
        if matched:
            fields["symmetry"] = {"value": matched.title(), "confidence": _conf_from_match(m, text)}

    # Fluorescence
    m = re.search(r"Fluorescence[:\s]*\n?\s*([A-Za-z]+(?:[^\S\n]+[A-Za-z]+)*)", text)
    if m:
        val = m.group(1).strip().lower()
        matched = _match_fuzzy(val, FLUOR_VALUES)
        if matched:
            fields["fluorescence"] = {"value": matched.title(), "confidence": _conf_from_match(m, text)}

    return fields


def _fill_missing_numeric(text, fields):
    # If carat missing, try generic number before "carat" or "ct"
    if "carat" not in fields:
        m = re.search(r"(\d+\.?\d*)\s*(?:carat|ct)", text, re.IGNORECASE)
        if m:
            fields["carat"] = {"value": m.group(1), "confidence": 40.0}

    # If depth missing, try generic percentage
    if "depth" not in fields:
        m = re.search(r"(\d+\.?\d*)\s*%", text)
        if m:
            val = float(m.group(1))
            if 40 <= val <= 80:
                fields["depth"] = {"value": m.group(1), "confidence": 35.0}

    # If table missing, try second percentage
    if "table" not in fields:
        matches = re.findall(r"(\d+\.?\d*)\s*%", text)
        if len(matches) >= 2:
            val = float(matches[1])
            if 40 <= val <= 80:
                fields["table"] = {"value": matches[1], "confidence": 35.0}


def _conf_from_match(match_obj, full_text):
    """Estimate confidence based on match length vs potential OCR noise."""
    matched = match_obj.group(0)
    # Simple heuristic: longer matches with digits are more reliable
    digit_ratio = sum(c.isdigit() for c in matched) / max(len(matched), 1)
    if digit_ratio > 0.3:
        return 70.0
    return 60.0


def _match_fuzzy(val, valid_set):
    """Match OCR output against valid values, tolerating minor OCR errors."""
    if val in valid_set:
        return val
    # Try removing spaces
    compact = val.replace(" ", "")
    if compact in valid_set:
        return compact
    # Common OCR substitutions
    subs = {"0": "o", "1": "l", "5": "s", "8": "b", "rn": "m"}
    for wrong, right in subs.items():
        test = val.replace(wrong, right)
        if test in valid_set:
            return test
        test_compact = compact.replace(wrong, right)
        if test_compact in valid_set:
            return test_compact
    return None
