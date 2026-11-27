import re
from typing import Optional, Dict


class TextNormalizer:
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Replace irregular whitespace, form feeds, and excessive newlines."""
        if not text:
            return ""
        # Normalize carriage returns
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Replace non-breaking spaces and fancy unicode quotes/bullets
        text = text.replace("\u00a0", " ").replace("\u2022", " - ").replace("\u25cf", " - ")
        text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
        # Collapse multiple empty lines to max 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Collapse multi-spaces within lines
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    @staticmethod
    def extract_basic_contact_info(text: str) -> Dict[str, Optional[str]]:
        """Extract email, phone, and links using regex heuristics."""
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}", text)
        
        email = email_match.group(0) if email_match else None
        phone = phone_match.group(0).strip() if phone_match else None

        return {
            "email": email,
            "phone": phone,
        }

