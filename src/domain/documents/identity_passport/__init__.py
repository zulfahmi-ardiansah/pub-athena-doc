from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.identity_passport.schema import IdentityPassportSchema
from src.domain.documents.identity_passport.parser import IdentityPassportStringParser
from src.domain.documents.identity_passport.prompt import (
    get_identity_passport_system_prompt,
    get_identity_passport_user_prompt,
)


class IdentityPassportDocument(BaseDocument):
    slug = "identity_passport"
    name = "Passport"
    description = "International passport bio-data page (ICAO Doc 9303)"
    schema_class = IdentityPassportSchema

    def build_system_prompt(self) -> str:
        return get_identity_passport_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_identity_passport_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return IdentityPassportStringParser.parse(raw_text)


__all__ = ["IdentityPassportDocument", "IdentityPassportSchema", "IdentityPassportStringParser"]
