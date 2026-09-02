import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class IdentityCardSchema(BaseModel):
    """Schema for Indonesian Identity Card (KTP - Kartu Tanda Penduduk)."""

    id_number: Optional[str] = Field(
        default=None,
        description="Nomor Induk Kependudukan / NIK (16 digits)",
        examples=["3171010101900001"]
    )
    full_name: Optional[str] = Field(
        default=None,
        description="Full Name as printed on KTP (Nama)"
    )
    birth_place: Optional[str] = Field(
        default=None,
        description="Place of Birth (Tempat Lahir)"
    )
    birth_date: Optional[str] = Field(
        default=None,
        description="Date of Birth (Tanggal Lahir, format: DD-MM-YYYY or text)"
    )
    gender: Optional[str] = Field(
        default=None,
        description="Gender (Jenis Kelamin: LAKI-LAKI or PEREMPUAN)"
    )
    blood_type: Optional[str] = Field(
        default=None,
        description="Blood type (Golongan Darah: A, B, AB, O, or -)"
    )
    address: Optional[str] = Field(
        default=None,
        description="Street / Residential Address (Alamat)"
    )
    neighborhood_unit: Optional[str] = Field(
        default=None,
        description="Neighborhood numbering (RT/RW e.g. 001/002)"
    )
    village: Optional[str] = Field(
        default=None,
        description="Village / Urban Community (Kelurahan or Desa)"
    )
    district: Optional[str] = Field(
        default=None,
        description="Sub-district (Kecamatan)"
    )
    religion: Optional[str] = Field(
        default=None,
        description="Religion (Agama: ISLAM, KRISTEN, KATHOLIK, HINDU, BUDDHA, KHONGHUCU)"
    )
    marital_status: Optional[str] = Field(
        default=None,
        description="Marital Status (Status Perkawinan: BELUM KAWIN, KAWIN, CERAI HIDUP, CERAI MATI)"
    )
    occupation: Optional[str] = Field(
        default=None,
        description="Occupation / Profession (Pekerjaan)"
    )
    nationality: Optional[str] = Field(
        default="WNI",
        description="Nationality (Kewarganegaraan: WNI or WNA)"
    )
    valid_until: Optional[str] = Field(
        default="SEUMUR HIDUP",
        description="Validity period (Berlaku Hingga: e.g. SEUMUR HIDUP or date)"
    )

    @field_validator("id_number")
    @classmethod
    def clean_and_validate_id_number(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        # Remove any whitespace or punctuation
        cleaned = re.sub(r"[^\d]", "", v)
        if len(cleaned) == 16:
            return cleaned
        return v
