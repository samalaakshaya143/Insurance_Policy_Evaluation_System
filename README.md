# Insurance Policy Evaluation System

A reproducible Python project that generates synthetic insurance submissions and records, evaluates eligibility and underwriting outcomes, and validates policy lifecycle data.

> **Educational demo only:** All records are synthetic and the business rules are simplified examples. Do not use this project for real insurance, coverage, pricing, or underwriting decisions. Do not enter real personal or confidential information.

## Run

Use Python 3.10 or newer. From PowerShell, open the project root (the folder containing `src`, `data`, and `reports`) and run:

```powershell
python src\main.py --scale 100 --seed 20261022
```

For the default full dataset:

```powershell
python src\main.py --seed 20261022
```

The scale must be at least `8` to include all deterministic exception scenarios. The default scale is `3000`. To select a different output directory:

```powershell
python src\main.py --scale 100 --seed 20261022 --out data\generated
```

Arguments:

| Argument | Meaning | Default |
|---|---|---:|
| `--scale` | Number of synthetic applicants; minimum 8 | `3000` |
| `--seed` | Seed for reproducible record generation | `20261022` |
| `--out` | Directory for generated files | `data/generated` |

The generator uses only the Python standard library. No `pip install` step is required.

## Outputs

The generator writes CSV and JSON files for each entity to the selected output directory, along with:

- `seed.sql` — SQL schema and seed records, with primary and foreign keys
- `source_manifest.json` — seed, provenance, row counts, and SHA-256 checksums
- `validation_summary.json` — validation result, record counts, and evaluation metrics

A copy of the summary is also written to `reports/evaluation_summary.json`.

The SQL script is generated for loading the records into SQLite or another compatible SQL environment. The generator creates the SQL script; it does not create a `.db` database file.

## Products and example rules

| Product | Code | Maximum coverage | Base rate |
|---|---|---:|---:|
| Personal Auto | `AUTO` | $50,000 | 1.8% |
| Homeowners | `HOME` | $750,000 | 0.4% |
| Small Business | `SMB` | $1,000,000 | 0.6% |

Premium formula:

```text
coverage × base_rate × (0.75 + risk_score / 200)
```

Missing risk data cannot be priced and is referred. Risk scores `85–96` are referred; scores `97–100` are declined. Coverage must be positive, within the product maximum, and no more than 125% of the declared asset value.

Automatic approval authority, underwriter referrals, risk/compliance referrals, and senior-underwriter declines are recorded with each underwriting decision. Normal policy issuance requires approval, customer acceptance, and payment. Renewals for inactive policies are marked invalid, and endorsements that exceed the product maximum are referred.

These are deterministic synthetic examples, not real insurance rating guidance.

## Data dictionary

Dates use ISO `YYYY-MM-DD` format. Coverage and premium values are in USD. Identifiers are unique strings. The generated SQL schema declares columns as `TEXT`.

| Entity | Primary key | Main fields and checks |
|---|---|---|
| Product | `product_code` | Name, maximum coverage, base rate, effective dates; codes `AUTO`, `HOME`, `SMB`. |
| Applicant | `applicant_id` | Synthetic name, region, creation date. |
| Insured asset | `asset_id` | Applicant and product references, asset type, positive declared value, optional risk score, creation date. |
| Coverage option | `coverage_id` | Product reference, name, limit no higher than the product maximum, effective dates. |
| Risk factor | `risk_factor_id` | Asset reference, factor name/value/multiplier, effective dates. Value and multiplier may be null when risk data is missing. |
| Quote | `quote_id` | Applicant, asset, and product references; requested coverage, optional risk score, premium, decision, reason, creation date. |
| Underwriting decision | `decision_id` | Quote reference, outcome, reason, authority level, decision date. One decision per quote. |
| Policy | `policy_id` | Quote, applicant, asset, and product references; coverage, premium, status, acceptance/payment flags, term dates. |
| Endorsement | `endorsement_id` | Policy reference, change type, coverage delta/proposed total, optional prior/replacement asset references, status, effective date. |
| Renewal | `renewal_id` | Policy reference, offered premium, status, customer response, offer and renewal dates. |
| Policy event | `event_id` | Policy reference, event type/date, and details. |
| Ground-truth issue | `issue_id` | Exception type, affected entity and record, expected action, and details. |

An applicant can have multiple assets, quotes, and policies. A product can have multiple assets, coverage options, and quotes. Each quote has one underwriting decision and may result in a policy. Policies can have multiple events, endorsements, and renewals. These relationships are one-to-many or one-to-one and require no many-to-many bridge table.

## Included exception scenarios

The `ground_truth` files label these generated cases:

- Policy issued without customer acceptance or payment
- Premium formula mismatch
- Endorsement above the product limit
- Renewal offered for a cancelled policy
- Overlapping active policy periods
- Missing risk data
- Customer-declined renewal

The dataset also includes high-risk referrals and declines, a cancelled policy, and a mid-term asset-change endorsement. Exception cases are created by documented deterministic rules, not random labels.

## Validation and reproducibility

Validation checks identifier uniqueness, expected row counts, foreign-key references, risk-factor consistency, quote-to-decision reconciliation, approval authority, premium calculations, policy dates and issuance conditions, renewal and endorsement rules, lifecycle events, and required exception labels.

To confirm reproducibility, generate two outputs with the same scale and seed, then compare their SHA-256 hashes:

```powershell
python src\main.py --scale 100 --seed 20261022 --out data\repro_a
python src\main.py --scale 100 --seed 20261022 --out data\repro_b

$hashesA = Get-ChildItem data\repro_a -File | Sort-Object Name | ForEach-Object {
    "$($_.Name):$((Get-FileHash $_.FullName -Algorithm SHA256).Hash)"
}
$hashesB = Get-ChildItem data\repro_b -File | Sort-Object Name | ForEach-Object {
    "$($_.Name):$((Get-FileHash $_.FullName -Algorithm SHA256).Hash)"
}
Compare-Object $hashesA $hashesB
```

No output from `Compare-Object` means the generated files match.

## Project structure

```text
src/
  eligibility.py          Product eligibility and coverage limits
  generate_data.py        Synthetic data generation and SQL seed export
  main.py                 Command-line entry point
  policy_management.py    Policy issuance, endorsements, and events
  premium_calculation.py  Premium formula
  renewal_management.py   Renewal rules
  risk_evaluation.py      Risk thresholds
  underwriting.py         Combined quote and underwriting evaluation
  validation.py           Data integrity and exception validation
data/                     Generated CSV, JSON, and SQL files
reports/                  Evaluation summary
tests/                    Project tests
```
