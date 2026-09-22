from src.domain.registry import get_document_registry
from src.domain.documents.identity_card.schema import IdentityCardSchema
from src.domain.documents.identity_card import IdentityCardDocument
from src.domain.documents.tax_number.schema import TaxNumberSchema
from src.domain.documents.tax_number import TaxNumberDocument
from src.domain.documents.business_number.schema import BusinessNumberSchema, FieldItem, LicenseItem
from src.domain.documents.business_number import (
    BusinessIdentificationNumberDocument,
)
from src.domain.documents.taxable_entrepreneur.schema import TaxableEntrepreneurSchema
from src.domain.documents.taxable_entrepreneur import (
    TaxableEntrepreneurDocument,
    TaxableEntrepreneurStringParser,
)


def test_document_registry():
    registry = get_document_registry()
    docs = registry.list_documents()
    slugs = [d["slug"] for d in docs]
    assert "identity_card" in slugs
    assert "tax_number" in slugs
    assert "business_identification_number" in slugs
    assert "taxable_entrepreneur" in slugs


def test_identity_card_schema_validation():
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


def test_tax_number_schema_validation():
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


def test_identity_card_jokowi_sample_validation():
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
    assert model.birth_date == "1961-06-21"
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
    assert model.valid_until == "2017-06-21"


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


def test_identity_card_ocr_quirk_normalization():
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
    assert model.birth_date == "1961-06-21"
    assert model.gender == "LAKI-LAKI"
    assert model.blood_type == "A"
    assert model.neighborhood_unit == "005/005"

    invalid_neighborhood = {"neighborhood_unit": "MENTENG"}
    model_inv = IdentityCardSchema.model_validate(invalid_neighborhood)
    assert model_inv.neighborhood_unit is None


def test_identity_card_string_parser():
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
    assert parsed.birth_date == "1990-01-01"
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


def test_tax_number_string_parser():
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
    assert parsed.registration_date == "2022-01-01"


def test_business_identification_number_schema_validation():
    data = {
        "number": "1234567890123",
        "name": "PT CONTOH SEJAHTERA ABADI",
        "office_address": "JL. JENDERAL SUDIRMAN KAV. 10, KOTA ADM. JAKARTA SELATAN",
        "postal_code": "12190",
        "phone_number": "0215551234",
        "email": "info@contohsejahtera.co.id",
        "investment_status": "PMDN",
        "issued_place": "Jakarta",
        "issued_date": "10 Januari 2020",
        "amendment_number": "1",
        "amendment_date": "05 Mei 2023",
        "printed_date": "05 Mei 2023",
        "signing_official_title": "Menteri Investasi dan Hilirisasi/ Kepala Badan Koordinasi Penanaman Modal",
        "fields": [
            {
                "no": "39",
                "field_code": "46206",
                "field_title": "Perdagangan Besar Hasil Perikanan",
                "business_location": "GD. PUSAT PERUM BULOG LT. 10 JL. JEND. GATOT SUBROTO KAV.49",
                "postal_code": "12950",
                "risk_level": "Menengah Tinggi",
                "licenses": [
                    {
                        "license_type": "NIB",
                        "license_status": "Terbit",
                        "remarks": "-",
                    },
                    {
                        "license_type": "Sertifikat Standar",
                        "license_status": "Belum Terverifikasi",
                        "remarks": "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 hari kerja",
                    },
                ],
            }
        ],
    }
    model = BusinessNumberSchema.model_validate(data)
    assert model.number == "1234567890123"
    assert model.name == "PT CONTOH SEJAHTERA ABADI"
    assert model.postal_code == "12190"
    assert model.investment_status == "PMDN"
    assert model.issued_date == "2020-01-10"
    assert model.amendment_number == "1"
    assert model.amendment_date == "2023-05-05"
    assert model.printed_date == "2023-05-05"
    assert model.fields is not None
    assert len(model.fields) == 1
    assert model.fields[0].field_code == "46206"
    assert model.fields[0].risk_level == "Menengah Tinggi"
    assert model.fields[0].licenses is not None
    assert len(model.fields[0].licenses) == 2
    assert model.fields[0].licenses[0].license_type == "NIB"
    assert model.fields[0].licenses[0].remarks is None
    assert model.fields[0].licenses[1].license_type == "Sertifikat Standar"
    assert model.fields[0].licenses[1].remarks == "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 hari kerja"


def test_business_identification_number_document_schema_and_prompts():
    doc = BusinessIdentificationNumberDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "number" in schema["properties"]
    assert "name" in schema["properties"]
    assert "office_address" in schema["properties"]
    assert "fields" in schema["properties"]

    sys_prompt = doc.build_system_prompt()
    assert "NIB" in sys_prompt
    assert "Extraction Rules:" in sys_prompt

    ocr_sample = (
        "NOMOR INDUK BERUSAHA : 1234567890123\n"
        "1. Nama Pelaku Usaha : PT CONTOH SEJAHTERA ABADI\n"
    )
    user_prompt = doc.build_user_prompt(ocr_sample)
    assert "Extract Indonesian NIB" in user_prompt
    assert "1234567890123" in user_prompt


def test_nib_string_parser():
    raw_ocr = """
    PEMERINTAH REPUBLIK INDONESIA
    PERIZINAN BERUSAHA BERBASIS RISIKO
    NOMOR INDUK BERUSAHA : 1234567890123
    1. Nama Pelaku Usaha : PT CONTOH SEJAHTERA ABADI
    2. Alamat Kantor : JL. JENDERAL SUDIRMAN KAV. 10, Kota Adm. Jakarta Selatan
    Kode Pos : 12190
    No. Telepon : 0215551234
    Email : info@contohsejahtera.co.id
    3. Status Penanaman Modal : PMDN
    Diterbitkan di : Jakarta, tanggal : 10 Januari 2020
    Perubahan ke-1, tanggal : 05 Mei 2023
    Dicetak tanggal : 05 Mei 2023
    """
    doc = BusinessIdentificationNumberDocument()
    parsed = doc.parse_string(raw_ocr)
    assert isinstance(parsed, BusinessNumberSchema)
    assert parsed.number == "1234567890123"
    assert parsed.name == "PT CONTOH SEJAHTERA ABADI"
    assert parsed.office_address == "JL. JENDERAL SUDIRMAN KAV. 10, Kota Adm. Jakarta Selatan"
    assert parsed.postal_code == "12190"
    assert parsed.phone_number == "0215551234"
    assert parsed.email == "info@contohsejahtera.co.id"
    assert parsed.investment_status == "PMDN"
    assert parsed.issued_place == "Jakarta"
    assert parsed.issued_date == "2020-01-10"
    assert parsed.amendment_number == "1"
    assert parsed.amendment_date == "2023-05-05"
    assert parsed.printed_date == "2023-05-05"
    assert parsed.fields is None


def test_license_item_value_normalization():
    # An OCR/LLM pass sometimes prefixes a stacked sub-row's Jenis/Status with a
    # leading bullet dash (from the table's visual stacking) instead of a clean value.
    item = LicenseItem.model_validate({
        "license_type": "- Sertifikat Standar",
        "license_status": "- Belum Terverifikasi",
        "remarks": "",
    })
    assert item.license_type == "Sertifikat Standar"
    assert item.license_status == "Belum Terverifikasi"
    assert item.remarks is None

    dash_only = LicenseItem.model_validate({"remarks": "-"})
    assert dash_only.remarks is None

    real_remark = LicenseItem.model_validate({
        "remarks": "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 hari kerja"
    })
    assert real_remark.remarks == "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 hari kerja"


def test_field_item_multiple_licenses():
    field = FieldItem.model_validate({
        "no": "39",
        "field_code": "46206",
        "field_title": "Perdagangan Besar Hasil Perikanan",
        "licenses": [
            {"license_type": "NIB", "license_status": "Terbit", "remarks": "-"},
            {
                "license_type": "Sertifikat Standar",
                "license_status": "Belum Terverifikasi",
                "remarks": "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 hari kerja",
            },
        ],
    })
    assert field.licenses is not None
    assert len(field.licenses) == 2
    assert field.licenses[0].license_type == "NIB"
    assert field.licenses[0].remarks is None
    assert field.licenses[1].license_status == "Belum Terverifikasi"
    assert field.licenses[1].remarks == "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 hari kerja"


def test_taxable_entrepreneur_schema_validation():
    data = {
        "letter_number": "S-47PKP/WPJ.05/KP.1003/2015",
        "tax_office_region": "KANTOR WILAYAH DJP JAKARTA BARAT",
        "tax_office": "KPP PRATAMA JAKARTA KEBON JERUK DUA",
        "tax_office_address": "JL. K.S. TUBUN 10, JAKARTA BARAT",
        "tax_number": "01.329.904.5-039.000",
        "taxpayer_name": "PT. RAMCOMAS MANDIRI",
        "business_fields": [
            {"code": "71100", "title": "JASA ARSITEKTUR DAN TEKNIK SIPIL SERTA KONSULTASI TEKNIS YBDI"}
        ],
        "address": "JL.KEDOYA ANGSANA BLOK B II NO.25, KEDOYA SELATAN KEBON JERUK, JAKARTA BARAT DKI JAKARTA",
        "trade_name": "-",
        "tax_obligation": "PPN",
        "confirmed_since": "21 Maret 1992",
        "issued_place": "Jakarta Barat",
        "issued_date": "17 April 2015",
        "signing_official_title": "a.n. Kepala Kantor Kepala Seksi Pelayanan",
        "signing_official_name": "MUNAWAM",
        "signing_official_number": "NIP.196005151981031001",
    }
    model = TaxableEntrepreneurSchema.model_validate(data)
    assert model.letter_number == "S-47PKP/WPJ.05/KP.1003/2015"
    assert model.tax_number == "01.329.904.5-039.000"
    assert model.taxpayer_name == "PT. RAMCOMAS MANDIRI"
    assert model.business_fields is not None
    assert len(model.business_fields) == 1
    assert model.business_fields[0].code == "71100"
    assert model.business_fields[0].title == "JASA ARSITEKTUR DAN TEKNIK SIPIL SERTA KONSULTASI TEKNIS YBDI"
    assert model.trade_name is None
    assert model.tax_obligation == "PPN"
    assert model.confirmed_since == "1992-03-21"
    assert model.issued_date == "2015-04-17"
    assert model.signing_official_number == "196005151981031001"


def test_taxable_entrepreneur_document_schema_and_prompts():
    doc = TaxableEntrepreneurDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "tax_number" in schema["properties"]
    assert "letter_number" in schema["properties"]
    assert "business_fields" in schema["properties"]
    assert "tax_obligation" in schema["properties"]

    sys_prompt = doc.build_system_prompt()
    assert "PKP" in sys_prompt
    assert "Extraction Rules:" in sys_prompt

    ocr_sample = (
        "SURAT PENGUKUHAN PENGUSAHA KENA PAJAK\n"
        "S-47PKP/WPJ.05/KP.1003/2015\n"
    )
    user_prompt = doc.build_user_prompt(ocr_sample)
    assert "Extract Indonesian SPPKP" in user_prompt
    assert "S-47PKP/WPJ.05/KP.1003/2015" in user_prompt


def test_taxable_entrepreneur_string_parser():
    raw_ocr = """
    KEMENTERIAN KEUANGAN REPUBLIK INDONESIA
    DIREKTORAT JENDERAL PAJAK
    KANTOR WILAYAH DJP JAKARTA BARAT
    KPP PRATAMA JAKARTA KEBON JERUK DUA
    JL. K.S. TUBUN 10, JAKARTA BARAT
    TELEPON 021 5643627-29 FAKSIMILE 021-6655220 SITUS www.pajak.go.id
    EMAIL pengaduan@pajak.go.id

    SURAT PENGUKUHAN PENGUSAHA KENA PAJAK
    S-47PKP/WPJ.05/KP.1003/2015

    1. Nomor Pokok Wajib Pajak : 01.329.904.5-039.000
    2. Nama : PT. RAMCOMAS MANDIRI

    3. Klasifikasi Lapangan Usaha : 71100 - JASA ARSITEKTUR DAN TEKNIK SIPIL SERTA
    KONSULTASI TEKNIS YBDI
    4. Alamat : JL.KEDOYA ANGSANA BLOK B II NO.25
    KEDOYA SELATAN KEBON JERUK
    JAKARTA BARAT DKI JAKARTA

    5. Merk Dagang/Usaha : -
    6. Kewajiban Pajak : [X] PPN [ ] PPnBM

    Telah dikukuhkan sebagai Pengusaha Kena Pajak terhitung sejak 21 Maret 1992.

    Jakarta Barat, 17 April 2015
    a.n. Kepala Kantor
    Kepala Seksi Pelayanan,

    MUNAWAM
    NIP.196005151981031001
    """
    doc = TaxableEntrepreneurDocument()
    parsed = doc.parse_string(raw_ocr)
    assert isinstance(parsed, TaxableEntrepreneurSchema)
    assert parsed.letter_number == "S-47PKP/WPJ.05/KP.1003/2015"
    assert parsed.tax_office_region == "KANTOR WILAYAH DJP JAKARTA BARAT"
    assert parsed.tax_office == "KPP PRATAMA JAKARTA KEBON JERUK DUA"
    assert parsed.tax_office_address == "JL. K.S. TUBUN 10, JAKARTA BARAT"
    assert parsed.tax_number == "01.329.904.5-039.000"
    assert parsed.taxpayer_name == "PT. RAMCOMAS MANDIRI"
    assert parsed.business_fields is not None
    assert len(parsed.business_fields) == 1
    assert parsed.business_fields[0].code == "71100"
    assert parsed.business_fields[0].title == "JASA ARSITEKTUR DAN TEKNIK SIPIL SERTA KONSULTASI TEKNIS YBDI"
    assert parsed.address == "JL.KEDOYA ANGSANA BLOK B II NO.25, KEDOYA SELATAN KEBON JERUK, JAKARTA BARAT DKI JAKARTA"
    assert parsed.trade_name is None
    assert parsed.tax_obligation == "PPN"
    assert parsed.confirmed_since == "1992-03-21"
    assert parsed.issued_place == "Jakarta Barat"
    assert parsed.issued_date == "2015-04-17"
    assert parsed.signing_official_title == "a.n. Kepala Kantor Kepala Seksi Pelayanan"
    assert parsed.signing_official_name == "MUNAWAM"
    assert parsed.signing_official_number == "196005151981031001"


def test_taxable_entrepreneur_string_parser_direct():
    parsed = TaxableEntrepreneurStringParser.parse(
        "1. Nomor Pokok Wajib Pajak : 01.329.904.5-039.000\n2. Nama : PT. RAMCOMAS MANDIRI"
    )
    assert parsed.tax_number == "01.329.904.5-039.000"
    assert parsed.taxpayer_name == "PT. RAMCOMAS MANDIRI"
