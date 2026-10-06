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
from src.domain.documents.business_deed.schema import BusinessDeedSchema
from src.domain.documents.business_deed import BusinessDeedDocument, BusinessDeedStringParser
from src.domain.documents.identity_stay import IdentityStayDocument, IdentityStaySchema
from src.domain.documents.certificate_local_value import CertificateLocalValueDocument, CertificateLocalValueSchema
from src.domain.documents.bank_account import BankAccountDocument, BankAccountSchema
from src.domain.documents.certificate_education import CertificateEducationDocument, CertificateEducationSchema
from src.domain.documents.certificate_competency import CertificateCompetencyDocument, CertificateCompetencySchema


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
    assert "bank_account" in slugs
    assert "bank_account_information" not in slugs
    assert "certificate_education" in slugs
    assert "certificate_competency" in slugs
    assert "education_diploma" not in slugs
    assert "limited_stay_permit" not in slugs
    assert "domestic_content_certificate" not in slugs


def test_certificate_competency_schema_and_prompt():
    doc = CertificateCompetencyDocument()
    schema = doc.get_json_schema()
    assert set(schema["properties"]) == set(CertificateCompetencySchema.model_fields)
    assert {"birth_place", "birth_date", "validity_period", "duration", "authority", "competency_field", "registration_number"}.isdisjoint(schema["properties"])
    assert set(schema["$defs"]["CompetencyUnit"]["properties"]) == {"unit_code", "unit_name"}
    prompt = doc.build_system_prompt()
    assert all(training_field in prompt for training_field in schema["properties"])
    assert "YYYY-MM-DD" in prompt and "do not calculate certificate_expiry_date" in prompt
    assert "```text\nNama: BUDI SANTOSO\n```" in doc.build_user_prompt("Nama: BUDI SANTOSO")


def test_certificate_competency_schema_normalization():
    model = CertificateCompetencySchema.model_validate({
        "certificate_number": "No. 001/2021",
        "certificate_holder": "Nama Peserta: Budi Santoso",
        "training_title": "Nama Kursus: SME Course",
        "training_start_date": "Start Date: July 1, 2022",
        "training_end_date": "Tanggal Selesai: 31 Oktober 2022",
        "certificate_issued_date": "Tanggal Terbit: 24 November 2022",
        "training_grade": "Nilai: A-",
        "training_field": "-",
    })
    assert model.certificate_number == "001/2021"
    assert model.certificate_holder == "Budi Santoso"
    assert model.training_title == "SME Course"
    assert model.training_start_date == "2022-07-01"
    assert model.training_end_date == "2022-10-31"
    assert model.certificate_issued_date == "2022-11-24"
    assert model.certificate_expiry_date is None
    assert model.training_grade == "A-"
    assert model.training_field is None


def test_certificate_competency_bnsp_parser():
    parsed = CertificateCompetencyDocument().parse_string("""
    BADAN NASIONAL SERTIFIKASI PROFESI
    SERTIFIKAT KOMPETENSI
    No. 64141 4211 2 000001 2018
    Dengan ini menyatakan bahwa,
    This is to certify that,
    BUDI SANTOSO
    No. Reg. KK 036 00001 2018
    Telah kompeten pada bidang:
    Is competent in the area of:
    Koperasi Jasa Keuangan
    Dengan Kualifikasi / Kompetensi:
    With Qualification / Competency:
    KASIR
    Sertifikat ini berlaku untuk: 3 (tiga) Tahun
    Jakarta, 21 Desember 2018
    Lembaga Sertifikasi Profesi Koperasi Jasa Keuangan
    """)
    assert parsed.certificate_number == "64141 4211 2 000001 2018"
    assert parsed.certificate_holder == "BUDI SANTOSO"
    assert parsed.training_title == "KASIR"
    assert parsed.training_field == "Koperasi Jasa Keuangan"
    assert parsed.training_institution == "Lembaga Sertifikasi Profesi Koperasi Jasa Keuangan"
    assert parsed.certificate_issued_date == "2018-12-21"
    assert parsed.certificate_expiry_date is None


def test_certificate_competency_code_only_units_parser():
    parsed = CertificateCompetencyDocument().parse_string("""
    No. 990 12.2 000001 2018
    Dengan ini menyatakan bahwa,
    BUDI SANTOSO
    Telah memenuhi persyaratan dan kompeten pada kualifikasi:
    Meets the requirements and competent for the qualification:
    1. PDB.EI.01.001.01
    2. PDB.EI.01.005.01
    Pada bidang pekerjaan:
    In the area of:
    Perdagangan Besar Sub Ekspor Profesi Penyelia Ekspor
    Sertifikat ini berlaku untuk 3 (Tiga) Tahun
    Jakarta, 24 November 2018
    Lembaga Sertifikasi Profesi LP3I
    """)
    assert parsed.training_units and [unit.unit_code for unit in parsed.training_units] == ["PDB.EI.01.001.01", "PDB.EI.01.005.01"]
    assert all(unit.unit_name is None for unit in parsed.training_units)
    assert parsed.training_title is None


def test_certificate_competency_course_parser():
    parsed = CertificateCompetencyDocument().parse_string("""
    Dicoding
    Nama: SITI AMINAH
    Course Title: Belajar Dasar Pemrograman JavaScript
    Issued Date: July 30, 2021
    Valid Until: July 30, 2024
    """)
    assert parsed.certificate_holder == "SITI AMINAH"
    assert parsed.training_title == "Belajar Dasar Pemrograman JavaScript"
    assert parsed.training_institution == "Dicoding"
    assert parsed.certificate_issued_date == "2021-07-30"
    assert parsed.certificate_expiry_date == "2024-07-30"
    assert parsed.training_units is None


def test_certificate_competency_authority_fallback():
    doc = CertificateCompetencyDocument()
    assert doc.parse_string("Authority: BNSP").training_institution == "BNSP"
    assert doc.parse_string("BADAN NASIONAL SERTIFIKASI PROFESI").training_institution == "Badan Nasional Sertifikasi Profesi"
    parsed = doc.parse_string("Authority: BNSP\nIssuer: LSP LP3I\nGrade: A-\nCompetency Field: Ekspor")
    assert parsed.training_institution == "LSP LP3I"
    assert parsed.training_grade == "A-"
    assert parsed.training_field == "Ekspor"
    assert CertificateCompetencySchema.model_validate({"training_institution": "Authority: BNSP"}).training_institution == "BNSP"


def test_certificate_education_schema_and_prompt():
    doc = CertificateEducationDocument()
    schema = doc.get_json_schema()
    properties = schema["properties"]
    assert list(properties) == [
        "transcript_number", "student_name", "student_number", "student_major",
        "student_institution",
        "enroll_level", "enroll_date", "transcript_credit", "transcript_grade",
        "transcript_issued_place", "transcript_issued_date", "enroll_courses",
    ]
    assert set(schema["$defs"]["AcademicCourse"]["properties"]) == {"course_code", "course_name", "course_credits", "course_grade", "course_semester"}
    prompt = doc.build_system_prompt()
    assert all(field in prompt for field in properties)
    assert "side-by-side" in prompt and "YYYY-MM-DD" in prompt
    assert {"birth_place", "birth_date", "education_address", "enroll_credit", "enroll_grade", "education_institution"}.isdisjoint(properties)
    assert "```text\nNama: RUDI HARTONO\n```" in doc.build_user_prompt("Nama: RUDI HARTONO")


def test_certificate_education_schema_normalization():
    model = CertificateEducationSchema.model_validate({
        "transcript_number": "No. Seri: 00123/2021",
        "student_name": "Nama Mahasiswa: Rudi Hartono",
        "student_number": "NIM: 00123456",
        "student_major": "Program Studi: Teknik Mesin",
        "student_institution": "Lembaga Pendidikan: Politeknik Negeri Bandung",
        "enroll_level": "Program Pendidikan: Diploma III",
        "enroll_date": "Tanggal Masuk: 1 September 2010",
        "transcript_credit": "Jumlah SKS: 110",
        "transcript_grade": "IPK: 3,36",
        "transcript_issued_date": "Issued Date: July 30, 2021",
        "enroll_courses": [{"course_code": "TM101", "course_name": "Kalkulus", "course_credits": "2", "course_grade": "3,5", "course_semester": "I"}],
    })
    assert model.transcript_number == "00123/2021"
    assert model.student_name == "Rudi Hartono"
    assert model.student_number == "00123456"
    assert model.student_major == "Teknik Mesin"
    assert model.enroll_level == "D3"
    assert model.enroll_date == "2010-09-01"
    assert model.transcript_credit == "110"
    assert model.transcript_grade == 3.36
    assert model.transcript_issued_date == "2021-07-30"
    assert model.enroll_courses and model.enroll_courses[0].course_semester == "I"
    assert model.enroll_courses[0].course_credits == 2
    assert model.enroll_courses[0].course_grade == 3.5
    assert '"transcript_grade":3.36' in model.model_dump_json()
    assert '"course_credits":2.0' in model.model_dump_json()
    assert '"course_grade":3.5' in model.model_dump_json()


def test_certificate_education_numeric_fields():
    model = CertificateEducationSchema.model_validate({
        "transcript_grade": 4,
        "enroll_courses": [
            {"course_credits": 2.5, "course_grade": 85},
            {"course_credits": "SKS: 2", "course_grade": "Grade: 3,25"},
            {"course_credits": "-", "course_grade": "B+"},
        ],
    })
    assert model.transcript_grade == 4
    assert model.enroll_courses and model.enroll_courses[0].course_credits == 2.5
    assert model.enroll_courses[0].course_grade == 85
    assert model.enroll_courses[1].course_credits == 2
    assert model.enroll_courses[1].course_grade == 3.25
    assert model.enroll_courses[2].course_credits is None
    assert model.enroll_courses[2].course_grade is None
    assert CertificateEducationSchema.model_validate({"transcript_grade": "3,22 (tiga koma dua dua)"}).transcript_grade == 3.22
    assert CertificateEducationSchema.model_validate({"transcript_grade": True}).transcript_grade is None
    assert CertificateEducationSchema.model_validate({"transcript_grade": float("inf")}).transcript_grade is None


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
    assert parsed.transcript_number == "001234"
    assert parsed.student_name == "RUDI HARTONO"
    assert parsed.student_number == "060100094"
    assert parsed.student_institution == "UNIVERSITAS SUMATERA UTARA"
    assert parsed.student_major == "FAKULTAS KEDOKTERAN"
    assert parsed.enroll_level == "Profesi Dokter"
    assert parsed.enroll_date == "2010-02-01"
    assert parsed.transcript_credit == "146"
    assert parsed.transcript_grade == 3.18
    assert parsed.transcript_issued_place == "Medan"
    assert parsed.transcript_issued_date == "2012-02-25"
    assert parsed.enroll_courses is None


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
    assert parsed.enroll_date is None
    assert parsed.transcript_issued_date == "2021-07-30"
    assert parsed.student_number == "001615442008"
    assert parsed.transcript_number == "872022021000837"
    assert parsed.transcript_credit == "148"


def test_bank_account_schema_and_prompt():
    doc = BankAccountDocument()
    properties = doc.get_json_schema()["properties"]
    assert set(properties) == {"bank_name", "bank_branch", "account_number", "account_holder", "account_type"}
    prompt = doc.build_system_prompt()
    assert all(field in prompt for field in properties)
    assert "balances" in prompt and "transaction tables" in prompt
    assert "```text\nNo. Rekening : 00001-2345\n```" in doc.build_user_prompt("No. Rekening : 00001-2345")
    model = BankAccountSchema.model_validate({
        "account_number": "No. Rekening : 00001-2345",
        "account_holder": "Atas Nama : PT CONTOH MAKMUR",
        "account_type": "Jenis Rekening : Tabungan",
    })
    assert model.account_number == "00001-2345"
    assert model.account_holder == "PT CONTOH MAKMUR"
    assert model.account_type == "Tabungan"
    assert BankAccountSchema.model_validate({"bank_branch": "Cabang: KCP Jakarta Cibis Nine"}).bank_branch == "KCP Jakarta Cibis Nine"
    assert BankAccountSchema.model_validate({"bank_branch": "KCP SUNGKONO"}).bank_branch == "KCP SUNGKONO"
    assert BankAccountSchema.model_validate({"account_number": "0000****1234"}).account_number is None


def test_bank_account_passbook_parser():
    raw_text = """
    Tabungan BRI Simpedes
    Kantor BANK BRI : 3868 UNIT MENES LABUAN
    CIF : RG91491
    No. Rekening : 3868-01-000123-45-6
    Nama : BUDI SANTOSO
    No. Seri : 12345678
    """
    parsed = BankAccountDocument().parse_string(raw_text)
    assert parsed.bank_name == "Bank Rakyat Indonesia"
    assert parsed.bank_branch == "3868 UNIT MENES LABUAN"
    assert parsed.account_number == "3868-01-000123-45-6"
    assert parsed.account_holder == "BUDI SANTOSO"
    assert parsed.account_type == "Simpedes"
    assert "customer_id" not in parsed.model_dump()
    assert "passbook_serial_number" not in parsed.model_dump()


def test_bank_account_unlabeled_bca_passbook_parser():
    parsed = BankAccountDocument().parse_string("""
    KCP SUNGKONO
    0001234567
    JANE DOE
    16/06/2020 BCA SUNGKONO
    BANK CENTRAL ASIA
    """)
    assert parsed.bank_name == "Bank Central Asia"
    assert parsed.bank_branch == "KCP SUNGKONO"
    assert parsed.account_number == "0001234567"
    assert parsed.account_holder == "JANE DOE"


def test_bank_account_statement_and_letter_parser():
    statement = BankAccountDocument().parse_string("""
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
    assert statement.account_holder == "PT CONTOH JAYA"
    assert "opening_balance" not in statement.model_dump()
    assert "transactions" not in statement.model_dump()

    letter = BankAccountDocument().parse_string("""
    PT CONTOH MAKMUR
    Untuk Pembayaran dapat di transfer ke Rekening:
    Bank Danamon, Cabang Puri Kencana
    ACC. No. : 4101234
    Atas Nama : PT CONTOH MAKMUR
    """)
    assert letter.bank_name == "Bank Danamon"
    assert letter.bank_branch == "Puri Kencana"
    assert letter.account_number == "4101234"
    assert letter.account_holder == "PT CONTOH MAKMUR"


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
        "product_local_value": "Nilai TKDN : 96,72%",
        "product_standard": "Standard Produk : -",
        "product_brand": "Merk : -",
        "business_tax_number": "NPWP : 82.934.355.7-543.000",
        "business_field": "Bidang Usaha : Industri Barang Bangunan Dari Kayu (KBLI: 16221)",
        "certificate_issued_date": "Issued Date : 28 Juli 2021",
    })
    assert model.product_name == "Basket Ecenggondok"
    assert model.product_local_value == 96.72
    assert '"product_local_value":96.72' in model.model_dump_json()
    assert model.product_standard is None
    assert model.product_brand is None
    assert model.business_tax_number == "82.934.355.7-543.000"
    assert model.business_field == "Industri Barang Bangunan Dari Kayu (KBLI: 16221)"
    assert model.certificate_issued_date == "2021-07-28"
    assert CertificateLocalValueSchema.model_validate({"product_local_value": "Nilai TKDN : (Terlampir)"}).product_local_value is None
    assert CertificateLocalValueSchema.model_validate({"product_local_value": "Nilai TKDN : 96.72"}).product_local_value == 96.72
    assert CertificateLocalValueSchema.model_validate({"product_local_value": 96.72}).product_local_value == 96.72
    assert CertificateLocalValueSchema.model_validate({"certificate_valid_year": "berlaku 2 tahun"}).certificate_valid_year == 2
    assert CertificateLocalValueSchema.model_validate({"certificate_valid_year": 3}).certificate_valid_year == 3
    assert CertificateLocalValueSchema.model_validate({"certificate_valid_year": "-"}).certificate_valid_year is None


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
    assert parsed.product_hs == "44209010"
    assert parsed.product_brand is None
    assert parsed.product_local_value == 96.72
    assert "tkdn_in_words" not in parsed.model_dump()
    assert parsed.product_standard is None
    assert parsed.product_certificate is None
    assert parsed.report_number == "LPA-3426/PK-3506/PTKDN.DIPA-INFRAS/VII/21"
    assert parsed.certificate_valid_year == 3
    assert '"certificate_valid_year":3' in parsed.model_dump_json()
    assert parsed.business_name == "CV. Contoh Indonesia"
    assert parsed.business_address == "Jl. Contoh No. 7, Bantul D.I. Yogyakarta"
    assert parsed.business_tax_number == "82.934.355.7-543.000"
    assert parsed.business_field == "Industri Barang Bangunan Dari Kayu (KBLI: 16221)"
    assert parsed.certificate_number == "4623/SJ-IND.8/TKDN/7/2021"
    assert parsed.certificate_issued_place == "Jakarta"
    assert parsed.certificate_issued_date == "2021-07-28"
    assert parsed.signing_official_title == "Kepala Pusat Peningkatan Penggunaan Produk Dalam Negeri"
    assert parsed.signing_official_name == "Nila Kumalasari"
    assert parsed.certificate_qr_number == "23361"


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
    assert parsed.product_local_value is None
    assert parsed.business_field == "Industri Peralatan Listrik Lainnya (KBLI: 27900)"
    assert parsed.certificate_issued_date == "2025-10-23"
    assert parsed.certificate_qr_number is None


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
        "permit_niora": "NIORA : AB12345678",
        "permit_number": "Permit Number : 2C21AB1234YZ",
        "holder_birth_place": "Place / Date of Birth : SINGAPORE / 04-03-1984",
        "holder_birth_date": "Place / Date of Birth : SINGAPORE / 04-03-1984",
        "permit_expiry_date": "Stay/Multiple Entries Permit Expiry : 18-12-2020",
        "holder_passport_expiry_date": "Passport Expiry : 11-01-2028",
        "permit_issued_date": "Issued Date : 26 Januari 2024",
        "holder_guarantor": "-",
    })
    assert model.permit_niora == "AB12345678"
    assert model.permit_number == "2C21AB1234YZ"
    assert model.holder_birth_place == "SINGAPORE"
    assert model.holder_birth_date == "1984-03-04"
    assert model.permit_expiry_date == "2020-12-18"
    assert model.holder_passport_expiry_date == "2028-01-11"
    assert model.permit_issued_date == "2024-01-26"
    assert model.holder_guarantor is None


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
    assert parsed.permit_issuing_office == "KANIM KELAS I KHUSUS NON TPI JAKARTA SELATAN"
    assert parsed.permit_issuing_office_address == "JL. CONTOH NO. 10 JAKARTA SELATAN"
    assert parsed.permit_niora == "AB12345678"
    assert parsed.permit_number == "2C21AB1234YZ"
    assert parsed.permit_expiry_date == "2020-12-18"
    assert parsed.permit_index == "1B"
    assert parsed.holder_full_name == "JANE DOE"
    assert parsed.holder_birth_place == "SINGAPORE"
    assert parsed.holder_birth_date == "1984-03-04"
    assert parsed.holder_passport_number == "P1234567"
    assert parsed.holder_passport_expiry_date == "2028-01-11"
    assert parsed.holder_nationality == "SINGAPURA"
    assert parsed.holder_gender == "FEMALE"
    assert parsed.holder_address == "JL. CONTOH NO. 10 RT 001 RW 002 KEBAYORAN LAMA"
    assert parsed.holder_occupation == "INVESTOR"
    assert parsed.holder_status == "INVESTMENT"
    assert parsed.holder_guarantor == "PT CONTOH INDONESIA"
    assert parsed.permit_issued_place == "Jakarta"
    assert parsed.permit_issued_date == "2024-01-26"


def test_identity_stay_obscured_values_remain_null():
    parsed = IdentityStayDocument().parse_string("NIORA :\nPermit Number :\nGuarantor Name : -\nPassport Expiry : -")
    assert parsed.permit_niora is None
    assert parsed.permit_number is None
    assert parsed.holder_guarantor is None
    assert parsed.holder_passport_expiry_date is None


def test_identity_card_schema_validation():
    data = {
        "document_number": "3171-0101-0190-0001",
        "holder_name": "JOHN DOE",
        "holder_gender": "LAKI-LAKI",
        "document_expiry_date": "SEUMUR HIDUP"
    }
    model = IdentityCardSchema.model_validate(data)
    assert model.document_number == "3171010101900001"
    assert model.holder_name == "JOHN DOE"
    assert model.holder_nationality == "WNI"


def test_tax_number_schema_validation():
    data = {
        "tax_number": "01.234.567.8-901.000",
        "business_name": "PT CONTOH MAKMUR",
        "tax_office": "KPP PRATAMA JAKARTA TANAH ABANG",
        "tax_office_address": "JL KH MAS MANSYUR NO. 71"
    }
    model = TaxNumberSchema.model_validate(data)
    assert model.tax_number == "01.234.567.8-901.000"
    assert model.business_name == "PT CONTOH MAKMUR"
    assert model.tax_office == "KPP PRATAMA JAKARTA TANAH ABANG"
    assert model.tax_office_address == "JL KH MAS MANSYUR NO. 71"


def test_identity_card_jokowi_sample_validation():
    data = {
        "document_province": "PROVINSI DKI JAKARTA",
        "document_city": "JAKARTA PUSAT",
        "document_number": "NIK : 3372052106610006",
        "holder_name": "IR JOKO WIDODO",
        "holder_birth_place": "SURAKARTA",
        "holder_birth_date": "21-06-1961",
        "holder_gender": "LAKI-LAKI",
        "holder_blood_type": "A",
        "holder_address": "JL TAMAN SUROPATI NO. 7",
        "holder_neighborhood_unit": "005",
        "holder_village": "MENTENG",
        "holder_district": "MENTENG",
        "holder_religion": "ISLAM",
        "holder_marital_status": "KAWIN",
        "holder_occupation": "GUBERNUR",
        "holder_nationality": "WNI",
        "document_expiry_date": "21-06-2017"
    }
    model = IdentityCardSchema.model_validate(data)
    assert model.document_province == "DKI JAKARTA"
    assert model.document_city == "JAKARTA PUSAT"
    assert model.document_number == "3372052106610006"
    assert model.holder_name == "IR JOKO WIDODO"
    assert model.holder_birth_place == "SURAKARTA"
    assert model.holder_birth_date == "1961-06-21"
    assert model.holder_gender == "LAKI-LAKI"
    assert model.holder_blood_type == "A"
    assert model.holder_address == "JL TAMAN SUROPATI NO. 7"
    assert model.holder_neighborhood_unit == "005"
    assert model.holder_village == "MENTENG"
    assert model.holder_district == "MENTENG"
    assert model.holder_religion == "ISLAM"
    assert model.holder_marital_status == "KAWIN"
    assert model.holder_occupation == "GUBERNUR"
    assert model.holder_nationality == "WNI"
    assert model.document_expiry_date == "2017-06-21"


def test_identity_card_document_schema_and_prompts():
    doc = IdentityCardDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "document_number" in schema["properties"]
    assert "document_province" in schema["properties"]
    assert "document_city" in schema["properties"]
    assert "holder_neighborhood_unit" in schema["properties"]

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
        "document_province": "PROVINSI JAWA BARAT",
        "holder_birth_place": "SURAKARTA, 21-06-1961",
        "holder_birth_date": "Tanggal: 21/06/1961",
        "holder_gender": "LAKI-LATI",
        "holder_blood_type": "GOL. DARAH : A",
        "holder_neighborhood_unit": "R/T/RW : 005 / 005",
    }
    model = IdentityCardSchema.model_validate(noisy_data)
    assert model.document_province == "JAWA BARAT"
    assert model.holder_birth_place == "SURAKARTA"
    assert model.holder_birth_date == "1961-06-21"
    assert model.holder_gender == "LAKI-LAKI"
    assert model.holder_blood_type == "A"
    assert model.holder_neighborhood_unit == "005/005"

    invalid_neighborhood = {"holder_neighborhood_unit": "MENTENG"}
    model_inv = IdentityCardSchema.model_validate(invalid_neighborhood)
    assert model_inv.holder_neighborhood_unit is None


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
    assert parsed.document_province == "DKI JAKARTA"
    assert parsed.document_city == "JAKARTA PUSAT"
    assert parsed.document_number == "3171010101900001"
    assert parsed.holder_name == "BUDI SANTOSO"
    assert parsed.holder_birth_place == "JAKARTA"
    assert parsed.holder_birth_date == "1990-01-01"
    assert parsed.holder_gender == "LAKI-LAKI"
    assert parsed.holder_blood_type == "O"
    assert parsed.holder_address == "JL TAMAN SUROPATI NO. 7"
    assert parsed.holder_neighborhood_unit == "005/005"
    assert parsed.holder_village == "MENTENG"
    assert parsed.holder_district == "MENTENG"
    assert parsed.holder_religion == "ISLAM"
    assert parsed.holder_marital_status == "KAWIN"
    assert parsed.holder_occupation == "KARYAWAN SWASTA"
    assert parsed.holder_nationality == "WNI"
    assert parsed.document_expiry_date == "SEUMUR HIDUP"


def test_tax_number_document_schema_and_prompts():
    doc = TaxNumberDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "tax_number" in schema["properties"]
    assert "business_name" in schema["properties"]
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
    assert parsed.business_name == "PT CONTOH MAKMUR"
    assert parsed.tax_office == "KPP MADYA GRESIK"
    assert parsed.tax_office_address == "JL DR WAHIDIN SUDIROHUSODO 700 GRESIK"
    assert parsed.tax_registration_date == "2022-01-01"


def test_business_identification_number_schema_validation():
    data = {
        "business_number": "1234567890123",
        "business_name": "PT CONTOH SEJAHTERA ABADI",
        "business_address": "JL. JENDERAL SUDIRMAN KAV. 10, KOTA ADM. JAKARTA SELATAN",
        "business_postal_code": "12190",
        "business_phone_number": "0215551234",
        "business_email": "info@contohsejahtera.co.id",
        "business_investment_status": "PMDN",
        "document_issued_place": "Jakarta",
        "document_issued_date": "10 Januari 2020",
        "amendment_number": "1",
        "amendment_date": "05 Mei 2023",
        "document_printed_date": "05 Mei 2023",
        "signing_official_title": "Menteri Investasi dan Hilirisasi/ Kepala Badan Koordinasi Penanaman Modal",
        "business_fields": [
            {
                "field_number": "39",
                "field_code": "46206",
                "field_title": "Perdagangan Besar Hasil Perikanan",
                "field_location": "GD. PUSAT PERUM BULOG LT. 10 JL. JEND. GATOT SUBROTO KAV.49",
                "field_postal_code": "12950",
                "field_risk": "Menengah Tinggi",
                "field_licenses": [
                    {
                        "license_type": "NIB",
                        "license_status": "Terbit",
                        "license_remarks": "-",
                    },
                    {
                        "license_type": "Sertifikat Standar",
                        "license_status": "Belum Terverifikasi",
                        "license_remarks": "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 hari kerja",
                    },
                ],
            }
        ],
    }
    model = BusinessNumberSchema.model_validate(data)
    assert model.business_number == "1234567890123"
    assert model.business_name == "PT CONTOH SEJAHTERA ABADI"
    assert model.business_postal_code == "12190"
    assert model.business_investment_status == "PMDN"
    assert model.document_issued_date == "2020-01-10"
    assert model.amendment_number == "1"
    assert model.amendment_date == "2023-05-05"
    assert model.document_printed_date == "2023-05-05"
    assert model.business_fields is not None
    assert len(model.business_fields) == 1
    assert model.business_fields[0].field_code == "46206"
    assert model.business_fields[0].field_risk == "Menengah Tinggi"
    assert model.business_fields[0].field_licenses is not None
    assert len(model.business_fields[0].field_licenses) == 2
    assert model.business_fields[0].field_licenses[0].license_type == "NIB"
    assert model.business_fields[0].field_licenses[0].license_remarks is None
    assert model.business_fields[0].field_licenses[1].license_type == "Sertifikat Standar"
    assert model.business_fields[0].field_licenses[1].license_remarks == "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 hari kerja"


def test_business_identification_number_document_schema_and_prompts():
    doc = BusinessIdentificationNumberDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "business_number" in schema["properties"]
    assert "business_name" in schema["properties"]
    assert "business_address" in schema["properties"]
    assert "business_fields" in schema["properties"]

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
    assert parsed.business_number == "1234567890123"
    assert parsed.business_name == "PT CONTOH SEJAHTERA ABADI"
    assert parsed.business_address == "JL. JENDERAL SUDIRMAN KAV. 10, Kota Adm. Jakarta Selatan"
    assert parsed.business_postal_code == "12190"
    assert parsed.business_phone_number == "0215551234"
    assert parsed.business_email == "info@contohsejahtera.co.id"
    assert parsed.business_investment_status == "PMDN"
    assert parsed.document_issued_place == "Jakarta"
    assert parsed.document_issued_date == "2020-01-10"
    assert parsed.amendment_number == "1"
    assert parsed.amendment_date == "2023-05-05"
    assert parsed.document_printed_date == "2023-05-05"
    assert parsed.business_fields is None


def test_license_item_value_normalization():
    # An OCR/LLM pass sometimes prefixes a stacked sub-row's Jenis/Status with a
    # leading bullet dash (from the table's visual stacking) instead of a clean value.
    item = LicenseItem.model_validate({
        "license_type": "- Sertifikat Standar",
        "license_status": "- Belum Terverifikasi",
        "license_remarks": "",
    })
    assert item.license_type == "Sertifikat Standar"
    assert item.license_status == "Belum Terverifikasi"
    assert item.license_remarks is None

    dash_only = LicenseItem.model_validate({"license_remarks": "-"})
    assert dash_only.license_remarks is None

    real_remark = LicenseItem.model_validate({
        "license_remarks": "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 hari kerja"
    })
    assert real_remark.license_remarks == "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 hari kerja"


def test_field_item_multiple_licenses():
    field = FieldItem.model_validate({
        "field_number": "39",
        "field_code": "46206",
        "field_title": "Perdagangan Besar Hasil Perikanan",
        "field_licenses": [
            {"license_type": "NIB", "license_status": "Terbit", "license_remarks": "-"},
            {
                "license_type": "Sertifikat Standar",
                "license_status": "Belum Terverifikasi",
                "license_remarks": "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 hari kerja",
            },
        ],
    })
    assert field.field_licenses is not None
    assert len(field.field_licenses) == 2
    assert field.field_licenses[0].license_type == "NIB"
    assert field.field_licenses[0].license_remarks is None
    assert field.field_licenses[1].license_status == "Belum Terverifikasi"
    assert field.field_licenses[1].license_remarks == "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 hari kerja"


def test_tax_entity_schema_validation():
    data = {
        "letter_number": "S-47PKP/WPJ.05/KP.1003/2015",
        "tax_office_region": "KANTOR WILAYAH DJP JAKARTA BARAT",
        "tax_office_name": "KPP PRATAMA JAKARTA KEBON JERUK DUA",
        "tax_office_address": "JL. K.S. TUBUN 10, JAKARTA BARAT",
        "business_tax_number": "01.329.904.5-039.000",
        "business_name": "PT. RAMCOMAS MANDIRI",
        "business_fields": [
            {"field_code": "71100", "field_title": "JASA ARSITEKTUR DAN TEKNIK SIPIL SERTA KONSULTASI TEKNIS YBDI"}
        ],
        "business_address": "JL.KEDOYA ANGSANA BLOK B II NO.25, KEDOYA SELATAN KEBON JERUK, JAKARTA BARAT DKI JAKARTA",
        "business_trade": "-",
        "tax_obligation": "PPN",
        "letter_confirmed_since": "21 Maret 1992",
        "letter_issued_place": "Jakarta Barat",
        "letter_issued_date": "17 April 2015",
        "signing_official_title": "a.n. Kepala Kantor Kepala Seksi Pelayanan",
        "signing_official_name": "MUNAWAM",
        "signing_official_number": "NIP.196005151981031001",
    }
    model = TaxEntitySchema.model_validate(data)
    assert model.letter_number == "S-47PKP/WPJ.05/KP.1003/2015"
    assert model.business_tax_number == "01.329.904.5-039.000"
    assert model.business_name == "PT. RAMCOMAS MANDIRI"
    assert model.business_fields is not None
    assert len(model.business_fields) == 1
    assert model.business_fields[0].field_code == "71100"
    assert model.business_fields[0].field_title == "JASA ARSITEKTUR DAN TEKNIK SIPIL SERTA KONSULTASI TEKNIS YBDI"
    assert model.business_trade is None
    assert model.tax_obligation == "PPN"
    assert model.letter_confirmed_since == "1992-03-21"
    assert model.letter_issued_date == "2015-04-17"
    assert model.signing_official_number == "196005151981031001"


def test_tax_entity_document_schema_and_prompts():
    doc = TaxEntityDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "business_tax_number" in schema["properties"]
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
    assert parsed.tax_office_name == "KPP PRATAMA JAKARTA KEBON JERUK DUA"
    assert parsed.tax_office_address == "JL. K.S. TUBUN 10, JAKARTA BARAT"
    assert parsed.business_tax_number == "01.329.904.5-039.000"
    assert parsed.business_name == "PT. RAMCOMAS MANDIRI"
    assert parsed.business_fields is not None
    assert len(parsed.business_fields) == 1
    assert parsed.business_fields[0].field_code == "71100"
    assert parsed.business_fields[0].field_title == "JASA ARSITEKTUR DAN TEKNIK SIPIL SERTA KONSULTASI TEKNIS YBDI"
    assert parsed.business_address == "JL.KEDOYA ANGSANA BLOK B II NO.25, KEDOYA SELATAN KEBON JERUK, JAKARTA BARAT DKI JAKARTA"
    assert parsed.business_trade is None
    assert parsed.tax_obligation == "PPN"
    assert parsed.letter_confirmed_since == "1992-03-21"
    assert parsed.letter_issued_place == "Jakarta Barat"
    assert parsed.letter_issued_date == "2015-04-17"
    assert parsed.signing_official_title == "a.n. Kepala Kantor Kepala Seksi Pelayanan"
    assert parsed.signing_official_name == "MUNAWAM"
    assert parsed.signing_official_number == "196005151981031001"


def test_tax_entity_string_parser_direct():
    parsed = TaxEntityStringParser.parse(
        "1. Nomor Pokok Wajib Pajak : 01.329.904.5-039.000\n2. Nama : PT. RAMCOMAS MANDIRI"
    )
    assert parsed.business_tax_number == "01.329.904.5-039.000"
    assert parsed.business_name == "PT. RAMCOMAS MANDIRI"


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
        "document_issuing_country": "USA<",
        "holder_surname": "TRAVELER",
        "holder_given_names": "HAPPY",
        "holder_passport_number": "E00007734",
        "holder_nationality": "USA",
        "holder_birth_date": "05 FEB 1990",
        "holder_gender": "F",
        "holder_birth_place": "WASHINGTON D.C., U.S.A.",
        "document_issued_date": "15 OCT 2020",
        "document_expiry_date": "14 OCT 2030",
        "document_issuing_authority": "UNITED STATES DEPARTMENT OF STATE",
        "document_mrz_line1": "p<usatraveler<<happy<<<<<<<<<<<<<<<<<<<<<<<<",
    }
    model = IdentityPassportSchema.model_validate(data)
    assert model.document_type == "P"
    assert model.document_issuing_country == "USA"
    assert model.holder_surname == "TRAVELER"
    assert model.holder_passport_number == "E00007734"
    assert model.holder_birth_date == "1990-02-05"
    assert model.document_issued_date == "2020-10-15"
    assert model.document_expiry_date == "2030-10-14"
    assert model.document_mrz_line1 == "P<USATRAVELER<<HAPPY<<<<<<<<<<<<<<<<<<<<<<<<"


def test_identity_passport_document_schema_and_prompts():
    doc = IdentityPassportDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "document_mrz_line1" in schema["properties"]
    assert "document_mrz_line2" in schema["properties"]
    assert "holder_passport_number" in schema["properties"]
    assert "document_issuing_country" in schema["properties"]

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
    assert parsed.document_issuing_country == "EOL"
    assert parsed.holder_surname == "SMITH"
    assert parsed.holder_given_names == "JANE"
    assert parsed.holder_passport_number == "PP3000000"
    assert parsed.holder_nationality == "EOL"
    assert parsed.holder_birth_date == "1981-07-14"
    assert parsed.holder_gender == "F"
    assert parsed.document_expiry_date == "2022-12-31"
    # VIZ-only fields aren't in the MRZ, so the string parser correctly leaves them unset
    assert parsed.holder_birth_place is None
    assert parsed.document_issued_date is None
    assert parsed.document_issuing_authority is None


def test_identity_passport_string_parser_multi_part_name():
    line1, line2 = _synthetic_mrz(
        surname="DE BRUIJN", given_names="WILLEKE LISELOTTE", country="NLD", passport_number="SPECI2014",
        nationality="NLD", dob_yymmdd="650310", sex="F", expiry_yymmdd="240309",
    )
    parsed = IdentityPassportStringParser.parse(f"{line1}\n{line2}")
    assert parsed.holder_surname == "DE BRUIJN"
    assert parsed.holder_given_names == "WILLEKE LISELOTTE"
    assert parsed.holder_nationality == "NLD"
    assert parsed.holder_birth_date == "1965-03-10"
    assert parsed.document_expiry_date == "2024-03-09"


def test_identity_passport_string_parser_no_mrz_found():
    parsed = IdentityPassportStringParser.parse("just some random text with no MRZ lines in it")
    assert isinstance(parsed, IdentityPassportSchema)
    assert parsed.document_mrz_line1 is None
    assert parsed.document_mrz_line2 is None
    assert parsed.holder_passport_number is None


def test_business_deed_schema_validation():
    data = {
        "deed_type": "= AKTA PENDIRIAN PERSEROAN TERBATAS =",
        "deed_number": "No. 2",
        "deed_date": "03 Agustus 2023",
        "notary_name": "CONTOH NOTARIS, S.H., M.Kn",
        "notary_address": "Alamat Jalan Contoh Nomor 1, Cianjur, Jawa Barat",
        "decision_number": "Nomor : AHU-0028078.AH.01.02.TAHUN 2022",
        "decision_issued_date": "19 April 2022",
    }
    model = BusinessDeedSchema.model_validate(data)
    assert model.deed_type == "Pendirian"
    assert model.deed_number == "2"
    assert model.deed_date == "2023-08-03"
    assert model.notary_name == "CONTOH NOTARIS, S.H., M.Kn"
    assert model.notary_address == "Jalan Contoh Nomor 1, Cianjur, Jawa Barat"
    assert model.decision_number is not None
    assert model.decision_number == "AHU-0028078.AH.01.02.TAHUN 2022"
    assert model.decision_issued_date == "2022-04-19"


def test_business_deed_document_schema_and_prompts():
    doc = BusinessDeedDocument()
    schema = doc.get_json_schema()
    assert "properties" in schema
    assert "deed_number" in schema["properties"]
    assert "notary_name" in schema["properties"]
    assert "decision_number" in schema["properties"]

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
    assert parsed.decision_number is not None
    assert parsed.decision_number == "AHU-0099999.AH.01.02.TAHUN 2023"
    assert parsed.decision_issued_date == "2023-01-15"
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
    assert parsed.decision_number is None


def test_business_deed_string_parser_old_numbering_format():
    raw_text = (
        "KEPUTUSAN MENTERI KEHAKIMAN REPUBLIK INDONESIA\n"
        "NOMOR : C2-10671.HT.01.01.TH.88.-\n"
        "MENTERI KEHAKIMAN REPUBLIK INDONESIA,\n"
    )
    parsed = BusinessDeedStringParser.parse(raw_text)
    assert parsed.decision_number is not None
    assert parsed.decision_number == "C2-10671.HT.01.01.TH.88"


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


def test_business_deed_decision_number_validation():
    deed = BusinessDeedSchema.model_validate({"decision_number": "NOMOR: AHU-01173.AH.01.02.Tahun 2010"})
    assert deed.decision_number == "AHU-01173.AH.01.02.Tahun 2010"
