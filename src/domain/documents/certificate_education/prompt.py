def get_certificate_education_system_prompt() -> str:
    return (
        "Extract education details from Indonesian ijazah, academic transcripts, and diploma attachments into the exact JSON schema.\n\n"
        "| JSON field | Printed label or location | Rule |\n"
        "| :--- | :--- | :--- |\n"
        "| number | No. Seri, Nomor Seri, No. Transkrip, Number | Certificate/transcript number, distinct from student_number |\n"
        "| student_name | Nama, Nama Mahasiswa, Nama Lengkap, Name | Student or graduate's own name |\n"
        "| student_number | NIM, NPM, Nomor Induk Mahasiswa, Student Registration Number, ID | Preserve leading zeros and separators |\n"
        "| student_major | Program Studi, Jurusan, Study Program, Fakultas | Full study program/major; use faculty only when no major is printed |\n"
        "| education_institution | Universitas, Institut, Politeknik, university header | Issuing institution |\n"
        "| education_address | Campus address, Alamat Fakultas, Faculty Address | Full printed institutional address |\n"
        "| birth_place | Tempat/Tanggal Lahir, Place/Date of Birth | Place only |\n"
        "| birth_date | Tempat/Tanggal Lahir, Date of Birth | YYYY-MM-DD |\n"
        "| enroll_level | Jenjang Pendidikan, Program Pendidikan, Program | Education level/program: D3, D4, S1, S2, S3, or printed professional program |\n"
        "| enroll_date | Mulai Pendidikan, Tanggal Masuk, Starting Date | Enrollment date in YYYY-MM-DD |\n"
        "| enroll_credit | Jumlah SKS, Total Credits | Total completed credits |\n"
        "| enroll_grade | IPK, Indeks Prestasi Kumulatif, GPA | Overall GPA as a JSON number |\n"
        "| issued_place | Place in final signature/date line | Issuing place |\n"
        "| issued_date | Final issue/signature date | YYYY-MM-DD |\n"
        "| courses | Repeated subject/course rows | One item per readable row: code, name, credits, grade, semester |\n\n"
        "STRICT GUIDELINES:\n"
        "1. Return null for missing, covered, or illegible values. Use only information printed in the document.\n"
        "2. Use student details from the header; exclude officials, parents, grading legends, and ministry names.\n"
        "3. Normalize birth_date, enroll_date, and issued_date to YYYY-MM-DD, including Indonesian textual dates and English month-first dates. Graduation dates must not replace enrollment or issue dates.\n"
        "4. Preserve the institution's full printed address. Do not substitute a birth place, student address, or a guessed city.\n"
        "5. Keep student_major (field of study) separate from enroll_level (education level/program). Prefer the study program over faculty for student_major.\n"
        "6. Output each bilingual fact once. Preserve leading zeros in both number and student_number.\n"
        "7. Course tables may be side-by-side or grouped by semester. Keep each row separate, use semester only when printed, and exclude totals and grading legends. Return courses as null when rows cannot be read reliably.\n"
        "8. Return only the requested fields. Each course contains code, name, credits, grade, and semester; omit weighted grade points.\n"
        "9. enroll_grade and each course's credits and grade must be JSON numbers, without quotes or labels. Convert decimal commas to decimal points. Use a printed numeric course grade or convert a letter grade only using the document's own grading legend. Return grade as null if neither is available; do not guess letter-grade values or use SKS x nilai as grade.\n"
    )


def get_certificate_education_user_prompt(raw_text: str) -> str:
    return (
        "Extract education details from this OCR text into the requested JSON schema:\n\n"
        f"```text\n{raw_text.strip()}\n```"
    )
