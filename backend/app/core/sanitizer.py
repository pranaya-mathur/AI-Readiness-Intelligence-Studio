import re
from typing import Optional


def sanitize_text(text: Optional[str], fallback: str = "") -> str:
    """
    Cleans up prompt leakage, raw JSON formats, schemas, instructions,
    and returns a clean client-facing sentence. If the text becomes empty
    or too short, it returns a professional fallback description.
    """
    if not text:
        return fallback

    # 1. Clean markdown JSON structures and braces
    text = re.sub(r"```json.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

    # 2. Clean curly braces structure if they look like JSON formats
    text = re.sub(r"\{\s*\"[a-zA-Z_]+\"\s*:\s*.*?\}", "", text, flags=re.DOTALL)
    text = re.sub(r"\{\s*\"[a-zA-Z_]+\"\s*:\s*.*", "", text, flags=re.DOTALL)

    # 3. List of regex patterns for typical prompt instructions
    prompt_patterns = [
        r"(?i)format\s+your\s+response\s+as\s+a\s+json\s+object:?",
        r"(?i)format\s+your\s+response\s+in\s+json:?",
        r"(?i)format\s+in\s+json:?",
        r"(?i)format\s+response\s+in\s+json:?",
        r"(?i)suggest\s+\d+\s+major\s+ai\s+risks\s+and\s+controls\.?",
        r"(?i)suggest\s+\d+\s+ai\s+use\s+cases\s+mapped\s+to\s+departments:?",
        r"(?i)suggest\s+\d+\s+strategic\s+steps\.?",
        r"(?i)suggest\s+\d+?",
        r"(?i)provide\s+the\s+output\s+in\s+json\s+format\s+exactly\s+as:?",
        r"(?i)provide\s+the\s+output:?",
        r"(?i)you\s+are\s+the\s+[a-zA-Z0-9_\s]+\s+agent\.?",
        r"(?i)analyze\s+this\s+raw\s+text\s+extract\s+from\s+corporate\s+documentation:?",
        r"(?i)identify\s+and\s+extract\s+\d+\s+distinct\s+\"extracted\s+business\s+signals\":?",
        r"(?i)build\s+a\s+30/60/90\s+day\s+roadmap:?",
        r"(?i)format\s+in\s+json\s*:",
        r"(?i)format\s+your\s+response\s*:",
        r"(?i)provide\s+the\s+output\s+in\s+json\s+format\s+exactly\s+as\s*:",
        r"(?i)suggest\s+3\s+ai\s+use\s+cases\s+mapped\s+to\s+departments\s*:",
    ]

    for pattern in prompt_patterns:
        text = re.sub(pattern, "", text)

    # 4. Clean only trailing and leading braces/brackets/quotes that look like JSON remnants,
    # but PRESERVE normal business punctuation (hyphens, commas, periods, colons, slashes).
    text = re.sub(r"[\{\}\[\]\"\'\*]+", " ", text)

    # Clean up excess whitespace and newlines
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    # 5. Trim leading/trailing punctuation leftovers
    text = re.sub(r"^[\s\"\'\{\}\[\]\:\-\,\.\*]+", "", text)
    text = re.sub(r"[\s\"\'\{\}\[\]\:\-\,\.\*]+$", "", text)
    text = text.strip()

    # 6. Fallback checks
    if (
        len(text) < 5
        or "json" in text.lower()
        or text.startswith("{")
        or text.endswith("}")
    ):
        return fallback

    return text
