import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from src.utility.date_utils import normalize_to_iso_date


class IdentityStaySchema(BaseModel):
    issuing_office: Optional[str] = Field(default=None, description="Immigration office printed in the header", examples=["KANIM KELAS I KHUSUS NON TPI JAKARTA SELATAN"])
    issuing_office_address: Optional[str] = Field(default=None, description="Address of the issuing immigration office", examples=["JL. CONTOH NO. 10 JAKARTA SELATAN"])
    niora: Optional[str] = Field(default=None, description="NIORA immigration registration number", examples=["12ABCD345678"])
    permit_number: Optional[str] = Field(default=None, description="Limited stay permit number", examples=["2C21AB1234YZ"])
    permit_expiry_date: Optional[str] = Field(default=None, description="Stay/multiple entries permit expiry date in YYYY-MM-DD", examples=["2025-04-18"])
    permit_index: Optional[str] = Field(default=None, description="Stay permit index as printed", examples=["1B"])
    full_name: Optional[str] = Field(default=None, description="Holder's full name", examples=["JANE DOE"])
    birth_place: Optional[str] = Field(default=None, description="Place of birth, separate from the birth date", examples=["SINGAPORE"])
    birth_date: Optional[str] = Field(default=None, description="Date of birth in YYYY-MM-DD", examples=["1984-03-04"])
    passport_number: Optional[str] = Field(default=None, description="Holder's passport number", examples=["P1234567"])
    passport_expiry_date: Optional[str] = Field(default=None, description="Passport expiry date in YYYY-MM-DD", examples=["2028-01-11"])
    nationality: Optional[str] = Field(default=None, description="Nationality as printed", examples=["SINGAPURA"])
    gender: Optional[str] = Field(default=None, description="Gender as printed", examples=["FEMALE"])
    address: Optional[str] = Field(default=None, description="Holder's address in Indonesia", examples=["JL. CONTOH NO. 10 JAKARTA"])
    occupation: Optional[str] = Field(default=None, description="Occupation as printed", examples=["INVESTOR"])
    status: Optional[str] = Field(default=None, description="Immigration stay status as printed", examples=["INVESTMENT"])
    guarantor_name: Optional[str] = Field(default=None, description="Guarantor name, when printed", examples=["PT CONTOH INDONESIA"])
    issued_place: Optional[str] = Field(default=None, description="Place in the issue line at the foot of the permit", examples=["Jakarta"])
    issued_date: Optional[str] = Field(default=None, description="Date in the issue line at the foot of the permit, in YYYY-MM-DD", examples=["2024-01-26"])
    signing_official_title: Optional[str] = Field(default=None, description="Title of the official printed under the issue line", examples=["Head of Immigration Office"])

    @field_validator("issuing_office", mode="before")
    @classmethod
    def clean_issuing_office(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^(?:ISSUING\s*OFFICE|IMMIGRATION\s*OFFICE)\s*[:.]?\s*")

    @field_validator("issuing_office_address", mode="before")
    @classmethod
    def clean_issuing_office_address(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^(?:ISSUING\s*OFFICE\s*ADDRESS|IMMIGRATION\s*OFFICE\s*ADDRESS)\s*[:.]?\s*")

    @field_validator("niora", mode="before")
    @classmethod
    def clean_niora(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^NIORA\s*[:.]?\s*")

    @field_validator("permit_number", mode="before")
    @classmethod
    def clean_permit_number(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^PERMIT\s*NUMBER\s*[:.]?\s*")

    @field_validator("permit_index", mode="before")
    @classmethod
    def clean_permit_index(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^STAY\s*PERMIT\s*INDEX\s*[:.]?\s*")

    @field_validator("full_name", mode="before")
    @classmethod
    def clean_full_name(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^FULL\s*NAME\s*[:.]?\s*")

    @field_validator("birth_place", mode="before")
    @classmethod
    def clean_birth_place(cls, v: Optional[str]) -> Optional[str]:
        value = cls._clean(v, r"^(?:PLACE\s*/\s*DATE\s*OF\s*BIRTH|PLACE\s*OF\s*BIRTH)\s*[:.]?\s*")
        if value:
            value = re.sub(r"\s*/\s*\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\s*$", "", value).strip()
        return value or None

    @field_validator("birth_date", mode="before")
    @classmethod
    def clean_birth_date(cls, v: Optional[str]) -> Optional[str]:
        return cls._date(v, r"^(?:PLACE\s*/\s*DATE\s*OF\s*BIRTH|DATE\s*OF\s*BIRTH)\s*[:.]?\s*")

    @field_validator("passport_number", mode="before")
    @classmethod
    def clean_passport_number(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^PASSPORT\s*NUMBER\s*[:.]?\s*")

    @field_validator("permit_expiry_date", mode="before")
    @classmethod
    def clean_stay_expiry(cls, v: Optional[str]) -> Optional[str]:
        return cls._date(v, r"^STAY\s*/\s*MULTIPLE\s*ENTRIES\s*PERMIT\s*EXPIRY\s*[:.]?\s*")

    @field_validator("passport_expiry_date", mode="before")
    @classmethod
    def clean_passport_expiry(cls, v: Optional[str]) -> Optional[str]:
        return cls._date(v, r"^PASSPORT\s*EXPIRY\s*[:.]?\s*")

    @field_validator("issued_date", mode="before")
    @classmethod
    def clean_issued_date(cls, v: Optional[str]) -> Optional[str]:
        return cls._date(v, r"^ISSUED\s*DATE\s*[:.]?\s*")

    @field_validator("nationality", mode="before")
    @classmethod
    def clean_nationality(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^NATIONALITY\s*[:.]?\s*")

    @field_validator("gender", mode="before")
    @classmethod
    def clean_gender(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^GENDER\s*[:.]?\s*")

    @field_validator("address", mode="before")
    @classmethod
    def clean_address(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^ADDRESS\s*[:.]?\s*")

    @field_validator("occupation", mode="before")
    @classmethod
    def clean_occupation(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^OCCUPATION\s*[:.]?\s*")

    @field_validator("status", mode="before")
    @classmethod
    def clean_status(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^STATUS\s*[:.]?\s*")

    @field_validator("guarantor_name", mode="before")
    @classmethod
    def clean_guarantor_name(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^GUARANTOR\s*NAME\s*[:.]?\s*")

    @field_validator("issued_place", mode="before")
    @classmethod
    def clean_issued_place(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^ISSUED\s*PLACE\s*[:.]?\s*")

    @field_validator("signing_official_title", mode="before")
    @classmethod
    def clean_signing_official_title(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^SIGNING\s*OFFICIAL\s*TITLE\s*[:.]?\s*")

    @staticmethod
    def _clean(value: Optional[str], label: str) -> Optional[str]:
        if not isinstance(value, str):
            return None
        cleaned = re.sub(label, "", value.strip(), flags=re.IGNORECASE).strip()
        return cleaned if cleaned and cleaned not in ("-", "–", "—") else None

    @classmethod
    def _date(cls, value: Optional[str], label: str) -> Optional[str]:
        cleaned = cls._clean(value, label)
        return normalize_to_iso_date(cleaned) if cleaned else None
