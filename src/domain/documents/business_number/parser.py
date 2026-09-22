import re
from typing import Any, Dict
from src.domain.documents.business_number.schema import BusinessNumberSchema


class BusinessNumberStringParser:
    """
    Deterministic rule-based & regex parser for Indonesian Business Identification Number
    (NIB) OCR text. Extracts header fields (NIB number, business name, address, contact,
    investment status, dates) without an LLM. The multi-page KBLI attachment table is not
    reliably parseable with regex and is left empty; use the LLM-based engines for that.
    """

    @classmethod
    def parse(cls, raw_text: str) -> BusinessNumberSchema:
        data: Dict[str, Any] = {}
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        cls._extract_number(raw_text, lines, data)
        cls._extract_name(raw_text, lines, data)
        cls._extract_office_address(raw_text, lines, data)
        cls._extract_postal_code(raw_text, lines, data)
        cls._extract_phone_number(raw_text, lines, data)
        cls._extract_email(raw_text, lines, data)
        cls._extract_investment_status(raw_text, lines, data)
        cls._extract_issued_place_and_date(raw_text, lines, data)
        cls._extract_amendment(raw_text, lines, data)
        cls._extract_printed_date(raw_text, lines, data)

        return BusinessNumberSchema.model_validate(data)

    @classmethod
    def _extract_number(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        label_match = re.search(r"NOMOR\s*INDUK\s*BERUSAHA\s*[:\.]?\s*(\d{13})", text, re.IGNORECASE)
        if label_match:
            data["number"] = label_match.group(1)
            return
        digit_match = re.search(r"\b(\d{13})\b", text)
        if digit_match:
            data["number"] = digit_match.group(1)

    @classmethod
    def _extract_name(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        for line in lines:
            if re.search(r"^(?:1\.\s*)?NAMA\s*PELAKU\s*USAHA\s*[:\.]?\s*", line, re.IGNORECASE):
                val = re.sub(r"^(?:1\.\s*)?NAMA\s*PELAKU\s*USAHA\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
                if val:
                    data["name"] = val
                    return

    @classmethod
    def _extract_office_address(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        for line in lines:
            if re.search(r"^(?:2\.\s*)?ALAMAT\s*KANTOR\s*[:\.]?\s*", line, re.IGNORECASE):
                val = re.sub(r"^(?:2\.\s*)?ALAMAT\s*KANTOR\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
                if val:
                    data["office_address"] = val
                    return

    @classmethod
    def _extract_postal_code(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        match = re.search(r"KODE\s*POS\s*[:\.]?\s*(\d{5})", text, re.IGNORECASE)
        if match:
            data["postal_code"] = match.group(1)

    @classmethod
    def _extract_phone_number(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        match = re.search(r"NO\.?\s*TELEPON\s*[:\.]?\s*([\d\-\+\(\)\s]{6,20})", text, re.IGNORECASE)
        if match:
            data["phone_number"] = match.group(1).strip()

    @classmethod
    def _extract_email(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        match = re.search(r"EMAIL\s*[:\.]?\s*([\w\.\-]+@[\w\.\-]+\.\w+)", text, re.IGNORECASE)
        if match:
            data["email"] = match.group(1).strip()

    @classmethod
    def _extract_investment_status(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        match = re.search(r"STATUS\s*PENANAMAN\s*MODAL\s*[:\.]?\s*(PMDN|PMA)", text, re.IGNORECASE)
        if match:
            data["investment_status"] = match.group(1).upper()

    @classmethod
    def _extract_issued_place_and_date(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        match = re.search(
            r"DITERBITKAN\s*DI\s*[:\.]?\s*([A-Za-z\s]+?)[,\n].*?TANGGAL\s*[:\.]?\s*(\d{1,2}\s+\w+\s+\d{4}|\d{2}[-/.]\d{2}[-/.]\d{4})",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            data["issued_place"] = match.group(1).strip()
            data["issued_date"] = match.group(2).strip()
            return
        place_match = re.search(r"DITERBITKAN\s*DI\s*[:\.]?\s*([A-Za-z\s]+)", text, re.IGNORECASE)
        if place_match:
            data["issued_place"] = place_match.group(1).strip()

    @classmethod
    def _extract_amendment(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        match = re.search(
            r"PERUBAHAN\s*KE[-\s]*(\d+).*?TANGGAL\s*[:\.]?\s*(\d{1,2}\s+\w+\s+\d{4}|\d{2}[-/.]\d{2}[-/.]\d{4})",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            data["amendment_number"] = match.group(1).strip()
            data["amendment_date"] = match.group(2).strip()

    @classmethod
    def _extract_printed_date(cls, text: str, lines: list, data: Dict[str, Any]) -> None:
        match = re.search(
            r"DICETAK\s*TANGGAL\s*[:\.]?\s*(\d{1,2}\s+\w+\s+\d{4}|\d{2}[-/.]\d{2}[-/.]\d{4})",
            text,
            re.IGNORECASE,
        )
        if match:
            data["printed_date"] = match.group(1).strip()
