"""
Sensitive data detection for secure vault uploads.

Pattern-based (regex + Luhn) matching for cards, credentials, PII keywords,
AWS/Azure/GCP cloud secrets, SSNs, private IPs, PEM blocks, and sensitive filenames.

ML/DLP integration is intentionally deferred — see project security scan assessment.
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
AWS_ACCESS_KEY_ID_PATTERN = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
SSN_PATTERN = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")
PEM_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
)
AZURE_STORAGE_CONNECTION_PATTERN = re.compile(
    r"DefaultEndpointsProtocol=https[^;\r\n]*;AccountName=[^;\r\n]+;AccountKey=[A-Za-z0-9+/=]{20,}",
    re.IGNORECASE,
)
AZURE_ACCOUNT_KEY_PATTERN = re.compile(
    r"(?i)AccountKey=[A-Za-z0-9+/=]{40,}"
)
AZURE_CLIENT_SECRET_PATTERN = re.compile(
    r"(?i)(?:azure[_-]?client[_-]?secret|AZURE_CLIENT_SECRET)\s*[=:]\s*['\"]?[A-Za-z0-9~._\-]{20,}"
)
GCP_SERVICE_ACCOUNT_PATTERN = re.compile(r'"type"\s*:\s*"service_account"')
GCP_API_KEY_PATTERN = re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")

SENSITIVE_FILENAME_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".env")
SENSITIVE_FILENAME_FRAGMENTS = (
    "id_rsa",
    "id_dsa",
    "secrets.env",
    "credentials.json",
    "service-account.json",
    "service_account.json",
    "gcp-credentials",
    "azure-credentials",
    ".env.local",
    ".env.production",
)


def _luhn_valid(digit_string: str) -> bool:
    digits = [int(c) for c in digit_string if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, digit in enumerate(digits):
        if i % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _has_valid_credit_card(content_str: str) -> bool:
    for match in CREDIT_CARD_PATTERN.finditer(content_str):
        digits = re.sub(r"\D", "", match.group(0))
        if 13 <= len(digits) <= 19 and _luhn_valid(digits):
            return True
    return False


def _scan_filename(filename: str) -> list[str]:
    reasons: list[str] = []
    lower = filename.lower().strip()
    if not lower:
        return reasons

    for suffix in SENSITIVE_FILENAME_SUFFIXES:
        if lower.endswith(suffix):
            reasons.append("sensitive_filename")
            break

    base = lower.split("/")[-1]
    if base == ".env" or base.startswith(".env."):
        if "sensitive_filename" not in reasons:
            reasons.append("sensitive_filename")

    for fragment in SENSITIVE_FILENAME_FRAGMENTS:
        if fragment in lower:
            if "sensitive_filename" not in reasons:
                reasons.append("sensitive_filename")
            break

    return reasons


def scan_file_content(file_content: bytes, filename: Optional[str] = None) -> SensitiveScanResult:
    """Scan raw bytes (and optional filename) for sensitive patterns. Best-effort UTF-8 decode."""
    reasons: list[str] = []

    if filename:
        reasons.extend(_scan_filename(filename))

    try:
        content_str = file_content.decode("utf-8", errors="ignore")
    except Exception:
        return SensitiveScanResult(is_sensitive=bool(reasons), reasons=reasons)

    if _has_valid_credit_card(content_str):
        reasons.append("credit_card_pattern")
    if SECRET_KEYWORDS_PATTERN.search(content_str):
        reasons.append("credential_keywords")
    if AWS_ACCESS_KEY_ID_PATTERN.search(content_str):
        reasons.append("aws_access_key_id")
    if AZURE_STORAGE_CONNECTION_PATTERN.search(content_str) or AZURE_ACCOUNT_KEY_PATTERN.search(
        content_str
    ):
        reasons.append("azure_storage_secret")
    if AZURE_CLIENT_SECRET_PATTERN.search(content_str):
        reasons.append("azure_client_secret")
    if GCP_SERVICE_ACCOUNT_PATTERN.search(content_str):
        reasons.append("gcp_service_account")
    if GCP_API_KEY_PATTERN.search(content_str):
        reasons.append("gcp_api_key")
    if PEM_PRIVATE_KEY_PATTERN.search(content_str):
        reasons.append("pem_private_key")
    if SSN_PATTERN.search(content_str):
        reasons.append("ssn_pattern")
    if EMAIL_PATTERN.search(content_str):
        reasons.append("email_address")
    if PRIVATE_IP_PATTERN.search(content_str):
        reasons.append("private_ip_address")

    return SensitiveScanResult(is_sensitive=bool(reasons), reasons=reasons)
