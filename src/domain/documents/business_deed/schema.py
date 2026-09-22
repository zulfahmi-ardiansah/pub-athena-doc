import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from src.utility.date_utils import normalize_to_iso_date


class SKKemenkumham(BaseModel):
    """The Kemenkumham (Ministry of Law and Human Rights) decree confirming a
    business deed - Surat Keputusan Menteri Hukum dan Hak Asasi Manusia."""

    number: Optional[str] = Field(
        default=None,
        description="SK decree number (Nomor SK), e.g. 'AHU-0028078.AH.01.02.TAHUN 2022' or an older "
        "'C2-10671.HT.01.01.TH.88' style number",
        examples=["AHU-0028078.AH.01.02.TAHUN 2022"]
    )
    issued_date: Optional[str] = Field(
        default=None,
        description="SK decree date (Tanggal Pembuatan), normalized to ISO 8601 (YYYY-MM-DD)",
        examples=["2022-04-19"]
    )

    @field_validator("number", mode="before")
    @classmethod
    def clean_number(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:NOMOR|NO\.?)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("issued_date", mode="before")
    @classmethod
    def clean_issued_date(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip()
        iso_date = normalize_to_iso_date(cleaned)
        return iso_date or (cleaned or None)


class BusinessDeedSchema(BaseModel):
    """Schema for an Indonesian business deed record: the notarial deed (Akta)
    that establishes or amends a company, plus the Kemenkumham decree (SK) that
    confirms it. Fields mirror the two-panel data entry form this module is
    modeled on ('Akta Badan Usaha' and 'SK Kemenkumham'); the SK's file
    attachment field is out of scope, since it's an upload, not extractable data.
    """

    deed_type: Optional[str] = Field(
        default=None,
        description="Deed type (Tipe Akta), e.g. 'Akta Pendirian Perseroan Terbatas', "
        "'Pernyataan Keputusan Pemegang Saham - Perubahan Anggaran Dasar'",
        examples=["Akta Pendirian Perseroan Terbatas"]
    )
    deed_number: Optional[str] = Field(
        default=None,
        description="Deed number (No. Akta)",
        examples=["151"]
    )
    deed_date: Optional[str] = Field(
        default=None,
        description="Deed signing date (Tanggal Pembuatan), normalized to ISO 8601 (YYYY-MM-DD)",
        examples=["2022-04-19"]
    )
    notary_name: Optional[str] = Field(
        default=None,
        description="Notary's name (Nama Notaris), including academic title suffixes as printed",
        examples=["JOSE DIMA SATRIA, S.H., M.Kn"]
    )
    notary_address: Optional[str] = Field(
        default=None,
        description="Notary's office address or domicile (Alamat Notaris)",
        examples=["Jalan Raya Sindanglaya nomor 180, Pacet, Cianjur, Jawa Barat"]
    )
    legal_decision: Optional[SKKemenkumham] = Field(
        default=None,
        description="The Kemenkumham decree (SK) confirming this deed"
    )

    @field_validator("deed_type", mode="before")
    @classmethod
    def clean_deed_type(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:TIPE\s*AKTA)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"^=+\s*|\s*=+$", "", cleaned).strip()
        return cleaned or None

    @field_validator("deed_number", mode="before")
    @classmethod
    def clean_deed_number(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:NO\.?\s*AKTA|NOMOR|NO\.?)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("deed_date", mode="before")
    @classmethod
    def clean_deed_date(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip()
        iso_date = normalize_to_iso_date(cleaned)
        return iso_date or (cleaned or None)

    @field_validator("notary_name", mode="before")
    @classmethod
    def clean_notary_name(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:NAMA\s*NOTARIS|NOTARIS)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("notary_address", mode="before")
    @classmethod
    def clean_notary_address(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:ALAMAT\s*NOTARIS|ALAMAT|KANTOR)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None
