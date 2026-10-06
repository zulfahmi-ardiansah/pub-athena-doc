def get_certificate_local_value_system_prompt() -> str:
    return (
        "Extract an Indonesian TKDN certificate into the exact JSON schema.\n\n"
        "| JSON field | Printed label or location | Rule |\n"
        "| :--- | :--- | :--- |\n"
        "| product_name | Jenis Produk | Product name |\n"
        "| product_type | Tipe | Product type |\n"
        "| product_specification | Spesifikasi | Join wrapped lines with spaces |\n"
        "| hs_code | Kode HS | Preserve digits as text |\n"
        "| brand | Merk | Printed brand |\n"
        "| local_value | Nilai TKDN | JSON number without the percent sign; null for Terlampir |\n"
        "| product_standard | Standard Produk / Standar Produk | Printed standard |\n"
        "| product_certificate | Sertifikat Produk | Printed product certificate |\n"
        "| report_number | No. Laporan | Verification report number, not certificate number |\n"
        "| validity_years | berlaku ... tahun | JSON integer for the number of years, e.g. 3 |\n"
        "| company_name | Nama Perusahaan | Certificate holder |\n"
        "| company_address | Alamat | Join wrapped address lines with spaces |\n"
        "| company_tax_number | NPWP | Preserve punctuation and leading zeroes |\n"
        "| industry | Bidang Usaha / Jenis Industri | Preserve industry name and any KBLI code |\n"
        "| certificate_number | No. Tanda Sah | Certificate number, not No. Laporan |\n"
        "| issued_place | Footer place/date line | Place before comma |\n"
        "| issued_date | Footer place/date line | ISO date YYYY-MM-DD |\n"
        "| signing_official_title | Footer title | Official's title |\n"
        "| signing_official_name | Footer name | Official's name |\n"
        "| qr_reference | Number below QR code | Printed number only, if legible |\n\n"
        "STRICT GUIDELINES:\n"
        "1. Extract only what is printed. Return null for absent, obscured, illegible, empty, or dash-only fields.\n"
        "2. Return null for local_value when only 'Terlampir' is printed; do not invent a percentage from an attachment that is not provided.\n"
        "3. Output numeric Nilai TKDN without the percent sign, e.g. 96,72% becomes the JSON number 96.72. Ignore Terbilang.\n"
        "4. Normalize issued_date to YYYY-MM-DD, including Indonesian month names. Do not calculate an expiry date from validity_years.\n"
        "5. Keep No. Laporan and No. Tanda Sah separate. Bidang Usaha and Jenis Industri both map to industry.\n"
        "6. Ignore regulation citations, watermark, stamps, signatures, and QR payload. Return the requested JSON object only.\n"
    )


def get_certificate_local_value_user_prompt(raw_text: str) -> str:
    return (
        "Extract Indonesian TKDN certificate data from this OCR text into the requested JSON schema:\n\n"
        f"```text\n{raw_text.strip()}\n```"
    )
