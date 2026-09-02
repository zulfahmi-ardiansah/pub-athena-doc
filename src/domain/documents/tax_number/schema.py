import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class TaxNumberSchema(BaseModel):
    """Schema for Indonesian Tax Identification Number (NPWP - Nomor Pokok Wajib Pajak)."""

    tax_id_number: Optional[str] = Field(
        default=None,
        description="Nomor Pokok Wajib Pajak / NPWP (15 or 16 digits format)",
        examples=["01.234.567.8-901.000", "012345678901000"]
    )
    taxpayer_name: Optional[str] = Field(
        default=None,
        description="Taxpayer Name (Nama Wajib Pajak)"
    )
    national_id_number: Optional[str] = Field(
        default=None,
        description="Linked NIK for individual NPWP (16 digits)",
        examples=["3171010101900001"]
    )
    address: Optional[str] = Field(
        default=None,
        description="Registered Taxpayer Address (Alamat)"
    )
    tax_office: Optional[str] = Field(
        default=None,
        description="Tax Office where registered (Kantor Pelayanan Pajak / KPP)"
    )
    registration_date: Optional[str] = Field(
        default=None,
        description="Registration date (Tanggal Terdaftar)"
    )

    @field_validator("tax_id_number")
    @classmethod
    def clean_and_validate_tax_id_number(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        cleaned = re.sub(r"[^\d]", "", v)
        if len(cleaned) in (15, 16):
            return v.strip()
        return v

    @field_validator("national_id_number")
    @classmethod
    def clean_and_validate_national_id_number(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        cleaned = re.sub(r"[^\d]", "", v)
        if len(cleaned) == 16:
            return cleaned
        return v
