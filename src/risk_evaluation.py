"""Risk score evaluation and underwriting referral thresholds."""


def evaluate_risk(risk_score):
    if risk_score is None:
        return "refer", "missing_risk_data"

    score = int(risk_score)

    if not 1 <= score <= 100:
        return "refer", "risk_score_out_of_range"

    if score >= 97:
        return "decline", "risk_score_at_least_97"

    if score >= 85:
        return "refer", "risk_score_at_least_85"

    return "approve", "risk_within_automatic_limit"