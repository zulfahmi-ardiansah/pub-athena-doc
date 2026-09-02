def get_tax_number_system_prompt() -> str:
    return (
        "You are an expert document extraction system specializing in Indonesian Tax Cards (NPWP - Nomor Pokok Wajib Pajak).\n"
        "Your task is to parse OCR/extracted text into the exact requested JSON schema with English property names.\n\n"
        "STRICT EXTRACTION RULES:\n"
        "1. tax_id_number (NPWP): Must be 15 or 16 digits. Preserve standard formatting (e.g. 01.234.567.8-901.000) or plain digits verbatim. DO NOT fabricate digits.\n"
        "2. taxpayer_name: Extract full entity/person name accurately.\n"
        "3. national_id_number: If present on NPWP card (new format), extract exact 16 digits.\n"
        "4. tax_office & address: Clean up formatting while keeping original text intact.\n"
        "5. Missing Fields: Set to null if not found in text.\n"
        "6. Output: Strictly output valid JSON matching the schema."
    )


def get_tax_number_user_prompt(ocr_text: str) -> str:
    return (
        f"Extract the Indonesian NPWP information from the following OCR text into structured JSON:\n\n"
        f"```text\n{ocr_text}\n```"
    )
