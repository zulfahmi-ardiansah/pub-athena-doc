import re
from typing import Dict, Optional
from src.domain.documents.identity_stay.schema import IdentityStaySchema


class IdentityStayStringParser:
    @classmethod
    def parse(cls, raw_text: str) -> IdentityStaySchema:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        data: Dict[str, Optional[str]] = {}
        labels = {
            "permit_niora": r"NIORA",
            "permit_number": r"Permit\s*Number",
            "permit_expiry_date": r"Stay\s*/\s*Multiple\s*Entries\s*Permit\s*Expiry",
            "permit_index": r"Stay\s*Permit\s*Index",
            "holder_full_name": r"Full\s*Name",
            "holder_passport_number": r"Passport\s*Number",
            "holder_passport_expiry_date": r"Passport\s*Expiry",
            "holder_nationality": r"Nationality",
            "holder_gender": r"Gender",
            "holder_occupation": r"Occupation",
            "holder_status": r"Status",
            "holder_guarantor": r"Guarantor\s*Name",
        }
        for field, label in labels.items():
            data[field] = cls._value(lines, label)

        birth = cls._value(lines, r"Place\s*/\s*Date\s*of\s*Birth")
        if birth:
            match = re.match(r"(.+?)\s*/\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{4})\s*$", birth)
            if match:
                data["holder_birth_place"], data["holder_birth_date"] = match.groups()

        data["holder_address"] = cls._value(lines, r"Address")
        for index, line in enumerate(lines):
            if re.match(r"^Address\s*:\s*\S", line, re.IGNORECASE) and index + 1 < len(lines):
                next_line = lines[index + 1]
                if next_line and not re.match(r"^(Occupation|Status|Guarantor\s*Name|DISCLAIMER)\b", next_line, re.IGNORECASE):
                    data["holder_address"] = f"{data['holder_address']} {next_line}" if data["holder_address"] else next_line
                break

        for index, line in enumerate(lines):
            if re.match(r"^KANIM\b", line, re.IGNORECASE):
                data["permit_issuing_office"] = line
                if index + 1 < len(lines) and re.match(r"^(?:JL\.?|JALAN\b)", lines[index + 1], re.IGNORECASE):
                    data["permit_issuing_office_address"] = lines[index + 1]
                break

        for index, line in enumerate(lines):
            if not re.match(r"^[A-Za-z][A-Za-z\s]+,\s*\d{1,2}[-/.]\d{1,2}[-/.]\d{4}$", line):
                continue
            if index + 1 < len(lines) and re.match(r"^Head\s+of\b", lines[index + 1], re.IGNORECASE):
                place, date = line.rsplit(",", 1)
                data["permit_issued_place"] = place.strip()
                data["permit_issued_date"] = date.strip()
                break

        return IdentityStaySchema.model_validate(data)

    @staticmethod
    def _value(lines: list[str], label: str) -> Optional[str]:
        pattern = re.compile(rf"^{label}\s*:\s*(.*?)\s*$", re.IGNORECASE)
        for line in lines:
            match = pattern.match(line)
            if match:
                return match.group(1) or None
        return None
