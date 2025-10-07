import re
import unicodedata
from typing import Optional

def sanitize_document_text(text: Optional[str]) -> str:
    """Normalize document text for prompts by removing control chars and collapsing whitespace."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\x00", " ")
    normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
