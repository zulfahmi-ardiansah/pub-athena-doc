import re
from typing import Dict, Optional
from src.domain.documents.certificate_education.schema import CertificateEducationSchema


class CertificateEducationStringParser:
    @classmethod
    def parse(cls, raw_text: str) -> CertificateEducationSchema:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        data: Dict[str, Optional[str]] = {}

        data["student_name"] = cls._find(lines, r"(?:Nama(?:\s+(?:Mahasiswa|Lengkap|Karyawan))?|Student\s+Name|Name)")
        data["education_institution"] = cls._find(lines, r"(?:Lembaga\s+Pendidikan|Education\s+Institution|Institution)")
        if not data["education_institution"]:
            data["education_institution"] = next((line for line in lines[:16] if re.match(r"^(?:Universitas|University|State\s+University|Institut|Institute|Politeknik|Polytechnic|Sekolah\s+Tinggi|Akademi)\b", line, re.IGNORECASE)), None)

        data["education_address"] = cls._find(lines, r"(?:Alamat\s+Fakultas(?:\s*/\s*Faculty\s+Address)?|Alamat\s+Institusi|Alamat\s+Pendidikan|Faculty\s+Address|Campus\s+Address|Institution\s+Address)")
        if not data["education_address"]:
            data["education_address"] = next((line for line in lines[:16] if re.match(r"^(?:Jalan|Jl\.?)\s+", line, re.IGNORECASE)), None)
        faculty = cls._find(lines, r"(?:Fakultas|Faculty)")
        if not faculty:
            faculty = next((line for line in lines[:16] if re.match(r"^(?:Fakultas|Faculty)\s+\S", line, re.IGNORECASE)), None)

        study_program = cls._find(lines, r"(?:Jurusan\s*/\s*Program\s+Studi|Program\s+Studi|Jurusan|Study\s+Program)")
        data["student_major"] = cls._find(lines, r"(?:Jurusan\s*/\s*Fakultas|Major\s*/\s*Faculty)") or study_program or faculty
        data["enroll_level"] = cls._find(lines, r"(?:Jenjang\s+(?:Pendidikan|Program)|Program\s+Pendidikan|Education\s+Level|Program)")
        if not data["enroll_level"]:
            for line in lines[:20]:
                match = re.search(r"\b(?:Program\s+)?(?:Diploma\s*(?:III|IV|3|4)|D[34]|S[123]|Sarjana|Magister|Doktor|Profesi\s+Dokter)\b", line, re.IGNORECASE)
                if match and re.search(r"(?:Program|Jenjang|Diploma|Sarjana|Magister|Doktor|Profesi)", line, re.IGNORECASE):
                    data["enroll_level"] = match.group(0)
                    break
        if not data["enroll_level"] and study_program:
            match = re.search(r"\b(?:Diploma\s*(?:III|IV|3|4)|D[34]|S[123]|Sarjana|Magister|Profesi\s+Dokter)\b", study_program, re.IGNORECASE)
            if match:
                data["enroll_level"] = match.group(0)

        data["student_number"] = cls._find(lines, r"(?:NIM|NPM|Nomor\s+Induk\s+Mahasiswa|Student\s+Registration\s+Number|ID)")
        data["number"] = cls._find(lines, r"(?:No\.?\s*Seri|Nomor\s+Seri|No\.?\s*Transkrip|Transcript\s+Number|Number)")

        birth = cls._find(lines, r"(?:Tempat\s*/\s*(?:Tgl\.?|Tanggal)\s*Lahir|Tempat\s+dan\s+Tanggal\s+Lahir|Place\s*/\s*Date\s+of\s+Birth)")
        if birth:
            data["birth_place"] = birth
            data["birth_date"] = birth
        else:
            data["birth_place"] = cls._find(lines, r"(?:Tempat\s+Lahir|Place\s+of\s+Birth)")
            data["birth_date"] = cls._find(lines, r"(?:Tanggal\s+Lahir|Date\s+of\s+Birth)")

        data["enroll_date"] = cls._find(lines, r"(?:Mulai\s+Pendidikan|Tanggal\s+Masuk|Date\s+of\s+Enrollment|Starting\s+Date)")
        data["enroll_grade"] = cls._find(lines, r"(?:Indeks?\s+Prestasi(?:\s+Kumulatif)?(?:\s*\(IPK\))?|IPK|GPA|Grade\s+Point\s+Average)")
        data["enroll_credit"] = cls._find(lines, r"(?:Jumlah\s+SKS(?:\s+Kumulatif)?|Total\s+(?:of\s+)?Credits?)")

        for line in reversed(lines[-18:]):
            match = re.match(r"^([A-Za-z][A-Za-z .'-]{2,30}),\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})\b", line)
            if match:
                data["issued_place"] = match.group(1).strip()
                data["issued_date"] = match.group(2)
                break

        return CertificateEducationSchema.model_validate(data)

    @staticmethod
    def _find(lines: list[str], label: str) -> Optional[str]:
        same_line = re.compile(rf"^(?:{label})(?:\s*\([^)]*\))?\s*[:：]\s*(.*?)\s*$", re.IGNORECASE)
        label_only = re.compile(rf"^(?:{label})(?:\s*\([^)]*\))?\s*$", re.IGNORECASE)
        for index, line in enumerate(lines):
            match = same_line.match(line)
            if match and match.group(1).strip():
                return match.group(1).strip()
            if (match or label_only.match(line)) and index + 1 < len(lines):
                next_line = re.match(r"^[:：]\s*(.+)$", lines[index + 1])
                if next_line:
                    return next_line.group(1).strip()
        return None
