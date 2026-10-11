import unittest
from app.services.preprocessing import TextPreprocessor
from app.services.lang_detect import LanguageDetector
from app.services.moderation_engine import moderation_engine
from app.core.config import settings

class TestModules2And3(unittest.TestCase):

    def setUp(self):
        self._supported_languages = settings.MODERATION_SUPPORTED_LANGUAGES
        settings.MODERATION_SUPPORTED_LANGUAGES = "en"

    def tearDown(self):
        settings.MODERATION_SUPPORTED_LANGUAGES = self._supported_languages

    def test_preprocessing_distinction(self):
        raw = "<script>alert(1)</script>Check out https://example.com by @user123 #StopHate 😀 sooooo good!"
        res = TextPreprocessor.process(raw)

        self.assertEqual(res["raw_text"], raw)
        self.assertNotIn("<script>", res["display_text"])
        self.assertIn("[URL]", res["model_text"])
        self.assertIn("@USER", res["model_text"])
        self.assertIn("StopHate", res["model_text"])
        self.assertIn("grinning_face", res["model_text"])
        self.assertIn("soo good", res["model_text"])

    def test_english_detection(self):
        text = "This is a clean English sentence for content moderation."
        res = LanguageDetector.detect_language(text)
        self.assertEqual(res["code"], "en")
        self.assertTrue(res["is_supported"])

    def test_hindi_devanagari_detection(self):
        text = "यह एक हिंदी पाठ्य सामग्री है।"
        res = LanguageDetector.detect_language(text)
        self.assertEqual(res["code"], "hi")
        self.assertEqual(res["name"], "Hindi")
        self.assertFalse(res["is_supported"])

    def test_marathi_detection(self):
        text = "हा एक मराठी मजकूर आहे. बाळ आणि ॲप."
        res = LanguageDetector.detect_language(text)
        self.assertEqual(res["code"], "mr")
        self.assertEqual(res["name"], "Marathi")
        self.assertFalse(res["is_supported"])

    def test_urdu_detection(self):
        text = "یہ ایک اردو متن ہے۔"
        res = LanguageDetector.detect_language(text)
        self.assertEqual(res["code"], "ur")
        self.assertEqual(res["name"], "Urdu")
        self.assertFalse(res["is_supported"])

    def test_detected_non_english_text_is_routed_for_human_review(self):
        detected = LanguageDetector.detect_language("यह एक हिंदी पाठ्य सामग्री है।")
        self.assertTrue(detected["is_detected"])
        self.assertFalse(detected["is_supported"])
        prediction = {"label": "Normal", "confidence": 0.95, "is_low_confidence": False}
        self.assertEqual(moderation_engine.determine_action(prediction, lang_info=detected), "FLAGGED_FOR_REVIEW")

    def test_mixed_hinglish_detection(self):
        text = "bhai yeh kya ho raha hai kaise ho aap"
        res = LanguageDetector.detect_language(text)
        self.assertEqual(res["code"], "hinglish")
        self.assertTrue(res["is_mixed"])

    def test_empty_input(self):
        res = TextPreprocessor.process("")
        self.assertEqual(res["model_text"], "")
        lang = LanguageDetector.detect_language("")
        self.assertEqual(lang["code"], "en")

    def test_extremely_long_input(self):
        long_text = "Word " * 500
        res = TextPreprocessor.process(long_text)
        self.assertGreater(res["char_count"], 2000)

    def test_unicode_nfkc_normalization(self):
        text = "Ｈｅｌｌｏ Ｗｏｒｌｄ"  # Fullwidth Unicode characters
        res = TextPreprocessor.process(text)
        self.assertEqual(res["model_text"], "Hello World")

    def test_unsupported_language_policy_routing(self):
        unsupported_lang = {
            "code": "unsupported",
            "name": "Unknown",
            "confidence": 0.30,
            "is_supported": False,
            "notice": "Language support is limited for this input. Manual review may be required."
        }
        pred = {"label": "Normal", "confidence": 0.95, "is_low_confidence": False}
        action = moderation_engine.determine_action(pred, lang_info=unsupported_lang)
        self.assertEqual(action, "FLAGGED_FOR_REVIEW")

if __name__ == "__main__":
    unittest.main()
