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
from src.domain.documents.identity_stay import IdentityStayDocument, IdentityStaySchema
from src.domain.documents.certificate_local_value import CertificateLocalValueDocument, CertificateLocalValueSchema
from src.domain.documents.bank_account_information import BankAccountInformationDocument, BankAccountInformationSchema
from src.domain.documents.certificate_education import CertificateEducationDocument, CertificateEducationSchema


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
    assert "identity_stay" in slugs
    assert "certificate_local_value" in slugs
    assert "bank_account_information" in slugs
    assert "certificate_education" in slugs
    assert "education_diploma" not in slugs
    assert "limited_stay_permit" not in slugs
    assert "domestic_content_certificate" not in slugs


def test_certificate_education_schema_and_prompt():
    doc = CertificateEducationDocument()
    schema = doc.get_json_schema()
    properties = schema["properties"]
    assert list(properties) == [
        "number", "student_name", "student_number", "student_major",
        "education_institution", "education_address", "birth_place", "birth_date",
        "enroll_level", "enroll_date", "enroll_credit", "enroll_grade",
        "issued_place", "issued_date", "courses",
    ]
    assert set(schema["$defs"]["AcademicCourse"]["properties"]) == {"code", "name", "credits", "grade", "semester"}
    prompt = doc.build_system_prompt()
    assert all(field in prompt for field in properties)
    assert "side-by-side" in prompt and "YYYY-MM-DD" in prompt
    assert "```text\nNama: RUDI HARTONO\n```" in doc.build_user_prompt("Nama: RUDI HARTONO")


def test_certificate_education_schema_normalization():
    model = CertificateEducationSchema.model_validate({
        "number": "No. Seri: 00123/2021",
        "student_name": "Nama Mahasiswa: Rudi Hartono",
        "student_number": "NIM: 00123456",
        "student_major": "Program Studi: Teknik Mesin",
        "education_institution": "Lembaga Pendidikan: Politeknik Negeri Bandung",
        "education_address": "Alamat Fakultas: Jalan Grafika 2, Yogyakarta 55281",
        "birth_place": "Bandung, 3 Desember 1995",
        "birth_date": "Bandung, 3 Desember 1995",
        "enroll_level": "Program Pendidikan: Diploma III",
        "enroll_date": "Tanggal Masuk: 1 September 2010",
        "enroll_credit": "Jumlah SKS: 110",
        "enroll_grade": "IPK: 3,36",
        "issued_date": "Issued Date: July 30, 2021",
        "courses": [{"code": "TM101", "name": "Kalkulus", "credits": "2", "grade": "3,5", "semester": "I"}],
    })
    assert model.number == "00123/2021"
    assert model.student_name == "Rudi Hartono"
    assert model.student_number == "00123456"
    assert model.student_major == "Teknik Mesin"
    assert model.education_address == "Jalan Grafika 2, Yogyakarta 55281"
    assert model.birth_place == "Bandung"
    assert model.birth_date == "1995-12-03"
    assert model.enroll_level == "D3"
    assert model.enroll_date == "2010-09-01"
    assert model.enroll_credit == "110"
    assert model.enroll_grade == 3.36
    assert model.issued_date == "2021-07-30"
    assert model.courses and model.courses[0].semester == "I"
    assert model.courses[0].credits == 2
    assert model.courses[0].grade == 3.5
    assert '"enroll_grade":3.36' in model.model_dump_json()
    assert '"credits":2.0' in model.model_dump_json()
    assert '"grade":3.5' in model.model_dump_json()


def test_certificate_education_numeric_fields():
    model = CertificateEducationSchema.model_validate({
        "enroll_grade": 4,
        "courses": [
            {"credits": 2.5, "grade": 85},
            {"credits": "SKS: 2", "grade": "Grade: 3,25"},
            {"credits": "-", "grade": "B+"},
        ],
    })
    assert model.enroll_grade == 4
    assert model.courses and model.courses[0].credits == 2.5
    assert model.courses[0].grade == 85
    assert model.courses[1].credits == 2
    assert model.courses[1].grade == 3.25
    assert model.courses[2].credits is None
    assert model.courses[2].grade is None
    assert CertificateEducationSchema.model_validate({"enroll_grade": "3,22 (tiga koma dua dua)"}).enroll_grade == 3.22
    assert CertificateEducationSchema.model_validate({"enroll_grade": True}).enroll_grade is None
    assert CertificateEducationSchema.model_validate({"enroll_grade": float("inf")}).enroll_grade is None


def test_certificate_education_transcript_parser():
    parsed = CertificateEducationDocument().parse_string("""
    UNIVERSITAS SUMATERA UTARA
    FAKULTAS KEDOKTERAN
    Jalan dr. T. Mansur No. 5, Kampus USU Medan 20155
    TRANSKRIP AKADEMIK PROGRAM PENDIDIKAN PROFESI DOKTER
    Nama (Name) : RUDI HARTONO
    No. Seri : 001234
    Nomor Induk Mahasiswa : 060100094
    Tempat/Tanggal Lahir : Pancur Batu / 5 April 1988
    Mulai Pendidikan : 1 Februari 2010
    Tanggal Kelulusan : 12 Desember 2011
    Indeks Prestasi Kumulatif (IPK) : 3,18
    Jumlah SKS : 146
    Medan, 25 Februari 2012
    """)
    assert parsed.number == "001234"
    assert parsed.student_name == "RUDI HARTONO"
    assert parsed.student_number == "060100094"
    assert parsed.education_institution == "UNIVERSITAS SUMATERA UTARA"
    assert parsed.education_address == "Jalan dr. T. Mansur No. 5, Kampus USU Medan 20155"
    assert parsed.student_major == "FAKULTAS KEDOKTERAN"
    assert parsed.enroll_level == "Profesi Dokter"
    assert parsed.birth_place == "Pancur Batu"
    assert parsed.birth_date == "1988-04-05"
    assert parsed.enroll_date == "2010-02-01"
    assert parsed.enroll_credit == "146"
    assert parsed.enroll_grade == 3.18
    assert parsed.issued_place == "Medan"
    assert parsed.issued_date == "2012-02-25"
    assert parsed.courses is None


def test_certificate_education_english_enclosure_parser():
    parsed = CertificateEducationDocument().parse_string("""
    STATE UNIVERSITY OF MAKASSAR
    ENCLOSURE OF CERTIFICATE
    Name : DARY SETIAWAN
    Place/Date of Birth : Polewali, August 17, 1998
    Study Program : Geography Education
    ID : 001615442008
    Number : 872022021000837
    Faculty : Mathematics and Science
    Program : Strata Satu (Bachelor)
    Graduated in July 28, 2021
    GPA : 3.53
    Total of Credits : 148
    Makassar, July 30, 2021
    """)
    assert parsed.student_name == "DARY SETIAWAN"
    assert parsed.student_major == "Geography Education"
    assert parsed.enroll_level == "S1"
    assert parsed.birth_place == "Polewali"
    assert parsed.birth_date == "1998-08-17"
    assert parsed.enroll_date is None
    assert parsed.issued_date == "2021-07-30"
    assert parsed.student_number == "001615442008"
    assert parsed.number == "872022021000837"
    assert parsed.enroll_credit == "148"
    assert parsed.education_address is None


def test_bank_account_information_schema_and_prompt():
    doc = BankAccountInformationDocument()
    properties = doc.get_json_schema()["properties"]
    assert set(properties) == {"bank_name", "bank_branch", "account_number", "account_holder_name", "account_type"}
    prompt = doc.build_system_prompt()
    assert all(field in prompt for field in properties)
    assert "balances" in prompt and "transaction tables" in prompt
    assert "```text\nNo. Rekening : 00001-2345\n```" in doc.build_user_prompt("No. Rekening : 00001-2345")
    model = BankAccountInformationSchema.model_validate({
        "account_number": "No. Rekening : 00001-2345",
        "account_holder_name": "Atas Nama : PT CONTOH MAKMUR",
        "account_type": "Jenis Rekening : Tabungan",
    })
    assert model.account_number == "00001-2345"
    assert model.account_holder_name == "PT CONTOH MAKMUR"
    assert model.account_type == "Tabungan"
    assert BankAccountInformationSchema.model_validate({"bank_branch": "Cabang: KCP Jakarta Cibis Nine"}).bank_branch == "KCP Jakarta Cibis Nine"
    assert BankAccountInformationSchema.model_validate({"bank_branch": "KCP SUNGKONO"}).bank_branch == "KCP SUNGKONO"
    assert BankAccountInformationSchema.model_validate({"account_number": "0000****1234"}).account_number is None


def test_bank_account_information_passbook_parser():
    raw_text = """
    Tabungan BRI Simpedes
    Kantor BANK BRI : 3868 UNIT MENES LABUAN
    CIF : RG91491
    No. Rekening : 3868-01-000123-45-6
    Nama : BUDI SANTOSO
    No. Seri : 12345678
    """
    parsed = BankAccountInformationDocument().parse_string(raw_text)
    assert parsed.bank_name == "Bank Rakyat Indonesia"
    assert parsed.bank_branch == "3868 UNIT MENES LABUAN"
    assert parsed.account_number == "3868-01-000123-45-6"
    assert parsed.account_holder_name == "BUDI SANTOSO"
    assert parsed.account_type == "Simpedes"
    assert "customer_id" not in parsed.model_dump()
    assert "passbook_serial_number" not in parsed.model_dump()


def test_bank_account_information_unlabeled_bca_passbook_parser():
    parsed = BankAccountInformationDocument().parse_string("""
    KCP SUNGKONO
    0001234567
    JANE DOE
    16/06/2020 BCA SUNGKONO
    BANK CENTRAL ASIA
    """)
    assert parsed.bank_name == "Bank Central Asia"
    assert parsed.bank_branch == "KCP SUNGKONO"
    assert parsed.account_number == "0001234567"
    assert parsed.account_holder_name == "JANE DOE"


def test_bank_account_information_statement_and_letter_parser():
    statement = BankAccountInformationDocument().parse_string("""
    mandiri
    Rekening Koran (Account Statement)
    Account No : 1270000001234 - PT CONTOH JAYA
    Currency : IDR
    Branch : KCP Jakarta Cibis Nine
    Opening Balance : 27,939,044.12
    Closing Balance : 17,543,779.44
    """)
    assert statement.bank_name == "Bank Mandiri"
    assert statement.bank_branch == "KCP Jakarta Cibis Nine"
    assert statement.account_number == "1270000001234"
    assert statement.account_holder_name == "PT CONTOH JAYA"
    assert "opening_balance" not in statement.model_dump()
    assert "transactions" not in statement.model_dump()

    letter = BankAccountInformationDocument().parse_string("""
    PT CONTOH MAKMUR
    Untuk Pembayaran dapat di transfer ke Rekening:
    Bank Danamon, Cabang Puri Kencana
    ACC. No. : 4101234
    Atas Nama : PT CONTOH MAKMUR
    """)
    assert letter.bank_name == "Bank Danamon"
    assert letter.bank_branch == "Puri Kencana"
    assert letter.account_number == "4101234"
    assert letter.account_holder_name == "PT CONTOH MAKMUR"


def test_certificate_local_value_schema_and_prompt():
    doc = CertificateLocalValueDocument()
    properties = doc.get_json_schema()["properties"]
    assert set(properties) == set(CertificateLocalValueSchema.model_fields)
    prompt = doc.build_system_prompt()
    assert "TKDN" in prompt
    assert all(field in prompt for field in properties)
    assert "Terlampir" in prompt and "YYYY-MM-DD" in prompt
    assert "```text\nNilai TKDN : 96,72%\n```" in doc.build_user_prompt("Nilai TKDN : 96,72%")


def test_certificate_local_value_schema_normalization():
    model = CertificateLocalValueSchema.model_validate({
        "product_name": "Jenis Produk : Basket Ecenggondok",
        "local_value": "Nilai TKDN : 96,72%",
        "product_standard": "Standard Produk : -",
        "brand": "Merk : -",
        "company_tax_number": "NPWP : 82.934.355.7-543.000",
        "industry": "Bidang Usaha : Industri Barang Bangunan Dari Kayu (KBLI: 16221)",
        "issued_date": "Issued Date : 28 Juli 2021",
    })
    assert model.product_name == "Basket Ecenggondok"
    assert model.local_value == 96.72
    assert '"local_value":96.72' in model.model_dump_json()
    assert model.product_standard is None
    assert model.brand is None
    assert model.company_tax_number == "82.934.355.7-543.000"
    assert model.industry == "Industri Barang Bangunan Dari Kayu (KBLI: 16221)"
    assert model.issued_date == "2021-07-28"
    assert CertificateLocalValueSchema.model_validate({"local_value": "Nilai TKDN : (Terlampir)"}).local_value is None
    assert CertificateLocalValueSchema.model_validate({"local_value": "Nilai TKDN : 96.72"}).local_value == 96.72
    assert CertificateLocalValueSchema.model_validate({"local_value": 96.72}).local_value == 96.72
    assert CertificateLocalValueSchema.model_validate({"validity_years": "berlaku 2 tahun"}).validity_years == 2
    assert CertificateLocalValueSchema.model_validate({"validity_years": 3}).validity_years == 3
    assert CertificateLocalValueSchema.model_validate({"validity_years": "-"}).validity_years is None


def test_certificate_local_value_string_parser_legacy_title():
    raw_text = """
    TANDA SAH CAPAIAN TINGKAT KOMPONEN DALAM NEGERI
    No. TKDN : 12-018
    Jenis Produk : Basket Ecenggondok
    Tipe : Ecenggondok
    Spesifikasi : 38 x 27 x 19 cm
    Kode HS : 44209010
    Merk : -
    Nilai TKDN : 96,72%
    Terbilang : Sembilan puluh enam koma tujuh dua persen
    Standard Produk : -
    Sertifikat Produk : -
    No. Laporan : LPA-3426/PK-3506/PTKDN.DIPA-INFRAS/VII/21
    yang telah ditandasahkan oleh Kementerian Perindustrian dan berlaku 3 tahun terhitung sejak tanggal tanda sah,
    diberikan kepada:
    Nama Perusahaan : CV. Contoh Indonesia
    Alamat : Jl. Contoh No. 7, Bantul
    D.I. Yogyakarta
    NPWP : 82.934.355.7-543.000
    Bidang Usaha : Industri Barang Bangunan Dari Kayu (KBLI: 16221)
    No. Tanda Sah : 4623/SJ-IND.8/TKDN/7/2021
    Jakarta, 28 Juli 2021
    Kepala Pusat Peningkatan Penggunaan Produk Dalam Negeri
    Nila Kumalasari
    #23361
    """
    parsed = CertificateLocalValueDocument().parse_string(raw_text)
    assert "certificate_title" not in parsed.model_dump()
    assert "tkdn_registration_number" not in parsed.model_dump()
    assert parsed.product_name == "Basket Ecenggondok"
    assert parsed.product_type == "Ecenggondok"
    assert parsed.product_specification == "38 x 27 x 19 cm"
    assert parsed.hs_code == "44209010"
    assert parsed.brand is None
    assert parsed.local_value == 96.72
    assert "tkdn_in_words" not in parsed.model_dump()
    assert parsed.product_standard is None
    assert parsed.product_certificate is None
    assert parsed.report_number == "LPA-3426/PK-3506/PTKDN.DIPA-INFRAS/VII/21"
    assert parsed.validity_years == 3
    assert '"validity_years":3' in parsed.model_dump_json()
    assert parsed.company_name == "CV. Contoh Indonesia"
    assert parsed.company_address == "Jl. Contoh No. 7, Bantul D.I. Yogyakarta"
    assert parsed.company_tax_number == "82.934.355.7-543.000"
    assert parsed.industry == "Industri Barang Bangunan Dari Kayu (KBLI: 16221)"
    assert parsed.certificate_number == "4623/SJ-IND.8/TKDN/7/2021"
    assert parsed.issued_place == "Jakarta"
    assert parsed.issued_date == "2021-07-28"
    assert parsed.signing_official_title == "Kepala Pusat Peningkatan Penggunaan Produk Dalam Negeri"
    assert parsed.signing_official_name == "Nila Kumalasari"
    assert parsed.qr_reference == "23361"


def test_certificate_local_value_string_parser_new_title_and_attachment():
    raw_text = """
    SERTIFIKAT TINGKAT KOMPONEN DALAM NEGERI
    Jenis Produk : Box Panel
    Tipe : -
    Spesifikasi : Ukuran: 200x200x120mm s.d.
    2000x3200x800mm
    Kode HS : 85371011
    Merk : IONEE PROTONE
    Nilai TKDN : Terlampir
    Terbilang : Lima puluh lima koma satu dua persen
    Standar Produk : -
    Sertifikat Produk : -
    No. Laporan : TKDN - 1611 - 2505797
    berlaku 3 tahun terhitung sejak tanggal tanda sah,
    Nama Perusahaan : PT Contoh Jaya Sentosa
    Alamat : Dusun Kebonagung RT.002 RW. 003
    Keboagung, Puri, Kabupaten Mojokerto
    NPWP : 50.559.741.9-602.000
    Jenis Industri : Industri Peralatan Listrik Lainnya (KBLI: 27900)
    No. Tanda Sah : 16335/SJ-IND.8/E-TKDN/10/2025
    Jakarta, 23 Oktober 2025
    Kepala Pusat Peningkatan Penggunaan Produk Dalam Negeri
    Heru Kustanto
    """
    parsed = CertificateLocalValueDocument().parse_string(raw_text)
    assert parsed.product_specification == "Ukuran: 200x200x120mm s.d. 2000x3200x800mm"
    assert parsed.product_type is None
    assert parsed.local_value is None
    assert parsed.industry == "Industri Peralatan Listrik Lainnya (KBLI: 27900)"
    assert parsed.issued_date == "2025-10-23"
    assert parsed.qr_reference is None


def test_identity_stay_schema_and_prompt():
    doc = IdentityStayDocument()
    properties = doc.get_json_schema()["properties"]
    assert set(properties) == set(IdentityStaySchema.model_fields)
    prompt = doc.build_system_prompt()
    assert "KITAS" in prompt
    assert all(field in prompt for field in properties)
    assert "null" in prompt and "YYYY-MM-DD" in prompt
    assert "```text\nNIORA : AB12345678\n```" in doc.build_user_prompt("NIORA : AB12345678")


def test_identity_stay_schema_normalization():
    model = IdentityStaySchema.model_validate({
        "niora": "NIORA : AB12345678",
        "permit_number": "Permit Number : 2C21AB1234YZ",
        "birth_place": "Place / Date of Birth : SINGAPORE / 04-03-1984",
        "birth_date": "Place / Date of Birth : SINGAPORE / 04-03-1984",
        "permit_expiry_date": "Stay/Multiple Entries Permit Expiry : 18-12-2020",
        "passport_expiry_date": "Passport Expiry : 11-01-2028",
        "issued_date": "Issued Date : 26 Januari 2024",
        "guarantor_name": "-",
    })
    assert model.niora == "AB12345678"
    assert model.permit_number == "2C21AB1234YZ"
    assert model.birth_place == "SINGAPORE"
    assert model.birth_date == "1984-03-04"
    assert model.permit_expiry_date == "2020-12-18"
    assert model.passport_expiry_date == "2028-01-11"
    assert model.issued_date == "2024-01-26"
    assert model.guarantor_name is None


def test_identity_stay_string_parser():
    raw_text = """
    KANIM KELAS I KHUSUS NON TPI JAKARTA SELATAN
    JL. CONTOH NO. 10 JAKARTA SELATAN
    IZIN TINGGAL TERBATAS ELEKTRONIK
    NIORA : AB12345678
    Permit Number : 2C21AB1234YZ
    Stay/Multiple Entries Permit Expiry : 18-12-2020
    Stay Permit Index : 1B
    Full Name : JANE DOE
    Place / Date of Birth : SINGAPORE / 04-03-1984
    Passport Number : P1234567
    Passport Expiry : 11-01-2028
    Nationality : SINGAPURA
    Gender : FEMALE
    Address : JL. CONTOH NO. 10 RT 001 RW 002
    KEBAYORAN LAMA
    Occupation : INVESTOR
    Status : INVESTMENT
    Guarantor Name : PT CONTOH INDONESIA
    Jakarta, 26-01-2024
    Head of Kelas I Khusus Non TPI Jakarta Selatan Immigration Office.
    """
    parsed = IdentityStayDocument().parse_string(raw_text)
    assert parsed.issuing_office == "KANIM KELAS I KHUSUS NON TPI JAKARTA SELATAN"
    assert parsed.issuing_office_address == "JL. CONTOH NO. 10 JAKARTA SELATAN"
    assert parsed.niora == "AB12345678"
    assert parsed.permit_number == "2C21AB1234YZ"
    assert parsed.permit_expiry_date == "2020-12-18"
    assert parsed.permit_index == "1B"
    assert parsed.full_name == "JANE DOE"
    assert parsed.birth_place == "SINGAPORE"
    assert parsed.birth_date == "1984-03-04"
    assert parsed.passport_number == "P1234567"
    assert parsed.passport_expiry_date == "2028-01-11"
    assert parsed.nationality == "SINGAPURA"
    assert parsed.gender == "FEMALE"
    assert parsed.address == "JL. CONTOH NO. 10 RT 001 RW 002 KEBAYORAN LAMA"
    assert parsed.occupation == "INVESTOR"
    assert parsed.status == "INVESTMENT"
    assert parsed.guarantor_name == "PT CONTOH INDONESIA"
    assert parsed.issued_place == "Jakarta"
    assert parsed.issued_date == "2024-01-26"
    assert parsed.signing_official_title.startswith("Head of Kelas I")


def test_identity_stay_obscured_values_remain_null():
    parsed = IdentityStayDocument().parse_string("NIORA :\nPermit Number :\nGuarantor Name : -\nPassport Expiry : -")
    assert parsed.niora is None
    assert parsed.permit_number is None
    assert parsed.guarantor_name is None
    assert parsed.passport_expiry_date is None


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
    assert model.deed_type == "Pendirian"
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
    # 'deed_type' is detected from the PENDIRIAN/PERUBAHAN keyword in the deed's
    # own title, directly above its opening formula.
    assert parsed.deed_type == "Pendirian"
    # 'notary_address' varies too much by notary template for the string parser
    # to extract reliably - left for the LLM-based engines.
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


def test_business_deed_string_parser_detects_perubahan_over_stale_pendirian_recital():
    # A deed's own title reads PERUBAHAN, but its recital text (appearing later,
    # after the opening formula) mentions the company's original 'akta
    # pendirian' for background - that must not override the deed's own type.
    raw_text = (
        "PERNYATAAN KEPUTUSAN PEMEGANG SAHAM\n"
        "PERUBAHAN ANGGARAN DASAR\n"
        "PT CONTOH SEJAHTERA ABADI\n"
        "Nomor 9.\n"
        "Pada hari ini, Rabu, tanggal 05-06-2023 (lima Juni dua ribu dua puluh "
        "tiga).\n"
        "Berhadapan dengan saya, RINA WIJAYA, Sarjana Hukum, Notaris di Jakarta,\n"
        "yang anggaran dasarnya dimuat dalam akta pendirian nomor 10 tanggal "
        "01-01-2010.\n"
    )
    parsed = BusinessDeedStringParser.parse(raw_text)
    assert parsed.deed_type == "Perubahan"
    assert parsed.deed_number == "9"


def test_business_deed_schema_deed_type_rejects_unrecognized_text():
    model = BusinessDeedSchema.model_validate({"deed_type": "Akta Kuasa Menjual"})
    assert model.deed_type is None


def test_legal_decision_standalone_validation():
    sk = SKKemenkumham.model_validate({"number": "NOMOR: AHU-01173.AH.01.02.Tahun 2010", "date": "-"})
    assert sk.number == "AHU-01173.AH.01.02.Tahun 2010"
