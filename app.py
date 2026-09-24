import os
import re
from typing import Dict, List, Literal, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from Models.cultural_fit import calculate_cultural_fit
from Models.monetary_motivation import calculate_monetary_score
from Models.recommendation_engine import generate_final_score
from Models.resume_parser import parse_resume
from Models.stability_score import calculate_stability
from Models.long_term_prediction import predict_long_term
from Models.ml_long_term_predictor import predict_long_term_ml
from services.email_service import EmailServiceError, send_interview_email, send_rejection_email

app = FastAPI(
    title="Hiring Recommendation API",
    description="Parses resumes, scores candidates on stability, long-term retention, "
                 "monetary motivation, and cultural fit, and sends interview/rejection emails.",
    version="2.0.0"
)

# Allow the local frontend (or any origin, for local/dev use) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Final score (0-100) a candidate needs to meet/beat to be considered a "pass".
# Override with the PASS_THRESHOLD environment variable.
PASS_THRESHOLD = float(os.getenv("PASS_THRESHOLD", "65"))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CandidateInput(BaseModel):
    name: Optional[str] = Field(None, description="Candidate name", examples=["Jane Doe"])
    email: Optional[str] = Field(None, description="Candidate email", examples=["jane@example.com"])
    job_title: Optional[str] = Field(None, description="Role being considered for", examples=["Backend Engineer"])

    job_durations: List[float] = Field(
        ..., description="Durations (months) of each previous job", examples=[[12, 18, 24]]
    )
    companies: int = Field(..., description="Number of companies worked at", examples=[3])

    # These three are commonly missing from resumes. They're optional here
    # and, when absent, are simply excluded from scoring rather than
    # defaulted to 0 or otherwise guessed at.
    experience: Optional[float] = Field(None, description="Total years of experience", examples=[4.5])
    current_salary: Optional[float] = Field(None, description="Current salary", examples=[8])
    expected_salary: Optional[float] = Field(None, description="Expected salary", examples=[12])

    candidate_skills: List[str] = Field(
        default_factory=list, description="Skills the candidate has", examples=[["Python", "FastAPI", "PostgreSQL"]]
    )
    company_skills: List[str] = Field(
        ..., description="Skills the company requires", examples=[["Python", "FastAPI", "Git", "Docker"]]
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v is None or v == "":
            return None
        if not EMAIL_RE.match(v):
            raise ValueError("email must look like a valid email address")
        return v

    @field_validator("current_salary", "expected_salary")
    @classmethod
    def validate_positive_salary(cls, v):
        if v is not None and v <= 0:
            raise ValueError("salary must be greater than 0 if provided")
        return v


class ScoreBreakdown(BaseModel):
    stability: Optional[float] = None
    long_term_probability: Optional[float] = None
    long_term_recommendation: Optional[str] = None
    monetary: Optional[float] = None
    culture: Optional[float] = None
    final_score: Optional[float] = None
    excluded_components: List[str] = Field(
        default_factory=list, description="Score components skipped due to missing data"
    )


class ScoreResponse(BaseModel):
    rule_based: ScoreBreakdown
    ml_based: ScoreBreakdown
    inputs_used: dict
    data_completeness: Dict[str, bool]
    overall_score: Optional[float]
    pass_threshold: float
    meets_criteria: bool


class ParsedResumeResponse(BaseModel):
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    experience: Optional[float]
    current_salary: Optional[float]
    expected_salary: Optional[float]
    skills: List[str]
    fields_found: Dict[str, bool]


class EmailRequest(BaseModel):
    to_email: str
    candidate_name: str
    email_type: Literal["interview", "rejection"]
    job_title: Optional[str] = None
    interview_datetime: Optional[str] = Field(None, description="Only used for interview emails")
    interview_location: Optional[str] = Field(None, description="Only used for interview emails, can be a video call link")
    additional_notes: Optional[str] = None

    @field_validator("to_email")
    @classmethod
    def validate_email(cls, v):
        if not EMAIL_RE.match(v):
            raise ValueError("to_email must be a valid email address")
        return v


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "ok", "message": "Hiring Recommendation API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/parse-resume", response_model=ParsedResumeResponse)
async def parse_resume_endpoint(file: UploadFile = File(...)):
    allowed = (".pdf", ".docx", ".txt")
    if not (file.filename or "").lower().endswith(allowed):
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Use one of: {', '.join(allowed)}")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        parsed = parse_resume(file_bytes, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse resume: {exc}")

    return ParsedResumeResponse(
        name=parsed["name"],
        email=parsed["email"],
        phone=parsed["phone"],
        experience=parsed["experience"],
        current_salary=parsed["current_salary"],
        expected_salary=parsed["expected_salary"],
        skills=parsed["skills"],
        fields_found=parsed["fields_found"],
    )


@app.post("/score", response_model=ScoreResponse)
def score_candidate(candidate: CandidateInput):
    if not candidate.job_durations:
        raise HTTPException(status_code=400, detail="job_durations must contain at least one value")
    if not candidate.company_skills:
        raise HTTPException(status_code=400, detail="company_skills must contain at least one value")

    avg_tenure = sum(candidate.job_durations) / len(candidate.job_durations)

    has_experience = candidate.experience is not None
    has_current_salary = candidate.current_salary is not None
    has_expected_salary = candidate.expected_salary is not None
    has_both_salaries = has_current_salary and has_expected_salary

    salary_jump = None
    if has_both_salaries:
        salary_jump = ((candidate.expected_salary - candidate.current_salary) / candidate.current_salary) * 100

    # --- Shared components (identical for both approaches) ---
    stability = calculate_stability(candidate.job_durations)
    culture = calculate_cultural_fit(candidate.candidate_skills, candidate.company_skills)
    monetary = calculate_monetary_score(candidate.current_salary, candidate.expected_salary) if has_both_salaries else None

    # --- Rule-based long-term prediction (only needs job_durations, always available) ---
    rule_long_term = predict_long_term(avg_tenure)
    rule_excluded = [] if monetary is not None else ["monetary"]
    rule_final = generate_final_score(
        stability, rule_long_term["long_term_probability"], monetary, culture
    )

    # --- ML-based long-term prediction (needs experience + both salaries) ---
    ml_excluded = list(rule_excluded)
    if has_experience and has_both_salaries:
        ml_long_term = predict_long_term_ml(
            avg_tenure=avg_tenure,
            companies=candidate.companies,
            salary_jump=salary_jump,
            experience=candidate.experience
        )
        ml_long_term_probability = ml_long_term["long_term_probability"]
        ml_long_term_recommendation = ml_long_term["recommendation"]
    else:
        ml_long_term_probability = None
        ml_long_term_recommendation = None
        ml_excluded.append("long_term (insufficient data: needs experience + current & expected salary)")

    ml_final = generate_final_score(
        stability, ml_long_term_probability, monetary, culture
    )

    rule_breakdown = ScoreBreakdown(
        stability=stability,
        long_term_probability=rule_long_term["long_term_probability"],
        long_term_recommendation=rule_long_term["recommendation"],
        monetary=monetary,
        culture=culture,
        final_score=rule_final,
        excluded_components=rule_excluded,
    )
    ml_breakdown = ScoreBreakdown(
        stability=stability,
        long_term_probability=ml_long_term_probability,
        long_term_recommendation=ml_long_term_recommendation,
        monetary=monetary,
        culture=culture,
        final_score=ml_final,
        excluded_components=ml_excluded,
    )

    available_finals = [s for s in (rule_final, ml_final) if s is not None]
    overall_score = round(sum(available_finals) / len(available_finals), 2) if available_finals else None
    meets_criteria = bool(overall_score is not None and overall_score >= PASS_THRESHOLD)

    return ScoreResponse(
        rule_based=rule_breakdown,
        ml_based=ml_breakdown,
        inputs_used={
            "avg_tenure_months": round(avg_tenure, 2),
            "salary_jump_percent": round(salary_jump, 2) if salary_jump is not None else None,
        },
        data_completeness={
            "experience_provided": has_experience,
            "current_salary_provided": has_current_salary,
            "expected_salary_provided": has_expected_salary,
        },
        overall_score=overall_score,
        pass_threshold=PASS_THRESHOLD,
        meets_criteria=meets_criteria,
    )


@app.post("/send-email")
def send_email(request: EmailRequest):
    try:
        if request.email_type == "interview":
            send_interview_email(
                to_email=request.to_email,
                candidate_name=request.candidate_name,
                job_title=request.job_title,
                interview_datetime=request.interview_datetime,
                interview_location=request.interview_location,
                additional_notes=request.additional_notes,
            )
        else:
            send_rejection_email(
                to_email=request.to_email,
                candidate_name=request.candidate_name,
                job_title=request.job_title,
                additional_notes=request.additional_notes,
            )
    except EmailServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"status": "sent", "to": request.to_email, "email_type": request.email_type}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
