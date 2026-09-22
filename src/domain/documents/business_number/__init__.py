from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.business_number.schema import BusinessNumberSchema
from src.domain.documents.business_number.parser import BusinessNumberStringParser
from src.domain.documents.business_number.prompt import (
    get_business_identification_number_system_prompt,
    get_business_identification_number_user_prompt,
)


class BusinessIdentificationNumberDocument(BaseDocument):
    slug = "business_identification_number"
    name = "Nomor Induk Berusaha (NIB)"
    description = "Indonesian Business Identification Number Certificate"
    schema_class = BusinessNumberSchema

    def build_system_prompt(self) -> str:
        return get_business_identification_number_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_business_identification_number_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return BusinessNumberStringParser.parse(raw_text)


__all__ = ["BusinessIdentificationNumberDocument", "BusinessNumberSchema", "BusinessNumberStringParser"]
