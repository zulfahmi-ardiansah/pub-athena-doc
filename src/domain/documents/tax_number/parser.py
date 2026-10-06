import re
from typing import Any, Dict
from src.domain.documents.tax_number.schema import TaxNumberSchema


class TaxNumberStringParser:
    """
    Deterministic rule-based & regex parser for Indonesian Tax Card (NPWP) OCR text.
    Extracts tax number, taxpayer name, KPP branch, address, and registration date without an LLM.
    """

    @classmethod
    def parse(cls, raw_text: str) -> TaxNumberSchema:
        data: Dict[str, Any] = {}
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        # 1. Extract NPWP Number (15 or 16 digits)
        cls._extract_tax_number(raw_text, lines, data)

        # 2. Extract Branch Office (KPP)
        cls._extract_tax_office(raw_text, lines, data)

        # 3. Extract Taxpayer Name
        cls._extract_business_name(raw_text, lines, data)

        # 4. Extract Address
        cls._extract_address(raw_text, lines, data)

        # 5. Extract Registration Date
        cls._extract_tax_registration_date(raw_text, lines, data)

        return TaxNumberSchema.model_validate(data)

    @classmethod
    def _extract_tax_number(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        # Formatted NPWP pattern: 00.000.000.0-000.000 or 00.000.000.0-000
        formatted_match = re.search(r"\b(\d{2}[\.\s]\d{3}[\.\s]\d{3}[\.\s][0-9OobB][-\s]\d{3}(?:[\.\s]\d{3})?)\b", text)
        if formatted_match:
            raw_val = formatted_match.group(1).replace(" ", "")
            data["tax_number"] = raw_val
            return

        # Explicit NPWP label
        label_match = re.search(r"NPWP\s*[:\.]?\s*([0-9OobB\.\-\s]{15,25})", text, re.IGNORECASE)
        if label_match:
            raw_val = label_match.group(1).strip()
            data["tax_number"] = raw_val
            return

        # 15 or 16 consecutive digits pattern
        digit_match = re.search(r"\b([0-9]{15,16})\b", text)
        if digit_match:
            data["tax_number"] = digit_match.group(1)

    @classmethod
    def _extract_tax_office(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        # Look for KPP header line
        for line in lines:
            if re.search(r"\b(?:KANTOR\s*PELAYANAN\s*PAJAK|KPP)\b", line, re.IGNORECASE):
                cleaned = re.sub(r"^.*(?:KANTOR\s*PELAYANAN\s*PAJAK|KPP)\s*[:\.]?\s*", "KPP ", line, flags=re.IGNORECASE).strip()
                data["tax_office"] = cleaned
                return

    @classmethod
    def _extract_business_name(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        for i, line in enumerate(lines):
            # Direct Nama label
            if re.search(r"^(?:NAMA\s*(?:WAJIB\s*PAJAK)?|NAME)\s*[:\.]?\s*", line, re.IGNORECASE):
                val = re.sub(r"^(?:NAMA\s*(?:WAJIB\s*PAJAK)?|NAME)\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
                if val:
                    data["business_name"] = val
                    return

            # Line right after NPWP number line if no colon
            if data.get("tax_number") and data["tax_number"] in line:
                if i + 1 < len(lines):
                    candidate = lines[i + 1].strip()
                    if not re.search(r"\b(?:KPP|ALAMAT|TERDAFTAR|NPWP)\b", candidate, re.IGNORECASE):
                        data["business_name"] = candidate
                        return

    @classmethod
    def _extract_address(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        for line in lines:
            if re.search(r"^(?:ALAMAT|ADDRESS)\s*[:\.]?\s*", line, re.IGNORECASE):
                val = re.sub(r"^(?:ALAMAT|ADDRESS)\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
                if val:
                    data["tax_office_address"] = val
                    return

    @classmethod
    def _extract_tax_registration_date(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        # Date pattern with label
        date_label_match = re.search(
            r"(?:TANGGAL\s*TERDAFTAR|TGL\s*DAFTAR|REGISTRATION\s*DATE)\s*[:\.]?\s*(\d{2}[-/.]\d{2}[-/.]\d{4})",
            text,
            re.IGNORECASE
        )
        if date_label_match:
            data["tax_registration_date"] = date_label_match.group(1).replace("/", "-").replace(".", "-")
            return

        # General date fallback
        date_match = re.search(r"\b(\d{2}[-/.]\d{2}[-/.]\d{4})\b", text)
        if date_match:
            data["tax_registration_date"] = date_match.group(1).replace("/", "-").replace(".", "-")
