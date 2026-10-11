import re
from typing import Any, Dict

from app.services.model_inference import HATE_KEYWORDS, OFFENSIVE_KEYWORDS


class XAIEngine:
    """Return keyword matches as rule indicators, not model explanations."""

    @staticmethod
    def explain(text: str, label: str, probabilities: Dict[str, float]) -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                "method": "Keyword Rule Highlights",
                "is_available": False,
                "summary": "No keyword-rule highlights are available for this text.",
                "top_words": [],
                "warning_notice": None,
            }

        matches = []
        seen = set()
        for token in re.findall(r"\b\w+\b", text.lower()):
            if token in seen:
                continue
            seen.add(token)
            if token in HATE_KEYWORDS:
                matches.append({"word": token, "matched_rule": "Hate Speech keyword"})
            elif token in OFFENSIVE_KEYWORDS:
                matches.append({"word": token, "matched_rule": "Offensive keyword"})

        return {
            "method": "Keyword Rule Highlights",
            "is_available": bool(matches),
            "summary": (
                "These terms matched keyword rules. This does not explain or prove the model prediction."
                if matches else "No keyword-rule highlights are available for this text."
            ),
            "top_words": matches[:5],
            "warning_notice": (
                "Keyword matches are heuristic indicators, not causal model explanations or conclusive proof of a policy violation."
                if matches else None
            ),
        }


xai_engine = XAIEngine()
