import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class BankAccountSchema(BaseModel):
    bank_name: Optional[str] = Field(default=None, description="Name of the bank that holds the account", examples=["Bank Mandiri"])
    bank_branch: Optional[str] = Field(default=None, description="Account branch or unit as printed, including a KCP prefix when present", examples=["KCP Jakarta Cibis Nine"])
    account_number: Optional[str] = Field(default=None, description="Account number as text, preserving leading zeros and printed hyphens", examples=["148-00-1234567-8"])
    account_holder: Optional[str] = Field(default=None, description="Name of the account owner, not a transaction counterparty", examples=["PT CONTOH MAKMUR"])
    account_type: Optional[str] = Field(default=None, description="Account product or type when printed", examples=["Tabungan Mandiri"])

    @staticmethod
    def _clean(value: Optional[str], label: str) -> Optional[str]:
        if not isinstance(value, str):
            return None
        cleaned = re.sub(label, "", value.strip(), flags=re.IGNORECASE).strip()
        return cleaned if cleaned and cleaned not in ("-", "–", "—") else None

    @field_validator("bank_name", mode="before")
    @classmethod
    def clean_bank_name(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^BANK\s*NAME\s*[:.]?\s*")

    @field_validator("bank_branch", mode="before")
    @classmethod
    def clean_bank_branch(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^(?:KANTOR|CABANG|BRANCH)\s*[:.]?\s*")

    @field_validator("account_number", mode="before")
    @classmethod
    def clean_account_number(cls, v: Optional[str]) -> Optional[str]:
        cleaned = cls._clean(v, r"^(?:NO\.?\s*REKENING(?:\s*SEABANK)?|ACCOUNT\s*(?:NO\.?|NUMBER)|ACC\.?\s*NO\.?)\s*[:.]?\s*")
        if cleaned:
            cleaned = re.split(r"\s+-\s+", cleaned, maxsplit=1)[0]
            cleaned = re.sub(r"\s+", "", cleaned)
        return cleaned if cleaned and re.fullmatch(r"\d[\d-]*", cleaned) else None

    @field_validator("account_holder", mode="before")
    @classmethod
    def clean_account_holder(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^(?:ATAS\s*NAMA|NAMA|ACCOUNT\s*HOLDER|ACCOUNT\s*NAME)\s*[:.]?\s*")

    @field_validator("account_type", mode="before")
    @classmethod
    def clean_account_type(cls, v: Optional[str]) -> Optional[str]:
        return cls._clean(v, r"^(?:JENIS\s*REKENING|JENIS\s*TABUNGAN|ACCOUNT\s*TYPE|ACCOUNT\s*NAME)\s*[:.]?\s*")
