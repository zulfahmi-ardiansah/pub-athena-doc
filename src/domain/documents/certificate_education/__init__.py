from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.certificate_education.schema import CertificateEducationSchema
from src.domain.documents.certificate_education.parser import CertificateEducationStringParser
from src.domain.documents.certificate_education.prompt import (
    get_certificate_education_system_prompt,
    get_certificate_education_user_prompt,
)


class CertificateEducationDocument(BaseDocument):
    slug = "certificate_education"
    name = "Ijazah / Academic Transcript"
    description = "Education and graduation details from Indonesian diplomas and academic transcripts"
    schema_class = CertificateEducationSchema

    def build_system_prompt(self) -> str:
        return get_certificate_education_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_certificate_education_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return CertificateEducationStringParser.parse(raw_text)


__all__ = ["CertificateEducationDocument", "CertificateEducationSchema", "CertificateEducationStringParser"]
