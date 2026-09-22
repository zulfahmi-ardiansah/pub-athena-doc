import re
from typing import Any, Dict, Optional
from src.domain.documents.identity_card.schema import IdentityCardSchema


class IdentificationNumberParser:
    """
    Deterministic rule-based & regex parser for Indonesian Identity Card (KTP) OCR text.
    Extracts all fields directly without requiring an LLM.
    """

    @classmethod
    def parse(cls, raw_text: str) -> IdentityCardSchema:
        data: Dict[str, Any] = {}
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        # 1. Extract Province & City from headers
        cls._extract_header_location(lines, data)

        # 2. Extract NIK (16 digits)
        cls._extract_nik(raw_text, data)

        # 3. Extract Line-by-Line Key-Value fields
        cls._extract_fields_from_lines(lines, data)

        # 4. Fallback search across full text if certain fields are still missing
        cls._fallback_extract_full_text(raw_text, data)

        return IdentityCardSchema.model_validate(data)

    @classmethod
    def _extract_header_location(cls, lines: list, data: Dict[str, Any]) -> None:
        prov_index = -1
        for i, line in enumerate(lines[:6]):
            # Province match
            prov_match = re.search(r"PROVINSI\s+([A-Z\s]+)", line, re.IGNORECASE)
            if prov_match and not data.get("province"):
                prov_val = prov_match.group(1).strip()
                prov_val = re.split(r"(KOTA|KABUPATEN|NIK)", prov_val, flags=re.IGNORECASE)[0].strip()
                data["province"] = prov_val
                prov_index = i

            # Explicit City / Regency match (e.g. KOTA JAKARTA PUSAT, KABUPATEN BOGOR)
            city_match = re.search(r"\b(KOTA|KABUPATEN)\s+([A-Z\s]+)", line, re.IGNORECASE)
            if city_match and not data.get("city"):
                city_type = city_match.group(1).upper()
                city_name = city_match.group(2).strip()
                city_name = re.split(r"(NIK|PROVINSI)", city_name, flags=re.IGNORECASE)[0].strip()
                data["city"] = f"{city_type} {city_name}".strip()

        # If province was found at index `prov_index`, check the immediate next line for city
        if prov_index != -1 and prov_index + 1 < len(lines) and not data.get("city"):
            next_line = lines[prov_index + 1].strip()
            if not re.search(r"\b(NIK|NAMA|TEMPAT|ALAMAT|PROVINSI|AGAMA|GOL)\b", next_line, re.IGNORECASE):
                cleaned_city = re.split(r"\b(NIK|NAMA)\b", next_line, flags=re.IGNORECASE)[0].strip()
                if cleaned_city:
                    data["city"] = cleaned_city

    @classmethod
    def _extract_nik(cls, text: str, data: Dict[str, Any]) -> None:
        # Direct NIK label search
        nik_label_match = re.search(r"N[I1l!|][KCk]\s*[:\.]?\s*([0-9OobB\s]{16,20})", text, re.IGNORECASE)
        if nik_label_match:
            raw_digits = nik_label_match.group(1)
            cleaned = cls._normalize_digits(raw_digits)
            if len(cleaned) == 16:
                data["id_number"] = cleaned
                return

        # 16-digit numeric pattern search across text
        nik_match = re.search(r"\b([1-9][0-9]{15})\b", text)
        if nik_match:
            data["id_number"] = nik_match.group(1)

    @classmethod
    def _normalize_digits(cls, text: str) -> str:
        text = text.replace("O", "0").replace("o", "0").replace("D", "0")
        text = text.replace("I", "1").replace("l", "1").replace("!", "1").replace("|", "1")
        text = text.replace("b", "6").replace("B", "8").replace("S", "5").replace("s", "5")
        return re.sub(r"\D", "", text)

    @classmethod
    def _extract_fields_from_lines(cls, lines: list, data: Dict[str, Any]) -> None:
        for line in lines:
            # Full Name
            if not data.get("full_name") and re.search(r"^NAMA\b", line, re.IGNORECASE):
                val = re.sub(r"^NAMA\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
                if val:
                    data["full_name"] = val

            # Tempat/Tgl Lahir
            if not data.get("birth_place") and re.search(r"TEMPAT[/\s]*(?:TGL|TANGGAL)?\s*LAHIR", line, re.IGNORECASE):
                val = re.sub(r"^.*LAHIR\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
                if "," in val:
                    parts = val.split(",", 1)
                    data["birth_place"] = parts[0].strip()
                    date_match = re.search(r"\b(\d{2}[-/]\d{2}[-/]\d{4})\b", parts[1])
                    if date_match:
                        data["birth_date"] = date_match.group(1).replace("/", "-")
                else:
                    date_match = re.search(r"\b(\d{2}[-/]\d{2}[-/]\d{4})\b", val)
                    if date_match:
                        data["birth_date"] = date_match.group(1).replace("/", "-")
                        place = val.replace(date_match.group(0), "").strip(" ,:-")
                        if place:
                            data["birth_place"] = place

            # Jenis Kelamin & Gol Darah
            if not data.get("gender") and re.search(r"JENIS\s*KELAMIN", line, re.IGNORECASE):
                if re.search(r"\bLAKI[- ]*LAKI\b", line, re.IGNORECASE):
                    data["gender"] = "LAKI-LAKI"
                elif re.search(r"\bPEREMPUAN\b", line, re.IGNORECASE):
                    data["gender"] = "PEREMPUAN"

            if not data.get("blood_type") and re.search(r"GOL(?:\.|\s*)\s*DARAH", line, re.IGNORECASE):
                blood_match = re.search(r"GOL(?:\.|\s*)\s*DARAH\s*[:\.]?\s*([ABO-]+)", line, re.IGNORECASE)
                if blood_match:
                    data["blood_type"] = blood_match.group(1).strip()

            # Alamat
            if not data.get("address") and re.search(r"^ALAMAT\b", line, re.IGNORECASE):
                val = re.sub(r"^ALAMAT\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
                if val:
                    data["address"] = val

            # RT/RW
            if not data.get("neighborhood_unit") and re.search(r"\bR[/\.]?T[/\s]*R[/\.]?W\b", line, re.IGNORECASE):
                rt_rw_match = re.search(r"R[/\.]?T[/\s]*R[/\.]?W\s*[:\.]?\s*([0-9/]+)", line, re.IGNORECASE)
                if rt_rw_match:
                    data["neighborhood_unit"] = rt_rw_match.group(1).strip()

            # Kel/Desa
            if not data.get("village") and re.search(r"KEL(?:/|\.|\s*)DESA", line, re.IGNORECASE):
                val = re.sub(r"^.*(?:KEL(?:/|\.|\s*)DESA)\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
                if val:
                    data["village"] = val

            # Kecamatan
            if not data.get("district") and re.search(r"KECAMATAN", line, re.IGNORECASE):
                val = re.sub(r"^.*KECAMATAN\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
                if val:
                    data["district"] = val

            # Agama
            if not data.get("religion") and re.search(r"^AGAMA\b", line, re.IGNORECASE):
                val = re.sub(r"^AGAMA\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip().upper()
                for rel in ["ISLAM", "KRISTEN", "KATHOLIK", "KATOLIK", "HINDU", "BUDDHA", "KHONGHUCU"]:
                    if rel in val:
                        data["religion"] = "KATHOLIK" if rel == "KATOLIK" else rel
                        break

            # Status Perkawinan
            if not data.get("marital_status") and re.search(r"STATUS\s*PERKAWINAN", line, re.IGNORECASE):
                val = re.sub(r"^.*STATUS\s*PERKAWINAN\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip().upper()
                for status in ["BELUM KAWIN", "CERAI HIDUP", "CERAI MATI", "KAWIN"]:
                    if status in val:
                        data["marital_status"] = status
                        break

            # Pekerjaan
            if not data.get("occupation") and re.search(r"^PEKERJAAN\b", line, re.IGNORECASE):
                val = re.sub(r"^PEKERJAAN\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
                if val:
                    data["occupation"] = val

            # Kewarganegaraan
            if not data.get("nationality") and re.search(r"KEWARGANEGARAAN", line, re.IGNORECASE):
                if "WNA" in line.upper():
                    data["nationality"] = "WNA"
                elif "WNI" in line.upper():
                    data["nationality"] = "WNI"

            # Berlaku Hingga
            if not data.get("valid_until") and re.search(r"BERLAKU\s*HINGGA", line, re.IGNORECASE):
                val = re.sub(r"^.*BERLAKU\s*HINGGA\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip().upper()
                if "SEUMUR" in val:
                    data["valid_until"] = "SEUMUR HIDUP"
                else:
                    date_match = re.search(r"\b(\d{2}[-/]\d{2}[-/]\d{4})\b", val)
                    if date_match:
                        data["valid_until"] = date_match.group(1).replace("/", "-")
                    elif val:
                        data["valid_until"] = val

    @classmethod
    def _fallback_extract_full_text(cls, text: str, data: Dict[str, Any]) -> None:
        if not data.get("gender"):
            if re.search(r"\bLAKI[- ]*LAKI\b", text, re.IGNORECASE):
                data["gender"] = "LAKI-LAKI"
            elif re.search(r"\bPEREMPUAN\b", text, re.IGNORECASE):
                data["gender"] = "PEREMPUAN"

        if not data.get("religion"):
            for rel in ["ISLAM", "KRISTEN", "KATHOLIK", "KATOLIK", "HINDU", "BUDDHA", "KHONGHUCU"]:
                if re.search(rf"\b{rel}\b", text, re.IGNORECASE):
                    data["religion"] = "KATHOLIK" if rel == "KATOLIK" else rel
                    break

        if not data.get("nationality"):
            data["nationality"] = "WNI"

        if not data.get("valid_until"):
            if re.search(r"SEUMUR\s*HIDUP", text, re.IGNORECASE):
                data["valid_until"] = "SEUMUR HIDUP"
