import io
import re
from pathlib import Path

import pytesseract
from PIL import Image


ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
TESSERACT_LANG = "eng"


def allowed_file(filename):
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def extract_text_from_image(image_bytes):
    image = Image.open(io.BytesIO(image_bytes))
    raw = pytesseract.image_to_string(image, lang=TESSERACT_LANG)
    lines = _parse_string_output(raw)
    return lines


def extract_text_from_pdf(pdf_bytes):
    try:
        import fitz
    except ImportError:
        raise ImportError("PyMuPDF (fitz) is required for PDF support.")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_lines = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300)
        img_bytes = pix.tobytes("png")
        page_lines = extract_text_from_image(img_bytes)
        all_lines.extend(page_lines)

    doc.close()
    return all_lines


def _parse_string_output(raw_text):
    """Parse Tesseract string output into (text, confidence) tuples.

    Strips blank lines, then merges continuation lines where
    the next line starts with a lowercase letter or is a short
    fragment continuing the previous line.
    """
    all_lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    merged = _merge_continuations(all_lines)
    conf = [70.0] * len(merged)
    return list(zip(merged, conf))


def _merge_continuations(lines):
    """Merge consecutive lines that are fragments of the same text line.

    A line is treated as a continuation when it starts with lowercase,
    a punctuation character, or is very short (<= 3 chars) and doesn't
    look like a label.

    This handles Tesseract's tendency to split words across lines with
    blank line separators.
    """
    result = []
    buffer = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if not buffer:
            buffer = stripped
            continue

        prev, curr = buffer, stripped

        # Heuristics for continuation
        starts_lower = curr[0].islower()
        starts_punct = curr[0] in "!.,:;?"
        is_short = len(curr) <= 3 and not curr.endswith(":")
        prev_incomplete = prev[-1] in "-:," or (
            len(prev) > 0 and prev[-1].isupper() and len(curr) <= 2
        )
        prev_no_end = not prev.endswith(".") and not prev.endswith(":")

        if (starts_lower or starts_punct or is_short or prev_incomplete) and prev_no_end:
            cleaned = curr.lstrip("!.,:;- ")
            buffer = prev + cleaned
        else:
            result.append(buffer)
            buffer = curr

    if buffer:
        result.append(buffer)

    # Second pass: try to merge lines where ends with label start and next continues it
    result = _merge_label_continuations(result)
    return result


def _merge_label_continuations(lines):
    """Merge lines where a label is split across lines.

    Only merges when the next line starts with a known continuation
    word, to avoid gluing unrelated lines together.
    """
    continuation_words = {
        "weight", "grade", "style", "cutting", "escence",
    }
    result = []
    buffer = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if not buffer:
            buffer = stripped
            continue

        prev, curr = buffer, stripped
        first_word = curr.split()[0].lower().rstrip(":")

        if first_word in continuation_words:
            buffer = prev + " " + curr
        else:
            result.append(buffer)
            buffer = curr

    if buffer:
        result.append(buffer)

    return result


def _avg_conf(confs):
    if not confs:
        return 0
    return round(sum(confs) / len(confs), 1)
