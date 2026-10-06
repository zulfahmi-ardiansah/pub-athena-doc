import re
from typing import Any, Dict
from src.domain.documents.business_deed.schema import BusinessDeedSchema


class BusinessDeedStringParser:
    """
    Deterministic rule-based & regex parser for Indonesian business deed filings
    (notarial Akta + Kemenkumham SK decree). Both document types follow legally
    mandated opening/closing formulas that are consistent across notaries and
    decades (Indonesian Notary Law / UUJN for the deed, standard Kemenkumham
    decree drafting for the SK), which this parser targets. 'notary_address'
    varies too much by notary/document template to regex reliably and is left
    for the LLM-based engines.
    """

    @classmethod
    def parse(cls, raw_text: str) -> BusinessDeedSchema:
        data: Dict[str, Any] = {}

        cls._extract_sk(raw_text, data)
        cls._extract_deed_number_and_date(raw_text, data)
        cls._extract_notary_name(raw_text, data)

        return BusinessDeedSchema.model_validate(data)

    @classmethod
    def _extract_sk(cls, text: str, data: Dict[str, Any]) -> None:
        # Anchor strictly to the decree's own title block
        number_match = re.search(
            r"KEPUTUSAN\s+MENTERI\s+(?:HUKUM\s+DAN\s+HAK\s+ASASI\s+MANUSIA|KEHAKIMAN)\s+REPUBLIK\s+INDONESIA"
            r"\s*\n?\s*NOMOR\s*:?\s*([A-Z0-9][A-Z0-9.\-]*(?:TAHUN|TH)\.?\s*\d{2,4})",
            text,
            re.IGNORECASE,
        )
        if number_match:
            data["decision_number"] = number_match.group(1).strip()

        date_match = re.search(
            r"DITETAPKAN\s*DI\s+([A-Za-z\s]+?)[,\n]\s*(?:PADA\s*)?TANGGAL\s*(\d{1,2}\s+\w+\s+\d{4})",
            text,
            re.IGNORECASE,
        )
        if date_match:
            data["decision_issued_date"] = date_match.group(2).strip()

    @classmethod
    def _extract_deed_number_and_date(cls, text: str, data: Dict[str, Any]) -> None:
        # The deed's mandated opening formula
        for candidate in re.finditer(r"\bNOMOR\s*:?\s*(\d{1,5})\s*\.", text, re.IGNORECASE):
            window = text[candidate.end():candidate.end() + 80]
            if re.search(r"PADA\s+HARI\s+INI", window, re.IGNORECASE):
                data["deed_number"] = candidate.group(1).strip()
                date_window = text[candidate.end():candidate.end() + 300]
                date_match = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b", date_window)
                if date_match:
                    data["deed_date"] = date_match.group(1)

                # The deed's own title (e.g. '= AKTA PENDIRIAN ... =' or
                # 'PERUBAHAN ANGGARAN DASAR') sits directly above its opening
                # formula. Look backward from there rather than anywhere in the
                # text, since a deed's recital/background prose can mention an
                # unrelated prior deed's type (e.g. an amendment deed's recital
                # referencing the company's original 'akta pendirian').
                title_window = text[max(0, candidate.start() - 300):candidate.start()]
                pendirian_pos = title_window.upper().rfind("PENDIRIAN")
                perubahan_pos = title_window.upper().rfind("PERUBAHAN")
                if pendirian_pos == -1 and perubahan_pos == -1:
                    pass
                elif perubahan_pos > pendirian_pos:
                    data["deed_type"] = "Perubahan"
                else:
                    data["deed_type"] = "Pendirian"
                return

    @classmethod
    def _extract_notary_name(cls, text: str, data: Dict[str, Any]) -> None:
        match = re.search(
            r"BERHADAPAN\s+DENGAN\s+SAYA,?\s*([A-Z][A-Za-z.\s\-]+?),\s*SARJANA\s+HUKUM",
            text,
            re.IGNORECASE,
        )
        if match:
            name = re.sub(r"[\s\-]+", " ", match.group(1)).strip()
            data["notary_name"] = name
