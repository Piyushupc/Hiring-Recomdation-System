def calculate_stability(job_durations):

    avg_tenure = sum(job_durations) / len(job_durations)

    if avg_tenure >= 36:
        score = 90

    elif avg_tenure >= 24:
        score = 75

    elif avg_tenure >= 12:
        score = 60

    else:
        score = 30

    return score
