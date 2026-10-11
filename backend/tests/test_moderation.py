import unittest
from app.services.model_inference import inference_service
from app.services.xai_engine import xai_engine
from app.services.moderation_engine import moderation_engine

class TestModerationPipeline(unittest.TestCase):
    def test_normal_text_classification(self):
        text = "Having a wonderful day learning artificial intelligence."
        pred = inference_service.predict(text)
        self.assertEqual(pred["label"], "Normal")
        self.assertGreater(pred["probabilities"]["Normal"], 0.5)

    def test_offensive_text_classification(self):
        text = "Shut up you stupid jerk."
        pred = inference_service.predict(text)
        self.assertIn(pred["label"], ["Offensive", "Hate Speech"])

    def test_xai_explanation(self):
        text = "This is stupid trash."
        pred = inference_service.predict(text)
        xai = xai_engine.explain(text, pred["label"], pred["probabilities"])
        self.assertEqual(xai["method"], "Keyword Rule Highlights")
        self.assertTrue(len(xai["top_words"]) > 0)

    def test_moderation_policy(self):
        prediction = {"label": "Normal", "confidence": 0.95, "is_low_confidence": False}
        action = moderation_engine.determine_action(prediction)
        self.assertEqual(action, "APPROVED")

        low_conf_pred = {"label": "Hate Speech", "confidence": 0.40, "is_low_confidence": True}
        action = moderation_engine.determine_action(low_conf_pred)
        self.assertEqual(action, "FLAGGED_FOR_REVIEW")

if __name__ == "__main__":
    unittest.main()
