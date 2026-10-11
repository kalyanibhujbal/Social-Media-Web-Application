import html
import re

class InputSanitizer:
    """Security input sanitizer to prevent XSS and script injections."""

    @staticmethod
    def sanitize_text(text: str) -> str:
        if not text:
            return ""
        # Escape HTML entities
        escaped = html.escape(text.strip())
        # Strip dangerous HTML tag patterns
        sanitized = re.sub(r'<script.*?>.*?</script>', '', escaped, flags=re.IGNORECASE | re.DOTALL)
        return sanitized

    @staticmethod
    def validate_length(text: str, max_length: int = 2000) -> bool:
        return 1 <= len(text.strip()) <= max_length
