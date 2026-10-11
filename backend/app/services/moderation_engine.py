from typing import Dict, Any
from app.core.config import settings

class ContentModerationEngine:
    """
    Module 6: Policy-based Content Moderation Decision Engine.
    
    Maintains strict separation between:
    1. AI Prediction (label)
    2. Confidence score
    3. Automated Recommendation (Publish, Manual Review, Block)
    4. Final Status (APPROVED, FLAGGED_FOR_REVIEW, BLOCKED)
    5. Human / Admin Decision
    """

    NOTICE_UNSUPPORTED_LANG = "Language support is limited for this input. Manual review may be required."

    @classmethod
    def process_moderation(cls, prediction: Dict[str, Any], lang_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Processes AI prediction and determines transparent moderation workflow results.
        """
        label = prediction.get("predicted_class", prediction.get("label", "Normal"))
        confidence = prediction.get("confidence", 0.95)
        is_low_conf = prediction.get("is_low_confidence", False)

        # Default fallback values
        recommendation = "Publish"
        final_status = "APPROVED"
        user_explanation = "Your post has been published to the community feed."

        # 1. Language Support Check
        if lang_info and not lang_info.get("is_supported", True):
            recommendation = "Manual Review"
            final_status = "FLAGGED_FOR_REVIEW"
            user_explanation = "Your post is pending manual review because the language detected requires secondary confirmation."
            return {
                "recommendation": recommendation,
                "final_status": final_status,
                "user_explanation": user_explanation
            }

        # 2. Low Confidence Check
        if is_low_conf or confidence < settings.CONFIDENCE_THRESHOLD_LOW:
            recommendation = "Manual Review"
            final_status = "FLAGGED_FOR_REVIEW"
            user_explanation = "Your submission is pending review by our moderation team to ensure community safety guidelines are met."
            return {
                "recommendation": recommendation,
                "final_status": final_status,
                "user_explanation": user_explanation
            }

        # 3. High Confidence Classification Thresholds
        if label == "Hate Speech":
            if confidence >= settings.CONFIDENCE_THRESHOLD_HIGH:
                recommendation = "Block"
                final_status = "BLOCKED"
                user_explanation = "Your content was not published as it contains language that violates community hate speech policies."
            else:
                recommendation = "Manual Review"
                final_status = "FLAGGED_FOR_REVIEW"
                user_explanation = "Your submission is pending manual review by our moderation team."
        elif label == "Offensive":
            if confidence >= settings.CONFIDENCE_THRESHOLD_HIGH:
                recommendation = "Block"
                final_status = "BLOCKED"
                user_explanation = "Your content was not published as it contains language that violates community offensive language guidelines."
            else:
                recommendation = "Manual Review"
                final_status = "FLAGGED_FOR_REVIEW"
                user_explanation = "Your submission is pending manual review by our moderation team."
        else:  # Normal
            if confidence >= settings.CONFIDENCE_THRESHOLD_LOW:
                recommendation = "Publish"
                final_status = "APPROVED"
                user_explanation = "Your post has been published to the community feed."
            else:
                recommendation = "Manual Review"
                final_status = "FLAGGED_FOR_REVIEW"
                user_explanation = "Your submission is pending manual review by our moderation team."

        return {
            "recommendation": recommendation,
            "final_status": final_status,
            "user_explanation": user_explanation
        }

    @classmethod
    def determine_action(cls, prediction: Dict[str, Any], lang_info: Dict[str, Any] = None) -> str:
        """Helper for backward compatibility returning final_status string."""
        return cls.process_moderation(prediction, lang_info)["final_status"]

moderation_engine = ContentModerationEngine()
