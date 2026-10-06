from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.bank_account.schema import BankAccountSchema
from src.domain.documents.bank_account.parser import BankAccountStringParser
from src.domain.documents.bank_account.prompt import (
    get_bank_account_system_prompt,
    get_bank_account_user_prompt,
)


class BankAccountDocument(BaseDocument):
    slug = "bank_account"
    name = "Bank Account"
    description = "Bank account details from passbooks, statements, and account letters"
    schema_class = BankAccountSchema

    def build_system_prompt(self) -> str:
        return get_bank_account_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_bank_account_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return BankAccountStringParser.parse(raw_text)


__all__ = ["BankAccountDocument", "BankAccountSchema", "BankAccountStringParser"]
