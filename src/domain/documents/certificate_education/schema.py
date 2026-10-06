import re
from math import isfinite
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
    month_first = re.search(r"\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})\b", cleaned)
    if month_first:
        cleaned = f"{month_first.group(2)} {month_first.group(1)} {month_first.group(3)}"
    return normalize_to_iso_date(cleaned)


def _number(value: object, label: str) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if isfinite(number) else None
    if isinstance(value, str):
        cleaned = _clean(value, label)
        match = re.fullmatch(r"(\d+(?:[.,]\d+)?)(?:\s*\([^)]*\))?", cleaned or "")
        if match:
            number = float(match.group(1).replace(",", "."))
            return number if isfinite(number) else None
    return None


class AcademicCourse(BaseModel):
    code: Optional[str] = Field(default=None, description="Printed course or subject code", examples=["19A51C101"])
    name: Optional[str] = Field(default=None, description="Printed course or subject name", examples=["Kalkulus"])
    credits: Optional[float] = Field(default=None, description="Numeric course credit value (SKS/credit)", examples=[2])
    grade: Optional[float] = Field(default=None, description="Numeric course grade printed directly or obtained from the document's grading legend", examples=[3.5])
    semester: Optional[str] = Field(default=None, description="Semester or term heading for this course, when printed", examples=["IV"])

    @field_validator("credits", mode="before")
    @classmethod
    def clean_credits(cls, v: object) -> Optional[float]:
        return _number(v, r"^(?:SKS|CREDITS?)\s*[:：.]?\s*")

    @field_validator("grade", mode="before")
    @classmethod
    def clean_grade(cls, v: object) -> Optional[float]:
        return _number(v, r"^(?:NILAI|GRADE|ANGKA|BOBOT)\s*[:：.]?\s*")


class CertificateEducationSchema(BaseModel):
    number: Optional[str] = Field(default=None, description="Printed transcript or serial number, distinct from NIM/NPM", examples=["872022023001083"])
    student_name: Optional[str] = Field(default=None, description="Graduate's name (Nama Karyawan in the target education form; Nama Mahasiswa/Nama on the source)", examples=["Rudi Hartono"])
    student_number: Optional[str] = Field(default=None, description="Student registration number (NIM/NPM/Nomor Induk Mahasiswa), preserving leading zeros", examples=["060100094"])
    student_major: Optional[str] = Field(default=None, description="Jurusan/Fakultas for the target form; prefer the printed study program or major, then faculty", examples=["Teknik Mesin"])
    education_institution: Optional[str] = Field(default=None, description="Name of the issuing educational institution (Lembaga Pendidikan)", examples=["Politeknik Negeri Bandung"])
    education_address: Optional[str] = Field(default=None, description="Printed institution or campus address, not the student's address or birth place", examples=["Jalan Grafika 2, Kampus UGM, Yogyakarta 55281, Indonesia"])
    birth_place: Optional[str] = Field(default=None, description="Graduate's place of birth, separate from birth date", examples=["Bandung"])
    birth_date: Optional[str] = Field(default=None, description="Graduate's date of birth in YYYY-MM-DD", examples=["1995-12-03"])
    enroll_level: Optional[str] = Field(default=None, description="Education level or program, such as D3, D4, S1, S2, or Profesi, only when supported by the document", examples=["D3"])
    enroll_date: Optional[str] = Field(default=None, description="Enrollment or starting date in YYYY-MM-DD", examples=["2010-02-01"])
    enroll_credit: Optional[str] = Field(default=None, description="Total completed SKS or credits, not a single course's credits", examples=["146"])
    enroll_grade: Optional[float] = Field(default=None, description="Numeric overall IPK/GPA, separate from a course grade or grading legend", examples=[3.18])
    issued_place: Optional[str] = Field(default=None, description="Place in the transcript's issue/signature line", examples=["Medan"])
    issued_date: Optional[str] = Field(default=None, description="Date in the transcript's issue/signature line in YYYY-MM-DD", examples=["2012-02-25"])
    courses: Optional[List[AcademicCourse]] = Field(default=None, description="Repeated course/subject rows from the transcript, when readable")

    @field_validator("student_name", mode="before")
    @classmethod
    def clean_student_name(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:NAMA(?:\s+(?:MAHASISWA|LENGKAP|KARYAWAN))?|STUDENT\s+NAME|NAME)\s*(?:\(NAME\))?\s*[:：.]?\s*")

    @field_validator("enroll_level", mode="before")
    @classmethod
    def clean_enroll_level(cls, v: Optional[str]) -> Optional[str]:
        cleaned = _clean(v, r"^(?:JENJANG\s+(?:PENDIDIKAN|PROGRAM)|PROGRAM\s+PENDIDIKAN|EDUCATION\s+LEVEL)\s*[:：.]?\s*")
        if not cleaned:
            return None
        upper = cleaned.upper()
        if re.search(r"\bPROFESI\s+DOKTER\b", upper):
            return "Profesi Dokter"
        for pattern, level in ((r"\b(?:DIPLOMA\s*(?:III|3)|D\s*3)\b", "D3"), (r"\b(?:DIPLOMA\s*(?:IV|4)|D\s*4)\b", "D4"), (r"\b(?:MAGISTER|MASTER|S\s*2)\b", "S2"), (r"\b(?:DOKTOR|DOCTORAL|S\s*3)\b", "S3"), (r"\b(?:SARJANA|BACHELOR|S\s*1)\b", "S1")):
            if re.search(pattern, upper):
                return level
        return cleaned

    @field_validator("education_institution", mode="before")
    @classmethod
    def clean_institution(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:LEMBAGA\s+PENDIDIKAN|EDUCATION\s+INSTITUTION|INSTITUTION)\s*[:：.]?\s*")

    @field_validator("student_major", mode="before")
    @classmethod
    def clean_student_major(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:JURUSAN\s*/\s*FAKULTAS|JURUSAN\s*/\s*PROGRAM\s+STUDI|JURUSAN|PROGRAM\s+STUDI|MAJOR\s*/\s*FACULTY)\s*[:：.]?\s*")

    @field_validator("student_number", mode="before")
    @classmethod
    def clean_student_number(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:NIM|NPM|NOMOR\s+INDUK\s+MAHASISWA|STUDENT\s+REGISTRATION\s+NUMBER)\s*[:：.]?\s*")

    @field_validator("number", mode="before")
    @classmethod
    def clean_number(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:NO\.?\s*SERI|NOMOR\s+SERI|NO\.?\s*TRANSKRIP|TRANSCRIPT\s+NUMBER)\s*[:：.]?\s*")

    @field_validator("birth_place", mode="before")
    @classmethod
    def clean_birth_place(cls, v: Optional[str]) -> Optional[str]:
        cleaned = _clean(v, r"^(?:TEMPAT\s*/\s*(?:TGL\.?|TANGGAL)\s*LAHIR|TEMPAT\s+LAHIR|PLACE\s*/\s*DATE\s+OF\s+BIRTH|PLACE\s+OF\s+BIRTH)\s*[:：.]?\s*")
        return re.split(r"\s*[,/]\s*(?=\d{1,2}\b|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d)", cleaned, maxsplit=1, flags=re.IGNORECASE)[0].strip() if cleaned else None

    @field_validator("birth_date", mode="before")
    @classmethod
    def clean_birth_date(cls, v: Optional[str]) -> Optional[str]:
        return _date(v, r"^(?:TEMPAT\s*/\s*(?:TGL\.?|TANGGAL)\s*LAHIR|TANGGAL\s+LAHIR|DATE\s+OF\s+BIRTH)\s*[:：.]?\s*")

    @field_validator("enroll_date", mode="before")
    @classmethod
    def clean_enroll_date(cls, v: Optional[str]) -> Optional[str]:
        return _date(v, r"^(?:MULAI\s+PENDIDIKAN|TANGGAL\s+MASUK|DATE\s+OF\s+ENROLLMENT|STARTING\s+DATE)\s*[:：.]?\s*")

    @field_validator("enroll_grade", mode="before")
    @classmethod
    def clean_enroll_grade(cls, v: object) -> Optional[float]:
        return _number(v, r"^(?:INDEKS?\s+PRESTASI(?:\s+KUMULATIF)?(?:\s*\(IPK\))?|IPK|GPA|GRADE\s+POINT\s+AVERAGE)\s*[:：.=]?\s*")

    @field_validator("enroll_credit", mode="before")
    @classmethod
    def clean_enroll_credit(cls, v: Optional[str]) -> Optional[str]:
        cleaned = _clean(v, r"^(?:JUMLAH\s+SKS(?:\s+KUMULATIF)?|TOTAL\s+(?:OF\s+)?CREDITS?)\s*[:：.]?\s*")
        match = re.search(r"\b\d{1,3}\b", cleaned or "")
        return match.group(0) if match else None

    @field_validator("issued_place", mode="before")
    @classmethod
    def clean_issued_place(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:TEMPAT\s+TERBIT|ISSUED\s+PLACE)\s*[:：.]?\s*")

    @field_validator("issued_date", mode="before")
    @classmethod
    def clean_issued_date(cls, v: Optional[str]) -> Optional[str]:
        return _date(v, r"^(?:TANGGAL\s+TERBIT|ISSUED\s+DATE)\s*[:：.]?\s*")


    @field_validator("education_address", mode="before")
    @classmethod
    def clean_education_address(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v, r"^(?:ALAMAT(?:\s+(?:FAKULTAS|INSTITUSI|PENDIDIKAN))?|FACULTY\s+ADDRESS|CAMPUS\s+ADDRESS|INSTITUTION\s+ADDRESS)\s*[:?.]?\s*")
