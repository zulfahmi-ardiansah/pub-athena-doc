from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.tax_entity.schema import TaxEntitySchema
from src.domain.documents.tax_entity.parser import TaxEntityStringParser
from src.domain.documents.tax_entity.prompt import (
    get_tax_entity_system_prompt,
    get_tax_entity_user_prompt,
)


class TaxEntityDocument(BaseDocument):
    slug = "tax_entity"
    name = "Surat Pengukuhan Pengusaha Kena Pajak (SPPKP/PKP)"
    description = "Indonesian Taxable Entrepreneur Confirmation Letter"
    schema_class = TaxEntitySchema

    def build_system_prompt(self) -> str:
        return get_tax_entity_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_tax_entity_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return TaxEntityStringParser.parse(raw_text)


__all__ = ["TaxEntityDocument", "TaxEntitySchema", "TaxEntityStringParser"]
