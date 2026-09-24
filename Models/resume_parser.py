"""
Resume parser.

Pulls whatever it reliably can out of a resume (PDF / DOCX / TXT) using
regex + layout heuristics: name, email, phone, total years of experience,
current salary, expected salary, and skills.

This is deliberately NOT a guessing machine: any field it isn't confident
about is left as None rather than filled with a wrong value. Callers
(app.py) are expected to treat None fields as "not provided" and exclude
them from scoring rather than defaulting them to 0 -- a missing salary is
not the same thing as a salary of 0.
"""

import io
import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text(file_bytes: bytes, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    if name.endswith(".docx"):
        return _extract_docx(file_bytes)
    if name.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore")
    # Fall back: try PDF, then DOCX, then plain text.
    for fn in (_extract_pdf, _extract_docx):
        try:
            text = fn(file_bytes)
            if text.strip():
                return text
        except Exception:
            continue
    return file_bytes.decode("utf-8", errors="ignore")


def _extract_pdf(file_bytes: bytes) -> str:
    import pdfplumber

    parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
    return "\n".join(parts)


def _extract_docx(file_bytes: bytes) -> str:
    import docx

    document = docx.Document(io.BytesIO(file_bytes))
    parts = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{3,4}")

EXPERIENCE_PATTERNS = [
    re.compile(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\.?\s*(?:of\s+)?experience", re.I),
    re.compile(r"total\s+experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)", re.I),
    re.compile(r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)", re.I),
]

_MONEY = r"(?:rs\.?|inr|₹|\$|usd)?\s*([\d,]+(?:\.\d+)?)\s*(lpa|lakh|lakhs|k|thousand|per\s*annum|/annum|/yr|per\s*year)?"

SALARY_PATTERNS = {
    "current_salary": [
        re.compile(r"current\s*(?:ctc|salary|compensation)\s*[:\-]?\s*" + _MONEY, re.I),
        re.compile(r"present\s*(?:ctc|salary)\s*[:\-]?\s*" + _MONEY, re.I),
    ],
    "expected_salary": [
        re.compile(r"expected\s*(?:ctc|salary|compensation)\s*[:\-]?\s*" + _MONEY, re.I),
        re.compile(r"desired\s*(?:ctc|salary)\s*[:\-]?\s*" + _MONEY, re.I),
    ],
}

# A reasonably broad skills vocabulary to match against. Extend this list
# (or swap it for a company-specific taxonomy) as needed.
COMMON_SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "C", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "SQL", "NoSQL",
    "FastAPI", "Django", "Flask", "Spring", "Spring Boot", "Node.js", "Express",
    "React", "Angular", "Vue", "Next.js", "Redux", "HTML", "CSS", "Sass", "Tailwind",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Oracle", "DynamoDB",
    "Elasticsearch", "Kafka", "RabbitMQ", "GraphQL", "REST", "gRPC",
  "Docker", "Kubernetes", "Terraform", "Ansible", "Jenkins", "CI/CD", "Git", "GitHub",
    "GitLab", "AWS", "Azure", "GCP", "Linux", "Bash", "Nginx",
    "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch", "Keras",
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "Data Science",
    "Data Analysis", "Data Engineering", "ETL", "Spark", "Hadoop", "Airflow",
    "Tableau", "Power BI", "Excel", "Selenium", "Pytest", "JUnit",
    "Agile", "Scrum", "Jira", "Figma", "Product Management", "Project Management",
]

_HEADER_STOPWORDS = (
    "resume", "curriculum vitae", "cv", "profile", "objective", "summary",
    "contact", "address", "phone", "email", "linkedin", "github", "portfolio",
)


def _find_email(text: str) -> Optional[str]:
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def _find_phone(text: str) -> Optional[str]:
    for line in text.splitlines():
        match = PHONE_RE.search(line)
        if match:
            digits = re.sub(r"\D", "", match.group(0))
            if 7 <= len(digits) <= 15:
                return match.group(0).strip()
    return None


def _find_name(text: str, email: Optional[str]) -> Optional[str]:
    """Heuristic: the candidate's name is almost always one of the first
    few non-empty lines, isn't the email/phone line, isn't a section
    header, and looks like "Firstname Lastname" (2-4 title-cased words,
    no digits)."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    local_part = email.split("@")[0].lower() if email else None

    for line in lines[:10]:
        low = line.lower()
        if any(word in low for word in _HEADER_STOPWORDS):
            continue
        if EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        if any(ch.isdigit() for ch in line):
            continue
        words = line.split()
        if not (1 < len(words) <= 4):
            continue
        if not all(w[0].isupper() for w in words if w[0].isalpha()):
            continue
        # Skip lines that are clearly not a name (contain punctuation
        # typical of taglines, e.g. "Software Engineer | Backend").
        if any(ch in line for ch in "|/@:•"):
            continue
        candidate = line.strip()
        if local_part and local_part.replace(".", "").replace("_", "") in candidate.lower().replace(" ", ""):
            return candidate  # extra confidence: matches the email handle
        return candidate
    return None


def _find_experience(text: str) -> Optional[float]:
    for pattern in EXPERIENCE_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


def _normalize_amount(raw_value: str, unit: Optional[str]) -> Optional[float]:
    try:
        value = float(raw_value.replace(",", ""))
    except ValueError:
        return None
    unit = (unit or "").lower()
    if unit in ("k", "thousand"):
        value = value / 100  # normalize to "lakh"-scale units used elsewhere in the form
    return round(value, 2)


def _find_salary(text: str, field: str) -> Optional[float]:
    for pattern in SALARY_PATTERNS[field]:
        match = pattern.search(text)
        if match:
            amount = _normalize_amount(match.group(1), match.group(2))
            if amount is not None:
                return amount
    return None


def _find_skills(text: str) -> List[str]:
    found = []
    lowered = text.lower()
    for skill in COMMON_SKILLS:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill.lower()) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, lowered):
            found.append(skill)
    return found


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_resume(file_bytes: bytes, filename: str) -> Dict:
    """Returns a dict of extracted fields. Any field that couldn't be
    confidently found is None (or an empty list for skills) -- never a
    guessed default -- so the caller can tell "not found" apart from
    "found and is zero"."""
    text = extract_text(file_bytes, filename)

    email = _find_email(text)
    name = _find_name(text, email)
    phone = _find_phone(text)
    experience = _find_experience(text)
    current_salary = _find_salary(text, "current_salary")
    expected_salary = _find_salary(text, "expected_salary")
    skills = _find_skills(text)

    fields_found = {
        "name": name is not None,
        "email": email is not None,
        "phone": phone is not None,
        "experience": experience is not None,
        "current_salary": current_salary is not None,
        "expected_salary": expected_salary is not None,
        "skills": len(skills) > 0,
    }

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "experience": experience,
        "current_salary": current_salary,
        "expected_salary": expected_salary,
        "skills": skills,
        "fields_found": fields_found,
        "raw_text_length": len(text),
    }
