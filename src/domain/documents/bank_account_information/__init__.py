from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.bank_account_information.schema import BankAccountInformationSchema
from src.domain.documents.bank_account_information.parser import BankAccountInformationStringParser
from src.domain.documents.bank_account_information.prompt import (
    get_bank_account_information_system_prompt,
    get_bank_account_information_user_prompt,
)


class BankAccountInformationDocument(BaseDocument):
    slug = "bank_account_information"
    name = "Bank Account Information"
    description = "Bank account details from passbooks, statements, and account letters"
    schema_class = BankAccountInformationSchema

    def build_system_prompt(self) -> str:
        return get_bank_account_information_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_bank_account_information_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return BankAccountInformationStringParser.parse(raw_text)


__all__ = ["BankAccountInformationDocument", "BankAccountInformationSchema", "BankAccountInformationStringParser"]
