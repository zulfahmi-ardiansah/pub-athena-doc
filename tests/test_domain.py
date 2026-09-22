from src.domain.registry import get_document_registry
from src.domain.documents.identity_card.schema import IdentityCardSchema
from src.domain.documents.identity_card import IdentityCardDocument
from src.domain.documents.tax_number.schema import TaxNumberSchema
from src.domain.documents.tax_number import TaxNumberDocument
from src.domain.documents.business_number.schema import BusinessNumberSchema, FieldItem, LicenseItem
from src.domain.documents.business_number import (
    BusinessIdentificationNumberDocument,
)
from src.domain.documents.tax_entity.schema import TaxEntitySchema
from src.domain.documents.tax_entity import (
    TaxEntityDocument,
    TaxEntityStringParser,
)
from src.domain.documents.identity_passport.schema import IdentityPassportSchema
from src.domain.documents.identity_passport import IdentityPassportDocument, IdentityPassportStringParser
from src.domain.documents.business_deed.schema import BusinessDeedSchema, SKKemenkumham
from src.domain.documents.business_deed import BusinessDeedDocument, BusinessDeedStringParser


def test_document_registry():
    registry = get_document_registry()
    docs = registry.list_documents()
    slugs = [d["slug"] for d in docs]
    assert "identity_card" in slugs
    assert "tax_number" in slugs
    assert "business_identification_number" in slugs
    assert "tax_entity" in slugs
    assert "identity_passport" in slugs
    assert "business_deed" in slugs


def test_identity_card_schema_validation():
    data = {
        "id_number": "3171-0101-0190-0001",
        "name": "JOHN DOE",
        "gender": "LAKI-LAKI",
        "expiry_date": "SEUMUR HIDUP"
    }
    model = IdentityCardSchema.model_validate(data)
    assert model.id_number == "3171010101900001"
    assert model.name == "JOHN DOE"
    assert model.nationality == "WNI"


def test_tax_number_schema_validation():
    data = {
        "tax_number": "01.234.567.8-901.000",
        "name": "PT CONTOH MAKMUR",
        "tax_office": "KPP PRATAMA JAKARTA TANAH ABANG",
        "tax_office_address": "JL KH MAS MANSYUR NO. 71"
    }
    model = TaxNumberSchema.model_validate(data)
    assert model.tax_number == "01.234.567.8-901.000"
    assert model.name == "PT CONTOH MAKMUR"
    assert model.tax_office == "KPP PRATAMA JAKARTA TANAH ABANG"
    assert model.tax_office_address == "JL KH MAS MANSYUR NO. 71"


def test_identity_card_jokowi_sample_validation():
    data = {
        "province": "PROVINSI DKI JAKARTA",
        "city": "JAKARTA PUSAT",
        "id_number": "NIK : 3372052106610006",
        "name": "IR JOKO WIDODO",
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
        "expiry_date": "21-06-2017"
    }
    model = IdentityCardSchema.model_validate(data)
    assert model.province == "DKI JAKARTA"
    assert model.city == "JAKARTA PUSAT"
    assert model.id_number == "3372052106610006"
    assert model.name == "IR JOKO WIDODO"
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
    assert model.expiry_date == "2017-06-21"


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
    assert parsed.name == "BUDI SANTOSO"
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
    assert parsed.expiry_date == "SEUMUR HIDUP"


def test_tax_number_document_schema_and_prompts():
    doc = TaxNumberDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "tax_number" in schema["properties"]
    assert "name" in schema["properties"]
    assert "tax_office" in schema["properties"]
    assert "tax_office_address" in schema["properties"]

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
    assert parsed.name == "PT CONTOH MAKMUR"
    assert parsed.tax_office == "KPP MADYA GRESIK"
    assert parsed.tax_office_address == "JL DR WAHIDIN SUDIROHUSODO 700 GRESIK"
    assert parsed.registration_date == "2022-01-01"


def test_business_identification_number_schema_validation():
    data = {
        "number": "1234567890123",
        "name": "PT CONTOH SEJAHTERA ABADI",
        "address": "JL. JENDERAL SUDIRMAN KAV. 10, KOTA ADM. JAKARTA SELATAN",
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
                "code": "46206",
                "title": "Perdagangan Besar Hasil Perikanan",
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
    assert model.fields[0].code == "46206"
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
    assert "address" in schema["properties"]
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
    assert parsed.address == "JL. JENDERAL SUDIRMAN KAV. 10, Kota Adm. Jakarta Selatan"
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
        "code": "46206",
        "title": "Perdagangan Besar Hasil Perikanan",
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


def test_tax_entity_schema_validation():
    data = {
        "letter_number": "S-47PKP/WPJ.05/KP.1003/2015",
        "tax_office_region": "KANTOR WILAYAH DJP JAKARTA BARAT",
        "tax_office": "KPP PRATAMA JAKARTA KEBON JERUK DUA",
        "tax_office_address": "JL. K.S. TUBUN 10, JAKARTA BARAT",
        "tax_number": "01.329.904.5-039.000",
        "name": "PT. RAMCOMAS MANDIRI",
        "fields": [
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
    model = TaxEntitySchema.model_validate(data)
    assert model.letter_number == "S-47PKP/WPJ.05/KP.1003/2015"
    assert model.tax_number == "01.329.904.5-039.000"
    assert model.name == "PT. RAMCOMAS MANDIRI"
    assert model.fields is not None
    assert len(model.fields) == 1
    assert model.fields[0].code == "71100"
    assert model.fields[0].title == "JASA ARSITEKTUR DAN TEKNIK SIPIL SERTA KONSULTASI TEKNIS YBDI"
    assert model.trade_name is None
    assert model.tax_obligation == "PPN"
    assert model.confirmed_since == "1992-03-21"
    assert model.issued_date == "2015-04-17"
    assert model.signing_official_number == "196005151981031001"


def test_tax_entity_document_schema_and_prompts():
    doc = TaxEntityDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "tax_number" in schema["properties"]
    assert "letter_number" in schema["properties"]
    assert "fields" in schema["properties"]
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


def test_tax_entity_string_parser():
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
    doc = TaxEntityDocument()
    parsed = doc.parse_string(raw_ocr)
    assert isinstance(parsed, TaxEntitySchema)
    assert parsed.letter_number == "S-47PKP/WPJ.05/KP.1003/2015"
    assert parsed.tax_office_region == "KANTOR WILAYAH DJP JAKARTA BARAT"
    assert parsed.tax_office == "KPP PRATAMA JAKARTA KEBON JERUK DUA"
    assert parsed.tax_office_address == "JL. K.S. TUBUN 10, JAKARTA BARAT"
    assert parsed.tax_number == "01.329.904.5-039.000"
    assert parsed.name == "PT. RAMCOMAS MANDIRI"
    assert parsed.fields is not None
    assert len(parsed.fields) == 1
    assert parsed.fields[0].code == "71100"
    assert parsed.fields[0].title == "JASA ARSITEKTUR DAN TEKNIK SIPIL SERTA KONSULTASI TEKNIS YBDI"
    assert parsed.address == "JL.KEDOYA ANGSANA BLOK B II NO.25, KEDOYA SELATAN KEBON JERUK, JAKARTA BARAT DKI JAKARTA"
    assert parsed.trade_name is None
    assert parsed.tax_obligation == "PPN"
    assert parsed.confirmed_since == "1992-03-21"
    assert parsed.issued_place == "Jakarta Barat"
    assert parsed.issued_date == "2015-04-17"
    assert parsed.signing_official_title == "a.n. Kepala Kantor Kepala Seksi Pelayanan"
    assert parsed.signing_official_name == "MUNAWAM"
    assert parsed.signing_official_number == "196005151981031001"


def test_tax_entity_string_parser_direct():
    parsed = TaxEntityStringParser.parse(
        "1. Nomor Pokok Wajib Pajak : 01.329.904.5-039.000\n2. Nama : PT. RAMCOMAS MANDIRI"
    )
    assert parsed.tax_number == "01.329.904.5-039.000"
    assert parsed.name == "PT. RAMCOMAS MANDIRI"


def _synthetic_mrz(surname: str, given_names: str, country: str, passport_number: str,
                    nationality: str, dob_yymmdd: str, sex: str, expiry_yymmdd: str) -> tuple:
    name_field = f"{surname}<<{given_names}".replace(" ", "<")
    line1 = f"P<{country}{name_field}"
    line1 = line1 + "<" * (44 - len(line1))
    line2 = (
        f"{passport_number:<9}"[:9].replace(" ", "<")
        + "0"
        + nationality
        + dob_yymmdd
        + "0"
        + sex
        + expiry_yymmdd
        + "0"
        + "<" * 14
        + "0"
        + "0"
    )
    return line1, line2


def test_identity_passport_schema_validation():
    data = {
        "document_type": "P<",
        "issuing_country": "USA<",
        "surname": "TRAVELER",
        "given_names": "HAPPY",
        "passport_number": "E00007734",
        "nationality": "USA",
        "birth_date": "05 FEB 1990",
        "gender": "F",
        "birth_place": "WASHINGTON D.C., U.S.A.",
        "issued_date": "15 OCT 2020",
        "expiry_date": "14 OCT 2030",
        "issuing_authority": "UNITED STATES DEPARTMENT OF STATE",
        "mrz_line1": "p<usatraveler<<happy<<<<<<<<<<<<<<<<<<<<<<<<",
    }
    model = IdentityPassportSchema.model_validate(data)
    assert model.document_type == "P"
    assert model.issuing_country == "USA"
    assert model.surname == "TRAVELER"
    assert model.passport_number == "E00007734"
    assert model.birth_date == "1990-02-05"
    assert model.issued_date == "2020-10-15"
    assert model.expiry_date == "2030-10-14"
    assert model.mrz_line1 == "P<USATRAVELER<<HAPPY<<<<<<<<<<<<<<<<<<<<<<<<"


def test_identity_passport_document_schema_and_prompts():
    doc = IdentityPassportDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "mrz_line1" in schema["properties"]
    assert "mrz_line2" in schema["properties"]
    assert "passport_number" in schema["properties"]
    assert "issuing_country" in schema["properties"]

    sys_prompt = doc.build_system_prompt()
    assert "MRZ" in sys_prompt
    assert "Extraction Rules:" in sys_prompt

    user_prompt = doc.build_user_prompt("P<USATRAVELER<<HAPPY")
    assert "MRZ" in user_prompt
    assert "P<USATRAVELER<<HAPPY" in user_prompt


def test_identity_passport_string_parser_single_given_name():
    line1, line2 = _synthetic_mrz(
        surname="SMITH", given_names="JANE", country="EOL", passport_number="PP3000000",
        nationality="EOL", dob_yymmdd="810714", sex="F", expiry_yymmdd="221231",
    )
    raw_ocr = f"REPUBLIC OF EOLIE\n{line1}\n{line2}\n"
    doc = IdentityPassportDocument()
    parsed = doc.parse_string(raw_ocr)
    assert isinstance(parsed, IdentityPassportSchema)
    assert parsed.document_type == "P"
    assert parsed.issuing_country == "EOL"
    assert parsed.surname == "SMITH"
    assert parsed.given_names == "JANE"
    assert parsed.passport_number == "PP3000000"
    assert parsed.nationality == "EOL"
    assert parsed.birth_date == "1981-07-14"
    assert parsed.gender == "F"
    assert parsed.expiry_date == "2022-12-31"
    # VIZ-only fields aren't in the MRZ, so the string parser correctly leaves them unset
    assert parsed.birth_place is None
    assert parsed.issued_date is None
    assert parsed.issuing_authority is None


def test_identity_passport_string_parser_multi_part_name():
    line1, line2 = _synthetic_mrz(
        surname="DE BRUIJN", given_names="WILLEKE LISELOTTE", country="NLD", passport_number="SPECI2014",
        nationality="NLD", dob_yymmdd="650310", sex="F", expiry_yymmdd="240309",
    )
    parsed = IdentityPassportStringParser.parse(f"{line1}\n{line2}")
    assert parsed.surname == "DE BRUIJN"
    assert parsed.given_names == "WILLEKE LISELOTTE"
    assert parsed.nationality == "NLD"
    assert parsed.birth_date == "1965-03-10"
    assert parsed.expiry_date == "2024-03-09"


def test_identity_passport_string_parser_no_mrz_found():
    parsed = IdentityPassportStringParser.parse("just some random text with no MRZ lines in it")
    assert isinstance(parsed, IdentityPassportSchema)
    assert parsed.mrz_line1 is None
    assert parsed.mrz_line2 is None
    assert parsed.passport_number is None


def test_business_deed_schema_validation():
    data = {
        "deed_type": "= AKTA PENDIRIAN PERSEROAN TERBATAS =",
        "deed_number": "No. 2",
        "deed_date": "03 Agustus 2023",
        "notary_name": "CONTOH NOTARIS, S.H., M.Kn",
        "notary_address": "Alamat Jalan Contoh Nomor 1, Cianjur, Jawa Barat",
        "legal_decision": {
            "number": "Nomor : AHU-0028078.AH.01.02.TAHUN 2022",
            "issued_date": "19 April 2022",
        },
    }
    model = BusinessDeedSchema.model_validate(data)
    assert model.deed_type == "AKTA PENDIRIAN PERSEROAN TERBATAS"
    assert model.deed_number == "2"
    assert model.deed_date == "2023-08-03"
    assert model.notary_name == "CONTOH NOTARIS, S.H., M.Kn"
    assert model.notary_address == "Jalan Contoh Nomor 1, Cianjur, Jawa Barat"
    assert model.legal_decision is not None
    assert model.legal_decision.number == "AHU-0028078.AH.01.02.TAHUN 2022"
    assert model.legal_decision.issued_date == "2022-04-19"


def test_business_deed_document_schema_and_prompts():
    doc = BusinessDeedDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "deed_number" in schema["properties"]
    assert "notary_name" in schema["properties"]
    assert "legal_decision" in schema["properties"]

    sys_prompt = doc.build_system_prompt()
    assert "Kemenkumham" in sys_prompt
    assert "Extraction Rules:" in sys_prompt

    user_prompt = doc.build_user_prompt("Nomor 151.\nPada hari ini, Selasa, tanggal 19-4-2022")
    assert "Extract Indonesian business deed" in user_prompt
    assert "Nomor 151." in user_prompt


def test_business_deed_string_parser_bundled_akta_and_sk():
    # Reproduces the real quirks found against the actual sample filings: a soft
    # hyphen between 'Nomor : N.' and 'Pada hari ini', and a dashed underline
    # artifact splitting the notary's name across wrapped lines.
    raw_text = (
        "AKTA PENDIRIAN PERSEROAN TERBATAS\n"
        "PT CONTOH SEJAHTERA ABADI\n"
        "Nomor : 7.\xad\n"
        "-Pada hari ini, Senin, tanggal 10-01-2023 (sepuluh Januari dua ribu dua "
        "puluh tiga).\n"
        "Berhadapan dengan saya, BUDI\n"
        "--------\n"
        "SANTOSO, Sarjana Hukum, Magister Kenotariatan, Notaris di Kota Jakarta,\n"
        "\n"
        "KEPUTUSAN MENTERI HUKUM DAN HAK ASASI MANUSIA REPUBLIK INDONESIA\n"
        "NOMOR AHU-0099999.AH.01.02.TAHUN 2023\n"
        "TENTANG\n"
        "PERSETUJUAN PERUBAHAN ANGGARAN DASAR PERSEROAN TERBATAS\n"
        "PT CONTOH SEJAHTERA ABADI\n"
        "Ditetapkan di Jakarta, Tanggal 15 Januari 2023.\n"
    )
    parsed = BusinessDeedStringParser.parse(raw_text)
    assert isinstance(parsed, BusinessDeedSchema)
    assert parsed.deed_number == "7"
    assert parsed.deed_date == "2023-01-10"
    assert parsed.notary_name == "BUDI SANTOSO"
    assert parsed.legal_decision is not None
    assert parsed.legal_decision.number == "AHU-0099999.AH.01.02.TAHUN 2023"
    assert parsed.legal_decision.issued_date == "2023-01-15"
    # 'deed_type' and 'notary_address' vary too much by notary template for the
    # string parser to extract reliably - left for the LLM-based engines.
    assert parsed.deed_type is None
    assert parsed.notary_address is None


def test_business_deed_string_parser_ignores_unrelated_sk_reference():
    # A deed's own text can reference an unrelated SK number (e.g. the notary's
    # own appointment decree printed on the letterhead) - the parser must not
    # mistake that for the company's own confirming SK, which only comes from a
    # 'KEPUTUSAN MENTERI ... REPUBLIK INDONESIA' title block.
    raw_text = (
        "NOTARIS CONTOH NAMA, S.H., M.Kn\n"
        "SK Menteri Hukum dan Hak Asasi Manusia Republik Indonesia\n"
        "Nomor : AHU-111.AH.01.02-Tahun 2005\n"
        "AKTA PENDIRIAN PERSEROAN TERBATAS\n"
        "PT CONTOH LAINNYA\n"
    )
    parsed = BusinessDeedStringParser.parse(raw_text)
    assert parsed.legal_decision is None


def test_business_deed_string_parser_old_numbering_format():
    raw_text = (
        "KEPUTUSAN MENTERI KEHAKIMAN REPUBLIK INDONESIA\n"
        "NOMOR : C2-10671.HT.01.01.TH.88.-\n"
        "MENTERI KEHAKIMAN REPUBLIK INDONESIA,\n"
    )
    parsed = BusinessDeedStringParser.parse(raw_text)
    assert parsed.legal_decision is not None
    assert parsed.legal_decision.number == "C2-10671.HT.01.01.TH.88"


def test_legal_decision_standalone_validation():
    sk = SKKemenkumham.model_validate({"number": "NOMOR: AHU-01173.AH.01.02.Tahun 2010", "date": "-"})
    assert sk.number == "AHU-01173.AH.01.02.Tahun 2010"
