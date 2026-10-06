import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from src.utility.date_utils import normalize_to_iso_date


class IdentityStaySchema(BaseModel):
    permit_issuing_office: Optional[str] = Field(default=None, description="Immigration office printed in the header", examples=["KANIM KELAS I KHUSUS NON TPI JAKARTA SELATAN"])
    permit_issuing_office_address: Optional[str] = Field(default=None, description="Address of the issuing immigration office", examples=["JL. CONTOH NO. 10 JAKARTA SELATAN"])
    permit_niora: Optional[str] = Field(default=None, description="NIORA immigration registration number", examples=["12ABCD345678"])
    permit_number: Optional[str] = Field(default=None, description="Limited stay permit number", examples=["2C21AB1234YZ"])
    permit_expiry_date: Optional[str] = Field(default=None, description="Stay/multiple entries permit expiry date in YYYY-MM-DD", examples=["2025-04-18"])
    permit_index: Optional[str] = Field(default=None, description="Stay permit index as printed", examples=["1B"])
    holder_full_name: Optional[str] = Field(default=None, description="Holder's full name", examples=["JANE DOE"])
    holder_birth_place: Optional[str] = Field(default=None, description="Place of birth, separate from the birth date", examples=["SINGAPORE"])
    holder_birth_date: Optional[str] = Field(default=None, description="Date of birth in YYYY-MM-DD", examples=["1984-03-04"])
    holder_passport_number: Optional[str] = Field(default=None, description="Holder's passport number", examples=["P1234567"])
    holder_passport_expiry_date: Optional[str] = Field(default=None, description="Passport expiry date in YYYY-MM-DD", examples=["2028-01-11"])
    holder_nationality: Optional[str] = Field(default=None, description="Nationality as printed", examples=["SINGAPURA"])
    holder_gender: Optional[str] = Field(default=None, description="Gender as printed", examples=["FEMALE"])
    holder_address: Optional[str] = Field(default=None, description="Holder's address in Indonesia", examples=["JL. CONTOH NO. 10 JAKARTA"])
    holder_occupation: Optional[str] = Field(default=None, description="Occupation as printed", examples=["INVESTOR"])
    holder_status: Optional[str] = Field(default=None, description="Immigration stay status as printed", examples=["INVESTMENT"])
    holder_guarantor: Optional[str] = Field(default=None, description="Guarantor name, when printed", examples=["PT CONTOH INDONESIA"])
    permit_issued_place: Optional[str] = Field(default=None, description="Place in the issue line at the foot of the permit", examples=["Jakarta"])
    permit_issued_date: Optional[str] = Field(default=None, description="Date in the issue line at the foot of the permit, in YYYY-MM-DD", examples=["2024-01-26"])

    @field_validator("permit_issuing_office", mode="before")
    @classmethod
    def clean_permit_issuing_office(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^(?:ISSUING\s*OFFICE|IMMIGRATION\s*OFFICE)\s*[:.]?\s*")

    @field_validator("permit_issuing_office_address", mode="before")
    @classmethod
    def clean_permit_issuing_office_address(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^(?:ISSUING\s*OFFICE\s*ADDRESS|IMMIGRATION\s*OFFICE\s*ADDRESS)\s*[:.]?\s*")

    @field_validator("permit_niora", mode="before")
    @classmethod
    def clean_permit_niora(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^NIORA\s*[:.]?\s*")

    @field_validator("permit_number", mode="before")
    @classmethod
    def clean_permit_number(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^PERMIT\s*NUMBER\s*[:.]?\s*")

    @field_validator("permit_index", mode="before")
    @classmethod
    def clean_permit_index(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^STAY\s*PERMIT\s*INDEX\s*[:.]?\s*")

    @field_validator("holder_full_name", mode="before")
    @classmethod
    def clean_holder_full_name(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^FULL\s*NAME\s*[:.]?\s*")

    @field_validator("holder_birth_place", mode="before")
    @classmethod
    def clean_holder_birth_place(cls, v: Optional[str]) -> Optional[str]:
        value = cls._clean(v, r"^(?:PLACE\s*/\s*DATE\s*OF\s*BIRTH|PLACE\s*OF\s*BIRTH)\s*[:.]?\s*")
        if value:
            value = re.sub(r"\s*/\s*\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\s*$", "", value).strip()
        return value or None

    @field_validator("holder_birth_date", mode="before")
    @classmethod
    def clean_holder_birth_date(cls, v: Optional[str]) -> Optional[str]:
        return cls._date(v, r"^(?:PLACE\s*/\s*DATE\s*OF\s*BIRTH|DATE\s*OF\s*BIRTH)\s*[:.]?\s*")

    @field_validator("holder_passport_number", mode="before")
    @classmethod
    def clean_holder_passport_number(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^PASSPORT\s*NUMBER\s*[:.]?\s*")

    @field_validator("permit_expiry_date", mode="before")
    @classmethod
    def clean_stay_expiry(cls, v: Optional[str]) -> Optional[str]:
        return cls._date(v, r"^STAY\s*/\s*MULTIPLE\s*ENTRIES\s*PERMIT\s*EXPIRY\s*[:.]?\s*")

    @field_validator("holder_passport_expiry_date", mode="before")
    @classmethod
    def clean_passport_expiry(cls, v: Optional[str]) -> Optional[str]:
        return cls._date(v, r"^PASSPORT\s*EXPIRY\s*[:.]?\s*")

    @field_validator("permit_issued_date", mode="before")
    @classmethod
    def clean_permit_issued_date(cls, v: Optional[str]) -> Optional[str]:
        return cls._date(v, r"^ISSUED\s*DATE\s*[:.]?\s*")

    @field_validator("holder_nationality", mode="before")
    @classmethod
    def clean_holder_nationality(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^NATIONALITY\s*[:.]?\s*")

    @field_validator("holder_gender", mode="before")
    @classmethod
    def clean_holder_gender(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^GENDER\s*[:.]?\s*")

    @field_validator("holder_address", mode="before")
    @classmethod
    def clean_holder_address(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^ADDRESS\s*[:.]?\s*")

    @field_validator("holder_occupation", mode="before")
    @classmethod
    def clean_holder_occupation(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^OCCUPATION\s*[:.]?\s*")

    @field_validator("holder_status", mode="before")
    @classmethod
    def clean_holder_status(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^STATUS\s*[:.]?\s*")

    @field_validator("holder_guarantor", mode="before")
    @classmethod
    def clean_holder_guarantor(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^GUARANTOR\s*NAME\s*[:.]?\s*")

    @field_validator("permit_issued_place", mode="before")
    @classmethod
    def clean_permit_issued_place(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^ISSUED\s*PLACE\s*[:.]?\s*")

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
