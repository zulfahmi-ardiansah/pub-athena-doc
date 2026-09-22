import re
from datetime import date
from typing import Any, Dict, Optional, Tuple
from src.domain.documents.passport.schema import PassportSchema


class PassportStringParser:
    """
    Deterministic parser for the Machine Readable Zone (MRZ) of an international
    passport bio-data page (ICAO Doc 9303 TD3 format: two fixed-width 44-character
    lines). The MRZ layout is identical worldwide regardless of issuing country or
    language, unlike the surrounding printed/visual fields - so this parser fills
    everything the MRZ encodes and leaves VIZ-only fields (place_of_birth,
    date_of_issue, issuing_authority) for the LLM-based engines to read.
    """

    @classmethod
    def parse(cls, raw_text: str) -> PassportSchema:
        data: Dict[str, Any] = {}
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        line1, line2 = cls._find_mrz_lines(lines)
        if line1 and line2:
            cls._parse_line1(line1, data)
            cls._parse_line2(line2, data)

        return PassportSchema.model_validate(data)

    @classmethod
    def _find_mrz_lines(cls, lines: list) -> Tuple[Optional[str], Optional[str]]:
        candidates = []
        for line in lines:
            compact = re.sub(r"\s+", "", line).upper()
            if len(compact) >= 40 and re.fullmatch(r"[A-Z0-9<]+", compact):
                candidates.append(cls._pad_or_trim(compact))
        if len(candidates) >= 2:
            return candidates[-2], candidates[-1]
        return None, None

    @classmethod
    def _pad_or_trim(cls, s: str, length: int = 44) -> str:
        if len(s) < length:
            return s + "<" * (length - len(s))
        return s[:length]

    @classmethod
    def _parse_line1(cls, line1: str, data: Dict[str, Any]) -> None:
        data["mrz_line1"] = line1
        data["document_type"] = line1[0:2]
        data["issuing_country"] = line1[2:5]

        name_field = line1[5:44]
        if "<<" in name_field:
            surname_part, given_part = name_field.split("<<", 1)
        else:
            surname_part, given_part = name_field, ""
        data["surname"] = surname_part
        data["given_names"] = given_part

    @classmethod
    def _parse_line2(cls, line2: str, data: Dict[str, Any]) -> None:
        data["mrz_line2"] = line2
        data["passport_number"] = line2[0:9]
        data["nationality"] = line2[10:13]
        data["date_of_birth"] = cls._mrz_date_to_iso(line2[13:19], prefer_future=False)
        data["sex"] = line2[20]
        data["date_of_expiry"] = cls._mrz_date_to_iso(line2[21:27], prefer_future=True)

    @classmethod
    def _mrz_date_to_iso(cls, raw: str, prefer_future: bool) -> Optional[str]:
        if not raw or not raw.isdigit() or len(raw) != 6:
            return None
        yy, mm, dd = int(raw[0:2]), int(raw[2:4]), int(raw[4:6])
        try:
            candidate_2000 = date(2000 + yy, mm, dd)
        except ValueError:
            return None
        if prefer_future:
            # Expiry dates: MRZ-era passports are always issued/expiring in the 2000s+.
            return candidate_2000.isoformat()
        if candidate_2000 > date.today():
            try:
                return date(1900 + yy, mm, dd).isoformat()
            except ValueError:
                return None
        return candidate_2000.isoformat()
