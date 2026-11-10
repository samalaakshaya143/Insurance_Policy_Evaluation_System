"""Renewal eligibility and customer response handling."""


def create_renewal(
    renewal_id,
    policy_id,
    policy_status,
    offered_premium,
    response="pending",
):
    if policy_status != "issued":
        status = "invalid_offer_for_inactive_policy"
    elif response == "declined":
        status = "declined"
    elif response == "accepted":
        status = "accepted"
    else:
        status = "offered"

    return {
        "renewal_id": renewal_id,
        "policy_id": policy_id,
        "offered_premium": round(float(offered_premium), 2),
        "status": status,
        "response": response,
        "offer_date": "2027-01-15",
        "renewal_date": "2027-03-01",
    }