"""Integrity, calculation, lifecycle, and labeled-exception validation."""

from datetime import date


def validate_records(
    products,
    applicants,
    assets,
    coverage_options,
    risk_factors,
    quotes,
    underwriting_decisions,
    policies,
    endorsements,
    renewals,
    policy_events,
    ground_truth,
    expected_applicants,
    expected_quotes,
    expected_policies,
    expected_renewals,
):
    errors = []

    def unique(rows, key, label):
        values = [row[key] for row in rows]
        if len(values) != len(set(values)):
            errors.append("duplicate {} primary key".format(label))

    key_specs = [
        (products, "product_code", "product"),
        (applicants, "applicant_id", "applicant"),
        (assets, "asset_id", "asset"),
        (coverage_options, "coverage_id", "coverage option"),
        (risk_factors, "risk_factor_id", "risk factor"),
        (quotes, "quote_id", "quote"),
        (underwriting_decisions, "decision_id", "underwriting decision"),
        (policies, "policy_id", "policy"),
        (endorsements, "endorsement_id", "endorsement"),
        (renewals, "renewal_id", "renewal"),
        (policy_events, "event_id", "policy event"),
        (ground_truth, "issue_id", "ground-truth issue"),
    ]
    for rows, key, label in key_specs:
        unique(rows, key, label)

    product_by_code = {row["product_code"]: row for row in products}
    applicant_ids = {row["applicant_id"] for row in applicants}
    asset_by_id = {row["asset_id"]: row for row in assets}
    quote_by_id = {row["quote_id"]: row for row in quotes}
    policy_by_id = {row["policy_id"]: row for row in policies}
    truth_labels = {
        (row["issue_type"], row["record_id"])
        for row in ground_truth
    }

    if len(applicants) != expected_applicants:
        errors.append("applicant count does not match requested scale")
    if len(quotes) != expected_quotes:
        errors.append("quote count does not match requested scale")
    if len(policies) != expected_policies:
        errors.append("policy count does not match requested scale")
    if len(renewals) != expected_renewals:
        errors.append("renewal count does not match requested scale")
    if len(products) != 3:
        errors.append("expected exactly three product lines")
    if len(coverage_options) != 3:
        errors.append("expected one standard coverage option per product")

    for asset in assets:
        if asset["applicant_id"] not in applicant_ids:
            errors.append(
                "asset applicant reference failure: " + asset["asset_id"]
            )
        if asset["product_code"] not in product_by_code:
            errors.append(
                "asset product reference failure: " + asset["asset_id"]
            )
        if asset["declared_value"] is None or float(asset["declared_value"]) <= 0:
            errors.append(
                "asset declared value must be positive: " + asset["asset_id"]
            )

    for option in coverage_options:
        product = product_by_code.get(option["product_code"])
        if product is None:
            errors.append(
                "coverage option product reference failure: "
                + option["coverage_id"]
            )
        elif float(option["limit_amount"]) > float(product["max_coverage"]):
            errors.append(
                "coverage option exceeds product limit: "
                + option["coverage_id"]
            )

    for factor in risk_factors:
        asset = asset_by_id.get(factor["asset_id"])
        if asset is None:
            errors.append(
                "risk factor asset reference failure: "
                + factor["risk_factor_id"]
            )
        elif factor["factor_value"] != asset["risk_score"]:
            errors.append(
                "risk factor does not match source asset: "
                + factor["risk_factor_id"]
            )
        if factor["effective_from"] >= factor["effective_to"]:
            errors.append(
                "risk factor effective dates are invalid: "
                + factor["risk_factor_id"]
            )

    for quote in quotes:
        if (
            quote["applicant_id"] not in applicant_ids
            or quote["asset_id"] not in asset_by_id
        ):
            errors.append("quote parent reference failure: " + quote["quote_id"])
        if quote["product_code"] not in product_by_code:
            errors.append("quote product reference failure: " + quote["quote_id"])

    decisions_by_quote = {
        row["quote_id"]: row
        for row in underwriting_decisions
    }
    if set(decisions_by_quote) != set(quote_by_id):
        errors.append("underwriting decisions must map one-to-one to quotes")

    allowed_authorities = {
        "system_rules",
        "system_automatic",
        "underwriter",
        "risk_compliance_reviewer",
        "senior_underwriter",
    }

    for decision in underwriting_decisions:
        if decision["quote_id"] not in quote_by_id:
            errors.append(
                "underwriting decision quote reference failure: "
                + decision["decision_id"]
            )
            continue

        quote = quote_by_id[decision["quote_id"]]
        if (
            decision["outcome"] != quote["decision"]
            or decision["reason"] != quote["reason"]
        ):
            errors.append(
                "underwriting decision does not reconcile to quote: "
                + decision["decision_id"]
            )

        if decision["authority_level"] not in allowed_authorities:
            errors.append(
                "invalid approval authority: " + decision["decision_id"]
            )

    for policy in policies:
        if policy["quote_id"] not in quote_by_id:
            errors.append("policy quote reference failure: " + policy["policy_id"])

        if (
            policy["applicant_id"] not in applicant_ids
            or policy["asset_id"] not in asset_by_id
        ):
            errors.append(
                "policy applicant or asset reference failure: "
                + policy["policy_id"]
            )

        if policy["product_code"] not in product_by_code:
            errors.append(
                "policy product reference failure: " + policy["policy_id"]
            )

        if date.fromisoformat(policy["start_date"]) >= date.fromisoformat(
            policy["end_date"]
        ):
            errors.append("policy term dates are invalid: " + policy["policy_id"])

        valid_issue = policy["accepted"] and policy["payment_received"]
        if policy["status"] == "issued" and not valid_issue:
            label = (
                "policy_issued_without_acceptance_or_payment",
                policy["policy_id"],
            )
            if label not in truth_labels:
                errors.append(
                    "unlabeled invalid policy issuance: " + policy["policy_id"]
                )

        if (
            policy["status"] == "issued"
            and valid_issue
            and policy["policy_id"] == "POL-2026-000001"
        ):
            errors.append("intentional invalid policy case was not preserved")

    for endorsement in endorsements:
        if endorsement["policy_id"] not in policy_by_id:
            errors.append(
                "endorsement policy reference failure: "
                + endorsement["endorsement_id"]
            )

        for field in ("prior_asset_id", "replacement_asset_id"):
            if endorsement.get(field) and endorsement[field] not in asset_by_id:
                errors.append(
                    "endorsement asset reference failure: "
                    + endorsement["endorsement_id"]
                )

        policy = policy_by_id.get(endorsement["policy_id"])
        if policy and endorsement["change_type"] == "coverage_increase":
            product = product_by_code[policy["product_code"]]
            if float(endorsement["proposed_coverage"]) > float(
                product["max_coverage"]
            ):
                label = (
                    "endorsement_exceeds_product_limit",
                    endorsement["endorsement_id"],
                )
                if label not in truth_labels:
                    errors.append(
                        "unlabeled excess endorsement: "
                        + endorsement["endorsement_id"]
                    )

    for renewal in renewals:
        policy = policy_by_id.get(renewal["policy_id"])

        if policy is None:
            errors.append(
                "renewal policy reference failure: " + renewal["renewal_id"]
            )
        elif policy["status"] == "cancelled":
            label = (
                "renewal_for_cancelled_policy",
                renewal["renewal_id"],
            )
            if (
                renewal["status"] != "invalid_offer_for_inactive_policy"
                or label not in truth_labels
            ):
                errors.append(
                    "cancelled-policy renewal is not correctly blocked and labeled"
                )

        if renewal["renewal_date"] <= renewal["offer_date"]:
            errors.append("renewal dates are out of order: " + renewal["renewal_id"])

        if renewal["status"] == "declined" and (
            "declined_renewal",
            renewal["renewal_id"],
        ) not in truth_labels:
            errors.append("declined renewal is not labeled: " + renewal["renewal_id"])

    for event in policy_events:
        if event["policy_id"] not in policy_by_id:
            errors.append("policy event reference failure: " + event["event_id"])

    premium_labels = {
        record_id
        for issue_type, record_id in truth_labels
        if issue_type == "premium_formula_mismatch"
    }

    for quote in quotes:
        risk = quote["risk_score"]

        if risk is None:
            if quote["premium"] is not None or quote["decision"] != "refer":
                errors.append(
                    "missing risk data was not referred: " + quote["quote_id"]
                )
            if ("missing_risk_data", quote["asset_id"]) not in truth_labels:
                errors.append("missing risk data exception is not labeled")
            continue

        expected = calculate_expected_premium(
            quote["requested_coverage"],
            product_by_code[quote["product_code"]]["base_rate"],
            risk,
        )
        mismatch = (
            quote["premium"] is None
            or abs(float(quote["premium"]) - expected) > 0.01
        )
        labeled = quote["quote_id"] in premium_labels

        if mismatch and not labeled:
            errors.append(
                "unlabeled premium formula mismatch: " + quote["quote_id"]
            )
        if labeled and not mismatch:
            errors.append(
                "premium mismatch label has no mismatch: " + quote["quote_id"]
            )

    active_policies = [
        policy
        for policy in policies
        if (
            policy["status"] == "issued"
            and policy["accepted"]
            and policy["payment_received"]
        )
    ]

    for index, first in enumerate(active_policies):
        for second in active_policies[index + 1:]:
            overlaps = (
                first["applicant_id"] == second["applicant_id"]
                and first["start_date"] < second["end_date"]
                and second["start_date"] < first["end_date"]
            )

            if overlaps:
                later = max(
                    (first, second),
                    key=lambda row: row["start_date"],
                )
                label = (
                    "overlapping_policy_period",
                    later["policy_id"],
                )
                if label not in truth_labels:
                    errors.append(
                        "unlabeled overlapping policy period: "
                        + later["policy_id"]
                    )

    required_issues = {
        "policy_issued_without_acceptance_or_payment",
        "premium_formula_mismatch",
        "endorsement_exceeds_product_limit",
        "renewal_for_cancelled_policy",
        "overlapping_policy_period",
        "missing_risk_data",
        "declined_renewal",
    }
    present_issues = {row["issue_type"] for row in ground_truth}

    if not required_issues.issubset(present_issues):
        errors.append("required ground-truth issue coverage is incomplete")

    if not any(
        quote["risk_score"] is not None
        and quote["risk_score"] >= 85
        and quote["decision"] == "refer"
        for quote in quotes
    ):
        errors.append("high-risk referral scenario is missing")

    if not any(
        quote["risk_score"] is not None
        and quote["risk_score"] >= 97
        and quote["decision"] == "decline"
        for quote in quotes
    ):
        errors.append("high-risk decline scenario is missing")

    if not any(
        row["change_type"] == "mid_term_asset_change"
        for row in endorsements
    ):
        errors.append("mid-term asset change scenario is missing")

    cancelled_ids = {
        policy["policy_id"]
        for policy in policies
        if policy["status"] == "cancelled"
    }
    cancellation_event_ids = {
        event["policy_id"]
        for event in policy_events
        if event["event_type"] == "cancellation"
    }

    if not cancelled_ids.issubset(cancellation_event_ids):
        errors.append("cancelled policy lifecycle event is missing")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
    }


def calculate_expected_premium(coverage, base_rate, risk_score):
    multiplier = 0.75 + int(risk_score) / 200.0
    return round(float(coverage) * float(base_rate) * multiplier, 2)