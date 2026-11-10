#!/usr/bin/env python3
"""Generate reproducible synthetic insurance quote and policy data."""

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from eligibility import PRODUCTS
from underwriting import evaluate_submission
from policy_management import (
    create_endorsement,
    issue_policy,
    make_policy_event,
)
from renewal_management import create_renewal
from validation import validate_records

SEED = 20261022


def write_csv(path, rows):
    fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sql_value(value):
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def write_sql(path, tables):
    primary_keys = {
        "products": "product_code",
        "applicants": "applicant_id",
        "insured_assets": "asset_id",
        "coverage_options": "coverage_id",
        "risk_factors": "risk_factor_id",
        "quotes": "quote_id",
        "underwriting_decisions": "decision_id",
        "policies": "policy_id",
        "endorsements": "endorsement_id",
        "renewals": "renewal_id",
        "policy_events": "event_id",
        "ground_truth": "issue_id",
    }

    foreign_keys = {
        "insured_assets": [
            ("applicant_id", "applicants", "applicant_id"),
            ("product_code", "products", "product_code"),
        ],
        "coverage_options": [
            ("product_code", "products", "product_code"),
        ],
        "risk_factors": [
            ("asset_id", "insured_assets", "asset_id"),
        ],
        "quotes": [
            ("applicant_id", "applicants", "applicant_id"),
            ("asset_id", "insured_assets", "asset_id"),
            ("product_code", "products", "product_code"),
        ],
        "underwriting_decisions": [
            ("quote_id", "quotes", "quote_id"),
        ],
        "policies": [
            ("quote_id", "quotes", "quote_id"),
            ("applicant_id", "applicants", "applicant_id"),
            ("asset_id", "insured_assets", "asset_id"),
            ("product_code", "products", "product_code"),
        ],
        "endorsements": [
            ("policy_id", "policies", "policy_id"),
            ("prior_asset_id", "insured_assets", "asset_id"),
            ("replacement_asset_id", "insured_assets", "asset_id"),
        ],
        "renewals": [
            ("policy_id", "policies", "policy_id"),
        ],
        "policy_events": [
            ("policy_id", "policies", "policy_id"),
        ],
    }

    with path.open("w", encoding="utf-8") as sql:
        sql.write("PRAGMA foreign_keys = ON;\nBEGIN TRANSACTION;\n")

        for name, rows in tables:
            fields = list(rows[0]) if rows else []
            definitions = []

            for field in fields:
                definition = "{} TEXT".format(field)
                if field == primary_keys[name]:
                    definition += " PRIMARY KEY"
                definitions.append(definition)

            for column, parent_table, parent_column in foreign_keys.get(name, []):
                definitions.append(
                    "FOREIGN KEY ({}) REFERENCES {}({})".format(
                        column,
                        parent_table,
                        parent_column,
                    )
                )

            sql.write(
                "CREATE TABLE {} ({});\n".format(
                    name,
                    ", ".join(definitions),
                )
            )

            for row in rows:
                values = ", ".join(sql_value(row[field]) for field in fields)
                sql.write(
                    "INSERT INTO {} ({}) VALUES ({});\n".format(
                        name,
                        ", ".join(fields),
                        values,
                    )
                )

        sql.write("COMMIT;\n")


def build(scale=3000, seed=SEED, out_dir="data/generated"):
    if scale < 8:
        raise ValueError(
            "scale must be at least 8 to include required edge scenarios"
        )

    rng = random.Random(seed)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    products = [
        {
            "product_code": code,
            "name": info["name"],
            "max_coverage": info["max_coverage"],
            "base_rate": info["base_rate"],
            "effective_from": "2026-01-01",
            "effective_to": "2027-12-31",
        }
        for code, info in PRODUCTS.items()
    ]

    applicants = []
    assets = []
    coverage_options = []
    risk_factors = []
    quotes = []
    underwriting_decisions = []
    policies = []
    endorsements = []
    renewals = []
    policy_events = []
    ground_truth = []

    quote_count = round(scale * 4 / 3)
    policy_count = round(scale * 2 / 3)
    renewal_count = round(scale * 0.4)
    product_codes = list(PRODUCTS)

    for code, info in PRODUCTS.items():
        coverage_options.append({
            "coverage_id": "COV-{}-BASE".format(code),
            "product_code": code,
            "name": "Standard",
            "limit_amount": info["max_coverage"],
            "effective_from": "2026-01-01",
            "effective_to": "2027-12-31",
        })

    # Create master records before their dependent records.
    for i in range(1, scale + 1):
        product_code = product_codes[(i - 1) % len(product_codes)]

        # Fixed cases guarantee baseline, referral, decline, and missing-data
        # coverage in every supported dataset size.
        if i in (1, 2, 3, 4, 8):
            risk_score = 20
        elif i == 6:
            risk_score = 90
        elif i == 7:
            risk_score = 99
        elif i == 5:
            risk_score = None
        else:
            risk_score = rng.randint(1, 100)

        applicant_id = "APP-2026-{:06d}".format(i)
        asset_id = "AST-2026-{:06d}".format(i)
        declared_value = int(
            PRODUCTS[product_code]["max_coverage"]
            * rng.uniform(0.3, 0.95)
        )

        applicants.append({
            "applicant_id": applicant_id,
            "name": "Applicant {:06d}".format(i),
            "region": ["NORTH", "SOUTH", "EAST", "WEST"][i % 4],
            "created_date": "2026-01-01",
        })

        assets.append({
            "asset_id": asset_id,
            "applicant_id": applicant_id,
            "product_code": product_code,
            "asset_type": {
                "AUTO": "vehicle",
                "HOME": "residence",
                "SMB": "business",
            }[product_code],
            "declared_value": declared_value,
            "risk_score": risk_score,
            "created_date": "2026-01-01",
        })

        risk_factors.append({
            "risk_factor_id": "RSK-2026-{:06d}".format(i),
            "asset_id": asset_id,
            "factor_name": "risk_score",
            "factor_value": risk_score,
            "factor_multiplier": (
                None
                if risk_score is None
                else round(0.75 + risk_score / 200.0, 3)
            ),
            "effective_from": "2026-01-01",
            "effective_to": "2027-12-31",
        })

    # Quotes 2 and 3 share applicant 1 so two active policies can overlap.
    for i in range(1, quote_count + 1):
        if i in (2, 3):
            asset = assets[0]
        else:
            asset = assets[(i - 1) % scale]

        product_code = asset["product_code"]
        coverage = min(
            PRODUCTS[product_code]["max_coverage"],
            int(asset["declared_value"] * 0.9),
        )

        result = evaluate_submission(
            product_code,
            coverage,
            asset["declared_value"],
            asset["risk_score"],
        )

        quote_id = "QTE-2026-{:06d}".format(i)
        premium = result["premium"]

        # Deliberate, labeled premium formula exception.
        if i == 3 and premium is not None:
            premium = round(premium * 1.4, 2)

        quotes.append({
            "quote_id": quote_id,
            "applicant_id": asset["applicant_id"],
            "asset_id": asset["asset_id"],
            "product_code": product_code,
            "requested_coverage": coverage,
            "risk_score": asset["risk_score"],
            "premium": premium,
            "decision": result["decision"],
            "reason": result["reason"],
            "created_date": "2026-02-01",
        })

        underwriting_decisions.append({
            "decision_id": "UWD-2026-{:06d}".format(i),
            "quote_id": quote_id,
            "outcome": result["decision"],
            "reason": result["reason"],
            "authority_level": result["authority_level"],
            "decided_date": "2026-02-01",
        })

        if i == 3:
            ground_truth.append({
                "issue_id": "ISS-0004",
                "issue_type": "premium_formula_mismatch",
                "entity": "quote",
                "record_id": quote_id,
                "expected_decision": "recalculate",
                "details": "Premium is 40 percent above the formula.",
            })

        if i == 5:
            ground_truth.append({
                "issue_id": "ISS-0006",
                "issue_type": "missing_risk_data",
                "entity": "insured_asset",
                "record_id": asset["asset_id"],
                "expected_decision": "refer",
                "details": (
                    "Risk score is missing; every quote for this asset "
                    "requires referral."
                ),
            })

    # Issue policies from approved quotes, then inject one labeled invalid
    # issuance to test the acceptance and payment control.
    approved_quotes = [
        quote for quote in quotes if quote["decision"] == "approve"
    ]

    if len(approved_quotes) < policy_count:
        raise ValueError(
            "Not enough approved quotes to generate the requested policy count"
        )

    for i, quote in enumerate(approved_quotes[:policy_count], 1):
        policy_id = "POL-2026-{:06d}".format(i)
        accepted = i != 1
        payment_received = i != 1

        policy = issue_policy(
            policy_id,
            quote["quote_id"],
            quote["applicant_id"],
            quote["asset_id"],
            quote["product_code"],
            quote["requested_coverage"],
            quote["premium"],
            accepted,
            payment_received,
            "2026-03-01",
            "2027-03-01",
            quote["decision"],
        )

        if i == 1:
            policy["status"] = "issued"
            ground_truth.append({
                "issue_id": "ISS-0001",
                "issue_type": "policy_issued_without_acceptance_or_payment",
                "entity": "policy",
                "record_id": policy_id,
                "expected_decision": "void",
                "details": "Acceptance and payment are both false.",
            })

        if i == 3:
            policy["start_date"] = "2026-10-01"
            ground_truth.append({
                "issue_id": "ISS-0005",
                "issue_type": "overlapping_policy_period",
                "entity": "policy",
                "record_id": policy_id,
                "expected_decision": "refer",
                "details": "Same applicant has an overlapping active policy term.",
            })

        if i == 4:
            policy["status"] = "cancelled"

        policies.append(policy)

        policy_events.append(make_policy_event(
            "EVT-2026-{:06d}".format(i),
            policy_id,
            "cancellation" if i == 4 else "policy_issued",
            "2026-04-01" if i == 4 else "2026-03-01",
            (
                "Policy cancelled mid-term"
                if i == 4
                else "Policy issued after acceptance and payment"
            ),
        ))

        if i == 2:
            replacement_asset_id = "AST-CHANGE-2026-000001"

            assets.append({
                "asset_id": replacement_asset_id,
                "applicant_id": quote["applicant_id"],
                "product_code": quote["product_code"],
                "asset_type": "replacement_asset",
                "declared_value": int(quote["requested_coverage"] * 1.1),
                "risk_score": quote["risk_score"],
                "created_date": "2026-06-01",
            })

            risk_factors.append({
                "risk_factor_id": "RSK-CHANGE-2026-000001",
                "asset_id": replacement_asset_id,
                "factor_name": "risk_score",
                "factor_value": quote["risk_score"],
                "factor_multiplier": round(
                    0.75 + quote["risk_score"] / 200.0,
                    3,
                ),
                "effective_from": "2026-06-01",
                "effective_to": "2027-12-31",
            })

            endorsements.append(create_endorsement(
                "END-{}-001".format(policy_id),
                policy_id,
                "mid_term_asset_change",
                0,
                quote["requested_coverage"],
                PRODUCTS[quote["product_code"]]["max_coverage"],
                "2026-06-01",
                quote["asset_id"],
                replacement_asset_id,
            ))

            policy_events.append(make_policy_event(
                "EVT-ASSET-2026-{}".format(policy_id[-6:]),
                policy_id,
                "asset_change_requested",
                "2026-06-01",
                "Replacement asset recorded in endorsement history",
            ))

        if i == 3:
            endorsement_id = "END-{}-001".format(policy_id)
            endorsements.append(create_endorsement(
                endorsement_id,
                policy_id,
                "coverage_increase",
                PRODUCTS[quote["product_code"]]["max_coverage"],
                quote["requested_coverage"],
                PRODUCTS[quote["product_code"]]["max_coverage"],
                "2026-08-01",
                quote["asset_id"],
                quote["asset_id"],
            ))

            ground_truth.append({
                "issue_id": "ISS-0003",
                "issue_type": "endorsement_exceeds_product_limit",
                "entity": "endorsement",
                "record_id": endorsement_id,
                "expected_decision": "refer",
                "details": "Proposed total coverage exceeds the product maximum.",
            })

    # Include an invalid offer for the persisted cancelled policy and a
    # separate customer-declined renewal.
    renewal_policies = [policies[3], policies[4]] + [
        policy
        for policy in policies
        if policy not in (policies[3], policies[4])
    ][:renewal_count - 2]

    for i, policy in enumerate(renewal_policies, 1):
        response = "declined" if i == 2 else "pending"
        renewal_id = "REN-{}-2027".format(policy["policy_id"])
        offered_premium = max(
            100.0,
            float(policy["premium"] or 0.0) * 1.05,
        )

        renewal = create_renewal(
            renewal_id,
            policy["policy_id"],
            policy["status"],
            offered_premium,
            response,
        )
        renewals.append(renewal)

        policy_events.append(make_policy_event(
            "EVT-REN-{:06d}".format(i),
            policy["policy_id"],
            "renewal_" + renewal["status"],
            "2027-01-15",
            "Renewal status: " + renewal["status"],
        ))

        if i == 1:
            ground_truth.append({
                "issue_id": "ISS-0002",
                "issue_type": "renewal_for_cancelled_policy",
                "entity": "renewal",
                "record_id": renewal_id,
                "expected_decision": "reject",
                "details": "The persisted policy is cancelled.",
            })

        if i == 2:
            ground_truth.append({
                "issue_id": "ISS-0007",
                "issue_type": "declined_renewal",
                "entity": "renewal",
                "record_id": renewal_id,
                "expected_decision": "record_decline",
                "details": "Customer declined the renewal offer.",
            })

    tables = [
        ("products", products),
        ("applicants", applicants),
        ("insured_assets", assets),
        ("coverage_options", coverage_options),
        ("risk_factors", risk_factors),
        ("quotes", quotes),
        ("underwriting_decisions", underwriting_decisions),
        ("policies", policies),
        ("endorsements", endorsements),
        ("renewals", renewals),
        ("policy_events", policy_events),
        ("ground_truth", ground_truth),
    ]

    checks = validate_records(
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
        scale,
        quote_count,
        policy_count,
        renewal_count,
    )

    for name, rows in tables:
        write_csv(output_dir / (name + ".csv"), rows)
        (output_dir / (name + ".json")).write_text(
            json.dumps(rows, indent=2),
            encoding="utf-8",
        )

    write_sql(output_dir / "seed.sql", tables)

    decision_counts = Counter(
        row["outcome"] for row in underwriting_decisions
    )
    renewal_counts = Counter(row["status"] for row in renewals)
    exception_counts = Counter(row["issue_type"] for row in ground_truth)

    summary = {
        "seed": seed,
        "counts": {name: len(rows) for name, rows in tables},
        "metrics": {
            "quote_decision_counts": dict(sorted(decision_counts.items())),
            "referral_rate": round(
                decision_counts.get("refer", 0) / len(quotes),
                4,
            ),
            "renewal_status_counts": dict(sorted(renewal_counts.items())),
            "labeled_exception_counts": dict(sorted(exception_counts.items())),
        },
        "validation": checks,
    }

    (output_dir / "validation_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    Path("reports").mkdir(exist_ok=True)
    Path("reports/evaluation_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    generated_files = sorted(
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.name != "source_manifest.json"
    )

    manifest = {
        "provenance": "Fully synthetic; no external or personal data",
        "generator": "src/generate_data.py",
        "seed": seed,
        "scale_applicants": scale,
        "counts": {name: len(rows) for name, rows in tables},
        "checksums_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in generated_files
        },
    }

    (output_dir / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scale",
        type=int,
        default=3000,
        help="number of synthetic applicants",
    )
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out", default="data/generated")
    args = parser.parse_args()

    if args.scale < 8:
        parser.error("--scale must be at least 8 for required edge-case coverage")

    result = build(args.scale, args.seed, args.out)
    print(json.dumps(result, indent=2))

    if result["validation"]["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()