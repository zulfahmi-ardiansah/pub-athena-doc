import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from src.utility.date_utils import normalize_to_iso_date


class IdentityCardSchema(BaseModel):
    """Schema for Indonesian Identity Card (KTP - Kartu Tanda Penduduk)."""

    province: Optional[str] = Field(
        default=None,
        description="Province name (Provinsi, without 'PROVINSI' prefix, e.g. 'DKI JAKARTA')",
        examples=["DKI JAKARTA"]
    )
    city: Optional[str] = Field(
        default=None,
        description="City or Regency name (Kota/Kabupaten, e.g. 'JAKARTA PUSAT')",
        examples=["JAKARTA PUSAT"]
    )
    id_number: Optional[str] = Field(
        default=None,
        description="Nomor Induk Kependudukan / NIK (16 digits)",
        examples=["3372052106610006"]
    )
    full_name: Optional[str] = Field(
        default=None,
        description="Full Name (Nama, e.g. 'IR JOKO WIDODO')",
        examples=["IR JOKO WIDODO"]
    )
    birth_place: Optional[str] = Field(
        default=None,
        description="Place of birth (Tempat Lahir, e.g. 'SURAKARTA')",
        examples=["SURAKARTA"]
    )
    birth_date: Optional[str] = Field(
        default=None,
        description="Date of birth (Tanggal Lahir), normalized to ISO 8601 (YYYY-MM-DD)",
        examples=["1961-06-21"]
    )
    gender: Optional[str] = Field(
        default=None,
        description="Gender (Jenis Kelamin: 'LAKI-LAKI' or 'PEREMPUAN')",
        examples=["LAKI-LAKI"]
    )
    blood_type: Optional[str] = Field(
        default=None,
        description="Blood type (Golongan Darah: 'A', 'B', 'AB', 'O', or '-')",
        examples=["A"]
    )
    address: Optional[str] = Field(
        default=None,
        description="Street / Residential address (Alamat, e.g. 'JL TAMAN SUROPATI NO. 7')",
        examples=["JL TAMAN SUROPATI NO. 7"]
    )
    neighborhood_unit: Optional[str] = Field(
        default=None,
        description="RT/RW numbering (e.g. '005' or '005/005')",
        examples=["005"]
    )
    village: Optional[str] = Field(
        default=None,
        description="Village / Urban community (Kelurahan or Desa, e.g. 'MENTENG')",
        examples=["MENTENG"]
    )
    district: Optional[str] = Field(
        default=None,
        description="Sub-district (Kecamatan, e.g. 'MENTENG')",
        examples=["MENTENG"]
    )
    religion: Optional[str] = Field(
        default=None,
        description="Religion (Agama: 'ISLAM', 'KRISTEN', 'KATHOLIK', 'HINDU', 'BUDDHA', 'KHONGHUCU')",
        examples=["ISLAM"]
    )
    marital_status: Optional[str] = Field(
        default=None,
        description="Marital status (Status Perkawinan: 'BELUM KAWIN', 'KAWIN', 'CERAI HIDUP', 'CERAI MATI')",
        examples=["KAWIN"]
    )
    occupation: Optional[str] = Field(
        default=None,
        description="Occupation / Profession (Pekerjaan, e.g. 'GUBERNUR')",
        examples=["GUBERNUR"]
    )
    nationality: Optional[str] = Field(
        default="WNI",
        description="Nationality (Kewarganegaraan: 'WNI' or 'WNA')",
        examples=["WNI"]
    )
    valid_until: Optional[str] = Field(
        default="SEUMUR HIDUP",
        description="Validity period (Berlaku Hingga: ISO 8601 date 'YYYY-MM-DD' or 'SEUMUR HIDUP')",
        examples=["2017-06-21"]
    )

    @field_validator("province", mode="before")
    @classmethod
    def clean_province(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^PROVINSI\s+", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("id_number", mode="before")
    @classmethod
    def clean_and_validate_id_number(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^NIK\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        cleaned_digits = re.sub(r"[^\dOo]", "", cleaned).replace("O", "0").replace("o", "0")
        if len(cleaned_digits) == 16:
            return cleaned_digits
        return v.strip()

    @field_validator("birth_place", mode="before")
    @classmethod
    def clean_birth_place(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip()
        cleaned = re.sub(r",\s*\d{1,2}[-/.\s][\w\d\s/-]+$", "", cleaned).strip()
        if "," in cleaned:
            cleaned = cleaned.split(",")[0].strip()
        return cleaned or None

    @field_validator("birth_date", mode="before")
    @classmethod
    def clean_birth_date(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip()
        iso_date = normalize_to_iso_date(cleaned)
        return iso_date or (cleaned or None)

    @field_validator("gender", mode="before")
    @classmethod
    def clean_gender(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip().upper()
        if "LAKI" in cleaned or "PRIA" in cleaned:
            return "LAKI-LAKI"
        if "PEREMPUAN" in cleaned or "WANITA" in cleaned:
            return "PEREMPUAN"
        return cleaned or None

    @field_validator("neighborhood_unit", mode="before")
    @classmethod
    def clean_neighborhood_unit(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip()
        cleaned = re.sub(r"^(?:R/?T/?R/?W|RT|RW)\s*[:\.]?\s*", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s*/\s*", "/", cleaned)
        if not re.search(r"\d", cleaned):
            return None
        return cleaned or None

    @field_validator("blood_type", mode="before")
    @classmethod
    def clean_blood_type(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip().upper()
        cleaned = re.sub(r"^(?:GOL(?:ONGAN)?\.?\s*DARAH\s*[:\.]?\s*)", "", cleaned, flags=re.IGNORECASE).strip()
        if cleaned in ["A", "B", "AB", "O", "-"]:
            return cleaned
        return cleaned or None

    @field_validator("valid_until", mode="before")
    @classmethod
    def clean_valid_until(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^BERLAKU\s*HINGGA\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        if "SEUMUR" in cleaned.upper():
            return "SEUMUR HIDUP"
        iso_date = normalize_to_iso_date(cleaned)
        return iso_date or (cleaned or None)

