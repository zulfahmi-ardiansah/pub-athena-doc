def get_certificate_education_system_prompt() -> str:
    return (
        "Extract education details from Indonesian ijazah, academic transcripts, and diploma attachments into the exact JSON schema.\n\n"
        "| JSON field | Printed label or location | Rule |\n"
        "| :--- | :--- | :--- |\n"
        "| transcript_number | No. Seri, Nomor Seri, No. Transkrip, Number | Certificate/transcript number, distinct from student_number |\n"
        "| student_name | Nama, Nama Mahasiswa, Nama Lengkap, Name | Student or graduate's own name |\n"
        "| student_number | NIM, NPM, Nomor Induk Mahasiswa, Student Registration Number, ID | Preserve leading zeros and separators |\n"
        "| student_major | Program Studi, Jurusan, Study Program, Fakultas | Full study program/major; use faculty only when no major is printed |\n"
        "| student_institution | Universitas, Institut, Politeknik, university header | Issuing institution |\n"
        "| enroll_level | Jenjang Pendidikan, Program Pendidikan, Program | Education level/program: D3, D4, S1, S2, S3, or printed professional program |\n"
        "| enroll_date | Mulai Pendidikan, Tanggal Masuk, Starting Date | Enrollment date in YYYY-MM-DD |\n"
        "| transcript_credit | Jumlah SKS, Total Credits | Total completed credits |\n"
        "| transcript_grade | IPK, Indeks Prestasi Kumulatif, GPA | Overall GPA as a JSON number |\n"
        "| transcript_issued_place | Place in final signature/date line | Issuing place |\n"
        "| transcript_issued_date | Final issue/signature date | YYYY-MM-DD |\n"
        "| enroll_courses | Repeated subject/course rows | One item per readable row: course_code, course_name, course_credits, course_grade, course_semester |\n\n"
        "STRICT GUIDELINES:\n"
        "1. Return null for missing, covered, or illegible values. Use only information printed in the document.\n"
        "2. Use student details from the header; exclude officials, parents, grading legends, and ministry names.\n"
        "3. Normalize enroll_date and transcript_issued_date to YYYY-MM-DD, including Indonesian textual dates and English month-first dates. Graduation dates must not replace enrollment or issue dates.\n"
        "4. Keep student_major (field of study) separate from enroll_level (education level/program). Prefer the study program over faculty for student_major.\n"
        "5. Output each bilingual fact once. Preserve leading zeros in both transcript_number and student_number.\n"
        "6. Course tables may be side-by-side or grouped by semester. Keep each row separate, use course_semester only when printed, and exclude totals and grading legends. Return enroll_courses as null when rows cannot be read reliably.\n"
        "7. Return only the requested fields. Each course contains course_code, course_name, course_credits, course_grade, and course_semester; omit weighted grade points.\n"
        "8. transcript_grade and each course's course_credits and course_grade must be JSON numbers, without quotes or labels. Convert decimal commas to decimal points. Use a printed numeric course grade or convert a letter grade only using the document's own grading legend. Return course_grade as null if neither is available; do not guess letter-grade values or use SKS x nilai as course_grade.\n"
    )


def get_certificate_education_user_prompt(raw_text: str) -> str:
    return (
        "Extract education details from this OCR text into the requested JSON schema:\n\n"
        f"```text\n{raw_text.strip()}\n```"
    )
