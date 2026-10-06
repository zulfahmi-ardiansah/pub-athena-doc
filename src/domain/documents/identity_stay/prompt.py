def get_identity_stay_system_prompt() -> str:
    return (
        "Extract the printed fields of an Indonesian electronic limited stay permit (KITAS / ITAS) into the JSON schema.\n\n"
        "| JSON field | Source label or location | Rule |\n"
        "| :--- | :--- | :--- |\n"
        "| issuing_office | KANIM header | Immigration office name, not the ministry name |\n"
        "| issuing_office_address | Header below KANIM | Office street address |\n"
        "| niora | NIORA | Registration identifier |\n"
        "| permit_number | Permit Number | Permit identifier |\n"
        "| permit_expiry_date | Stay/Multiple Entries Permit Expiry | ISO date |\n"
        "| permit_index | Stay Permit Index | Preserve printed code |\n"
        "| full_name | Full Name | Complete printed name |\n"
        "| birth_place | Place / Date of Birth | Text before the slash |\n"
        "| birth_date | Place / Date of Birth | Date after the slash, ISO date |\n"
        "| passport_number | Passport Number | Preserve printed identifier |\n"
        "| passport_expiry_date | Passport Expiry | ISO date |\n"
        "| nationality | Nationality | Preserve printed country name |\n"
        "| gender | Gender | Preserve printed value |\n"
        "| address | Address | Join wrapped address lines with spaces |\n"
        "| occupation | Occupation | Preserve printed value |\n"
        "| status | Status | Immigration stay status, separate from occupation |\n"
        "| guarantor_name | Guarantor Name | Name only if this row is present |\n"
        "| issued_place | Footer place/date line | Place before the comma |\n"
        "| issued_date | Footer place/date line | ISO date after the comma |\n"
        "| signing_official_title | Footer below place/date | Official title as printed |\n\n"
        "STRICT GUIDELINES:\n"
        "1. Extract only values visible on the permit. Do not infer covered or illegible text.\n"
        "2. Return null for missing, covered, illegible, empty, or dash-only values, including an absent guarantor row.\n"
        "3. Normalize every date to YYYY-MM-DD. Do not put the birth place and birth date in the same field.\n"
        "4. Keep permit expiry and passport expiry separate. The footer date is the issue date, not an expiry date.\n"
        "5. Preserve identifier letters, numbers, and punctuation; do not guess obscured characters.\n"
        "6. Ignore the photo, QR code, disclaimer, screenshot controls, and watermark. Return the requested JSON object only.\n"
    )


def get_identity_stay_user_prompt(raw_text: str) -> str:
    return (
        "Extract Indonesian KITAS data from this OCR text into the requested JSON schema:\n\n"
        f"```text\n{raw_text.strip()}\n```"
    )
