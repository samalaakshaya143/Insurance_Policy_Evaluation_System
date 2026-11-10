"""Combine eligibility, risk, and rating into an explainable decision."""

from eligibility import check_eligibility
from premium_calculation import calculate_premium
from risk_evaluation import evaluate_risk


def evaluate_submission(product_code, requested_coverage, declared_value, risk_score):
    eligible, eligibility_reason = check_eligibility(
        product_code,
        requested_coverage,
        declared_value,
    )

    if not eligible:
        return {
            "decision": "decline",
            "reason": eligibility_reason,
            "premium": None,
            "authority_level": "system_rules",
        }

    risk_decision, risk_reason = evaluate_risk(risk_score)
    premium = calculate_premium(product_code, requested_coverage, risk_score)

    authority = {
        "approve": "system_automatic",
        "refer": (
            "risk_compliance_reviewer"
            if risk_score is None
            else "underwriter"
        ),
        "decline": "senior_underwriter",
    }[risk_decision]

    return {
        "decision": risk_decision,
        "reason": risk_reason,
        "premium": premium,
        "authority_level": authority,
    }