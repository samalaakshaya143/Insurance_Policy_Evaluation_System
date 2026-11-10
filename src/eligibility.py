"""Product eligibility and coverage limit rules."""

PRODUCTS = {
    "AUTO": {
        "name": "Personal Auto",
        "max_coverage": 50_000,
        "base_rate": 0.018,
    },
    "HOME": {
        "name": "Homeowners",
        "max_coverage": 750_000,
        "base_rate": 0.004,
    },
    "SMB": {
        "name": "Small Business",
        "max_coverage": 1_000_000,
        "base_rate": 0.006,
    },
}


def check_eligibility(product_code, requested_coverage, declared_value):
    product = PRODUCTS.get(product_code)

    if product is None:
        return False, "unknown_product"

    if requested_coverage is None or requested_coverage <= 0:
        return False, "coverage_must_be_positive"

    if requested_coverage > product["max_coverage"]:
        return False, "coverage_exceeds_product_limit"

    if declared_value is None or declared_value <= 0:
        return False, "missing_or_invalid_asset_value"

    if requested_coverage > declared_value * 1.25:
        return False, "coverage_exceeds_asset_value_limit"

    return True, "eligible"