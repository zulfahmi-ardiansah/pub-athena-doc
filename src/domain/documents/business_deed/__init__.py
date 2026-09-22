from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.business_deed.schema import BusinessDeedSchema
from src.domain.documents.business_deed.parser import BusinessDeedStringParser
from src.domain.documents.business_deed.prompt import (
    get_business_deed_system_prompt,
    get_business_deed_user_prompt,
)


class BusinessDeedDocument(BaseDocument):
    slug = "business_deed"
    name = "Business Deed & SK Kemenkumham"
    description = "Indonesian notarial business deed (Akta) and its Kemenkumham confirmation decree (SK)"
    schema_class = BusinessDeedSchema

    def build_system_prompt(self) -> str:
        return get_business_deed_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_business_deed_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return BusinessDeedStringParser.parse(raw_text)


__all__ = ["BusinessDeedDocument", "BusinessDeedSchema", "BusinessDeedStringParser"]
