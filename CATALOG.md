# CATALOG.md

Every field extracted by each document module (`src/domain/documents/<slug>/schema.py`), with what it holds. Nested objects are listed as `parent.field`.

Fields that mean the same thing across modules share the same name: `name` (the document's primary named party), `address` (that party's own address), `tax_office`/`tax_office_address` (the issuing KPP), `birth_date`/`birth_place`, `issued_date`, `expiry_date`, `gender`. See `AGENTS.md` for the convention to follow when adding a new module.

## `identity_card` (Indonesian KTP)

| Property | Function |
|---|---|
| `province` | Province name |
| `city` | City or regency name |
| `id_number` | 16-digit population ID (NIK) |
| `name` | Holder's full name |
| `birth_place` | Place of birth |
| `birth_date` | Date of birth (ISO 8601) |
| `gender` | Sex: `LAKI-LAKI` or `PEREMPUAN` |
| `blood_type` | Blood type: `A`/`B`/`AB`/`O`/`-` |
| `address` | Street/residential address |
| `neighborhood_unit` | RT/RW numbering |
| `village` | Kelurahan/Desa (village/urban community) |
| `district` | Kecamatan (sub-district) |
| `religion` | Religion |
| `marital_status` | Marital status |
| `occupation` | Occupation/profession |
| `nationality` | `WNI` or `WNA` |
| `expiry_date` | Validity date (ISO 8601) or `SEUMUR HIDUP` (lifetime) |

## `tax_number` (Indonesian NPWP)

| Property | Function |
|---|---|
| `tax_number` | 15/16-digit taxpayer ID (NPWP) |
| `name` | Taxpayer name |
| `tax_office` | Registered tax office (KPP) |
| `tax_office_address` | Tax office address |
| `registration_date` | Registration date (ISO 8601) |

## `business_identification_number` (Indonesian NIB)

| Property | Function |
|---|---|
| `number` | 13-digit business ID (NIB) |
| `name` | Business actor name |
| `address` | Office address |
| `postal_code` | Office postal code |
| `phone_number` | Office phone number |
| `email` | Office email address |
| `investment_status` | `PMDN` (domestic) or `PMA` (foreign) |
| `issued_place` | Place of issuance |
| `issued_date` | Issuance date (ISO 8601) |
| `amendment_number` | Amendment sequence number, if amended |
| `amendment_date` | Amendment date (ISO 8601) |
| `printed_date` | Certificate print date (ISO 8601) |
| `signing_official_title` | Title of the signing official |
| `fields[]` | KBLI business classification line items |
| `fields[].no` | Row number in the KBLI table |
| `fields[].code` | 5-digit KBLI classification code |
| `fields[].title` | KBLI classification title |
| `fields[].business_location` | Business location for this row |
| `fields[].postal_code` | Postal code for this row's location |
| `fields[].risk_level` | Risk level (Rendah/Menengah Rendah/Menengah Tinggi/Tinggi) |
| `fields[].licenses[]` | Jenis/Status/Keterangan license entries for this row |
| `fields[].licenses[].license_type` | License type (e.g. NIB, Sertifikat Standar, Izin) |
| `fields[].licenses[].license_status` | License status (e.g. Terbit, Belum Terverifikasi) |
| `fields[].licenses[].remarks` | Remarks/instructions for that license |

## `tax_entity` (Indonesian SPPKP/PKP)

| Property | Function |
|---|---|
| `letter_number` | SPPKP letter reference number |
| `tax_office_region` | Regional tax office (Kantor Wilayah DJP) |
| `tax_office` | Issuing local tax office (KPP Pratama) |
| `tax_office_address` | Issuing tax office's address |
| `tax_number` | 15/16-digit taxpayer ID (NPWP) |
| `name` | Taxpayer/business actor name |
| `fields[]` | Business classification (KLU) entries |
| `fields[].code` | KLU classification code |
| `fields[].title` | KLU classification title |
| `address` | Registered business address |
| `trade_name` | Trade/brand name (`null` if printed as a placeholder dash) |
| `tax_obligation` | Checked tax obligation(s) (e.g. `PPN`), `; `-joined if multiple |
| `confirmed_since` | Date confirmed as a Taxable Entrepreneur (ISO 8601) |
| `issued_place` | Place of issuance |
| `issued_date` | Issuance date (ISO 8601) |
| `signing_official_title` | Title of the signing official |
| `signing_official_name` | Name of the signing official |
| `signing_official_number` | Signing official's civil servant number (NIP) |

## `identity_passport` (any ICAO Doc 9303 passport)

| Property | Function |
|---|---|
| `document_type` | MRZ document code, normally `P` |
| `issuing_country` | 3-letter ICAO issuing country code |
| `surname` | Holder's surname/family name |
| `given_names` | Holder's given name(s) |
| `passport_number` | Passport document number |
| `nationality` | 3-letter ICAO nationality code |
| `birth_date` | Date of birth (ISO 8601) |
| `gender` | `M`, `F`, or `X` |
| `birth_place` | Place of birth, if printed |
| `issued_date` | Issuance date (ISO 8601) |
| `expiry_date` | Expiry date (ISO 8601) |
| `issuing_authority` | Authority that issued the passport |
| `mrz_line1` | Raw first MRZ line, verbatim (44 chars) |
| `mrz_line2` | Raw second MRZ line, verbatim (44 chars) |

`surname`/`given_names` stay split rather than unified into `name` - the MRZ mandates this structure worldwide, so merging them would lose real information, unlike the naming choices elsewhere in this catalog.

## `business_deed` (Indonesian Akta + SK Kemenkumham)

| Property | Function |
|---|---|
| `deed_type` | Deed type (Tipe Akta), e.g. Akta Pendirian |
| `deed_number` | Deed number (No. Akta) |
| `deed_date` | Deed signing date (ISO 8601) |
| `notary_name` | Notary's name, with academic titles as printed |
| `notary_address` | Notary's office address/domicile |
| `legal_decision` | The Kemenkumham decree (SK) confirming this deed |
| `legal_decision.number` | SK decree number |
| `legal_decision.issued_date` | SK decree date (ISO 8601) |
