import re
from typing import Any, Dict
from src.domain.documents.tax_entity.schema import TaxEntitySchema


class TaxEntityStringParser:
    """
    Deterministic rule-based & regex parser for Indonesian Taxable Entrepreneur
    Confirmation Letter (SPPKP/PKP) OCR text. Extracts all fields without an LLM.
    """

    @classmethod
    def parse(cls, raw_text: str) -> TaxEntitySchema:
        data: Dict[str, Any] = {}
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        cls._extract_letter_number(raw_text, data)
        cls._extract_tax_office(lines, data)
        cls._extract_tax_number(lines, data)
        cls._extract_taxpayer_name(lines, data)
        cls._extract_business_classification(raw_text, data)
        cls._extract_address(raw_text, data)
        cls._extract_trade_name(lines, data)
        cls._extract_tax_obligation(raw_text, data)
        cls._extract_confirmed_since(raw_text, data)
        cls._extract_issued_place_and_date(raw_text, data)
        cls._extract_signing_official(lines, data)

        return TaxEntitySchema.model_validate(data)

    @classmethod
    def _extract_letter_number(cls, text: str, data: Dict[str, Any]) -> None:
        match = re.search(r"\bS-\d+PKP/[\w./]+", text, re.IGNORECASE)
        if match:
            data["letter_number"] = match.group(0)

    @classmethod
    def _extract_tax_office(cls, lines: list, data: Dict[str, Any]) -> None:
        for i, line in enumerate(lines):
            if re.search(r"KANTOR\s*WILAYAH\s*DJP", line, re.IGNORECASE):
                data["tax_office_region"] = line.strip()
            elif re.search(r"KPP\s*PRATAMA", line, re.IGNORECASE) or re.search(r"^KPP\b", line, re.IGNORECASE):
                data["tax_office"] = line.strip()
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if not re.search(r"TELEPON|LAYANAN|EMAIL|SURAT", next_line, re.IGNORECASE):
                        data["tax_office_address"] = next_line.strip()

    @classmethod
    def _extract_tax_number(cls, lines: list, data: Dict[str, Any]) -> None:
        for line in lines:
            match = re.search(
                r"NOMOR\s*POKOK\s*WAJIB\s*PAJAK\s*[:\.]?\s*([0-9OobB.\-]{15,25})",
                line,
                re.IGNORECASE,
            )
            if match:
                data["tax_number"] = match.group(1).strip()
                return

    @classmethod
    def _extract_taxpayer_name(cls, lines: list, data: Dict[str, Any]) -> None:
        for line in lines:
            if re.search(r"^2\.?\s*NAMA\s*[:\.]?\s*", line, re.IGNORECASE):
                val = re.sub(r"^2\.?\s*NAMA\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
                if val:
                    data["taxpayer_name"] = val
                    return

    @classmethod
    def _extract_business_classification(cls, text: str, data: Dict[str, Any]) -> None:
        match = re.search(
            r"KLASIFIKASI\s*LAPANGAN\s*USAHA\s*[:\.]?\s*(.+?)(?=\n\s*4\.\s*ALAMAT)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return

        # One or more "CODE - TITLE" lines; a title can wrap onto following lines
        # until the next CODE line (or the end of the block) appears.
        entries = []
        current_code = None
        current_title_parts: list = []
        for raw_line in match.group(1).splitlines():
            line = raw_line.strip()
            if not line:
                continue
            code_match = re.match(r"^(\d{4,5})\s*-\s*(.+)$", line)
            if code_match:
                if current_code:
                    entries.append({"code": current_code, "title": " ".join(current_title_parts).strip()})
                current_code = code_match.group(1)
                current_title_parts = [code_match.group(2).strip()]
            elif current_code:
                current_title_parts.append(line)
        if current_code:
            entries.append({"code": current_code, "title": " ".join(current_title_parts).strip()})

        if entries:
            data["business_fields"] = entries

    @classmethod
    def _extract_address(cls, text: str, data: Dict[str, Any]) -> None:
        match = re.search(
            r"4\.?\s*ALAMAT\s*[:\.]?\s*(.+?)(?=\n\s*5\.)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            address = re.sub(r"\s*\n\s*", ", ", match.group(1).strip())
            data["address"] = address

    @classmethod
    def _extract_trade_name(cls, lines: list, data: Dict[str, Any]) -> None:
        for line in lines:
            if re.search(r"^5\.?\s*MERK\s*DAGANG", line, re.IGNORECASE):
                val = re.sub(r"^5\.?\s*MERK\s*DAGANG(?:/USAHA)?\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
                data["trade_name"] = val
                return

    @classmethod
    def _extract_tax_obligation(cls, text: str, data: Dict[str, Any]) -> None:
        match = re.search(r"KEWAJIBAN\s*PAJAK\s*[:\.]?\s*(.+)", text, re.IGNORECASE)
        if not match:
            return
        segment = match.group(1)
        checked = re.findall(r"\[\s*[xX]\s*\]\s*([A-Za-z]+)", segment)
        if checked:
            data["tax_obligation"] = "; ".join(c.strip() for c in checked)

    @classmethod
    def _extract_confirmed_since(cls, text: str, data: Dict[str, Any]) -> None:
        match = re.search(
            r"TERHITUNG\s*SEJAK\s*(\d{1,2}\s+\w+\s+\d{4}|\d{2}[-/.]\d{2}[-/.]\d{4})",
            text,
            re.IGNORECASE,
        )
        if match:
            data["confirmed_since"] = match.group(1).strip()

    @classmethod
    def _extract_issued_place_and_date(cls, text: str, data: Dict[str, Any]) -> None:
        match = re.search(
            r"\b([A-Za-z\s]+?),\s*(\d{1,2}\s+\w+\s+\d{4})",
            text,
        )
        if match:
            data["issued_place"] = match.group(1).strip()
            data["issued_date"] = match.group(2).strip()

    @classmethod
    def _extract_signing_official(cls, lines: list, data: Dict[str, Any]) -> None:
        title_parts = []
        for i, line in enumerate(lines):
            if re.search(r"^A\.?N\.?\s*KEPALA\s*KANTOR", line, re.IGNORECASE):
                title_parts.append(line.strip())
                if i + 1 < len(lines) and not re.search(r"^NIP", lines[i + 1], re.IGNORECASE):
                    title_parts.append(lines[i + 1].strip().rstrip(","))
                break
        if title_parts:
            data["signing_official_title"] = " ".join(title_parts)

        for i, line in enumerate(lines):
            nip_match = re.search(r"NIP\s*[:\.]?\s*(\d{9,20})", line, re.IGNORECASE)
            if nip_match:
                data["signing_official_number"] = nip_match.group(1)
                if i - 1 >= 0:
                    name_candidate = lines[i - 1].strip()
                    if name_candidate and name_candidate.isupper():
                        data["signing_official_name"] = name_candidate
                break
