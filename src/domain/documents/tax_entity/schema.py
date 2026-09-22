import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from src.utility.date_utils import normalize_to_iso_date


class BusinessField(BaseModel):
    """A single business classification (Klasifikasi Lapangan Usaha / KLU) entry."""

    code: Optional[str] = Field(
        default=None,
        description="Business classification code (Kode KLU)",
        examples=["71100"]
    )
    title: Optional[str] = Field(
        default=None,
        description="Business classification title (Judul KLU)",
        examples=["JASA ARSITEKTUR DAN TEKNIK SIPIL SERTA KONSULTASI TEKNIS YBDI"]
    )


class TaxEntitySchema(BaseModel):
    """Schema for Indonesian Taxable Entrepreneur Confirmation Letter
    (SPPKP - Surat Pengukuhan Pengusaha Kena Pajak / PKP)."""

    letter_number: Optional[str] = Field(
        default=None,
        description="SPPKP letter reference number, e.g. 'S-47PKP/WPJ.05/KP.1003/2015'",
        examples=["S-47PKP/WPJ.05/KP.1003/2015"]
    )
    tax_office_region: Optional[str] = Field(
        default=None,
        description="Regional tax office (Kantor Wilayah DJP)",
        examples=["KANTOR WILAYAH DJP JAKARTA BARAT"]
    )
    tax_office: Optional[str] = Field(
        default=None,
        description="Issuing local tax office (KPP Pratama)",
        examples=["KPP PRATAMA JAKARTA KEBON JERUK DUA"]
    )
    tax_office_address: Optional[str] = Field(
        default=None,
        description="Issuing tax office address",
        examples=["JL. K.S. TUBUN 10, JAKARTA BARAT"]
    )
    tax_number: Optional[str] = Field(
        default=None,
        description="Nomor Pokok Wajib Pajak / NPWP (15 or 16 digits format)",
        examples=["01.329.904.5-039.000"]
    )
    name: Optional[str] = Field(
        default=None,
        description="Taxpayer / business actor name (Nama)",
        examples=["PT. RAMCOMAS MANDIRI"]
    )
    fields: Optional[List[BusinessField]] = Field(
        default=None,
        description="Business classification (Klasifikasi Lapangan Usaha / KLU) entries"
    )
    address: Optional[str] = Field(
        default=None,
        description="Registered business address (Alamat)",
        examples=["JL.KEDOYA ANGSANA BLOK B II NO.25, KEDOYA SELATAN KEBON JERUK, JAKARTA BARAT DKI JAKARTA"]
    )
    trade_name: Optional[str] = Field(
        default=None,
        description="Trade / business brand name (Merk Dagang/Usaha), null if printed as a placeholder dash",
        examples=["-"]
    )
    tax_obligation: Optional[str] = Field(
        default=None,
        description="Checked tax obligation(s) (Kewajiban Pajak), joined with '; ' if more than one is checked",
        examples=["PPN", "PPN; PPnBM"]
    )
    confirmed_since: Optional[str] = Field(
        default=None,
        description="Date confirmed as a Taxable Entrepreneur (terhitung sejak), normalized to ISO 8601 (YYYY-MM-DD)",
        examples=["1992-03-21"]
    )
    issued_place: Optional[str] = Field(
        default=None,
        description="Place of issuance",
        examples=["Jakarta Barat"]
    )
    issued_date: Optional[str] = Field(
        default=None,
        description="Issuance date, normalized to ISO 8601 (YYYY-MM-DD)",
        examples=["2015-04-17"]
    )
    signing_official_title: Optional[str] = Field(
        default=None,
        description="Title of the signing official, verbatim as printed",
        examples=["a.n. Kepala Kantor Kepala Seksi Pelayanan"]
    )
    signing_official_name: Optional[str] = Field(
        default=None,
        description="Name of the signing official",
        examples=["MUNAWAM"]
    )
    signing_official_number: Optional[str] = Field(
        default=None,
        description="Civil servant registration number of the signing official (NIP)",
        examples=["196005151981031001"]
    )

    @field_validator("letter_number", mode="before")
    @classmethod
    def clean_letter_number(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        return v.strip() or None

    @field_validator("tax_office_region", mode="before")
    @classmethod
    def clean_tax_office_region(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:KANTOR\s*WILAYAH(?:\s*DJP)?)\s*[:\.]?\s*", "KANTOR WILAYAH DJP ", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("tax_office", mode="before")
    @classmethod
    def clean_tax_office(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:KANTOR\s*PELAYANAN\s*PAJAK|KPP)\s*[:\.]?\s*", "KPP ", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("tax_office_address", mode="before")
    @classmethod
    def clean_tax_office_address(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:ALAMAT)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("tax_number", mode="before")
    @classmethod
    def clean_tax_number(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:NOMOR\s*POKOK\s*WAJIB\s*PAJAK|NPWP)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        cleaned_digits = re.sub(r"[^\dOo]", "", cleaned).replace("O", "0").replace("o", "0")
        if len(cleaned_digits) in (15, 16):
            return cleaned
        return v.strip()

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:NAMA)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("address", mode="before")
    @classmethod
    def clean_address(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:ALAMAT)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("trade_name", mode="before")
    @classmethod
    def clean_trade_name(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:MERK\s*DAGANG(?:/USAHA)?)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        if cleaned in ("", "-"):
            return None
        return cleaned

    @field_validator("confirmed_since", "issued_date", mode="before")
    @classmethod
    def clean_date_fields(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip()
        iso_date = normalize_to_iso_date(cleaned)
        return iso_date or (cleaned or None)

    @field_validator("issued_place", mode="before")
    @classmethod
    def clean_issued_place(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        return v.strip() or None

    @field_validator("signing_official_number", mode="before")
    @classmethod
    def clean_signing_official_number(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^NIP\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        digits = re.sub(r"\D", "", cleaned)
        return digits or (cleaned or None)
