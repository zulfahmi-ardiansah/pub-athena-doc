import re
import math
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
from src.utility.date_utils import normalize_to_iso_date


class CertificateLocalValueSchema(BaseModel):
    product_name: Optional[str] = Field(default=None, description="Jenis Produk", examples=["Basket Ecenggondok"])
    product_type: Optional[str] = Field(default=None, description="Tipe", examples=["Ecenggondok"])
    product_specification: Optional[str] = Field(default=None, description="Spesifikasi, including wrapped lines", examples=["38 x 27 x 19 cm"])
    product_hs: Optional[str] = Field(default=None, description="Kode HS", examples=["44209010"])
    product_brand: Optional[str] = Field(default=None, description="Merk", examples=["CONTOH"])
    product_local_value: Optional[float] = Field(default=None, description="Numeric TKDN percentage without the percent sign; null when only Terlampir is printed", examples=[96.72])
    product_standard: Optional[str] = Field(default=None, description="Standard Produk", examples=["SNI 1234:2020"])
    product_certificate: Optional[str] = Field(default=None, description="Sertifikat Produk", examples=["SP-1234"])
    report_number: Optional[str] = Field(default=None, description="No. Laporan verification report number", examples=["LPA-3426/PK-3506/PTKDN.DIPA-INFRAS/VII/21"])
    certificate_valid_year: Optional[int] = Field(default=None, description="Printed validity period in years as a JSON integer; no expiry date is inferred", examples=[3])
    business_name: Optional[str] = Field(default=None, description="Nama Perusahaan, the certificate holder", examples=["CV. Contoh Indonesia"])
    business_address: Optional[str] = Field(default=None, description="Alamat of the certificate holder, including wrapped lines", examples=["Jl. Contoh No. 7, Bantul, Yogyakarta"])
    business_tax_number: Optional[str] = Field(default=None, description="Company NPWP", examples=["82.934.355.7-543.000"])
    business_field: Optional[str] = Field(default=None, description="Bidang Usaha or Jenis Industri, including the printed KBLI code", examples=["Industri Barang Bangunan Dari Kayu (KBLI: 16221)"])
    certificate_number: Optional[str] = Field(default=None, description="No. Tanda Sah certificate number, distinct from No. Laporan", examples=["4623/SJ-IND.8/TKDN/7/2021"])
    certificate_issued_place: Optional[str] = Field(default=None, description="Place in the issue line", examples=["Jakarta"])
    certificate_issued_date: Optional[str] = Field(default=None, description="Date in the issue line, normalized to YYYY-MM-DD", examples=["2021-07-28"])
    signing_official_title: Optional[str] = Field(default=None, description="Title of the signing official", examples=["Kepala Pusat Peningkatan Penggunaan Produk Dalam Negeri"])
    signing_official_name: Optional[str] = Field(default=None, description="Name of the signing official", examples=["Nila Kumalasari"])
    certificate_qr_number: Optional[str] = Field(default=None, description="Printed number below the QR code, when present", examples=["23361"])

    @staticmethod
    def _clean(value: Optional[str], label: str) -> Optional[str]:
        if not isinstance(value, str):
            return None
        cleaned = re.sub(label, "", value.strip(), flags=re.IGNORECASE).strip()
        return cleaned if cleaned and cleaned not in ("-", "–", "—") else None

    @field_validator("product_name", mode="before")
    @classmethod
    def clean_product_name(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^JENIS\s*PRODUK\s*[:.]?\s*")

    @field_validator("product_type", mode="before")
    @classmethod
    def clean_product_type(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^TIPE\s*[:.]?\s*")

    @field_validator("product_specification", mode="before")
    @classmethod
    def clean_product_specification(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^SPESIFIKASI\s*[:.]?\s*")

    @field_validator("product_hs", mode="before")
    @classmethod
    def clean_product_hs(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^KODE\s*HS\s*[:.]?\s*")

    @field_validator("product_brand", mode="before")
    @classmethod
    def clean_product_brand(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^MERK\s*[:.]?\s*")

    @field_validator("product_local_value", mode="before")
    @classmethod
    def clean_product_local_value(cls, v: Any) -> Optional[float]:
        if isinstance(v, bool):
            return None
        if isinstance(v, (int, float, Decimal)):
            number = float(v)
            return number if math.isfinite(number) else None
        cleaned = cls._clean(v, r"^NILAI\s*TKDN\s*[:.]?\s*")
        if not cleaned:
            return None
        if re.fullmatch(r"\d+(?:[.,]\d+)?\s*%?", cleaned):
            return float(cleaned.replace(",", ".").rstrip("%").strip())
        return None

    @field_validator("product_standard", mode="before")
    @classmethod
    def clean_product_standard(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^STANDAR(?:D)?\s*PRODUK\s*[:.]?\s*")

    @field_validator("product_certificate", mode="before")
    @classmethod
    def clean_product_certificate(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^SERTIFIKAT\s*PRODUK\s*[:.]?\s*")

    @field_validator("report_number", mode="before")
    @classmethod
    def clean_report_number(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^NO\.?\s*LAPORAN\s*[:.]?\s*")

    @field_validator("certificate_valid_year", mode="before")
    @classmethod
    def clean_certificate_valid_year(cls, v: Any) -> Optional[int]:
        if isinstance(v, bool):
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, (float, Decimal)):
            return int(v) if math.isfinite(float(v)) and v == int(v) else None
        cleaned = cls._clean(v, r"^VALIDITY\s*YEARS\s*[:.]?\s*")
        if not cleaned:
            return None
        if cleaned.isdigit():
            return int(cleaned)
        match = re.search(r"\b(\d+)\s*tahun\b", cleaned, re.IGNORECASE)
        return int(match.group(1)) if match else None

    @field_validator("business_name", mode="before")
    @classmethod
    def clean_business_name(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^NAMA\s*PERUSAHAAN\s*[:.]?\s*")

    @field_validator("business_address", mode="before")
    @classmethod
    def clean_business_address(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^ALAMAT\s*[:.]?\s*")

    @field_validator("business_tax_number", mode="before")
    @classmethod
    def clean_business_tax_number(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^NPWP\s*[:.]?\s*")

    @field_validator("business_field", mode="before")
    @classmethod
    def clean_business_field(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^(?:BIDANG\s*USAHA|JENIS\s*INDUSTRI)\s*[:.]?\s*")

    @field_validator("certificate_number", mode="before")
    @classmethod
    def clean_certificate_number(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^NO\.?\s*TANDA\s*SAH\s*[:.]?\s*")

    @field_validator("certificate_issued_place", mode="before")
    @classmethod
    def clean_certificate_issued_place(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^ISSUED\s*PLACE\s*[:.]?\s*")

    @field_validator("certificate_issued_date", mode="before")
    @classmethod
    def clean_certificate_issued_date(cls, v: Optional[str]) -> Optional[str]:
        cleaned = cls._clean(v, r"^ISSUED\s*DATE\s*[:.]?\s*")
        return normalize_to_iso_date(cleaned) if cleaned else None

    @field_validator("signing_official_title", mode="before")
    @classmethod
    def clean_signing_official_title(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^SIGNING\s*OFFICIAL\s*TITLE\s*[:.]?\s*")

    @field_validator("signing_official_name", mode="before")
    @classmethod
    def clean_signing_official_name(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^SIGNING\s*OFFICIAL\s*NAME\s*[:.]?\s*")

    @field_validator("certificate_qr_number", mode="before")
    @classmethod
    def clean_certificate_qr_number(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^#\s*")
