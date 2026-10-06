import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from src.utility.date_utils import normalize_to_iso_date


def _clean(value: Optional[str], label: str = "") -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(label, "", value.strip(), flags=re.IGNORECASE).strip() if label else value.strip()
    return cleaned if cleaned and cleaned not in ("-", "–", "—") else None


def _date(value: Optional[str], label: str) -> Optional[str]:
    cleaned = _clean(value, label)
    if not cleaned:
        return None
    cleaned = re.sub(r"\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})\b", r"\2 \1 \3", cleaned)
    return normalize_to_iso_date(cleaned)


class CompetencyUnit(BaseModel):
    code: Optional[str] = Field(default=None, description="Printed competency unit code", examples=["PDB.EI.01.001.01"])
    name: Optional[str] = Field(default=None, description="Printed competency unit name, if present", examples=["Mengelola Dokumen Ekspor"])


class CertificateCompetencySchema(BaseModel):
    number: Optional[str] = Field(default=None, description="Certificate number, separate from holder registration number", examples=["990 12.2 000001 2018"])
    name: Optional[str] = Field(default=None, description="Recipient or certificate holder's name", examples=["Budi Santoso"])
    title: Optional[str] = Field(default=None, description="Course, training, certification scheme, or qualification name", examples=["Belajar Dasar Pemrograman JavaScript"])
    field: Optional[str] = Field(default=None, description="Printed occupational area, separate from the qualification", examples=["Koperasi Jasa Keuangan"])
    institution: Optional[str] = Field(default=None, description="Course provider or issuing certification body (LSP); overseeing authority when no issuer is printed", examples=["Lembaga Sertifikasi Profesi LP3I"])
    training_start_date: Optional[str] = Field(default=None, description="Course or training start date in YYYY-MM-DD", examples=["2022-07-01"])
    training_end_date: Optional[str] = Field(default=None, description="Course or training end date in YYYY-MM-DD", examples=["2022-10-31"])
    grade: Optional[str] = Field(default=None, description="Printed course result or grade, preserving letter or numeric grading", examples=["A-"])
    issued_place: Optional[str] = Field(default=None, description="Place in the certificate issue/signature line", examples=["Jakarta"])
    issued_date: Optional[str] = Field(default=None, description="Certificate issue date in YYYY-MM-DD", examples=["2018-11-24"])
    expiry_date: Optional[str] = Field(default=None, description="Explicitly printed expiry date in YYYY-MM-DD", examples=["2021-11-24"])
    signing_official_name: Optional[str] = Field(default=None, description="Printed certificate signatory's name", examples=["Budi Pratama"])
    signing_official_title: Optional[str] = Field(default=None, description="Printed certificate signatory's role", examples=["Direktur"])
    units: Optional[List[CompetencyUnit]] = Field(default=None, description="Repeated competency unit codes and names, when printed")

    @field_validator("number", mode="before")
    @classmethod
    def clean_number(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:NOMOR(?:\s+SERTIFIKAT)?|CERTIFICATE\s+NUMBER|NO\b\.?)\s*[:.]?\s*")

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:NAMA(?:\s+(?:PESERTA|PEMEGANG))?|NAME|RECIPIENT)\s*[:.]?\s*")

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:NAMA\s+(?:PELATIHAN|KURSUS)|SKEMA\s+SERTIFIKASI|KUALIFIKASI|COURSE(?:\s+TITLE)?|QUALIFICATION)\s*[:.]?\s*")

    @field_validator("field", mode="before")
    @classmethod
    def clean_field(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:BIDANG(?:\s+PEKERJAAN)?|COMPETENCY\s+FIELD)\s*[:.]?\s*")

    @field_validator("institution", mode="before")
    @classmethod
    def clean_institution(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:PENYELENGGARA|INSTITUTION|ISSUER|AUTHORITY)\s*[:.]?\s*")

    @field_validator("training_start_date", mode="before")
    @classmethod
    def clean_training_start_date(cls, v: Optional[str]) -> Optional[str]:
        return _date(v, r"^(?:TANGGAL\s+MULAI|START\s+DATE)\s*[:.]?\s*")

    @field_validator("training_end_date", mode="before")
    @classmethod
    def clean_training_end_date(cls, v: Optional[str]) -> Optional[str]:
        return _date(v, r"^(?:TANGGAL\s+SELESAI|END\s+DATE|COMPLETION\s+DATE)\s*[:.]?\s*")

    @field_validator("grade", mode="before")
    @classmethod
    def clean_grade(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:NILAI|GRADE|HASIL)\s*[:.]?\s*")

    @field_validator("issued_place", mode="before")
    @classmethod
    def clean_issued_place(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:TEMPAT\s+TERBIT|ISSUED\s+PLACE)\s*[:.]?\s*")

    @field_validator("issued_date", mode="before")
    @classmethod
    def clean_issued_date(cls, v: Optional[str]) -> Optional[str]:
        return _date(v, r"^(?:TANGGAL\s+TERBIT|ISSUED\s+DATE|DATE\s+OF\s+ISSUE)\s*[:.]?\s*")

    @field_validator("expiry_date", mode="before")
    @classmethod
    def clean_expiry_date(cls, v: Optional[str]) -> Optional[str]:
        return _date(v, r"^(?:BERLAKU\s+SAMPAI|EXPIRY\s+DATE|VALID\s+UNTIL)\s*[:.]?\s*")

    @field_validator("signing_official_name", mode="before")
    @classmethod
    def clean_signing_official_name(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:PENANDATANGAN|SIGNATORY)\s*[:.]?\s*")

    @field_validator("signing_official_title", mode="before")
    @classmethod
    def clean_signing_official_title(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:JABATAN|SIGNATORY\s+TITLE)\s*[:.]?\s*")
