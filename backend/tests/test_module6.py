import unittest
from app.services.moderation_engine import moderation_engine

class TestModule6ContentModeration(unittest.TestCase):

    def test_normal_high_confidence_path(self):
        pred = {"predicted_class": "Normal", "confidence": 0.95, "is_low_confidence": False}
        res = moderation_engine.process_moderation(pred)
        self.assertEqual(res["recommendation"], "Publish")
        self.assertEqual(res["final_status"], "APPROVED")

    def test_offensive_high_confidence_path(self):
        pred = {"predicted_class": "Offensive", "confidence": 0.90, "is_low_confidence": False}
        res = moderation_engine.process_moderation(pred)
        self.assertEqual(res["recommendation"], "Block")
        self.assertEqual(res["final_status"], "BLOCKED")

    def test_hateful_high_confidence_path(self):
        pred = {"predicted_class": "Hate Speech", "confidence": 0.92, "is_low_confidence": False}
        res = moderation_engine.process_moderation(pred)
        self.assertEqual(res["recommendation"], "Block")
        self.assertEqual(res["final_status"], "BLOCKED")

    def test_low_confidence_path(self):
        pred = {"predicted_class": "Hate Speech", "confidence": 0.40, "is_low_confidence": True}
        res = moderation_engine.process_moderation(pred)
        self.assertEqual(res["recommendation"], "Manual Review")
        self.assertEqual(res["final_status"], "FLAGGED_FOR_REVIEW")

    def test_unsupported_language_path(self):
        pred = {"predicted_class": "Normal", "confidence": 0.90, "is_low_confidence": False}
        lang_info = {"is_supported": False, "code": "unsupported"}
        res = moderation_engine.process_moderation(pred, lang_info=lang_info)
        self.assertEqual(res["recommendation"], "Manual Review")
        self.assertEqual(res["final_status"], "FLAGGED_FOR_REVIEW")

if __name__ == "__main__":
    unittest.main()
