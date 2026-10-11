import re
from typing import Any, Dict

from app.core.config import settings


class LanguageDetector:
    """Lightweight script/word-pattern language hinting.

    Detection is heuristic and is deliberately kept separate from the list of
    languages the configured moderation classifier can handle. By default the
    configured classifier is English-only, so detected Hindi/Marathi text is
    routed for human review instead of receiving an English-model decision.
    """

    DEVANAGARI = re.compile(r"[\u0900-\u097F]")
    MARATHI_MARKERS = re.compile(r"[\u0933\u0972\u0973\u0974\u0975]")
    URDU_MARKERS = re.compile(r"[\u067E\u0686\u0698\u06AF\u06C1\u06D2\u0679\u0686\u0691]")
    ARABIC_PERSIAN = re.compile(r"[\u0600-\u06FF]")
    CHINESE = re.compile(r"[\u4E00-\u9FFF]")
    SPANISH_WORDS = re.compile(r"\b(el|la|los|las|de|en|y|que|con|por|para|un|una|es|son)\b", re.IGNORECASE)
    ENGLISH_WORDS = re.compile(r"\b(the|is|at|which|on|and|a|an|in|for|it|that|this|with|you|are|was)\b", re.IGNORECASE)
    HINGLISH_WORDS = re.compile(r"\b(hai|kya|bhai|bhi|kar|raha|hoon|koi|nahin|sath|pyaar|achha|kaise)\b", re.IGNORECASE)

    @staticmethod
    def _supported_languages() -> set[str]:
        return {
            item.strip().lower()
            for item in settings.MODERATION_SUPPORTED_LANGUAGES.split(",")
            if item.strip()
        }

    @classmethod
    def _result(cls, code: str, name: str, confidence: float, *, mixed: bool = False) -> Dict[str, Any]:
        supported = code in cls._supported_languages()
        return {
            "code": code,
            "name": name,
            "confidence": confidence,
            "is_detected": code != "unsupported",
            "is_supported": supported,
            "is_mixed": mixed,
            "notice": None if supported else "The configured moderation model is not verified for this language. Human review may be required.",
        }

    @classmethod
    def detect_language(cls, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return cls._result("en", "English", 1.0)

        text_str = text.strip()
        has_devanagari = bool(cls.DEVANAGARI.search(text_str))
        has_arabic = bool(cls.ARABIC_PERSIAN.search(text_str))
        has_chinese = bool(cls.CHINESE.search(text_str))
        has_hinglish = bool(cls.HINGLISH_WORDS.search(text_str))
        has_english = bool(cls.ENGLISH_WORDS.search(text_str))
        has_spanish = bool(cls.SPANISH_WORDS.search(text_str))

        if has_chinese:
            return cls._result("zh", "Chinese", 0.95)
        if has_devanagari:
            is_marathi = bool(cls.MARATHI_MARKERS.search(text_str))
            code, name = ("mr", "Marathi") if is_marathi else ("hi", "Hindi")
            mixed = has_english or bool(re.search(r"[a-zA-Z]", text_str))
            return cls._result(code, name, 0.92 if not mixed else 0.80, mixed=mixed)
        if has_arabic:
            is_urdu = bool(cls.URDU_MARKERS.search(text_str))
            code, name = ("ur", "Urdu") if is_urdu else ("ar", "Arabic")
            return cls._result(code, name, 0.90)
        if has_hinglish:
            return cls._result("hinglish", "Hinglish (Code-Mixed)", 0.85, mixed=True)
        if has_spanish:
            return cls._result("es", "Spanish", 0.88)
        if has_english or re.search(r"[a-zA-Z]", text_str):
            return cls._result("en", "English", 0.90)

        return {
            "code": "unsupported",
            "name": "Unknown / Unsupported",
            "confidence": 0.40,
            "is_detected": False,
            "is_supported": False,
            "is_mixed": False,
            "notice": "The language could not be identified reliably. Human review may be required.",
        }
