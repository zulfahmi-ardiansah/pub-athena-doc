import re
from typing import Dict, Optional
from src.domain.documents.certificate_local_value.schema import CertificateLocalValueSchema


class CertificateLocalValueStringParser:
    _labels = {
        "product_name": r"Jenis\s*Produk",
        "product_type": r"Tipe",
        "product_specification": r"Spesifikasi",
        "product_hs": r"Kode\s*HS",
        "product_brand": r"Merk",
        "product_local_value": r"Nilai\s*TKDN",
        "product_standard": r"Standar(?:d)?\s*Produk",
        "product_certificate": r"Sertifikat\s*Produk",
        "report_number": r"No\.?\s*Laporan",
        "business_name": r"Nama\s*Perusahaan",
        "business_address": r"Alamat",
        "business_tax_number": r"NPWP",
        "business_field": r"(?:Bidang\s*Usaha|Jenis\s*Industri)",
        "certificate_number": r"No\.?\s*Tanda\s*Sah",
    }

    @classmethod
    def parse(cls, raw_text: str) -> CertificateLocalValueSchema:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        data: Dict[str, Optional[str]] = {}
        label_pattern = re.compile(r"^(?:" + "|".join(cls._labels.values()) + r")\s*:", re.IGNORECASE)
        for field, label in cls._labels.items():
            pattern = re.compile(rf"^{label}\s*:\s*(.*)$", re.IGNORECASE)
            for index, line in enumerate(lines):
                match = pattern.match(line)
                if not match:
                    continue
                value = match.group(1).strip()
                if field in ("product_specification", "business_address", "business_field"):
                    continuation = []
                    for next_line in lines[index + 1:]:
                        if label_pattern.match(next_line) or re.match(r"^(?:yang\s+telah|diberikan\s+kepada|Jakarta\s*,|Kepala\s+Pusat)\b", next_line, re.IGNORECASE):
                            break
                        continuation.append(next_line)
                    value = " ".join([value, *continuation]).strip()
                data[field] = value or None
                break

        validity = re.search(r"\bberlaku\s+(\d+)\s+tahun\b", raw_text, re.IGNORECASE)
        if validity:
            data["certificate_valid_year"] = validity.group(1)

        date_pattern = re.compile(r"^([A-Za-z][A-Za-z\s]+),\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})$", re.IGNORECASE)
        for line in lines:
            match = date_pattern.match(line)
            if match:
                data["certificate_issued_place"], data["certificate_issued_date"] = match.groups()
                break

        for index, line in enumerate(lines):
            if re.match(r"^Kepala\s+Pusat\b", line, re.IGNORECASE):
                data["signing_official_title"] = line
                if index + 1 < len(lines) and re.fullmatch(r"[A-Za-z][A-Za-z .'-]+", lines[index + 1]):
                    data["signing_official_name"] = lines[index + 1]
                break

        for line in lines:
            match = re.fullmatch(r"#\s*(\d+)", line)
            if match:
                data["certificate_qr_number"] = match.group(1)
                break

        return CertificateLocalValueSchema.model_validate(data)
