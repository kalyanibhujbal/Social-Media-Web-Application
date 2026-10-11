from fastapi import APIRouter, Depends, Request
from app.schemas.moderation import AnalyzeRequest, AnalyzeResponse
from app.schemas.post import AIPrediction, XAIExplanation, WordAttribution
from app.services.preprocessing import TextPreprocessor
from app.services.lang_detect import LanguageDetector
from app.services.model_inference import inference_service
from app.services.xai_engine import xai_engine
from app.services.moderation_engine import moderation_engine
from app.middleware.rate_limit import rate_limit_check

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(req: AnalyzeRequest, request: Request):
    """Interactive AI & XAI Text Moderation Sandbox."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)
    preproc = TextPreprocessor.process(req.text)
    lang = LanguageDetector.detect_language(preproc["model_text"])
    prediction = inference_service.predict(preproc["model_text"])

    explanation = None
    if req.include_explanation:
        xai_res = xai_engine.explain(
            text=preproc["model_text"],
            label=prediction["label"],
            probabilities=prediction["probabilities"]
        )
        explanation = XAIExplanation(
            method=xai_res["method"],
            top_words=[WordAttribution(**item) for item in xai_res["top_words"]]
        )

    action = moderation_engine.determine_action(prediction, lang_info=lang)

    ai_pred = AIPrediction(
        label=prediction["predicted_class"],
        predicted_class=prediction["predicted_class"],
        confidence=prediction["confidence"],
        confidence_level=prediction["confidence_level"],
        probabilities=prediction["probabilities"],
        is_low_confidence=prediction["is_low_confidence"],
        model_name=prediction["model_name"],
        model_version=prediction["model_version"],
        inference_timestamp=prediction["inference_timestamp"],
        explanation=explanation
    )

    return AnalyzeResponse(
        text=req.text,
        detected_language=lang["name"],
        language_supported=lang["is_supported"],
        language_notice=lang.get("notice"),
        prediction=ai_pred,
        action_recommendation=action
    )
