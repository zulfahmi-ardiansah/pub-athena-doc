from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.passport.schema import PassportSchema
from src.domain.documents.passport.parser import PassportStringParser
from src.domain.documents.passport.prompt import (
    get_passport_system_prompt,
    get_passport_user_prompt,
)


class PassportDocument(BaseDocument):
    slug = "passport"
    name = "Passport"
    description = "International passport bio-data page (ICAO Doc 9303)"
    schema_class = PassportSchema

    def build_system_prompt(self) -> str:
        return get_passport_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_passport_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return PassportStringParser.parse(raw_text)


__all__ = ["PassportDocument", "PassportSchema", "PassportStringParser"]
