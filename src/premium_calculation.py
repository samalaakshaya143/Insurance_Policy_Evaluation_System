"""Transparent insurance premium calculation."""

from eligibility import PRODUCTS


def calculate_premium(product_code, coverage_amount, risk_score):
    if product_code not in PRODUCTS:
        raise ValueError("Unknown product code: {}".format(product_code))

    if coverage_amount is None or coverage_amount <= 0:
        raise ValueError("coverage_amount must be positive")

    if risk_score is None:
        return None

    if not 1 <= int(risk_score) <= 100:
        raise ValueError("risk_score must be between 1 and 100")

    risk_multiplier = 0.75 + int(risk_score) / 200.0
    base_rate = PRODUCTS[product_code]["base_rate"]

    return round(float(coverage_amount) * base_rate * risk_multiplier, 2)