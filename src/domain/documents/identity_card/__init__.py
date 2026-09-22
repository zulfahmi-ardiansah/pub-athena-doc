from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.identity_card.schema import IdentityCardSchema
from src.domain.documents.identity_card.parser import IdentificationNumberParser
from src.domain.documents.identity_card.prompt import (
    get_identity_card_system_prompt,
    get_identity_card_user_prompt,
)


class IdentityCardDocument(BaseDocument):
    slug = "identity_card"
    name = "Kartu Tanda Penduduk (KTP)"
    description = "Indonesian National Identity Card"
    schema_class = IdentityCardSchema

    def build_system_prompt(self) -> str:
        return get_identity_card_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_identity_card_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return IdentificationNumberParser.parse(raw_text)


__all__ = ["IdentityCardDocument", "IdentityCardSchema", "IdentificationNumberParser"]
