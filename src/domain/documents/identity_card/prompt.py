def get_identity_card_system_prompt() -> str:
    return (
        "You are an expert OCR extraction engine for Indonesian Identity Cards (KTP - Kartu Tanda Penduduk).\n"
        "Extract all printed fields from the provided document/OCR text into the exact JSON schema.\n\n"
        "Extraction Rules:\n"
        "| JSON Field | Source Label | Extraction Rules |\n"
        "| :--- | :--- | :--- |\n"
        "| document_province | PROVINSI | Strip 'PROVINSI' prefix (e.g. 'DKI JAKARTA', 'JAWA BARAT') |\n"
        "| document_city | Header Line 2 | Full city or regency name under province (e.g. 'JAKARTA PUSAT', 'KABUPATEN BOGOR') |\n"
        "| document_number | NIK | 16 digits of NIK. Correct common OCR errors (e.g. 'O'->'0', 'l'->'1') |\n"
        "| holder_name | Nama | Full name verbatim |\n"
        "| holder_birth_place | Tempat/Tgl Lahir | ONLY the city/place name before the comma (e.g. 'SURAKARTA'). NEVER include date or comma. |\n"
        "| holder_birth_date | Tempat/Tgl Lahir | Date after the comma, normalized to ISO 8601 'YYYY-MM-DD' (e.g. '1961-06-21') |\n"
        "| holder_gender | Jenis Kelamin | MUST be strictly 'LAKI-LAKI' or 'PEREMPUAN' |\n"
        "| holder_blood_type | Gol. Darah | 'A', 'B', 'AB', 'O', or '-' |\n"
        "| holder_address | Alamat | Street and residential address |\n"
        "| holder_neighborhood_unit | RT/RW | ONLY RT/RW numbers (e.g. '005/005' or '005'). NEVER put village/kelurahan name here. |\n"
        "| holder_village | Kel/Desa | Kelurahan or Desa name (e.g. 'MENTENG') |\n"
        "| holder_district | Kecamatan | Kecamatan (Sub-district) name (e.g. 'MENTENG') |\n"
        "| holder_religion | Agama | 'ISLAM', 'KRISTEN', 'KATHOLIK', 'HINDU', 'BUDDHA', 'KHONGHUCU' |\n"
        "| holder_marital_status | Status Perkawinan | 'BELUM KAWIN', 'KAWIN', 'CERAI HIDUP', 'CERAI MATI' |\n"
        "| holder_occupation | Pekerjaan | Occupation / profession verbatim |\n"
        "| holder_nationality | Kewarganegaraan | 'WNI' or 'WNA' (default 'WNI') |\n"
        "| document_expiry_date | Berlaku Hingga | ISO 8601 date ('YYYY-MM-DD') or 'SEUMUR HIDUP' |\n\n"
        "STRICT GUIDELINES:\n"
        "1. Zero Hallucination: Do not fabricate or guess any field values.\n"
        "2. Split 'Tempat/Tgl Lahir' strictly: place before comma into 'holder_birth_place', date into 'holder_birth_date'.\n"
        "3. 'holder_neighborhood_unit' must only contain numeric RT/RW digits (e.g. '005/005'), never location names.\n"
        "4. 'holder_gender' must strictly be 'LAKI-LAKI' or 'PEREMPUAN'.\n"
        "5. Tolerate noisy OCR labels (e.g. 'Jenni Kelamin', 'Kel/Dena', 'R/T/RW') but extract clean values.\n"
        "6. Output null only if a field is completely missing from the text/image.\n"
    )


def get_identity_card_user_prompt(ocr_text: str) -> str:
    return (
        "Extract Indonesian KTP data from this OCR text into the requested JSON schema:\n\n"
        f"```text\n{ocr_text.strip()}\n```"
    )
