import re
import unicodedata
import html
import emoji
from typing import Dict, Any, List

class TextPreprocessor:
    """
    Module 2: Advanced Text Preprocessing Service.
    
    Preserves explicit distinction between:
    1. raw_text: Original user text.
    2. display_text: HTML-sanitized, safe for rendering in UI.
    3. model_text: Normalized specifically for Transformer model tokenization.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        """Strip control characters, URLs, and normalize whitespace."""
        if not text:
            return ""
        cleaned = TextPreprocessor.handle_urls(text)
        return TextPreprocessor.normalize_whitespace(cleaned)

    @staticmethod
    def tokenize(text: str) -> list:
        """Simple tokenization helper."""
        cleaned = TextPreprocessor.clean_text(text)
        return re.findall(r'\b\w+\b', cleaned.lower())

    @staticmethod
    def sanitize_display(raw_text: str) -> str:
        """HTML sanitization for safe UI display (XSS prevention)."""
        if not raw_text:
            return ""
        escaped = html.escape(raw_text.strip())
        sanitized = re.sub(r'<script.*?>.*?</script>', '', escaped, flags=re.IGNORECASE | re.DOTALL)
        return sanitized

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Unicode NFKC normalization for cross-platform compatibility."""
        return unicodedata.normalize("NFKC", text)

    @staticmethod
    def handle_urls(text: str) -> str:
        """Replace URLs with explicit [URL] token for model compatibility."""
        return re.sub(r'https?://\S+|www\.\S+', '[URL]', text)

    @staticmethod
    def handle_mentions(text: str) -> str:
        """Replace social media user mentions (@username) with @USER token."""
        return re.sub(r'@\w+', '@USER', text)

    @staticmethod
    def handle_hashtags(text: str) -> str:
        """Unpack hashtags (#HateSpeech -> HateSpeech) preserving contextual text."""
        return re.sub(r'#(\w+)', r'\1', text)

    @staticmethod
    def convert_emojis(text: str) -> str:
        """Demojize emojis to descriptive textual sentiment markers (e.g. 😀 -> :grinning_face:)."""
        return emoji.demojize(text, delimiters=(" ", " "))

    @staticmethod
    def Compress_repeated_chars(text: str) -> str:
        """Compress 3+ repeated characters (e.g. 'sooooo' -> 'soo') preserving emotional cues."""
        return re.sub(r'(.)\1{2,}', r'\1\1', text)

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Collapse redundant newlines, tabs, and spaces."""
        return re.sub(r'\s+', ' ', text).strip()

    @classmethod
    def process(cls, raw_text: str) -> Dict[str, Any]:
        """
        Full Preprocessing Pipeline:
        raw_text -> display_text -> unicode_norm -> model_text
        """
        if not raw_text:
            return {
                "raw_text": "",
                "display_text": "",
                "model_text": "",
                "char_count": 0,
                "token_count": 0,
                "tokens": []
            }

        # 1. Display-safe sanitization
        display_text = cls.sanitize_display(raw_text)

        # 2. Unicode NFKC Normalization
        norm_text = cls.normalize_unicode(display_text)

        # 3. Model Preprocessing Steps
        text_step1 = cls.handle_urls(norm_text)
        text_step2 = cls.handle_mentions(text_step1)
        text_step3 = cls.handle_hashtags(text_step2)
        text_step4 = cls.convert_emojis(text_step3)
        text_step5 = cls.Compress_repeated_chars(text_step4)
        model_text = cls.normalize_whitespace(text_step5)

        # Tokenization
        tokens = re.findall(r'\b\w+\b', model_text.lower())

        return {
            "raw_text": raw_text,
            "display_text": display_text,
            "model_text": model_text,
            "char_count": len(raw_text),
            "token_count": len(tokens),
            "tokens": tokens
        }
