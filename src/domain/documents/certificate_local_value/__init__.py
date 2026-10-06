from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.certificate_local_value.schema import CertificateLocalValueSchema
from src.domain.documents.certificate_local_value.parser import CertificateLocalValueStringParser
from src.domain.documents.certificate_local_value.prompt import (
    get_certificate_local_value_system_prompt,
    get_certificate_local_value_user_prompt,
)


class CertificateLocalValueDocument(BaseDocument):
    slug = "certificate_local_value"
    name = "Sertifikat Tingkat Komponen Dalam Negeri (TKDN)"
    description = "Indonesian domestic content certificate"
    schema_class = CertificateLocalValueSchema

    def build_system_prompt(self) -> str:
        return get_certificate_local_value_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_certificate_local_value_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return CertificateLocalValueStringParser.parse(raw_text)


__all__ = ["CertificateLocalValueDocument", "CertificateLocalValueSchema", "CertificateLocalValueStringParser"]
