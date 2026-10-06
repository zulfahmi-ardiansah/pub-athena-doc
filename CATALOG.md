# Document Property Catalog

Properties returned in the `data` object for each registered document type. Descriptions follow the document schemas. Nested paths use `[]` for each item in a repeated list. Fields can be `null` when the source document does not provide a value.

## Kartu Tanda Penduduk (KTP) (`identity_card`)

Indonesian National Identity Card.

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

## Nomor Pokok Wajib Pajak (NPWP) (`tax_number`)

Indonesian Taxpayer Identification Card.

| Property name | Description |
| --- | --- |
| `tax_number` | Nomor Pokok Wajib Pajak / NPWP (15 or 16 digits format) |
| `business_name` | Taxpayer Name (Nama Wajib Pajak, e.g. 'BUDI') |
| `tax_office` | Tax Branch Office where registered (Kantor Pelayanan Pajak / KPP, e.g. 'KPP MADYA GRESIK') |
| `tax_office_address` | Tax Branch Office Address (Alamat KPP, e.g. 'JL DR WAHIDIN SUDIROHUSODO 700 GRESIK') |
| `tax_registration_date` | Registration date (Tanggal Terdaftar), normalized to ISO 8601 (YYYY-MM-DD) |

## Nomor Induk Berusaha (NIB) (`business_identification_number`)

Indonesian Business Identification Number Certificate.

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

## Surat Pengukuhan Pengusaha Kena Pajak (SPPKP/PKP) (`tax_entity`)

Indonesian Taxable Entrepreneur Confirmation Letter.

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

## Passport (`identity_passport`)

International passport bio-data page (ICAO Doc 9303).

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

## Business Deed & SK Kemenkumham (`business_deed`)

Indonesian notarial business deed (Akta) and its Kemenkumham confirmation decree (SK).

| Property name | Description |
| --- | --- |
| `deed_type` | Deed type (Tipe Akta): 'Pendirian' (establishment) or 'Perubahan' (amendment) |
| `deed_number` | Deed number (No. Akta) |
| `deed_date` | Deed signing date (Tanggal Pembuatan), normalized to ISO 8601 (YYYY-MM-DD) |
| `notary_name` | Notary's name (Nama Notaris), including academic title suffixes as printed |
| `notary_address` | Notary's office address or domicile (Alamat Notaris) |
| `decision_number` | SK decree number (Nomor SK), e.g. 'AHU-0028078.AH.01.02.TAHUN 2022' or an older 'C2-10671.HT.01.01.TH.88' style number |
| `decision_issued_date` | SK decree date (Tanggal Pembuatan), normalized to ISO 8601 (YYYY-MM-DD) |

## Kartu Izin Tinggal Terbatas (KITAS) (`identity_stay`)

Indonesian electronic limited stay permit.

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

## Sertifikat Tingkat Komponen Dalam Negeri (TKDN) (`certificate_local_value`)

Indonesian domestic content certificate.

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

## Bank Account (`bank_account`)

Bank account details from passbooks, statements, and account letters.

| Property name | Description |
| --- | --- |
| `bank_name` | Name of the bank that holds the account |
| `bank_branch` | Account branch or unit as printed, including a KCP prefix when present |
| `account_number` | Account number as text, preserving leading zeros and printed hyphens |
| `account_holder` | Name of the account owner, not a transaction counterparty |
| `account_type` | Account product or type when printed |

## Ijazah / Academic Transcript (`certificate_education`)

Education and graduation details from Indonesian diplomas and academic transcripts.

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

## Course / Competency Certificate (`certificate_competency`)

Informal education, training, course completion, and professional competency certificates.

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
