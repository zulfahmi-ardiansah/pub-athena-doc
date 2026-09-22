from typing import Dict, List, Optional
from src.domain.base import BaseDocument
from src.domain.documents.identity_card import IdentityCardDocument
from src.domain.documents.tax_number import TaxNumberDocument
from src.domain.documents.business_number import BusinessIdentificationNumberDocument
from src.domain.documents.tax_entity import TaxEntityDocument
from src.domain.documents.identity_passport import IdentityPassportDocument
from src.domain.documents.business_deed import BusinessDeedDocument


class DocumentRegistry:
    """Central registry of supported document extraction specifications."""

    def __init__(self) -> None:
        self._documents: Dict[str, BaseDocument] = {}
        # Register default supported documents
        self.register(IdentityCardDocument())
        self.register(TaxNumberDocument())
        self.register(BusinessIdentificationNumberDocument())
        self.register(TaxEntityDocument())
        self.register(IdentityPassportDocument())
        self.register(BusinessDeedDocument())

    def register(self, doc: BaseDocument) -> None:
        """Register a new document specification."""
        self._documents[doc.slug] = doc

    def get(self, slug: str) -> Optional[BaseDocument]:
        """Retrieve a document specification by slug."""
        return self._documents.get(slug)

    def list_documents(self) -> List[Dict[str, str]]:
        """List all registered document types with metadata."""
        return [
            {
                "slug": doc.slug,
                "name": doc.name,
                "description": doc.description,
            }
            for doc in self._documents.values()
        ]


_registry_instance: Optional[DocumentRegistry] = None


def get_document_registry() -> DocumentRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = DocumentRegistry()
    return _registry_instance
