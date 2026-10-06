import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from src.utility.date_utils import normalize_to_iso_date


class TaxNumberSchema(BaseModel):
    """Schema for Indonesian Tax Identification Number (NPWP - Nomor Pokok Wajib Pajak)."""

    tax_number: Optional[str] = Field(
        default=None,
        description="Nomor Pokok Wajib Pajak / NPWP (15 or 16 digits format)",
        examples=["01.234.567.8-901.000", "12.345.678.9-636.000"]
    )
    business_name: Optional[str] = Field(
        default=None,
        description="Taxpayer Name (Nama Wajib Pajak, e.g. 'BUDI')",
        examples=["BUDI", "PT CONTOH MAKMUR"]
    )
    tax_office: Optional[str] = Field(
        default=None,
        description="Tax Branch Office where registered (Kantor Pelayanan Pajak / KPP, e.g. 'KPP MADYA GRESIK')",
        examples=["KPP MADYA GRESIK"]
    )
    tax_office_address: Optional[str] = Field(
        default=None,
        description="Tax Branch Office Address (Alamat KPP, e.g. 'JL DR WAHIDIN SUDIROHUSODO 700 GRESIK')",
        examples=["JL DR WAHIDIN SUDIROHUSODO 700 GRESIK"]
    )
    tax_registration_date: Optional[str] = Field(
        default=None,
        description="Registration date (Tanggal Terdaftar), normalized to ISO 8601 (YYYY-MM-DD)",
        examples=["2022-01-01"]
    )

    @field_validator("tax_number", mode="before")
    @classmethod
    def clean_and_validate_tax_number(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^NPWP\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        cleaned_digits = re.sub(r"[^\dOo]", "", cleaned).replace("O", "0").replace("o", "0")
        if len(cleaned_digits) in (15, 16):
            return cleaned
        return v.strip()

    @field_validator("business_name", mode="before")
    @classmethod
    def clean_business_name(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:NAMA\s*(?:WAJIB\s*PAJAK)?|NAME)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("tax_office", mode="before")
    @classmethod
    def clean_tax_office(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip()
        cleaned = re.sub(r"^(?:KANTOR\s*PELAYANAN\s*PAJAK|KPP)\s*[:\.]?\s*", "KPP ", cleaned, flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("tax_office_address", mode="before")
    @classmethod
    def clean_tax_office_address(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:ALAMAT|ADDRESS)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("tax_registration_date", mode="before")
    @classmethod
    def clean_tax_registration_date(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:TANGGAL\s*TERDAFTAR|TGL\s*DAFTAR|REGISTRATION\s*DATE)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        iso_date = normalize_to_iso_date(cleaned)
        return iso_date or (cleaned or None)
