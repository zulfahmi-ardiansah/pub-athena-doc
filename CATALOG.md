# Document Property Catalog

Properties returned in the `data` object for each registered document type. Descriptions follow the document schemas. Nested paths use `[]` for each item in a repeated list. Fields can be `null` when the source document does not provide a value.

<a id="identity_card"></a>

## Kartu Tanda Penduduk (KTP) (`identity_card`)

Extracts 16-digit NIK, full name, address hierarchy, religion, marital status, and validity:

### Example

```json
{
  "document_province": "DKI JAKARTA",
  "document_city": "JAKARTA PUSAT",
  "document_number": "3171010101900001",
  "holder_name": "BUDI SANTOSO",
  "holder_birth_place": "JAKARTA",
  "holder_birth_date": "1990-01-01",
  "holder_gender": "LAKI-LAKI",
  "holder_blood_type": "O",
  "holder_address": "JL. JENDERAL SUDIRMAN NO. 45",
  "holder_neighborhood_unit": "002/005",
  "holder_village": "BENDUNGAN HILIR",
  "holder_district": "TANAH ABANG",
  "holder_religion": "ISLAM",
  "holder_marital_status": "BELUM KAWIN",
  "holder_occupation": "KARYAWAN SWASTA",
  "holder_nationality": "WNI",
  "document_expiry_date": "SEUMUR HIDUP"
}
```

| Property name | Description |
| --- | --- |
| `document_province` | Province name (Provinsi, without 'PROVINSI' prefix, e.g. 'DKI JAKARTA') |
| `document_city` | City or Regency name (Kota/Kabupaten, e.g. 'JAKARTA PUSAT') |
| `document_number` | Nomor Induk Kependudukan / NIK (16 digits) |
| `holder_name` | Full Name (Nama, e.g. 'IR JOKO WIDODO') |
| `holder_birth_place` | Place of birth (Tempat Lahir, e.g. 'SURAKARTA') |
| `holder_birth_date` | Date of birth (Tanggal Lahir), normalized to ISO 8601 (YYYY-MM-DD) |
| `holder_gender` | Gender (Jenis Kelamin: 'LAKI-LAKI' or 'PEREMPUAN') |
| `holder_blood_type` | Blood type (Golongan Darah: 'A', 'B', 'AB', 'O', or '-') |
| `holder_address` | Street / Residential address (Alamat, e.g. 'JL TAMAN SUROPATI NO. 7') |
| `holder_neighborhood_unit` | RT/RW numbering (e.g. '005' or '005/005') |
| `holder_village` | Village / Urban community (Kelurahan or Desa, e.g. 'MENTENG') |
| `holder_district` | Sub-district (Kecamatan, e.g. 'MENTENG') |
| `holder_religion` | Religion (Agama: 'ISLAM', 'KRISTEN', 'KATHOLIK', 'HINDU', 'BUDDHA', 'KHONGHUCU') |
| `holder_marital_status` | Marital status (Status Perkawinan: 'BELUM KAWIN', 'KAWIN', 'CERAI HIDUP', 'CERAI MATI') |
| `holder_occupation` | Occupation / Profession (Pekerjaan, e.g. 'GUBERNUR') |
| `holder_nationality` | Nationality (Kewarganegaraan: 'WNI' or 'WNA') |
| `document_expiry_date` | Validity period (Berlaku Hingga: ISO 8601 date 'YYYY-MM-DD' or 'SEUMUR HIDUP') |

<a id="tax_number"></a>

## Nomor Pokok Wajib Pajak (NPWP) (`tax_number`)

Extracts 15/16-digit NPWP, taxpayer name, registered KPP branch office and address, and registration date:

### Example

```json
{
  "tax_number": "01.234.567.8-012.000",
  "business_name": "PT ADIDAYA WIKASITA",
  "tax_office": "KPP PRATAMA SETIABUDI DUA",
  "tax_office_address": "JL. GATOT SUBROTO KAV. 18",
  "tax_registration_date": "2018-08-15"
}
```

| Property name | Description |
| --- | --- |
| `tax_number` | Nomor Pokok Wajib Pajak / NPWP (15 or 16 digits format) |
| `business_name` | Taxpayer Name (Nama Wajib Pajak, e.g. 'BUDI') |
| `tax_office` | Tax Branch Office where registered (Kantor Pelayanan Pajak / KPP, e.g. 'KPP MADYA GRESIK') |
| `tax_office_address` | Tax Branch Office Address (Alamat KPP, e.g. 'JL DR WAHIDIN SUDIROHUSODO 700 GRESIK') |
| `tax_registration_date` | Registration date (Tanggal Terdaftar), normalized to ISO 8601 (YYYY-MM-DD) |

<a id="business_identification_number"></a>

## Nomor Induk Berusaha (NIB) (`business_identification_number`)

Extracts the 13-digit NIB, business actor name and contact details, investment status, issuance/amendment dates, and the full KBLI (business classification) attachment table:

### Example

```json
{
  "business_number": "2210210046937",
  "business_name": "PT Mitra BUMDes Nusantara",
  "business_address": "LIPPO KUNINGAN TOWER LANTAI 11, JL. H.R. RASUNA SAID KAV. B-12",
  "business_postal_code": "12940",
  "business_phone_number": "02121393278",
  "business_email": "mbn@mitrabumdes.co.id",
  "business_investment_status": "PMDN",
  "document_issued_place": "Jakarta",
  "document_issued_date": "2021-10-22",
  "amendment_number": "1",
  "amendment_date": "2025-03-19",
  "document_printed_date": "2025-03-19",
  "signing_official_title": "Menteri Investasi dan Hilirisasi/ Kepala Badan Koordinasi Penanaman Modal",
  "business_fields": [
    {
      "field_number": "1",
      "field_code": "46321",
      "field_title": "Perdagangan Besar Daging Sapi Dan Daging Sapi Olahan",
      "field_location": "GD. PUSAT PERUM BULOG LT. 10 JL. JEND. GATOT SUBROTO KAV.49",
      "field_postal_code": "12950",
      "field_risk": "Rendah",
      "field_licenses": [
        {
          "license_type": "NIB",
          "license_status": "Terbit",
          "license_remarks": null
        }
      ]
    },
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
          "license_remarks": null
        },
        {
          "license_type": "Sertifikat Standar",
          "license_status": "Belum Terverifikasi",
          "license_remarks": "Lakukan pemenuhan standar melalui oss.go.id paling lambat 90 (sembilan puluh) hari kerja sebelum waktu perkiraan mulai beroperasi/produksi"
        }
      ]
    }
  ]
}
```

| Property name | Description |
| --- | --- |
| `business_number` | Nomor Induk Berusaha / NIB (13-digit business identification number) |
| `business_name` | Business actor name (Nama Pelaku Usaha) |
| `business_address` | Office address (Alamat Kantor) |
| `business_postal_code` | Office postal code (Kode Pos) |
| `business_phone_number` | Office phone number (No. Telepon) |
| `business_email` | Office email address (Email) |
| `business_investment_status` | Investment status (Status Penanaman Modal), e.g. 'PMDN' or 'PMA' |
| `document_issued_place` | Place of issuance (Diterbitkan di) |
| `document_issued_date` | Issuance date (Tanggal), normalized to ISO 8601 (YYYY-MM-DD) |
| `amendment_number` | Amendment number if the NIB has been amended (Perubahan ke-) |
| `amendment_date` | Amendment date (Tanggal Perubahan), normalized to ISO 8601 (YYYY-MM-DD) |
| `document_printed_date` | Print date (Dicetak tanggal), normalized to ISO 8601 (YYYY-MM-DD) |
| `signing_official_title` | Title of the signing official (e.g. 'Menteri Investasi dan Hilirisasi/ Kepala Badan Koordinasi Penanaman Modal') |
| `business_fields` | Business classification (KBLI) line items from the attachment table |
| `business_fields[].field_number` | Row number in the KBLI attachment table |
| `business_fields[].field_code` | 5-digit KBLI (Klasifikasi Baku Lapangan Usaha Indonesia) code |
| `business_fields[].field_title` | Business classification title/description (Judul KBLI) |
| `business_fields[].field_location` | Business location address for this KBLI row (Lokasi Usaha) |
| `business_fields[].field_postal_code` | Postal code for this KBLI row's business location (Kode Pos) |
| `business_fields[].field_risk` | Risk level (Tingkat Risiko), e.g. 'Rendah', 'Menengah Rendah', 'Menengah Tinggi', 'Tinggi' |
| `business_fields[].field_licenses` | One entry per Jenis/Status/Keterangan sub-row under this KBLI row's Perizinan Berusaha block |
| `business_fields[].field_licenses[].license_type` | License type (Jenis), e.g. 'NIB', 'Sertifikat Standar', 'Izin' |
| `business_fields[].field_licenses[].license_status` | License status (Status), e.g. 'Terbit', 'Belum Terbit', 'Belum Terverifikasi' |
| `business_fields[].field_licenses[].license_remarks` | Remarks/instructions for this specific license (Keterangan), verbatim as printed |

<a id="tax_entity"></a>

## Surat Pengukuhan Pengusaha Kena Pajak (SPPKP/PKP) (`tax_entity`)

Extracts the issuing tax office, NPWP, taxpayer name, business classification (KLU), address, checked tax obligation(s), and signing official details:

### Example

```json
{
  "letter_number": "S-47PKP/WPJ.05/KP.1003/2015",
  "tax_office_region": "KANTOR WILAYAH DJP JAKARTA BARAT",
  "tax_office_name": "KPP PRATAMA JAKARTA KEBON JERUK DUA",
  "tax_office_address": "JL. K.S. TUBUN 10, JAKARTA BARAT",
  "business_tax_number": "01.329.904.5-039.000",
  "business_name": "PT. RAMCOMAS MANDIRI",
  "business_fields": [
    {
      "field_code": "71100",
      "field_title": "JASA ARSITEKTUR DAN TEKNIK SIPIL SERTA KONSULTASI TEKNIS YBDI"
    }
  ],
  "business_address": "JL.KEDOYA ANGSANA BLOK B II NO.25, KEDOYA SELATAN KEBON JERUK, JAKARTA BARAT DKI JAKARTA",
  "business_trade": null,
  "tax_obligation": "PPN",
  "letter_confirmed_since": "1992-03-21",
  "letter_issued_place": "Jakarta Barat",
  "letter_issued_date": "2015-04-17",
  "signing_official_title": "a.n. Kepala Kantor Kepala Seksi Pelayanan",
  "signing_official_name": "MUNAWAM",
  "signing_official_number": "196005151981031001"
}
```

| Property name | Description |
| --- | --- |
| `letter_number` | SPPKP letter reference number, e.g. 'S-47PKP/WPJ.05/KP.1003/2015' |
| `tax_office_region` | Regional tax office (Kantor Wilayah DJP) |
| `tax_office_name` | Issuing local tax office (KPP Pratama) |
| `tax_office_address` | Issuing tax office address |
| `business_tax_number` | Nomor Pokok Wajib Pajak / NPWP (15 or 16 digits format) |
| `business_name` | Taxpayer / business actor name (Nama) |
| `business_fields` | Business classification (Klasifikasi Lapangan Usaha / KLU) entries |
| `business_fields[].field_code` | Business classification code (Kode KLU) |
| `business_fields[].field_title` | Business classification title (Judul KLU) |
| `business_address` | Registered business address (Alamat) |
| `business_trade` | Trade / business brand name (Merk Dagang/Usaha), null if printed as a placeholder dash |
| `tax_obligation` | Checked tax obligation(s) (Kewajiban Pajak), joined with '; ' if more than one is checked |
| `letter_confirmed_since` | Date confirmed as a Taxable Entrepreneur (terhitung sejak), normalized to ISO 8601 (YYYY-MM-DD) |
| `letter_issued_place` | Place of issuance |
| `letter_issued_date` | Issuance date, normalized to ISO 8601 (YYYY-MM-DD) |
| `signing_official_title` | Title of the signing official, verbatim as printed |
| `signing_official_name` | Name of the signing official |
| `signing_official_number` | Civil servant registration number of the signing official (NIP) |

<a id="identity_passport"></a>

## Passport (`identity_passport`)

Unlike the Indonesian document types above, a passport's printed labels vary by issuing country and language ("Surname"/"Nom"/"姓"/"성명"/"Apelyido"). What's universal is the **Machine Readable Zone (MRZ)** - two fixed-width 44-character lines at the bottom of every passport bio-data page worldwide - so extraction centers on that, plus the handful of visual fields present on essentially every passport regardless of country:

### Example

```json
{
  "document_type": "P",
  "document_issuing_country": "USA",
  "holder_surname": "TRAVELER",
  "holder_given_names": "HAPPY",
  "holder_passport_number": "E00007734",
  "holder_nationality": "USA",
  "holder_birth_date": "1990-02-05",
  "holder_gender": "F",
  "holder_birth_place": "WASHINGTON D.C., U.S.A.",
  "document_issued_date": "2020-10-15",
  "document_expiry_date": "2030-10-14",
  "document_issuing_authority": "UNITED STATES DEPARTMENT OF STATE",
  "document_mrz_line1": "P<USATRAVELER<<HAPPY<<<<<<<<<<<<<<<<<<<<<<<<",
  "document_mrz_line2": "E000077347USA6502056F3010145900100120<095838"
}
```

| Property name | Description |
| --- | --- |
| `document_type` | MRZ document code, normally 'P' for an ordinary passport |
| `document_issuing_country` | 3-letter ICAO issuing country/organization code |
| `holder_surname` | Holder's surname/family name |
| `holder_given_names` | Holder's given name(s) |
| `holder_passport_number` | Passport document number |
| `holder_nationality` | 3-letter ICAO nationality code |
| `holder_birth_date` | Date of birth, normalized to ISO 8601 (YYYY-MM-DD) |
| `holder_gender` | Sex as printed/encoded: 'M', 'F', or 'X' |
| `holder_birth_place` | Place of birth, if printed (not every issuing country prints this) |
| `document_issued_date` | Date the passport was issued, normalized to ISO 8601 (YYYY-MM-DD) |
| `document_expiry_date` | Date the passport expires, normalized to ISO 8601 (YYYY-MM-DD) |
| `document_issuing_authority` | Authority that issued the passport |
| `document_mrz_line1` | Raw first line of the Machine Readable Zone, verbatim (44 characters, TD3 format) |
| `document_mrz_line2` | Raw second line of the Machine Readable Zone, verbatim (44 characters, TD3 format) |

<a id="business_deed"></a>

## Business Deed & SK Kemenkumham (`business_deed`)

Extracts the key filing metadata from an Indonesian notarial business deed (Akta Pendirian/Perubahan) together with its Kemenkumham confirmation decree (SK - Surat Keputusan Menteri Hukum dan Hak Asasi Manusia), which are commonly bundled into a single multi-page filing:

### Example

```json
{
  "deed_type": "Perubahan",
  "deed_number": "151",
  "deed_date": "2022-04-19",
  "notary_name": "JOSE DIMA SATRIA, S.H., M.Kn",
  "notary_address": "Jalan Benda, Jakarta Selatan",
  "decision_number": "AHU-0028078.AH.01.02.TAHUN 2022",
  "decision_issued_date": "2022-04-19"
}
```

| Property name | Description |
| --- | --- |
| `deed_type` | Deed type (Tipe Akta): 'Pendirian' (establishment) or 'Perubahan' (amendment) |
| `deed_number` | Deed number (No. Akta) |
| `deed_date` | Deed signing date (Tanggal Pembuatan), normalized to ISO 8601 (YYYY-MM-DD) |
| `notary_name` | Notary's name (Nama Notaris), including academic title suffixes as printed |
| `notary_address` | Notary's office address or domicile (Alamat Notaris) |
| `decision_number` | SK decree number (Nomor SK), e.g. 'AHU-0028078.AH.01.02.TAHUN 2022' or an older 'C2-10671.HT.01.01.TH.88' style number |
| `decision_issued_date` | SK decree date (Tanggal Pembuatan), normalized to ISO 8601 (YYYY-MM-DD) |

<a id="identity_stay"></a>

## Kartu Izin Tinggal Terbatas (KITAS) (`identity_stay`)

Extracts the holder's identity, immigration and passport identifiers, separate permit and passport expiry dates, stay status, and issuance details from an electronic limited stay permit:

### Example

```json
{
  "permit_issuing_office": "KANIM KELAS I KHUSUS NON TPI JAKARTA SELATAN",
  "permit_issuing_office_address": "JL. CONTOH NO. 10 JAKARTA SELATAN",
  "permit_niora": "AB12345678",
  "permit_number": "2C21AB1234YZ",
  "permit_expiry_date": "2025-04-18",
  "permit_index": "1B",
  "holder_full_name": "JANE DOE",
  "holder_birth_place": "SINGAPORE",
  "holder_birth_date": "1984-03-04",
  "holder_passport_number": "P1234567",
  "holder_passport_expiry_date": "2028-01-11",
  "holder_nationality": "SINGAPURA",
  "holder_gender": "FEMALE",
  "holder_address": "JL. CONTOH NO. 10 RT 001 RW 002, KEBAYORAN LAMA",
  "holder_occupation": "INVESTOR",
  "holder_status": "INVESTMENT",
  "holder_guarantor": null,
  "permit_issued_place": "Jakarta",
  "permit_issued_date": "2024-01-26"
}
```

| Property name | Description |
| --- | --- |
| `permit_issuing_office` | Immigration office printed in the header |
| `permit_issuing_office_address` | Address of the issuing immigration office |
| `permit_niora` | NIORA immigration registration number |
| `permit_number` | Limited stay permit number |
| `permit_expiry_date` | Stay/multiple entries permit expiry date in YYYY-MM-DD |
| `permit_index` | Stay permit index as printed |
| `holder_full_name` | Holder's full name |
| `holder_birth_place` | Place of birth, separate from the birth date |
| `holder_birth_date` | Date of birth in YYYY-MM-DD |
| `holder_passport_number` | Holder's passport number |
| `holder_passport_expiry_date` | Passport expiry date in YYYY-MM-DD |
| `holder_nationality` | Nationality as printed |
| `holder_gender` | Gender as printed |
| `holder_address` | Holder's address in Indonesia |
| `holder_occupation` | Occupation as printed |
| `holder_status` | Immigration stay status as printed |
| `holder_guarantor` | Guarantor name, when printed |
| `permit_issued_place` | Place in the issue line at the foot of the permit |
| `permit_issued_date` | Date in the issue line at the foot of the permit, in YYYY-MM-DD |

<a id="certificate_local_value"></a>

## Sertifikat Tingkat Komponen Dalam Negeri (TKDN) (`certificate_local_value`)

Extracts product details, TKDN value, verification and certificate numbers, company details, validity period, and issuer details from a TKDN certificate:

### Example

```json
{
  "product_name": "Basket Ecenggondok",
  "product_type": "Ecenggondok",
  "product_specification": "38 x 27 x 19 cm",
  "product_hs": "44209010",
  "product_brand": null,
  "product_local_value": 96.72,
  "product_standard": null,
  "product_certificate": null,
  "report_number": "LPA-3426/PK-3506/PTKDN.DIPA-INFRAS/VII/21",
  "certificate_valid_year": 3,
  "business_name": "CV. Contoh Indonesia",
  "business_address": "Jl. Contoh No. 7, Bantul, D.I. Yogyakarta",
  "business_tax_number": "82.934.355.7-543.000",
  "business_field": "Industri Barang Bangunan Dari Kayu (KBLI: 16221)",
  "certificate_number": "4623/SJ-IND.8/TKDN/7/2021",
  "certificate_issued_place": "Jakarta",
  "certificate_issued_date": "2021-07-28",
  "signing_official_title": "Kepala Pusat Peningkatan Penggunaan Produk Dalam Negeri",
  "signing_official_name": "Nila Kumalasari",
  "certificate_qr_number": "23361"
}
```

| Property name | Description |
| --- | --- |
| `product_name` | Jenis Produk |
| `product_type` | Tipe |
| `product_specification` | Spesifikasi, including wrapped lines |
| `product_hs` | Kode HS |
| `product_brand` | Merk |
| `product_local_value` | Numeric TKDN percentage without the percent sign; null when only Terlampir is printed |
| `product_standard` | Standard Produk |
| `product_certificate` | Sertifikat Produk |
| `report_number` | No. Laporan verification report number |
| `certificate_valid_year` | Printed validity period in years as a JSON integer; no expiry date is inferred |
| `business_name` | Nama Perusahaan, the certificate holder |
| `business_address` | Alamat of the certificate holder, including wrapped lines |
| `business_tax_number` | Company NPWP |
| `business_field` | Bidang Usaha or Jenis Industri, including the printed KBLI code |
| `certificate_number` | No. Tanda Sah certificate number, distinct from No. Laporan |
| `certificate_issued_place` | Place in the issue line |
| `certificate_issued_date` | Date in the issue line, normalized to YYYY-MM-DD |
| `signing_official_title` | Title of the signing official |
| `signing_official_name` | Name of the signing official |
| `certificate_qr_number` | Printed number below the QR code, when present |

<a id="bank_account"></a>

## Bank Account (`bank_account`)

Extracts the account-holding bank, branch, account number, holder, and account type from a passbook, statement, or account letter:

### Example

```json
{
  "bank_name": "Bank Rakyat Indonesia",
  "bank_branch": "3868 UNIT MENES LABUAN",
  "account_number": "3868-01-000123-45-6",
  "account_holder": "BUDI SANTOSO",
  "account_type": "Simpedes"
}
```

| Property name | Description |
| --- | --- |
| `bank_name` | Name of the bank that holds the account |
| `bank_branch` | Account branch or unit as printed, including a KCP prefix when present |
| `account_number` | Account number as text, preserving leading zeros and printed hyphens |
| `account_holder` | Name of the account owner, not a transaction counterparty |
| `account_type` | Account product or type when printed |

<a id="certificate_education"></a>

## Ijazah / Academic Transcript (`certificate_education`)

Extracts student identity, institution details, education program, enrollment date, total credits, GPA, and the repeated course table:

### Example

```json
{
  "transcript_number": "001234/2021",
  "student_name": "Rudi Hartono",
  "student_number": "00123456",
  "student_major": "Teknik Mesin",
  "student_institution": "Politeknik Negeri Bandung",
  "enroll_level": "D3",
  "enroll_date": "2010-09-01",
  "transcript_credit": "110",
  "transcript_grade": 3.36,
  "transcript_issued_place": "Bandung",
  "transcript_issued_date": "2015-10-12",
  "enroll_courses": [
    {
      "course_code": "TM101",
      "course_name": "Matematika",
      "course_credits": 2,
      "course_grade": 3,
      "course_semester": "I"
    }
  ]
}
```

| Property name | Description |
| --- | --- |
| `transcript_number` | Printed transcript or serial number, distinct from NIM/NPM |
| `student_name` | Graduate's name (Nama Karyawan in the target education form; Nama Mahasiswa/Nama on the source) |
| `student_number` | Student registration number (NIM/NPM/Nomor Induk Mahasiswa), preserving leading zeros |
| `student_major` | Jurusan/Fakultas for the target form; prefer the printed study program or major, then faculty |
| `student_institution` | Name of the issuing educational institution (Lembaga Pendidikan) |
| `enroll_level` | Education level or program, such as D3, D4, S1, S2, or Profesi, only when supported by the document |
| `enroll_date` | Enrollment or starting date in YYYY-MM-DD |
| `transcript_credit` | Total completed SKS or credits, not a single course's credits |
| `transcript_grade` | Numeric overall IPK/GPA, separate from a course grade or grading legend |
| `transcript_issued_place` | Place in the transcript's issue/signature line |
| `transcript_issued_date` | Date in the transcript's issue/signature line in YYYY-MM-DD |
| `enroll_courses` | Repeated course/subject rows from the transcript, when readable |
| `enroll_courses[].course_code` | Printed course or subject code |
| `enroll_courses[].course_name` | Printed course or subject name |
| `enroll_courses[].course_credits` | Numeric course credit value (SKS/credit) |
| `enroll_courses[].course_grade` | Numeric course grade printed directly or obtained from the document's grading legend |
| `enroll_courses[].course_semester` | Semester or term heading for this course, when printed |

<a id="certificate_competency"></a>

## Course / Competency Certificate (`certificate_competency`)

Extracts informal education credentials: course completion, training, and professional competency certificates, including BNSP/LSP certificates:

### Example

```json
{
  "certificate_number": "64141 4211 2 000001 2018",
  "certificate_holder": "Budi Santoso",
  "training_title": "Kasir",
  "training_field": "Koperasi Jasa Keuangan",
  "training_institution": "Lembaga Sertifikasi Profesi Koperasi Jasa Keuangan",
  "training_start_date": null,
  "training_end_date": null,
  "training_grade": null,
  "certificate_issued_place": "Jakarta",
  "certificate_issued_date": "2018-12-21",
  "certificate_expiry_date": null,
  "training_units": null
}
```

| Property name | Description |
| --- | --- |
| `certificate_number` | Certificate number, separate from holder registration number |
| `certificate_holder` | Recipient or certificate holder's name |
| `training_title` | Course, training, certification scheme, or qualification name |
| `training_field` | Printed occupational area, separate from the qualification |
| `training_institution` | Course provider or issuing certification body (LSP); overseeing authority when no issuer is printed |
| `training_start_date` | Course or training start date in YYYY-MM-DD |
| `training_end_date` | Course or training end date in YYYY-MM-DD |
| `training_grade` | Printed course result or grade, preserving letter or numeric grading |
| `certificate_issued_place` | Place in the certificate issue/signature line |
| `certificate_issued_date` | Certificate issue date in YYYY-MM-DD |
| `certificate_expiry_date` | Explicitly printed expiry date in YYYY-MM-DD |
| `training_units` | Repeated competency unit codes and names, when printed |
| `training_units[].unit_code` | Printed competency unit code |
| `training_units[].unit_name` | Printed competency unit name, if present |
