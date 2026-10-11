import unittest
from app.services.model_inference import inference_service
from app.services.xai_engine import xai_engine

class TestModule5ExplainableAI(unittest.TestCase):

    def test_hateful_text_explanation(self):
        text = "I hate you and want you dead, racist scum."
        pred = inference_service.predict(text)
        xai = xai_engine.explain(text, pred["predicted_class"], pred["probabilities"])

        self.assertTrue(xai["is_available"])
        self.assertEqual(xai["method"], "Keyword Rule Highlights")
        self.assertIn("matched keyword rules", xai["summary"])
        self.assertTrue(len(xai["top_words"]) > 0)
        self.assertIsNotNone(xai["warning_notice"])

    def test_empty_input_explanation(self):
        pred = inference_service.predict("")
        xai = xai_engine.explain("", pred["predicted_class"], pred["probabilities"])

        self.assertFalse(xai["is_available"])
        self.assertEqual(xai["summary"], "No keyword-rule highlights are available for this text.")
        self.assertEqual(len(xai["top_words"]), 0)

    def test_multilingual_text_explanation(self):
        text = "यह एक खराब बात है stop hate"
        pred = inference_service.predict(text)
        xai = xai_engine.explain(text, pred["predicted_class"], pred["probabilities"])

        self.assertTrue(isinstance(xai["top_words"], list))
        self.assertIn("method", xai)

    def test_no_hallucinated_explanation_on_special_chars(self):
        text = "!!! ??? ###"
        pred = inference_service.predict(text)
        xai = xai_engine.explain(text, pred["predicted_class"], pred["probabilities"])

        self.assertFalse(xai["is_available"])
        self.assertEqual(xai["summary"], "No keyword-rule highlights are available for this text.")

if __name__ == "__main__":
    unittest.main()
