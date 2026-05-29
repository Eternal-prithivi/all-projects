"""
Sensitive data detection for secure vault uploads.
Matches research-paper style patterns: cards, credentials/PII keywords, private IPs.
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class SensitiveScanResult:
    is_sensitive: bool
    reasons: list[str]


CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
SECRET_KEYWORDS_PATTERN = re.compile(
    r"(?i)\b("
    r"password|secret|key|pwd|token|credentials|api[_-]?key|apikeys|"
    r"private[_-]?key|auth[_-]?token|access[_-]?key|client[_-]?secret|"
    r"aws[_-]?secret[_-]?access[_-]?key|aws_access_key"
    r")\b"
)
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)
PRIVATE_IP_PATTERN = re.compile(
    r"\b(?:"
    r"10(?:\.\d{1,3}){3}|"
    r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|"
    r"192\.168(?:\.\d{1,3}){2}"
    r")\b"
)


def scan_file_content(file_content: bytes, filename: Optional[str] = None) -> SensitiveScanResult:
    """Scan raw bytes for sensitive patterns. Best-effort UTF-8 decode."""
    reasons: list[str] = []
    try:
        content_str = file_content.decode("utf-8", errors="ignore")
    except Exception:
        return SensitiveScanResult(is_sensitive=False, reasons=[])

    if CREDIT_CARD_PATTERN.search(content_str):
        reasons.append("credit_card_pattern")
    if SECRET_KEYWORDS_PATTERN.search(content_str):
        reasons.append("credential_keywords")
    if EMAIL_PATTERN.search(content_str):
        reasons.append("email_address")
    if PRIVATE_IP_PATTERN.search(content_str):
        reasons.append("private_ip_address")

    return SensitiveScanResult(is_sensitive=bool(reasons), reasons=reasons)
