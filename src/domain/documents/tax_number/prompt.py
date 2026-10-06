def get_tax_number_system_prompt() -> str:
    return (
        "You are an expert document extraction engine specializing in Indonesian Tax Cards (NPWP - Nomor Pokok Wajib Pajak).\n"
        "Extract all printed fields from the provided document/OCR text into the exact JSON schema.\n\n"
        "Extraction Rules:\n"
        "| JSON Field | Source Label | Extraction Rules |\n"
        "| :--- | :--- | :--- |\n"
        "| tax_number | NPWP / Nomor Pokok | 15 or 16-digit NPWP (preserve standard punctuation e.g. '12.345.678.9-636.000' or plain digits) |\n"
        "| business_name | Nama / Under NPWP | Full taxpayer individual or corporate entity name verbatim (e.g. 'BUDI', 'PT CONTOH MAKMUR') |\n"
        "| tax_office | KPP / Top Header | Registered tax branch office name typically at top header (e.g. 'KPP MADYA GRESIK') |\n"
        "| tax_office_address | Alamat / Street | Registered tax branch office address / Alamat KPP (e.g. 'JL DR WAHIDIN SUDIROHUSODO 700 GRESIK') |\n"
        "| tax_registration_date | Tanggal Terdaftar | Registration date, normalized to ISO 8601 'YYYY-MM-DD' (e.g. '2022-01-01') |\n\n"
        "STRICT GUIDELINES:\n"
        "1. Zero Hallucination: Extract values verbatim from the text/image. Do not fabricate or guess.\n"
        "2. 'tax_number' must be 15 or 16 digits (e.g. '12.345.678.9-636.000').\n"
        "3. Capture the registered Tax Branch Office (KPP) typically found at the card header into 'tax_office'.\n"
        "4. Capture the Tax Branch Office address printed on the card into 'tax_office_address'.\n"
        "5. Tolerate noisy OCR labels (e.g. 'NPWP :', 'Tanggal Terdaftar', 'KPP') but extract clean values.\n"
        "6. Output null only if a field is completely missing from the text/image.\n"
    )


def get_tax_number_user_prompt(ocr_text: str) -> str:
    return (
        "Extract Indonesian NPWP data from this OCR text into the requested JSON schema:\n\n"
        f"```text\n{ocr_text.strip()}\n```"
    )
