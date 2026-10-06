import re
from typing import Dict, Optional
from src.domain.documents.bank_account.schema import BankAccountSchema


class BankAccountStringParser:
    @classmethod
    def parse(cls, raw_text: str) -> BankAccountSchema:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        data: Dict[str, Optional[str]] = {}

        banks = (
            (r"\bBANK\s+CENTRAL\s+ASIA\b", "Bank Central Asia"),
            (r"\bBANK\s+RAKYAT\s+INDONESIA\b|\bBANK\s+BRI\b", "Bank Rakyat Indonesia"),
            (r"\bBANK\s+MANDIRI\b|\bmandiri\b", "Bank Mandiri"),
            (r"\bSeaBank\b", "SeaBank"),
            (r"\bBank\s+Danamon\b", "Bank Danamon"),
            (r"\bFirst\s+Bank\s+of\s+Wiki\b", "First Bank of Wiki"),
            (r"\bFirst\s+Bank\b", "First Bank"),
            (r"\bMinnesota\s+Bank\s+and\s+Trust\b", "Minnesota Bank and Trust"),
        )
        for pattern, name in banks:
            if re.search(pattern, raw_text, re.IGNORECASE):
                data["bank_name"] = name
                break
        if not data.get("bank_name"):
            data["bank_name"] = cls._find(lines, r"Bank\s*Name")

        account = cls._find(lines, r"(?:No\.?\s*Rekening(?:\s*SeaBank)?|Account\s*(?:No\.?|Number)|ACC\.?\s*No\.?)")
        if account:
            number, separator, holder = account.partition(" - ")
            data["account_number"] = number
            if separator:
                data["account_holder"] = holder.strip() or None
        else:
            letter_account = re.search(r"\baccount\s+is\s+(\d[\d-]{5,})\b", raw_text, re.IGNORECASE)
            if letter_account:
                data["account_number"] = letter_account.group(1)

        named_holder = cls._find(lines, r"(?:Atas\s*Nama|Nama|Account\s*Holder)")
        if named_holder:
            data["account_holder"] = named_holder
        data["bank_branch"] = cls._find(lines, r"(?:Kantor\s+Bank\s+BRI|Cabang|Branch)")
        if not data.get("bank_branch"):
            inline_branch = re.search(r"\bBank\s+Danamon,\s*Cabang\s+([^,\n]+)", raw_text, re.IGNORECASE)
            if inline_branch:
                data["bank_branch"] = inline_branch.group(1).strip()
        if not data.get("bank_branch"):
            data["bank_branch"] = next((line for line in lines if re.match(r"^KCP\s+[A-Z]", line, re.IGNORECASE)), None)

        if data.get("bank_name") == "Bank Central Asia" and not data.get("account_number"):
            for index, line in enumerate(lines):
                if not re.match(r"^KCP\s+", line, re.IGNORECASE):
                    continue
                if index + 2 < len(lines) and re.fullmatch(r"\d{8,16}", lines[index + 1]):
                    data["account_number"] = lines[index + 1]
                    if re.fullmatch(r"[A-Za-z][A-Za-z .'-]+", lines[index + 2]):
                        data["account_holder"] = lines[index + 2]
                break

        data["account_type"] = cls._find(lines, r"(?:Jenis\s*Rekening|Jenis\s*Tabungan|Account\s*(?:Type|Name))")
        if not data.get("account_type"):
            types = (
                (r"\bSimpedes\b", "Simpedes"),
                (r"\bBritAma\b", "BritAma"),
                (r"\bTAB\s+MANDIRI\b", "Tabungan Mandiri"),
                (r"\bCHEQUING\s+ACCOUNT\b", "Chequing"),
            )
            for pattern, kind in types:
                if re.search(pattern, raw_text, re.IGNORECASE):
                    data["account_type"] = kind
                    break

        return BankAccountSchema.model_validate(data)

    @staticmethod
    def _find(lines: list[str], label: str) -> Optional[str]:
        pattern = re.compile(rf"^{label}\s*:\s*(.+?)\s*$", re.IGNORECASE)
        for line in lines:
            match = pattern.match(line)
            if match:
                return match.group(1).strip() or None
        return None
