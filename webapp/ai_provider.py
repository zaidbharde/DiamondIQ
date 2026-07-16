import logging
import os

logger = logging.getLogger(__name__)

PROVIDER_OPENAI = "openai"
PROVIDER_GEMINI = "gemini"


def _env(name, default=""):
    return os.getenv(name, default)


def select_provider():
    """Resolve which AI provider to use from environment configuration.

    AI_PROVIDER=openai   →  requires OPENAI_API_KEY
    AI_PROVIDER=gemini   →  requires GEMINI_API_KEY
    AI_PROVIDER=auto     →  OPENAI_API_KEY wins, else GEMINI_API_KEY, else None

    Returns ``"openai"``, ``"gemini"``, or ``None`` when no provider is available.
    """
    setting = _env("AI_PROVIDER", "auto").strip().lower()

    if setting == PROVIDER_OPENAI:
        if _env("OPENAI_API_KEY"):
            return PROVIDER_OPENAI
        logger.warning("AI_PROVIDER=openai but OPENAI_API_KEY is not set")
        return None

    if setting == PROVIDER_GEMINI:
        if _env("GEMINI_API_KEY"):
            return PROVIDER_GEMINI
        logger.warning("AI_PROVIDER=gemini but GEMINI_API_KEY is not set")
        return None

    # auto mode (default)
    if _env("OPENAI_API_KEY"):
        return PROVIDER_OPENAI
    if _env("GEMINI_API_KEY"):
        return PROVIDER_GEMINI

    return None


def get_openai_model():
    """Return the configured OpenAI model.  Defaults to ``gpt-4.1-mini``."""
    model = _env("OPENAI_MODEL", "gpt-4.1-mini")
    if not model:
        model = "gpt-4.1-mini"
    return model


_GEMINI_MODEL_CACHE = None


def discover_gemini_model():
    """Auto-discover the best available Gemini vision model.

    Queries ``genai.list_models()``, prefers stable flash models, and caches
    the result so the API is only called once per process lifetime.
    """
    global _GEMINI_MODEL_CACHE
    if _GEMINI_MODEL_CACHE:
        return _GEMINI_MODEL_CACHE

    _genai_key = os.getenv("GEMINI_API_KEY")
    if _genai_key and not os.getenv("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = _genai_key

    try:
        import google.generativeai as genai

        if _genai_key:
            genai.configure(api_key=_genai_key)

        preferred = [
            "gemini-flash-latest",
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
        ]

        available = {m.name.removeprefix("models/") for m in genai.list_models()}

        for name in preferred:
            if name in available:
                _GEMINI_MODEL_CACHE = name
                logger.info("Auto-selected Gemini model: %s", name)
                return name

        for m in genai.list_models():
            name = m.name.removeprefix("models/")
            if "generateContent" in m.supported_generation_methods:
                if "flash" in name.lower() and "preview" not in name and "exp" not in name:
                    _GEMINI_MODEL_CACHE = name
                    logger.info("Auto-selected Gemini model (fallback): %s", name)
                    return name
    except Exception as exc:
        logger.warning("Gemini model discovery failed (%s), using fallback model", exc)

    _GEMINI_MODEL_CACHE = "gemini-flash-latest"
    logger.info("Using default Gemini model: %s", _GEMINI_MODEL_CACHE)
    return _GEMINI_MODEL_CACHE


def get_gemini_model():
    """Return the configured Gemini model.

    ``GEMINI_MODEL=auto`` (or missing / empty) triggers auto-discovery.
    Any other value is used as-is.
    """
    model = _env("GEMINI_MODEL", "auto").strip().lower()
    if model == "auto" or not model:
        return discover_gemini_model()
    logger.info("Using configured Gemini model: %s", model)
    return model
