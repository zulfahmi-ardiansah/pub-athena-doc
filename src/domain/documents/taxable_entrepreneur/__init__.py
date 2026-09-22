from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.taxable_entrepreneur.schema import TaxableEntrepreneurSchema
from src.domain.documents.taxable_entrepreneur.parser import TaxableEntrepreneurStringParser
from src.domain.documents.taxable_entrepreneur.prompt import (
    get_taxable_entrepreneur_system_prompt,
    get_taxable_entrepreneur_user_prompt,
)


class TaxableEntrepreneurDocument(BaseDocument):
    slug = "taxable_entrepreneur"
    name = "Surat Pengukuhan Pengusaha Kena Pajak (SPPKP/PKP)"
    description = "Indonesian Taxable Entrepreneur Confirmation Letter"
    schema_class = TaxableEntrepreneurSchema

    def build_system_prompt(self) -> str:
        return get_taxable_entrepreneur_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_taxable_entrepreneur_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return TaxableEntrepreneurStringParser.parse(raw_text)


__all__ = ["TaxableEntrepreneurDocument", "TaxableEntrepreneurSchema", "TaxableEntrepreneurStringParser"]
