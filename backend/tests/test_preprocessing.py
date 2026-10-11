import unittest
from app.services.preprocessing import TextPreprocessor

class TestTextPreprocessing(unittest.TestCase):
    def test_clean_text(self):
        text = "Hello   world!\nThis is a test URL: https://example.com/test"
        cleaned = TextPreprocessor.clean_text(text)
        self.assertNotIn("https://example.com", cleaned)
        self.assertIn("[URL]", cleaned)
        self.assertEqual(cleaned, "Hello world! This is a test URL: [URL]")

    def test_tokenize(self):
        tokens = TextPreprocessor.tokenize("Hate speech detection in social media text")
        self.assertIn("hate", tokens)
        self.assertIn("speech", tokens)
        self.assertEqual(len(tokens), 7)

if __name__ == "__main__":
    unittest.main()
