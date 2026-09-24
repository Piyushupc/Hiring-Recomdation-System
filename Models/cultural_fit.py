def calculate_cultural_fit(
        candidate_skills,
        company_skills
):

    matched = len(
        set(candidate_skills)
        &
        set(company_skills)
    )

    score = (
        matched / len(company_skills)
    ) * 100

    return round(score, 2)
