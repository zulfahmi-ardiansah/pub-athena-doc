import logging
from io import StringIO
import pytest
from src.utility.pi_sanitizer import (
    mask_nik,
    mask_npwp,
    mask_phone,
    mask_email,
    mask_credit_card,
    mask_kitas_identifier,
    mask_bank_account,
    sanitize_pi_string,
    sanitize_pi_dict,
    PILoggingFilter,
)


def test_mask_bank_account_information():
    assert mask_bank_account("148-00-1234567-8") == "14*-**-******7-8"
    assert mask_bank_account("4101234") == "41***34"
    assert sanitize_pi_string("No. Rekening : 148-00-1234567-8") == "No. Rekening : 14*-**-******7-8"
    assert sanitize_pi_dict({"account_number": "4101234"}) == {"account_number": "41***34"}


def test_mask_kitas_identifiers():
    assert mask_kitas_identifier("AB12345678") == "AB******78"
    assert sanitize_pi_string("NIORA : AB12345678 Permit Number : 2C21AB1234YZ Passport Number : P1234567") == (
        "NIORA : AB******78 Permit Number : 2C********YZ Passport Number : P1****67"
    )
    assert sanitize_pi_dict({"niora": "AB12345678", "permit_number": "2C21AB1234YZ", "passport_number": "P1234567"}) == {
        "niora": "AB******78", "permit_number": "2C********YZ", "passport_number": "P1****67"
    }


def test_mask_nik():
    # 16 digits
    nik = "3201011205900001"
    masked = mask_nik(nik)
    assert masked == "320101******0001"
    assert len(masked) == 16


def test_mask_renamed_document_identifiers():
    assert sanitize_pi_dict({"document_number": "3201011205900001"}) == {
        "document_number": "320101******0001"
    }
    assert sanitize_pi_dict({"business_tax_number": "01.234.567.8-123.456"}) == {
        "business_tax_number": "01.***.***.*-***.456"
    }
    assert sanitize_pi_dict({"permit_niora": "AB12345678"}) == {
        "permit_niora": "AB******78"
    }


def test_mask_npwp():
    # Formatted NPWP
    formatted = "01.234.567.8-123.456"
    assert mask_npwp(formatted) == "01.***.***.*-***.456"

    # Raw 15 digits
    raw = "012345678123456"
    assert mask_npwp(raw) == "01*******456"


def test_mask_phone():
    # Phone numbers
    assert mask_phone("081234567890") == "0812****890"
    assert mask_phone("+6281234567890") == "+62812****890"
    assert mask_phone("6281234567890") == "62812****890"


def test_mask_email():
    assert mask_email("user.name@example.com") == "u***e@example.com"
    assert mask_email("admin@domain.co.id") == "a***n@domain.co.id"


def test_mask_credit_card():
    assert mask_credit_card("4111 2222 3333 4444") == "4111-****-****-4444"
    assert mask_credit_card("4111-2222-3333-4444") == "4111-****-****-4444"
    assert mask_credit_card("4111222233334444") == "4111-****-****-4444"


def test_sanitize_pi_string():
    raw_text = (
        "Customer NIK is 3201011205900001 and NPWP 01.234.567.8-123.456. "
        "Contact at 081234567890 or test.user@perusahaan.co.id. "
        "Auth: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz and AIzaSyD9876543210abcdefghijklmnopq12. "
        "api_key: 'SuperSecretKey12345'"
    )
    sanitized = sanitize_pi_string(raw_text)

    # Verify PI is masked
    assert "3201011205900001" not in sanitized
    assert "320101******0001" in sanitized

    assert "01.234.567.8-123.456" not in sanitized
    assert "01.***.***.*-***.456" in sanitized

    assert "081234567890" not in sanitized
    assert "0812****890" in sanitized

    assert "test.user@perusahaan.co.id" not in sanitized
    assert "t***r@perusahaan.co.id" in sanitized

    assert "Bearer [REDACTED]" in sanitized
    assert "AIza*******************************" in sanitized
    assert "SuperSecretKey12345" not in sanitized
    assert "[REDACTED]" in sanitized


def test_sanitize_pi_dict():
    sample_doc = {
        "document_type": "identity_card",
        "nik": "3201011205900001",
        "nama": "Budi Santoso",
        "nomor_npwp": "01.234.567.8-123.456",
        "metadata": {
            "contact_email": "budi@email.com",
            "phone": "081987654321",
            "token": "secret_session_token_123"
        }
    }
    sanitized = sanitize_pi_dict(sample_doc)

    assert sanitized["document_type"] == "identity_card"
    assert sanitized["nik"] == "320101******0001"
    assert sanitized["nomor_npwp"] == "01.***.***.*-***.456"
    assert sanitized["metadata"]["contact_email"] == "b***i@email.com"
    assert sanitized["metadata"]["phone"] == "0819****321"
    assert sanitized["metadata"]["token"] == "[REDACTED]"


def test_pi_logging_filter():
    stream = StringIO()
    logger = logging.getLogger("test_pi_logger")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(PILoggingFilter(enabled=True))
    logger.addHandler(handler)

    logger.info("Processing user with NIK 3201011205900001 and email user@test.com")
    output = stream.getvalue()

    assert "3201011205900001" not in output
    assert "320101******0001" in output
    assert "user@test.com" not in output
    assert "u***r@test.com" in output
