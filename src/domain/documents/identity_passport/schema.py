import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from src.utility.date_utils import normalize_to_iso_date


class IdentityPassportSchema(BaseModel):
    """Schema for an international passport bio-data page (ICAO Doc 9303 TD3 format).

    Passports are internationally standardized via the Machine Readable Zone (MRZ,
    the two fixed-width lines at the bottom of the page), but the printed/visual
    fields around it are labeled per-country in that country's own language(s).
    This schema captures the fields common across countries: the MRZ itself
    (verbatim, for audit/checksum use) plus the handful of visual fields that
    appear on essentially every passport regardless of issuing country.
    """

    document_type: Optional[str] = Field(
        default=None,
        description="MRZ document code, normally 'P' for an ordinary passport",
        examples=["P"]
    )
    document_issuing_country: Optional[str] = Field(
        default=None,
        description="3-letter ICAO issuing country/organization code",
        examples=["USA", "JPN", "KOR", "NLD", "PHL"]
    )
    holder_surname: Optional[str] = Field(
        default=None,
        description="Holder's surname/family name",
        examples=["SMITH"]
    )
    holder_given_names: Optional[str] = Field(
        default=None,
        description="Holder's given name(s)",
        examples=["JANE"]
    )
    holder_passport_number: Optional[str] = Field(
        default=None,
        description="Passport document number",
        examples=["PP3000000"]
    )
    holder_nationality: Optional[str] = Field(
        default=None,
        description="3-letter ICAO nationality code",
        examples=["USA", "JPN", "KOR", "NLD", "PHL"]
    )
    holder_birth_date: Optional[str] = Field(
        default=None,
        description="Date of birth, normalized to ISO 8601 (YYYY-MM-DD)",
        examples=["1981-07-14"]
    )
    holder_gender: Optional[str] = Field(
        default=None,
        description="Sex as printed/encoded: 'M', 'F', or 'X'",
        examples=["F"]
    )
    holder_birth_place: Optional[str] = Field(
        default=None,
        description="Place of birth, if printed (not every issuing country prints this)",
        examples=["MANILA"]
    )
    document_issued_date: Optional[str] = Field(
        default=None,
        description="Date the passport was issued, normalized to ISO 8601 (YYYY-MM-DD)",
        examples=["2013-01-01"]
    )
    document_expiry_date: Optional[str] = Field(
        default=None,
        description="Date the passport expires, normalized to ISO 8601 (YYYY-MM-DD)",
        examples=["2022-12-31"]
    )
    document_issuing_authority: Optional[str] = Field(
        default=None,
        description="Authority that issued the passport",
        examples=["INTERIOR MINISTRY", "DFA MANILA", "UNITED STATES DEPARTMENT OF STATE"]
    )
    document_mrz_line1: Optional[str] = Field(
        default=None,
        description="Raw first line of the Machine Readable Zone, verbatim (44 characters, TD3 format)",
        examples=["P<EOLSMITH<<JANE<<<<<<<<<<<<<<<<<<<<<<<<<<<<"]
    )
    document_mrz_line2: Optional[str] = Field(
        default=None,
        description="Raw second line of the Machine Readable Zone, verbatim (44 characters, TD3 format)",
        examples=["PP3000009EOL8107145F2212315<<<<<<<<<<<<<<<02"]
    )

    @field_validator("document_type", "document_issuing_country", "holder_nationality", mode="before")
    @classmethod
    def clean_code_fields(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip().upper().replace("<", "")
        return cleaned or None

    @field_validator("holder_surname", "holder_given_names", mode="before")
    @classmethod
    def clean_name_fields(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:SURNAME|GIVEN\s*NAMES?)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE)
        cleaned = cleaned.replace("<", " ")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or None

    @field_validator("holder_passport_number", mode="before")
    @classmethod
    def clean_holder_passport_number(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:PASSPORT\s*(?:NO\.?|NUMBER|N[°o])?)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE)
        cleaned = cleaned.replace("<", "").strip()
        return cleaned or None

    @field_validator("holder_gender", mode="before")
    @classmethod
    def clean_holder_gender(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip().upper().replace("<", "")
        if cleaned in ("M", "F", "X"):
            return cleaned
        return cleaned or None

    @field_validator("holder_birth_place", "document_issuing_authority", mode="before")
    @classmethod
    def clean_text_fields(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        return v.strip() or None

    @field_validator("holder_birth_date", "document_issued_date", "document_expiry_date", mode="before")
    @classmethod
    def clean_date_fields(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip()
        iso_date = normalize_to_iso_date(cleaned)
        return iso_date or (cleaned or None)

    @field_validator("document_mrz_line1", "document_mrz_line2", mode="before")
    @classmethod
    def clean_mrz_line(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"\s+", "", v.strip().upper())
        return cleaned or None
