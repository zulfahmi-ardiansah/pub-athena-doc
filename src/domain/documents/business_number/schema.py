import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from src.utility.date_utils import normalize_to_iso_date


class LicenseItem(BaseModel):
    """A single Jenis/Status/Keterangan license entry under a KBLI row's 'Perizinan Berusaha' block.

    A KBLI row can require more than one license (e.g. both an NIB and a Sertifikat Standar),
    each with its own status and remarks - these are printed as separate stacked sub-rows,
    not a single shared status/remarks for the whole KBLI row.
    """

    license_type: Optional[str] = Field(
        default=None,
        description="License type (Jenis), e.g. 'NIB', 'Sertifikat Standar', 'Izin'",
        examples=["NIB"]
    )
    license_status: Optional[str] = Field(
        default=None,
        description="License status (Status), e.g. 'Terbit', 'Belum Terbit', 'Belum Terverifikasi'",
        examples=["Terbit"]
    )
    remarks: Optional[str] = Field(
        default=None,
        description="Remarks/instructions for this specific license (Keterangan), verbatim as printed",
        examples=["Lakukan pemenuhan standar/persyaratan melalui oss.go.id paling lambat 90 hari kerja"]
    )

    @field_validator("license_type", "license_status", mode="before")
    @classmethod
    def clean_license_value(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^[-•]\s*", "", v.strip()).strip()
        return cleaned or None

    @field_validator("remarks", mode="before")
    @classmethod
    def clean_remarks(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip()
        if cleaned in ("", "-"):
            return None
        return cleaned


class FieldItem(BaseModel):
    """A single business classification line-item from the NIB's KBLI attachment table."""

    no: Optional[str] = Field(
        default=None,
        description="Row number in the KBLI attachment table",
        examples=["1"]
    )
    code: Optional[str] = Field(
        default=None,
        description="5-digit KBLI (Klasifikasi Baku Lapangan Usaha Indonesia) code",
        examples=["46321"]
    )
    title: Optional[str] = Field(
        default=None,
        description="Business classification title/description (Judul KBLI)",
        examples=["Perdagangan Besar Daging Sapi Dan Daging Sapi Olahan"]
    )
    business_location: Optional[str] = Field(
        default=None,
        description="Business location address for this KBLI row (Lokasi Usaha)",
        examples=["GD. PUSAT PERUM BULOG LT. 10 JL. JEND. GATOT SUBROTO KAV.49"]
    )
    postal_code: Optional[str] = Field(
        default=None,
        description="Postal code for this KBLI row's business location (Kode Pos)",
        examples=["12950"]
    )
    risk_level: Optional[str] = Field(
        default=None,
        description="Risk level (Tingkat Risiko), e.g. 'Rendah', 'Menengah Rendah', 'Menengah Tinggi', 'Tinggi'",
        examples=["Rendah"]
    )
    licenses: Optional[List[LicenseItem]] = Field(
        default=None,
        description="One entry per Jenis/Status/Keterangan sub-row under this KBLI row's Perizinan Berusaha block"
    )


class BusinessNumberSchema(BaseModel):
    """Schema for Indonesian Business Identification Number (NIB - Nomor Induk Berusaha)."""

    number: Optional[str] = Field(
        default=None,
        description="Nomor Induk Berusaha / NIB (13-digit business identification number)",
        examples=["2210210046937"]
    )
    name: Optional[str] = Field(
        default=None,
        description="Business actor name (Nama Pelaku Usaha)",
        examples=["PT Mitra BUMDes Nusantara"]
    )
    address: Optional[str] = Field(
        default=None,
        description="Office address (Alamat Kantor)",
        examples=["LIPPO KUNINGAN TOWER LANTAI 11, JL. H.R. RASUNA SAID KAV. B-12"]
    )
    postal_code: Optional[str] = Field(
        default=None,
        description="Office postal code (Kode Pos)",
        examples=["12940"]
    )
    phone_number: Optional[str] = Field(
        default=None,
        description="Office phone number (No. Telepon)",
        examples=["02121393278"]
    )
    email: Optional[str] = Field(
        default=None,
        description="Office email address (Email)",
        examples=["mbn@mitrabumdes.co.id"]
    )
    investment_status: Optional[str] = Field(
        default=None,
        description="Investment status (Status Penanaman Modal), e.g. 'PMDN' or 'PMA'",
        examples=["PMDN"]
    )
    issued_place: Optional[str] = Field(
        default=None,
        description="Place of issuance (Diterbitkan di)",
        examples=["Jakarta"]
    )
    issued_date: Optional[str] = Field(
        default=None,
        description="Issuance date (Tanggal), normalized to ISO 8601 (YYYY-MM-DD)",
        examples=["2021-10-22"]
    )
    amendment_number: Optional[str] = Field(
        default=None,
        description="Amendment number if the NIB has been amended (Perubahan ke-)",
        examples=["1"]
    )
    amendment_date: Optional[str] = Field(
        default=None,
        description="Amendment date (Tanggal Perubahan), normalized to ISO 8601 (YYYY-MM-DD)",
        examples=["2025-03-19"]
    )
    printed_date: Optional[str] = Field(
        default=None,
        description="Print date (Dicetak tanggal), normalized to ISO 8601 (YYYY-MM-DD)",
        examples=["2025-03-19"]
    )
    signing_official_title: Optional[str] = Field(
        default=None,
        description="Title of the signing official (e.g. 'Menteri Investasi dan Hilirisasi/ Kepala Badan Koordinasi Penanaman Modal')",
        examples=["Menteri Investasi dan Hilirisasi/ Kepala Badan Koordinasi Penanaman Modal"]
    )
    fields: Optional[List[FieldItem]] = Field(
        default=None,
        description="Business classification (KBLI) line items from the attachment table"
    )

    @field_validator("number", mode="before")
    @classmethod
    def clean_number(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:NOMOR\s*INDUK\s*BERUSAHA|NIB)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        digit_match = re.search(r"\b(\d{13})\b", cleaned)
        if digit_match:
            return digit_match.group(1)
        return cleaned or None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:NAMA\s*PELAKU\s*USAHA)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("address", mode="before")
    @classmethod
    def clean_address(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:ALAMAT\s*KANTOR)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("postal_code", mode="before")
    @classmethod
    def clean_postal_code(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:KODE\s*POS)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("phone_number", mode="before")
    @classmethod
    def clean_phone_number(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:NO\.?\s*TELEPON|TELEPON)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:EMAIL)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("investment_status", mode="before")
    @classmethod
    def clean_investment_status(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:STATUS\s*PENANAMAN\s*MODAL)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("issued_place", mode="before")
    @classmethod
    def clean_issued_place(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:DITERBITKAN\s*DI)\s*[:\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None

    @field_validator("issued_date", "amendment_date", "printed_date", mode="before")
    @classmethod
    def clean_date_fields(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(
            r"^(?:TANGGAL|DICETAK\s*TANGGAL)\s*[:\.]?\s*",
            "",
            v.strip(),
            flags=re.IGNORECASE
        ).strip()
        iso_date = normalize_to_iso_date(cleaned)
        return iso_date or (cleaned or None)

    @field_validator("amendment_number", mode="before")
    @classmethod
    def clean_amendment_number(cls, v: Optional[str]) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = re.sub(r"^(?:PERUBAHAN\s*KE)\s*[:\-\.]?\s*", "", v.strip(), flags=re.IGNORECASE).strip()
        return cleaned or None
