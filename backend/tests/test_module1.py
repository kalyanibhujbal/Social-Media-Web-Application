import unittest
from app.services.sanitizer import InputSanitizer
from app.middleware.rate_limit import rate_limit_check
from fastapi import HTTPException

class TestModule1UserInput(unittest.TestCase):
    def test_xss_sanitization(self):
        malicious = "<script>alert('xss')</script>Hello World"
        sanitized = InputSanitizer.sanitize_text(malicious)
        self.assertNotIn("<script>", sanitized)
        self.assertIn("&lt;script&gt;", sanitized)
        self.assertIn("Hello World", sanitized)

    def test_length_validation(self):
        empty_text = "   "
        valid_text = "This is a valid post content."
        oversized = "a" * 2005

        self.assertFalse(InputSanitizer.validate_length(empty_text, max_length=2000))
        self.assertTrue(InputSanitizer.validate_length(valid_text, max_length=2000))
        self.assertFalse(InputSanitizer.validate_length(oversized, max_length=2000))

    def test_rate_limiting(self):
        client_ip = "192.168.1.100"
        # Trigger 5 rapid requests within allowed 10 limit
        for _ in range(5):
            rate_limit_check(client_ip, max_requests=10, window_seconds=60)
        # Should not raise exception
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
