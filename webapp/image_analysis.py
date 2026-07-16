import base64
import json
import logging
import os
import time
from pathlib import Path

from PIL import Image

from .ai_provider import (
    PROVIDER_GEMINI,
    PROVIDER_OPENAI,
    get_gemini_model,
    get_openai_model,
    select_provider,
)

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_SIZE_MB = 10
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

DIAMOND_SHAPES = [
    "Round", "Princess", "Cushion", "Emerald", "Oval",
    "Pear", "Marquise", "Asscher", "Radiant", "Heart",
]

CUT_GRADES = ["Fair", "Good", "Very Good", "Premium", "Ideal"]
COLOR_GRADES = ["D", "E", "F", "G", "H", "I", "J"]
POLISH_GRADES = ["Excellent", "Very Good", "Good", "Fair", "Poor"]
SYMMETRY_GRADES = ["Excellent", "Very Good", "Good", "Fair", "Poor"]

ANALYSIS_PROMPT = (
    "You are a diamond expert. Analyze this diamond image and return ONLY a JSON object "
    "with the following fields. Never guess exact carat, clarity, depth, table, or measurements. "
    "Return null for anything you cannot determine with reasonable confidence.\n\n"
    "Fields:\n"
    "- shape: one of Round, Princess, Cushion, Emerald, Oval, Pear, Marquise, Asscher, Radiant, Heart, or null\n"
    "- estimated_cut: one of Fair, Good, Very Good, Premium, Ideal, or null\n"
    "- estimated_color: one of D, E, F, G, H, I, J, or null\n"
    "- estimated_polish: one of Excellent, Very Good, Good, Fair, Poor, or null\n"
    "- estimated_symmetry: one of Excellent, Very Good, Good, Fair, Poor, or null\n"
    "- shape_confidence: 0-100 or null\n"
    "- cut_confidence: 0-100 or null\n"
    "- color_confidence: 0-100 or null\n"
    "- polish_confidence: 0-100 or null\n"
    "- symmetry_confidence: 0-100 or null\n\n"
    "Example: {\"shape\":\"Round\",\"estimated_cut\":\"Premium\",\"estimated_color\":\"G\","
    "\"estimated_polish\":\"Excellent\",\"estimated_symmetry\":\"Very Good\","
    "\"shape_confidence\":85,\"cut_confidence\":55,\"color_confidence\":40,"
    "\"polish_confidence\":50,\"symmetry_confidence\":50}\n\n"
    "IMPORTANT: Only use exact values from the lists above. Return null for unknown."
)


def allowed_image(filename):
    ext = Path(filename).suffix.lower()
    return ext in SUPPORTED_FORMATS


def validate_image_size(file_bytes):
    return len(file_bytes) <= MAX_SIZE_BYTES


def analyze_image(image_bytes, filename):
    """Analyze a diamond image using the configured AI vision provider.

    Provider and model are resolved from environment variables through
    ``ai_provider``.  In ``auto`` mode the primary provider is tried first;
    if it fails the other provider is used as a fallback.
    """
    start = time.time()

    provider = select_provider()
    if not provider:
        logger.info("Provider=None (no API key configured)")
        return _no_api_available_result()

    logger.info("Provider=%s", provider)
    result = _run_provider(provider, image_bytes, filename)

    if result and result.get("provider"):
        elapsed = time.time() - start
        logger.info(
            "Provider=%s time=%.2fs fallback=False",
            provider, elapsed,
        )
        result.pop("model_used", None)
        return result

    fallback = _get_fallback(provider)
    if fallback:
        logger.info("Provider=%s failed, fallback to %s", provider, fallback)
        result = _run_provider(fallback, image_bytes, filename)
        if result and result.get("provider"):
            elapsed = time.time() - start
            logger.info(
                "Provider=%s time=%.2fs fallback=True",
                fallback, elapsed,
            )
            result.pop("model_used", None)
            return result

    if result and result.get("error"):
        return result
    return _no_api_available_result()


def _get_fallback(provider):
    """Return the alternative provider when running in ``auto`` mode."""
    setting = os.getenv("AI_PROVIDER", "auto").strip().lower()
    if setting != "auto":
        return None
    if provider == PROVIDER_OPENAI and os.getenv("GEMINI_API_KEY"):
        return PROVIDER_GEMINI
    if provider == PROVIDER_GEMINI and os.getenv("OPENAI_API_KEY"):
        return PROVIDER_OPENAI
    return None


def _run_provider(provider, image_bytes, filename):
    """Dispatch to the correct provider implementation."""
    if provider == PROVIDER_OPENAI:
        model = get_openai_model()
        logger.info("Selected model: %s", model)
        return _try_openai(image_bytes, filename, model)
    if provider == PROVIDER_GEMINI:
        model = get_gemini_model()
        logger.info("Selected model: %s", model)
        return _try_gemini(image_bytes, filename, model)
    return _provider_error("Unknown provider: %s" % provider)


def _try_openai(image_bytes, filename, model):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _provider_error("OPENAI_API_KEY not set")

    try:
        import openai

        base64_image = _encode_image(image_bytes)
        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ANALYSIS_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this diamond image and return the JSON as specified."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "low",
                            },
                        },
                    ],
                },
            ],
            max_tokens=300,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        data["provider"] = "openai"
        return data

    except ImportError:
        return _provider_error("OpenAI SDK not installed (pip install openai)")
    except Exception as exc:
        logger.error("OpenAI analysis failed: %s", exc)
        return _provider_error(f"OpenAI analysis failed: {str(exc)}")


def _try_gemini(image_bytes, filename, model):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _provider_error("GEMINI_API_KEY not set")

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        gen_model = genai.GenerativeModel(model)

        base64_image = _encode_image(image_bytes)

        response = gen_model.generate_content([
            ANALYSIS_PROMPT,
            {"mime_type": "image/png", "data": base64_image},
        ])
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            text = text.rsplit("```", 1)[0]
            text = text.strip()

        data = json.loads(text)
        data["provider"] = "gemini"
        return data

    except ImportError:
        return _provider_error("Gemini SDK not installed (pip install google-generativeai)")
    except Exception as exc:
        error_str = str(exc)
        if "not found" in error_str.lower() or "404" in error_str:
            logger.error("Model '%s' not found by API.", model)
            try:
                import google.generativeai as genai
                for m in genai.list_models():
                    if "generateContent" in m.supported_generation_methods:
                        logger.info("  Available: %s", m.name.removeprefix("models/"))
            except Exception:
                pass
        else:
            logger.error("Gemini analysis failed: %s", error_str)
        return _provider_error(f"Gemini analysis failed: {str(exc)}")


def _provider_error(message):
    return {"provider": None, "error": message, "fallback": True}


def _no_api_available_result():
    return {
        "provider": None,
        "no_api_key": True,
        "message": (
            "AI image analysis requires an API key. "
            "Set OPENAI_API_KEY or GEMINI_API_KEY in your .env file to enable this feature."
        ),
        "shape": None,
        "estimated_cut": None,
        "estimated_color": None,
        "estimated_polish": None,
        "estimated_symmetry": None,
        "shape_confidence": None,
        "cut_confidence": None,
        "color_confidence": None,
        "polish_confidence": None,
        "symmetry_confidence": None,
    }


def _encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode("utf-8")


def is_analyzeable(filename):
    return allowed_image(filename) and os.path.getsize(filename) <= MAX_SIZE_BYTES
