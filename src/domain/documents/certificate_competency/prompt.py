def get_certificate_competency_system_prompt() -> str:
    return (
        "Extract informal education certificates: courses, training, course completion, and professional competency certifications into the exact JSON schema.\n\n"
        "| JSON field | Printed label or location | Rule |\n"
        "| :--- | :--- | :--- |\n"
        "| number | No., Nomor Sertifikat, Certificate Number | Certificate number, preserving spaces and separators |\n"
        "| name | Nama Peserta, Name, Dengan ini menyatakan bahwa | Recipient or holder, not a signatory |\n"
        "| title | Course title, Nama Pelatihan, Kualifikasi/Kompetensi, Skema Sertifikasi | Actual course or awarded qualification, not the generic Sertifikat heading |\n"
        "| field | Pada bidang pekerjaan, Telah kompeten pada bidang | Occupational area, distinct from qualification |\n"
        "| institution | Course provider, Penyelenggara, Lembaga Sertifikasi Profesi | Issuing provider/body, including the full LSP name |\n"
        "| training_start_date | Tanggal Mulai, course period start | YYYY-MM-DD |\n"
        "| training_end_date | Tanggal Selesai, course period end | YYYY-MM-DD |\n"
        "| grade | Nilai, Grade, course result | Preserve printed letter or numeric grade as a string |\n"
        "| issued_place | Issue/signature line | Issuing place |\n"
        "| issued_date | Issue/signature date | YYYY-MM-DD |\n"
        "| expiry_date | Berlaku Sampai, Valid Until | Explicit expiry date in YYYY-MM-DD only |\n"
        "| signing_official_name | Signature block | Printed official name |\n"
        "| signing_official_title | Direktur, Ketua, signatory role | Printed role |\n"
        "| units | Repeating competency list/table | One code/name item per competency unit; missing names are null |\n\n"
        "STRICT GUIDELINES:\n"
        "1. Extract only printed facts. Missing, covered, illegible, or placeholder-dash values are null. Return only this schema.\n"
        "2. Keep certificate number separate from holder registration number, barcode/security serials, and unrelated identifiers.\n"
        "3. Use the recipient's name, not signatories, instructors, or organizers. Use the issuing course provider or certification body for institution. If only an overseeing authority is printed, use its name. When both are printed, prefer the issuing provider/body; do not combine their names.\n"
        "4. Normalize all dates to YYYY-MM-DD, including Indonesian textual dates and English month-first dates. Keep training, issue, and expiry dates separate.\n"
        "5. Use only an explicitly printed expiry_date; do not calculate expiry_date from a validity duration. A course may have no expiry date.\n"
        "6. Preserve grade such as A or A- without inventing a numeric conversion.\n"
        "7. Bilingual text repeats facts; output each fact once using the printed Indonesian wording when available. field is the area; title is the qualification or course.\n"
        "8. Keep each competency unit separate. Code-only numbered lists have name=null. Reverse-page tables may supply names. Do not invent missing units or names.\n"
        "9. Extract one certificate per request. For collages with several certificates and no single identifiable target, leave conflicting scalar fields null rather than combining different certificates.\n"
    )


def get_certificate_competency_user_prompt(raw_text: str) -> str:
    return (
        "Extract informal education certificate details from this OCR text into the requested JSON schema:\n\n"
        f"```text\n{raw_text.strip()}\n```"
    )
