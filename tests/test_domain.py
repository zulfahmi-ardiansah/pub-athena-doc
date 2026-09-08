from src.domain.registry import get_document_registry
from src.domain.documents.identity_card.schema import IdentityCardSchema
from src.domain.documents.identity_card import IdentityCardDocument, KtpStringParser
from src.domain.documents.tax_number.schema import TaxNumberSchema
from src.domain.documents.tax_number import TaxNumberDocument, NpwpStringParser


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
        "tax_number": "01.234.567.8-901.000",
        "tax_payer": "PT CONTOH MAKMUR",
        "branch_office": "KPP PRATAMA JAKARTA TANAH ABANG",
        "branch_address": "JL KH MAS MANSYUR NO. 71"
    }
    model = TaxNumberSchema.model_validate(data)
    assert model.tax_number == "01.234.567.8-901.000"
    assert model.tax_payer == "PT CONTOH MAKMUR"
    assert model.branch_office == "KPP PRATAMA JAKARTA TANAH ABANG"
    assert model.branch_address == "JL KH MAS MANSYUR NO. 71"


def test_ktp_jokowi_sample_validation():
    data = {
        "province": "PROVINSI DKI JAKARTA",
        "city": "JAKARTA PUSAT",
        "id_number": "NIK : 3372052106610006",
        "full_name": "IR JOKO WIDODO",
        "birth_place": "SURAKARTA",
        "birth_date": "21-06-1961",
        "gender": "LAKI-LAKI",
        "blood_type": "A",
        "address": "JL TAMAN SUROPATI NO. 7",
        "neighborhood_unit": "005",
        "village": "MENTENG",
        "district": "MENTENG",
        "religion": "ISLAM",
        "marital_status": "KAWIN",
        "occupation": "GUBERNUR",
        "nationality": "WNI",
        "valid_until": "21-06-2017"
    }
    model = IdentityCardSchema.model_validate(data)
    assert model.province == "DKI JAKARTA"
    assert model.city == "JAKARTA PUSAT"
    assert model.id_number == "3372052106610006"
    assert model.full_name == "IR JOKO WIDODO"
    assert model.birth_place == "SURAKARTA"
    assert model.birth_date == "21-06-1961"
    assert model.gender == "LAKI-LAKI"
    assert model.blood_type == "A"
    assert model.address == "JL TAMAN SUROPATI NO. 7"
    assert model.neighborhood_unit == "005"
    assert model.village == "MENTENG"
    assert model.district == "MENTENG"
    assert model.religion == "ISLAM"
    assert model.marital_status == "KAWIN"
    assert model.occupation == "GUBERNUR"
    assert model.nationality == "WNI"
    assert model.valid_until == "21-06-2017"


def test_identity_card_document_schema_and_prompts():
    doc = IdentityCardDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "id_number" in schema["properties"]
    assert "province" in schema["properties"]
    assert "city" in schema["properties"]
    assert "neighborhood_unit" in schema["properties"]

    sys_prompt = doc.build_system_prompt()
    assert "KTP" in sys_prompt
    assert "Extraction Rules:" in sys_prompt

    ocr_sample = (
        "PROVINSI DKI JAKARTA\n"
        "JAKARTA PUSAT\n"
        "NIK : 3372052106610006\n"
        "Nama : IR JOKO WIDODO"
    )
    user_prompt = doc.build_user_prompt(ocr_sample)
    assert "Extract Indonesian KTP data" in user_prompt
    assert "NIK : 3372052106610006" in user_prompt


def test_ktp_ocr_quirk_normalization():
    noisy_data = {
        "province": "PROVINSI JAWA BARAT",
        "birth_place": "SURAKARTA, 21-06-1961",
        "birth_date": "Tanggal: 21/06/1961",
        "gender": "LAKI-LATI",
        "blood_type": "GOL. DARAH : A",
        "neighborhood_unit": "R/T/RW : 005 / 005",
    }
    model = IdentityCardSchema.model_validate(noisy_data)
    assert model.province == "JAWA BARAT"
    assert model.birth_place == "SURAKARTA"
    assert model.birth_date == "21-06-1961"
    assert model.gender == "LAKI-LAKI"
    assert model.blood_type == "A"
    assert model.neighborhood_unit == "005/005"

    invalid_neighborhood = {"neighborhood_unit": "MENTENG"}
    model_inv = IdentityCardSchema.model_validate(invalid_neighborhood)
    assert model_inv.neighborhood_unit is None


def test_ktp_string_parser():
    raw_ocr = """
    PROVINSI DKI JAKARTA
    JAKARTA PUSAT
    NIK : 3171010101900001
    Nama : BUDI SANTOSO
    Tempat/Tgl Lahir : JAKARTA, 01-01-1990
    Jenis Kelamin : LAKI-LAKI  Gol. Darah : O
    Alamat : JL TAMAN SUROPATI NO. 7
    RT/RW : 005/005
    Kel/Desa : MENTENG
    Kecamatan : MENTENG
    Agama : ISLAM
    Status Perkawinan : KAWIN
    Pekerjaan : KARYAWAN SWASTA
    Kewarganegaraan : WNI
    Berlaku Hingga : SEUMUR HIDUP
    """
    doc = IdentityCardDocument()
    parsed = doc.parse_string(raw_ocr)
    assert isinstance(parsed, IdentityCardSchema)
    assert parsed.province == "DKI JAKARTA"
    assert parsed.city == "JAKARTA PUSAT"
    assert parsed.id_number == "3171010101900001"
    assert parsed.full_name == "BUDI SANTOSO"
    assert parsed.birth_place == "JAKARTA"
    assert parsed.birth_date == "01-01-1990"
    assert parsed.gender == "LAKI-LAKI"
    assert parsed.blood_type == "O"
    assert parsed.address == "JL TAMAN SUROPATI NO. 7"
    assert parsed.neighborhood_unit == "005/005"
    assert parsed.village == "MENTENG"
    assert parsed.district == "MENTENG"
    assert parsed.religion == "ISLAM"
    assert parsed.marital_status == "KAWIN"
    assert parsed.occupation == "KARYAWAN SWASTA"
    assert parsed.nationality == "WNI"
    assert parsed.valid_until == "SEUMUR HIDUP"


def test_tax_number_document_schema_and_prompts():
    doc = TaxNumberDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "tax_number" in schema["properties"]
    assert "tax_payer" in schema["properties"]
    assert "branch_office" in schema["properties"]
    assert "branch_address" in schema["properties"]

    sys_prompt = doc.build_system_prompt()
    assert "NPWP" in sys_prompt
    assert "Extraction Rules:" in sys_prompt

    ocr_sample = (
        "KPP MADYA GRESIK\n"
        "12.345.678.9-636.000\n"
        "BUDI\n"
        "JL DR WAHIDIN SUDIROHUSODO 700 GRESIK\n"
        "Tanggal Terdaftar 01/01/2022"
    )
    user_prompt = doc.build_user_prompt(ocr_sample)
    assert "Extract Indonesian NPWP data" in user_prompt
    assert "12.345.678.9-636.000" in user_prompt


def test_npwp_string_parser():
    raw_ocr = """
    KEMENTERIAN KEUANGAN REPUBLIK INDONESIA
    DIREKTORAT JENDERAL PAJAK
    KPP MADYA GRESIK
    NPWP : 12.345.678.9-636.000
    Nama Wajib Pajak : PT CONTOH MAKMUR
    Alamat : JL DR WAHIDIN SUDIROHUSODO 700 GRESIK
    Tanggal Terdaftar : 01/01/2022
    """
    doc = TaxNumberDocument()
    parsed = doc.parse_string(raw_ocr)
    assert isinstance(parsed, TaxNumberSchema)
    assert parsed.tax_number == "12.345.678.9-636.000"
    assert parsed.tax_payer == "PT CONTOH MAKMUR"
    assert parsed.branch_office == "KPP MADYA GRESIK"
    assert parsed.branch_address == "JL DR WAHIDIN SUDIROHUSODO 700 GRESIK"
    assert parsed.registration_date == "01-01-2022"
