# Hiring Recommendation System

FastAPI backend + HTML/JS frontend that:
- **Parses an uploaded resume** (PDF/DOCX/TXT) to auto-fill name, email, experience,
  current salary, expected salary, and skills
- **Scores candidates** on stability, long-term retention, monetary motivation, and
  cultural fit — gracefully excluding any component whose underlying data (experience,
  current/expected salary) wasn't found, instead of guessing or defaulting it to 0
- **Flags pass/fail** against a configurable threshold
- **Sends interview or rejection emails** via SMTP, one click from the UI

## Project structure

```
hiring_recommendation_system/
├── Models/
│   ├── cultural_fit.py
│   ├── monetary_motivation.py
│   ├── stability_score.py
│   ├── long_term_prediction.py       # rule-based
│   ├── ml_long_term_predictor.py     # loads long_term_model.pkl
│   ├── recommendation_engine.py      # combines scores, reweights around missing data
│   └── resume_parser.py              # extracts fields from PDF/DOCX/TXT resumes
├── services/
│   └── email_service.py              # SMTP interview/rejection emails
├── app.py                            # FastAPI app
├── long_term_model.pkl               # trained model (from train_model.py)
├── requirements.txt
├── .env.example                      # SMTP / threshold config template
├── frontend/
│   └── index.html                    # standalone HTML/JS UI
└── README.md
```

## 1. Setup

```bash
cd hiring_recommendation_system
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure email (optional but needed for the send-mail buttons)

Copy `.env.example` to `.env` and fill in real SMTP credentials (e.g. a Gmail
account with an [app password](https://myaccount.google.com/apppasswords)),
then export them into your shell / process before starting the API:

```bash
export $(grep -v '^#' .env | xargs)   # or use python-dotenv / your platform's env config
```

If `SMTP_USER` / `SMTP_PASSWORD` aren't set, `/score` and `/parse-resume` still
work fine — only `/send-email` will fail with a clear error telling you what's
missing.

## 3. Run the API

```bash
uvicorn app:app --reload --port 8000
```

- API docs (Swagger UI): http://localhost:8000/docs
- Health check: http://localhost:8000/health

## 4. Run the frontend

Just open `frontend/index.html` directly in a browser. It talks to the API at
`http://localhost:8000` by default — change the API URL at the top of the
page if you host the API elsewhere.

## Workflow

1. Upload a resume (PDF/DOCX/TXT) and click **Parse** — name, email,
   experience, current/expected salary, and skills get filled in
   automatically wherever found. Anything not found is left blank.
2. Click **Calculate Recommendation**. Any field left blank is excluded from
   scoring rather than counted as 0 — the remaining weights are rescaled so a
   missing salary, for instance, doesn't unfairly lower the score.
3. If the candidate's overall score meets the pass threshold, a **Send
   Interview Mail** button appears; otherwise a **Send Rejection Mail**
   button appears. Both call `/send-email` in the backend.

## API reference

### `POST /parse-resume`

`multipart/form-data` with a `file` field (`.pdf`, `.docx`, or `.txt`).

**Response:**
```json
{
  "name": "Jane Doe",
  "email": "jane.doe@example.com",
  "phone": "+1 415-555-0192",
  "experience": 4.5,
  "current_salary": 12,
  "expected_salary": 18,
  "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "AWS"],
  "fields_found": {
    "name": true, "email": true, "phone": true,
    "experience": true, "current_salary": true,
    "expected_salary": true, "skills": true
  }
}
```
Fields that couldn't be found are `null` (and `skills` an empty list) — never
guessed. This is a regex/heuristic parser, not an NER model, so always let the
recruiter review and correct the auto-filled fields before scoring.

### `POST /score`

**Request body:**
```json
{
  "name": "Jane Doe",
  "email": "jane.doe@example.com",
  "job_title": "Backend Engineer",
  "job_durations": [12, 18, 24],
  "companies": 3,
  "experience": 4.5,
  "current_salary": 8,
  "expected_salary": 12,
  "candidate_skills": ["Python", "FastAPI", "PostgreSQL"],
  "company_skills": ["Python", "FastAPI", "Git", "Docker"]
}
```
`experience`, `current_salary`, and `expected_salary` are optional — omit
them (or send `null`) if they're not available. `name`/`email`/`job_title`
are also optional and are just carried through for your records / the email
step; they don't affect scoring.

**Response:** `rule_based` and `ml_based` score breakdowns (each including an
`excluded_components` list explaining what was skipped and why), the derived
`avg_tenure_months` / `salary_jump_percent`, `data_completeness`, an
`overall_score`, the `pass_threshold`, and `meets_criteria`.

### `POST /send-email`

```json
{
  "to_email": "jane.doe@example.com",
  "candidate_name": "Jane Doe",
  "email_type": "interview",
  "job_title": "Backend Engineer",
  "interview_datetime": "Mon, 16 Sep 2026, 3:00 PM IST",
  "interview_location": "https://meet.example.com/abc-defg",
  "additional_notes": "Please bring a photo ID."
}
```
`email_type` is `"interview"` or `"rejection"`. `interview_datetime` /
`interview_location` are only used for interview emails. Requires
`SMTP_USER` / `SMTP_PASSWORD` to be configured (see step 2); otherwise
returns a 502 with a clear message.

## How missing fields are handled in scoring

- **Monetary motivation** needs both `current_salary` and `expected_salary`.
  If either is missing, `monetary` is `null` and excluded from the final
  score (the remaining components' weights are rescaled proportionally, not
  padded with a 0).
- **ML long-term prediction** needs `experience` plus both salaries (it was
  trained on those features). If any are missing, the ML long-term score is
  `null`; the **rule-based** long-term score still works, since it only needs
  `job_durations`.
- **Stability** and **cultural fit** only need `job_durations` and skills, so
  they're essentially always available.
- If literally everything needed is missing, `final_score` is `null` rather
  than a misleading number.

## Note on the two long-term engines

The rule-based engine and the ML model can disagree — they were built from
different logic (the model was trained on `employee_data.csv`, which itself
uses somewhat different rules than `long_term_prediction.py`). The API
returns both so you can compare them side by side rather than silently
picking one. If you want a single source of truth going forward, consider
retraining the model on real historical outcome data rather than the
synthetic dataset from `generate_dataset.py`.

## Retraining the model

`train_model.py` (not modified here) regenerates `long_term_model.pkl` from
`employee_data.csv`. Re-run it if you update the dataset, then replace the
`.pkl` file in this project's root.
