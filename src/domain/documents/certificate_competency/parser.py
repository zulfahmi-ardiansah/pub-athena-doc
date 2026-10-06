import re
from typing import Any, Dict, Optional
from src.domain.documents.certificate_competency.schema import CertificateCompetencySchema


class CertificateCompetencyStringParser:
    @classmethod
    def parse(cls, raw_text: str) -> CertificateCompetencySchema:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        data: Dict[str, Any] = {}
        labels = {
            "number": r"(?:No\.?|Nomor(?:\s+Sertifikat)?|Certificate\s+Number)",
            "name": r"(?:Nama(?:\s+(?:Peserta|Pemegang))?|Name|Recipient)",
            "title": r"(?:Nama\s+(?:Pelatihan|Kursus)|Skema\s+Sertifikasi|Kualifikasi|Course(?:\s+Title)?|Qualification)",
            "field": r"(?:Bidang(?:\s+Pekerjaan)?|Competency\s+Field)",
            "institution": r"(?:Penyelenggara|Institution|Issuer)",
            "training_start_date": r"(?:Tanggal\s+Mulai|Start\s+Date)",
            "training_end_date": r"(?:Tanggal\s+Selesai|End\s+Date|Completion\s+Date)",
            "grade": r"(?:Nilai|Grade|Hasil)",
            "issued_place": r"(?:Tempat\s+Terbit|Issued\s+Place)",
            "issued_date": r"(?:Tanggal\s+Terbit|Issued\s+Date|Date\s+of\s+Issue)",
            "expiry_date": r"(?:Berlaku\s+Sampai|Expiry\s+Date|Valid\s+Until)",
            "signing_official_name": r"(?:Penandatangan|Signatory)",
            "signing_official_title": r"(?:Jabatan|Signatory\s+Title)",
        }
        for field, label in labels.items():
            data[field] = cls._find(lines, label)

        if not data["number"]:
            match = re.search(r"^\s*No\.?(?!\s*Reg\b)\s+([A-Z0-9][A-Z0-9 ./-]*\d)\s*$", raw_text, re.IGNORECASE | re.MULTILINE)
            if match:
                data["number"] = match.group(1).strip()

        if not data["name"]:
            data["name"] = cls._after(lines, r"^Dengan\s+ini\s+menyatakan\s+bahwa\s*[,.:]?$")
        if not data["title"]:
            data["title"] = cls._after(lines, r"^(?:Dengan\s+Kualifikasi\s*/\s*Kompetensi|Telah\s+lulus\s+dari\s+kelas)\s*[:.]?$")
        if not data["field"]:
            data["field"] = cls._after(lines, r"^(?:Pada\s+bidang\s+pekerjaan|Telah\s+kompeten\s+pada\s+bidang)\s*[:.]?$")
        if not data["institution"]:
            data["institution"] = next((line for line in lines if re.match(r"^Lembaga\s+Sertifikasi\s+Profesi\b", line, re.IGNORECASE)), None)
            if not data["institution"]:
                data["institution"] = next((line for line in lines if re.fullmatch(r"Dicoding(?:\s+Indonesia)?", line, re.IGNORECASE)), None)
        if not data["institution"]:
            data["institution"] = cls._find(lines, r"Authority")
        if not data["institution"] and re.search(r"\bBadan\s+Nasional\s+Sertifikasi\s+Profesi\b", raw_text, re.IGNORECASE):
            data["institution"] = "Badan Nasional Sertifikasi Profesi"

        for line in reversed(lines[-16:]):
            match = re.match(r"^([A-Za-z][A-Za-z .'-]{2,30}),\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})\b", line)
            if match:
                data["issued_place"] = data["issued_place"] or match.group(1).strip()
                data["issued_date"] = data["issued_date"] or match.group(2)
                break

        block = re.search(r"Telah\s+memenuhi\s+persyaratan\s+dan\s+kompeten\s+pada\s+kualifikasi\s*:(.*?)Pada\s+bidang\s+pekerjaan", raw_text, re.IGNORECASE | re.DOTALL)
        if block:
            units = re.findall(r"^\s*\d+\.\s*([A-Z][A-Z0-9]*(?:[./-][A-Z0-9]+){2,})\s*$", block.group(1), re.MULTILINE)
            if units:
                data["units"] = [{"code": code, "name": None} for code in units]

        return CertificateCompetencySchema.model_validate(data)

    @staticmethod
    def _find(lines: list[str], label: str) -> Optional[str]:
        pattern = re.compile(rf"^(?:{label})\s*[:：]\s*(.+)$", re.IGNORECASE)
        for line in lines:
            match = pattern.match(line)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def _after(lines: list[str], label: str) -> Optional[str]:
        for index, line in enumerate(lines):
            if not re.match(label, line, re.IGNORECASE):
                continue
            for candidate in lines[index + 1:index + 3]:
                if re.match(r"^(?:This\s+is\s+to\s+certify|With\s+Qualification|In\s+the\s+area|Is\s+competent)\b", candidate, re.IGNORECASE):
                    continue
                if re.match(r"^(?:No\.?\s|Sertifikat\b|Telah\b|Dengan\b|Pada\b|\d+\.)", candidate, re.IGNORECASE):
                    return None
                return candidate
        return None
