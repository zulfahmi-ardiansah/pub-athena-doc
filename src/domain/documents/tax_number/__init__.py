from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.tax_number.schema import TaxNumberSchema
from src.domain.documents.tax_number.parser import TaxNumberStringParser
from src.domain.documents.tax_number.prompt import (
    get_tax_number_system_prompt,
    get_tax_number_user_prompt,
)


class TaxNumberDocument(BaseDocument):
    slug = "tax_number"
    name = "Nomor Pokok Wajib Pajak (NPWP)"
    description = "Indonesian Taxpayer Identification Card"
    schema_class = TaxNumberSchema

    def build_system_prompt(self) -> str:
        return get_tax_number_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_tax_number_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return TaxNumberStringParser.parse(raw_text)


__all__ = ["TaxNumberDocument", "TaxNumberSchema", "TaxNumberStringParser"]
