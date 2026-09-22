import logging
import re
from typing import Any, Dict, List, Optional, Set, Union

# Regex patterns for Personal Information (PI) & sensitive credentials
# 1. 16-digit Personal Identification Numbers (e.g. Indonesian NIK / KK, National ID)
RE_NIK = re.compile(r"\b(\d{6})\d{6}(\d{4})\b")

# 2. Tax Identification Numbers (e.g. Indonesian NPWP formatted & raw 15/16 digits)
RE_NPWP_FORMATTED = re.compile(r"\b(\d{2})\.\d{3}\.\d{3}\.\d{1}-\d{3}\.(\d{3})\b")
RE_NPWP_RAW = re.compile(r"\b(\d{2})\d{10}(\d{3})\b")

# 3. Phone Numbers (e.g. +628xxx, 628xxx, 08xxx)
RE_PHONE_ID = re.compile(r"\b(\+?62|0)(8\d{2})\d{4,6}(\d{3})\b")

# 4. Email addresses
RE_EMAIL = re.compile(r"\b([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*([a-zA-Z0-9_.+-])@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b")

# 5. Credit card / 16-digit payment card numbers
RE_CREDIT_CARD = re.compile(r"\b(\d{4})[ -]?\d{4}[ -]?\d{4}[ -]?(\d{4})\b")

# 6. Auth Tokens & Secret Keys
RE_BEARER_TOKEN = re.compile(r"\bBearer\s+[A-Za-z0-9_\-\.]+", re.IGNORECASE)
RE_GOOGLE_API_KEY = re.compile(r"\bAIza[0-9A-Za-z\-_]{30,}\b")
RE_GENERIC_SECRET = re.compile(
    r"""(?i)(["']?(?:api[_-]?key|access[_-]?token|secret|password|client[_-]?secret|private[_-]?key)["']?\s*[:=]\s*["']?)([^"',\s]{4,})(["']?)"""
)

# Known sensitive secret keys that should always be [REDACTED]
CREDENTIAL_FIELD_NAMES: Set[str] = {
    "password",
    "secret",
    "token",
    "access_token",
    "api_key",
    "auth_token",
    "authorization",
    "client_secret",
    "private_key",
    "cvv",
}

# Known document identifier fields that should be masked
IDENTIFIER_FIELD_NAMES: Set[str] = {
    "nik",
    "nomor_ktp",
    "npwp",
    "nomor_npwp",
    "kk",
    "no_kk",
    "nomor_kk",
    "credit_card",
    "card_number",
    "bank_account",
    "nomor_rekening",
}


def mask_nik(nik_str: str) -> str:
    """Masks 16-digit NIK/KK preserving first 6 (region) and last 4 digits."""
    return RE_NIK.sub(r"\1******\2", str(nik_str))


def mask_npwp(npwp_str: str) -> str:
    """Masks NPWP preserving prefix and suffix."""
    if "." in npwp_str or "-" in npwp_str:
        return RE_NPWP_FORMATTED.sub(r"\1.***.***.*-***.\2", str(npwp_str))
    return RE_NPWP_RAW.sub(r"\1*******\2", str(npwp_str))


def mask_phone(phone_str: str) -> str:
    """Masks phone number preserving country/operator prefix and last 3 digits."""
    return RE_PHONE_ID.sub(r"\1\2****\3", str(phone_str))


def mask_email(email_str: str) -> str:
    """Masks email address preserving first and last username char and domain."""
    return RE_EMAIL.sub(r"\1***\2@\3", str(email_str))


def mask_credit_card(card_str: str) -> str:
    """Masks payment card numbers preserving first 4 and last 4 digits."""
    return RE_CREDIT_CARD.sub(r"\1-****-****-\2", str(card_str))


def sanitize_pi_string(text: str) -> str:
    """
    Sanitizes a free-text string by redacting all known Personal Information (PI)
    and sensitive credentials.
    """
    if not isinstance(text, str) or not text:
        return text

    # Redact credentials first
    text = RE_BEARER_TOKEN.sub("Bearer [REDACTED]", text)
    text = RE_GOOGLE_API_KEY.sub("AIza*******************************", text)
    text = RE_GENERIC_SECRET.sub(r"\1[REDACTED]\3", text)

    # Redact Personal Identification (NIK / KK)
    text = RE_NIK.sub(r"\1******\2", text)

    # Redact Tax Identification (NPWP)
    text = RE_NPWP_FORMATTED.sub(r"\1.***.***.*-***.\2", text)
    text = RE_NPWP_RAW.sub(r"\1*******\2", text)

    # Redact Payment Cards
    text = RE_CREDIT_CARD.sub(r"\1-****-****-\2", text)

    # Redact Phone Numbers
    text = RE_PHONE_ID.sub(r"\1\2****\3", text)

    # Redact Emails
    text = RE_EMAIL.sub(r"\1***\2@\3", text)

    return text


def sanitize_pi_dict(
    data: Any,
    sensitive_keys: Optional[Set[str]] = None,
    mask_all_string_values: bool = True
) -> Any:
    """
    Recursively sanitizes a dictionary, list, or nested object.
    Specific sensitive keys are explicitly redacted or masked.
    """
    if isinstance(data, dict):
        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            key_str = str(key).lower()
            if any(s in key_str for s in CREDENTIAL_FIELD_NAMES):
                sanitized[key] = "[REDACTED]"
            elif any(s in key_str for s in IDENTIFIER_FIELD_NAMES):
                if isinstance(value, str):
                    sanitized[key] = sanitize_pi_string(value)
                    if sanitized[key] == value and len(value) > 6:
                        sanitized[key] = value[:6] + "*" * (len(value) - 10) + value[-4:]
                elif isinstance(value, (int, float)):
                    val_str = str(value)
                    if len(val_str) == 16:
                        sanitized[key] = f"{val_str[:6]}******{val_str[-4:]}"
                    else:
                        sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_pi_dict(value, sensitive_keys, mask_all_string_values)
        return sanitized

    elif isinstance(data, list):
        return [sanitize_pi_dict(item, sensitive_keys, mask_all_string_values) for item in data]

    elif isinstance(data, str) and mask_all_string_values:
        return sanitize_pi_string(data)

    return data


class PILoggingFilter(logging.Filter):
    """
    Logging Filter that intercepts all log records and applies Personal Information (PI)
    masking to message text, string arguments, exception text, and record attributes.
    """

    def __init__(self, enabled: bool = True):
        super().__init__()
        self.enabled = enabled

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.enabled:
            return True

        try:
            # 1. Sanitize the main log message
            if isinstance(record.msg, str):
                record.msg = sanitize_pi_string(record.msg)
            elif isinstance(record.msg, (dict, list)):
                record.msg = sanitize_pi_dict(record.msg)

            # 2. Sanitize any positional arguments
            if record.args:
                if isinstance(record.args, tuple):
                    record.args = tuple(
                        sanitize_pi_string(a) if isinstance(a, str)
                        else (sanitize_pi_dict(a) if isinstance(a, (dict, list)) else a)
                        for a in record.args
                    )
                elif isinstance(record.args, dict):
                    record.args = sanitize_pi_dict(record.args)

            # 3. Sanitize cached exception text if present
            if getattr(record, "exc_text", None):
                record.exc_text = sanitize_pi_string(record.exc_text) # type: ignore

        except Exception:
            # Prevent logging filter failures from crashing the application
            pass

        return True


# Backward compatibility aliases
sanitize_pdp_string = sanitize_pi_string
sanitize_pdp_dict = sanitize_pi_dict
PDPLoggingFilter = PILoggingFilter
