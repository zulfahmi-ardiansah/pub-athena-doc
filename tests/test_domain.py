from src.domain.registry import get_document_registry
from src.domain.documents.identity_card.schema import IdentityCardSchema
from src.domain.documents.tax_number.schema import TaxNumberSchema


def test_document_registry():
    registry = get_document_registry()
    docs = registry.list_documents()
    slugs = [d["slug"] for d in docs]
    assert "identity_card" in slugs
    assert "tax_number" in slugs


def test_ktp_schema_validation():
    data = {
        "id_number": "3171-0101-0190-0001",
        "full_name": "JOHN DOE",
        "gender": "LAKI-LAKI",
        "valid_until": "SEUMUR HIDUP"
    }
    model = IdentityCardSchema.model_validate(data)
    assert model.id_number == "3171010101900001"
    assert model.full_name == "JOHN DOE"
    assert model.nationality == "WNI"


def test_npwp_schema_validation():
    data = {
        "tax_id_number": "01.234.567.8-901.000",
        "taxpayer_name": "PT CONTOH MAKMUR",
        "tax_office": "KPP PRATAMA JAKARTA TANAH ABANG"
    }
    model = TaxNumberSchema.model_validate(data)
    assert model.tax_id_number == "01.234.567.8-901.000"
    assert model.taxpayer_name == "PT CONTOH MAKMUR"
