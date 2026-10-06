from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.identity_stay.schema import IdentityStaySchema
from src.domain.documents.identity_stay.parser import IdentityStayStringParser
from src.domain.documents.identity_stay.prompt import (
    get_identity_stay_system_prompt,
    get_identity_stay_user_prompt,
)


class IdentityStayDocument(BaseDocument):
    slug = "identity_stay"
    name = "Kartu Izin Tinggal Terbatas (KITAS)"
    description = "Indonesian electronic limited stay permit"
    schema_class = IdentityStaySchema

    def build_system_prompt(self) -> str:
        return get_identity_stay_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_identity_stay_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return IdentityStayStringParser.parse(raw_text)


__all__ = ["IdentityStayDocument", "IdentityStaySchema", "IdentityStayStringParser"]
