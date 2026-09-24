def calculate_monetary_score(
        current_salary,
        expected_salary
):

    salary_jump = (
        (expected_salary - current_salary)
        / current_salary
    ) * 100

    if salary_jump > 50:
        return 90

    elif salary_jump > 25:
        return 70

    else:
        return 40
