import re
from typing import Optional

_INDONESIAN_MONTHS = {
    "januari": "01",
    "februari": "02",
    "maret": "03",
    "april": "04",
    "mei": "05",
    "juni": "06",
    "juli": "07",
    "agustus": "08",
    "september": "09",
    "oktober": "10",
    "november": "11",
    "desember": "12",
}

_ENGLISH_MONTHS = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "sept": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}


def normalize_to_iso_date(value: Optional[str]) -> Optional[str]:
    """
    Normalizes a date string to ISO 8601 (YYYY-MM-DD).

    Accepts numeric DD-MM-YYYY / DD/MM/YYYY / DD.MM.YYYY, already-ISO YYYY-MM-DD,
    and Indonesian textual dates (e.g. '22 Oktober 2021'). Returns None if the
    value doesn't contain a recognizable date, so callers can fall back to the
    original (possibly non-date) text, e.g. 'SEUMUR HIDUP'.
    """
    if not value or not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None

    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", cleaned)
    if iso_match:
        return iso_match.group(0)

    numeric_match = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", cleaned)
    if numeric_match:
        day, month, year = numeric_match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # Optional non-Latin/other-language prefix before the month token, for
    # bilingual dates like '10 MAA/MAR 1965' or '01 2월/FEB 1987'.
    text_match = re.search(r"\b(\d{1,2})\s+(?:\S*/)?([A-Za-z]{3,9})\.?\s+(\d{4})\b", cleaned)
    if text_match:
        day, month_name, year = text_match.groups()
        month_key = month_name.strip().lower()
        month_num = _INDONESIAN_MONTHS.get(month_key) or _ENGLISH_MONTHS.get(month_key)
        if month_num:
            return f"{year}-{month_num}-{int(day):02d}"

    return None
