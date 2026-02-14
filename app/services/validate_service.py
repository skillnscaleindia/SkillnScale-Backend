"""
Smart description validation for service requests.

Uses Google Gemini REST API (via httpx) for intelligent validation,
with keyword-based fallback when Gemini is unavailable.
No external SDK required — uses httpx already in requirements.
"""

import re
import json
import logging
import httpx
from typing import Dict, Set, Optional

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

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


# ── Gemini REST API validation ─────────────────────────────────────

def _validate_with_gemini(category_id: str, description: str) -> Optional[dict]:
    """Call Gemini REST API directly via httpx (sync)."""
    try:
        from app.core.config import settings
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.info("GEMINI_API_KEY is empty, using keyword fallback")
            return None
        logger.info(f"Calling Gemini API for category={category_id}")
    except Exception as e:
        logger.warning(f"Failed to load GEMINI_API_KEY: {e}")
        return None

    category_name = CATEGORY_NAMES.get(category_id, category_id)
    example = _example_for(category_id)

    prompt = (
        f'You are a validator for a home-services app called SkillnScale.\n'
        f'The user selected the service category: "{category_name}"\n'
        f'The user typed this description: "{description}"\n\n'
        f'Determine if the description is a VALID, RELEVANT service request for "{category_name}".\n\n'
        f'Rules:\n'
        f'- VALID: describes a real problem or service need related to {category_name}. Informal/short is fine.\n'
        f'- INVALID: gibberish, unrelated to {category_name}, offensive, or not a service need.\n\n'
        f'Respond in EXACTLY this JSON format, nothing else:\n'
        f'{{"is_valid": true, "message": "one-line friendly feedback"}}\n\n'
        f'If invalid, suggest something like: "This doesn\'t seem related to {category_name}. Try: {example}"\n'
        f'If valid, say: "Got it! We\'ll find you the right professional."'
    )

    try:
        resp = httpx.post(
            f"{GEMINI_API_URL}?key={api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 150},
            },
            timeout=8.0,
        )

        if resp.status_code != 200:
            logger.warning(f"Gemini API returned {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Strip markdown fences if present
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()

        result = json.loads(text)
        return {
            "is_valid": bool(result.get("is_valid", False)),
            "message": result.get("message", ""),
            "suggestion": _example_for(category_id) if not result.get("is_valid") else None,
        }
    except Exception as e:
        logger.warning(f"Gemini validation error: {e}")
        return None


# ── Keyword-based fallback ─────────────────────────────────────────

CATEGORY_KEYWORDS: Dict[str, Set[str]] = {
    "plumbing": {
        "tap", "faucet", "leak", "leaking", "pipe", "drain", "clogged",
        "blocked", "sink", "toilet", "flush", "shower", "geyser", "heater",
        "water", "drip", "valve", "tank", "pipeline", "sewage", "bathroom",
        "kitchen", "basin", "mixer", "plumber", "plumbing", "fitting",
    },
    "electrician": {
        "wire", "wiring", "switch", "socket", "plug", "light", "bulb",
        "fan", "circuit", "breaker", "mcb", "fuse", "short", "spark",
        "voltage", "inverter", "battery", "board", "panel", "electric",
        "electrical", "current", "power", "meter", "led", "tube",
    },
    "cleaning": {
        "clean", "cleaning", "dust", "dirty", "stain", "wash", "mop",
        "sweep", "scrub", "deep", "carpet", "sofa", "upholstery",
        "kitchen", "bathroom", "floor", "tile", "window", "glass",
        "mattress", "sanitize", "disinfect", "polish",
    },
    "painting": {
        "paint", "painting", "wall", "ceiling", "color", "colour",
        "primer", "putty", "waterproof", "crack", "peel", "peeling",
        "texture", "coat", "enamel", "exterior", "interior", "damp",
    },
    "ac_repair": {
        "ac", "air", "conditioner", "conditioning", "cooling", "cool",
        "compressor", "gas", "refrigerant", "filter", "coil", "split",
        "thermostat", "temperature", "frost", "noise", "servicing",
    },
    "salon": {
        "hair", "haircut", "cut", "trim", "style", "facial", "face",
        "skin", "makeup", "bridal", "spa", "massage", "nail", "manicure",
        "pedicure", "wax", "waxing", "threading", "bleach", "grooming",
    },
    "pest_control": {
        "pest", "cockroach", "roach", "termite", "rat", "mice", "mouse",
        "mosquito", "ant", "bug", "insect", "spider", "bedbug", "lizard",
        "infestation", "fumigation", "spray",
    },
    "carpentry": {
        "wood", "wooden", "furniture", "door", "cabinet", "shelf",
        "table", "chair", "bed", "wardrobe", "drawer", "cupboard",
        "frame", "hinge", "lock", "handle", "laminate", "plywood",
        "carpenter", "carpentry", "assemble", "dismantle",
    },
}

GENERIC_KEYWORDS: Set[str] = {
    "repair", "fix", "broken", "damage", "damaged", "replace",
    "install", "maintain", "service", "check", "inspect",
    "not", "working", "problem", "issue", "help", "need",
    "emergency", "urgent", "change", "setup", "fitting", "work",
}

MIN_WORDS = 3


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z]+", text.lower())


def _is_gibberish(word: str) -> bool:
    if len(word) < 4:
        return False
    return not bool(re.search(r"[aeiou]", word.lower()))


def _validate_with_keywords(category_id: str, description: str) -> dict:
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
            "message": "That doesn't look like a valid description.",
            "suggestion": _example_for(category_id),
        }

    token_set = set(tokens)
    cat_keywords = CATEGORY_KEYWORDS.get(category_id, set())
    cat_matches = token_set & cat_keywords
    generic_matches = token_set & GENERIC_KEYWORDS

    # Must have at least one category-specific keyword
    if len(cat_matches) == 0:
        category_name = CATEGORY_NAMES.get(category_id, category_id)
        return {
            "is_valid": False,
            "message": f"This doesn't seem related to {category_name}. Please describe a specific {category_name.lower()} issue.",
            "suggestion": _example_for(category_id),
        }

    return {"is_valid": True, "message": "Looks good!", "suggestion": None}


# ── Main entry point ───────────────────────────────────────────────

def validate_service_description(category_id: str, description: str) -> dict:
    """Validate with Gemini LLM first; keyword fallback if unavailable."""
    result = _validate_with_gemini(category_id, description)
    if result is not None:
        return result
    return _validate_with_keywords(category_id, description)


# ── Example prompts ────────────────────────────────────────────────

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
