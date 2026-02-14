"""
Smart description validation for service requests.

Uses Google Gemini LLM for intelligent validation, with keyword-based
fallback when Gemini API is unavailable or not configured.
"""

import re
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)

# ── Gemini setup ───────────────────────────────────────────────────

_gemini_model = None

def _get_gemini_model():
    """Lazy-init the Gemini model."""
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model

    try:
        from app.core.config import settings
        if not settings.GEMINI_API_KEY:
            logger.info("GEMINI_API_KEY not set — using keyword fallback.")
            return None

        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("Gemini model initialized successfully.")
        return _gemini_model
    except Exception as e:
        logger.warning(f"Failed to init Gemini: {e} — using keyword fallback.")
        return None


# ── Category display names ─────────────────────────────────────────

CATEGORY_NAMES: Dict[str, str] = {
    "plumbing": "Plumbing",
    "electrician": "Electrician",
    "cleaning": "Cleaning",
    "painting": "Painting",
    "ac_repair": "AC Repair",
    "salon": "Salon & Beauty",
    "pest_control": "Pest Control",
    "carpentry": "Carpentry",
}


# ── Gemini-based validation ────────────────────────────────────────

def _validate_with_gemini(category_id: str, description: str) -> dict | None:
    """
    Use Gemini to determine if the description is relevant.
    Returns the validation dict, or None if Gemini is unavailable.
    """
    model = _get_gemini_model()
    if model is None:
        return None

    category_name = CATEGORY_NAMES.get(category_id, category_id)
    example = _example_for(category_id)

    prompt = f"""You are a validator for a home-services app called SkillnScale.

The user selected the service category: "{category_name}"
The user typed this description: "{description}"

Determine if the description is a VALID, RELEVANT service request for the "{category_name}" category.

Rules:
- VALID: The text describes a real problem, task, or service need related to {category_name}. It can be informal, short, or use slang — that's fine as long as the intent is clear.
- INVALID: The text is gibberish, completely unrelated to {category_name}, offensive, a random test string, or does not describe any service need.

Respond in EXACTLY this JSON format, nothing else:
{{"is_valid": true/false, "message": "<one-line friendly feedback to the user>"}}

If invalid, include a helpful suggestion in the message, like: "This doesn't seem related to {category_name}. Try something like: {example}"
If valid, say something encouraging like: "Got it! We'll find you the right professional."
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()

        import json
        result = json.loads(text)
        return {
            "is_valid": bool(result.get("is_valid", False)),
            "message": result.get("message", ""),
            "suggestion": _example_for(category_id) if not result.get("is_valid") else None,
        }
    except Exception as e:
        logger.warning(f"Gemini validation failed: {e}")
        return None


# ── Keyword-based fallback ─────────────────────────────────────────

CATEGORY_KEYWORDS: Dict[str, Set[str]] = {
    "plumbing": {
        "tap", "faucet", "leak", "leaking", "pipe", "drain", "clogged",
        "blocked", "sink", "toilet", "flush", "shower", "geyser", "heater",
        "water", "drip", "dripping", "valve", "tank", "pipeline", "sewage",
        "overflow", "bathroom", "kitchen", "washing", "basin", "mixer",
        "plumber", "plumbing", "fitting", "joint", "connection",
    },
    "electrician": {
        "wire", "wiring", "switch", "socket", "plug", "light", "bulb",
        "fan", "circuit", "breaker", "mcb", "fuse", "short", "spark",
        "voltage", "inverter", "battery", "generator", "board", "panel",
        "earthing", "grounding", "electric", "electrical", "current",
        "power", "meter", "led", "tube", "chandelier", "dimmer",
    },
    "cleaning": {
        "clean", "cleaning", "dust", "dirty", "stain", "wash", "mop",
        "sweep", "scrub", "deep", "carpet", "sofa", "upholstery",
        "kitchen", "bathroom", "floor", "tile", "window", "glass",
        "mattress", "curtain", "sanitize", "disinfect", "polish",
    },
    "painting": {
        "paint", "painting", "wall", "ceiling", "color", "colour",
        "primer", "putty", "waterproof", "waterproofing", "crack",
        "peel", "peeling", "texture", "coat", "enamel", "distemper",
        "emulsion", "exterior", "interior", "damp", "seepage",
    },
    "ac_repair": {
        "ac", "air", "conditioner", "conditioning", "cooling", "cool",
        "compressor", "gas", "refrigerant", "filter", "coil", "split",
        "window", "duct", "thermostat", "remote", "temperature", "frost",
        "ice", "freeze", "noise", "smell", "service", "servicing",
    },
    "salon": {
        "hair", "haircut", "cut", "trim", "style", "styling", "color",
        "colour", "facial", "face", "skin", "makeup", "bridal", "spa",
        "massage", "nail", "manicure", "pedicure", "wax", "waxing",
        "threading", "bleach", "shave", "beard", "grooming",
    },
    "pest_control": {
        "pest", "cockroach", "roach", "termite", "rat", "mice", "mouse",
        "mosquito", "ant", "ants", "bug", "bugs", "insect", "spider",
        "bed", "bedbug", "lizard", "snake", "bee", "wasp", "fly",
        "flies", "infestation", "fumigation", "spray",
    },
    "carpentry": {
        "wood", "wooden", "furniture", "door", "cabinet", "shelf",
        "shelves", "table", "chair", "bed", "wardrobe", "drawer",
        "cupboard", "frame", "hinge", "lock", "handle", "polish",
        "laminate", "plywood", "carpenter", "carpentry", "assemble",
        "assembly", "dismantle", "repair",
    },
}

GENERIC_KEYWORDS: Set[str] = {
    "repair", "fix", "broken", "damage", "damaged", "replace",
    "install", "installation", "maintain", "maintenance", "service",
    "servicing", "check", "inspect", "inspection", "not", "working",
    "problem", "issue", "help", "need", "emergency", "urgent",
    "new", "old", "change", "setup", "fitting", "work",
}

MIN_WORDS = 3


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z]+", text.lower())


def _is_gibberish(word: str) -> bool:
    if len(word) < 4:
        return False
    return not bool(re.search(r"[aeiou]", word.lower()))


def _validate_with_keywords(category_id: str, description: str) -> dict:
    """Keyword-based fallback validation."""
    tokens = _tokenize(description)

    if len(tokens) < MIN_WORDS:
        return {
            "is_valid": False,
            "message": "Please provide more details about your issue.",
            "suggestion": _example_for(category_id),
        }

    gibberish_count = sum(1 for t in tokens if _is_gibberish(t))
    if gibberish_count > len(tokens) * 0.5:
        return {
            "is_valid": False,
            "message": "That doesn't look like a valid description. Please describe your issue clearly.",
            "suggestion": _example_for(category_id),
        }

    token_set = set(tokens)
    cat_keywords = CATEGORY_KEYWORDS.get(category_id, set())
    cat_matches = token_set & cat_keywords
    generic_matches = token_set & GENERIC_KEYWORDS
    total_matches = len(cat_matches) + len(generic_matches)

    if total_matches == 0:
        return {
            "is_valid": False,
            "message": "This doesn't seem related to the service. Please describe a specific issue.",
            "suggestion": _example_for(category_id),
        }

    return {
        "is_valid": True,
        "message": "Got it! We'll find you the right professional.",
        "suggestion": None,
    }


# ── Main entry point ───────────────────────────────────────────────

def validate_service_description(category_id: str, description: str) -> dict:
    """
    Validate whether the description is relevant to the category.
    Uses Gemini LLM first; falls back to keywords if unavailable.
    """
    # Try Gemini first
    result = _validate_with_gemini(category_id, description)
    if result is not None:
        return result

    # Fallback to keyword-based
    return _validate_with_keywords(category_id, description)


# ── Example prompts per category ────────────────────────────────────

_EXAMPLES: Dict[str, str] = {
    "plumbing": "e.g., Kitchen tap is leaking and needs replacement",
    "electrician": "e.g., Power socket not working in the bedroom",
    "cleaning": "e.g., Need deep cleaning for 2BHK apartment",
    "painting": "e.g., Walls have cracks and need repainting",
    "ac_repair": "e.g., AC not cooling properly, needs gas refill",
    "salon": "e.g., Need a haircut and facial at home",
    "pest_control": "e.g., Cockroach infestation in kitchen area",
    "carpentry": "e.g., Wardrobe door hinge is broken",
}


def _example_for(category_id: str) -> str:
    return _EXAMPLES.get(category_id, "e.g., Describe what needs to be fixed or serviced")
