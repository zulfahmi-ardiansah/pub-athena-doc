from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.domain.documents.certificate_competency.schema import CertificateCompetencySchema
from src.domain.documents.certificate_competency.parser import CertificateCompetencyStringParser
from src.domain.documents.certificate_competency.prompt import (
    get_certificate_competency_system_prompt,
    get_certificate_competency_user_prompt,
)


class CertificateCompetencyDocument(BaseDocument):
    slug = "certificate_competency"
    name = "Course / Competency Certificate"
    description = "Informal education, training, course completion, and professional competency certificates"
    schema_class = CertificateCompetencySchema

    def build_system_prompt(self) -> str:
        return get_certificate_competency_system_prompt()

    def build_user_prompt(self, raw_text: str) -> str:
        return get_certificate_competency_user_prompt(raw_text)

    def parse_string(self, raw_text: str) -> BaseModel:
        return CertificateCompetencyStringParser.parse(raw_text)


__all__ = ["CertificateCompetencyDocument", "CertificateCompetencySchema", "CertificateCompetencyStringParser"]
