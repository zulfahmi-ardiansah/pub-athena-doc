def get_bank_account_information_system_prompt() -> str:
    return (
        "Extract bank account information from Indonesian or English passbooks, statements, account letters, and payment instructions into the exact JSON schema.\n\n"
        "| JSON field | Printed label or location | Rule |\n"
        "| :--- | :--- | :--- |\n"
        "| bank_name | Bank logo/name or Bank Name | The bank holding the account, not a transaction counterparty |\n"
        "| bank_branch | Kantor, Cabang, Branch, KCP | Preserve the full branch name, including KCP when printed |\n"
        "| account_number | No. Rekening, Account No./Number, ACC. No. | Preserve leading zeros and printed hyphens |\n"
        "| account_holder_name | Nama, Atas Nama, Account Holder, name beside account number | Owner of this account |\n"
        "| account_type | Product name, Jenis Rekening, Account Type/Name | Simpedes, BritAma, Tabungan, Checking, or other printed type |\n\n"
        "STRICT GUIDELINES:\n"
        "1. Extract only values shown in the document. Return null for missing, covered, or illegible values.\n"
        "2. Do not confuse the account number with CIF, passbook serial number, KTP/NIK, phone, statement number, or transaction reference.\n"
        "3. Keep KCP as part of bank_branch when present. In BCA passbooks, the account number and holder can appear on unlabeled lines immediately below the KCP branch line.\n"
        "4. On statements, use the owner in the account header, not a person or company mentioned in a transaction row.\n"
        "5. On payment letters, use the bank and account named in the transfer instructions; do not use the recipient company as account holder.\n"
        "6. Ignore balances, transaction tables, dates, signatures, bank advertisements, and unrelated document identifiers. Return only the five requested JSON fields.\n"
    )


def get_bank_account_information_user_prompt(raw_text: str) -> str:
    return (
        "Extract bank account information from this OCR text into the requested JSON schema:\n\n"
        f"```text\n{raw_text.strip()}\n```"
    )
