"""Policy issuance, endorsements, and lifecycle event helpers."""


def issue_policy(
    policy_id,
    quote_id,
    applicant_id,
    asset_id,
    product_code,
    coverage_amount,
    premium,
    accepted,
    payment_received,
    start_date,
    end_date,
    underwriting_decision,
):
    can_issue = (
        bool(accepted)
        and bool(payment_received)
        and underwriting_decision == "approve"
    )

    return {
        "policy_id": policy_id,
        "quote_id": quote_id,
        "applicant_id": applicant_id,
        "asset_id": asset_id,
        "product_code": product_code,
        "coverage_amount": coverage_amount,
        "premium": premium,
        "status": "issued" if can_issue else "blocked",
        "accepted": bool(accepted),
        "payment_received": bool(payment_received),
        "start_date": start_date,
        "end_date": end_date,
    }


def create_endorsement(
    endorsement_id,
    policy_id,
    change_type,
    coverage_delta,
    current_coverage,
    product_limit,
    effective_date,
    prior_asset_id="",
    replacement_asset_id="",
):
    proposed_coverage = current_coverage + coverage_delta
    status = (
        "referred"
        if proposed_coverage > product_limit
        else "pending_review"
    )

    return {
        "endorsement_id": endorsement_id,
        "policy_id": policy_id,
        "change_type": change_type,
        "coverage_delta": coverage_delta,
        "proposed_coverage": proposed_coverage,
        "prior_asset_id": prior_asset_id,
        "replacement_asset_id": replacement_asset_id,
        "status": status,
        "effective_date": effective_date,
    }


def make_policy_event(event_id, policy_id, event_type, event_date, details):
    return {
        "event_id": event_id,
        "policy_id": policy_id,
        "event_type": event_type,
        "event_date": event_date,
        "details": details,
    }