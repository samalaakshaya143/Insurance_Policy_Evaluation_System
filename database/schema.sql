-- SQLite schema for the synthetic Insurance Policy Evaluation System.
-- Dates use ISO-8601 YYYY-MM-DD strings. Monetary amounts are USD.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS products (
    product_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    max_coverage REAL NOT NULL CHECK (max_coverage > 0),
    base_rate REAL NOT NULL CHECK (base_rate > 0),
    effective_from TEXT NOT NULL,
    effective_to TEXT NOT NULL,
    CHECK (effective_from < effective_to)
);

CREATE TABLE IF NOT EXISTS applicants (
    applicant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT NOT NULL CHECK (region IN ('NORTH', 'SOUTH', 'EAST', 'WEST')),
    created_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS insured_assets (
    asset_id TEXT PRIMARY KEY,
    applicant_id TEXT NOT NULL REFERENCES applicants(applicant_id),
    product_code TEXT NOT NULL REFERENCES products(product_code),
    asset_type TEXT NOT NULL,
    declared_value REAL NOT NULL CHECK (declared_value > 0),
    risk_score INTEGER CHECK (
        risk_score IS NULL OR risk_score BETWEEN 1 AND 100
    ),
    created_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS coverage_options (
    coverage_id TEXT PRIMARY KEY,
    product_code TEXT NOT NULL REFERENCES products(product_code),
    name TEXT NOT NULL,
    limit_amount REAL NOT NULL CHECK (limit_amount > 0),
    effective_from TEXT NOT NULL,
    effective_to TEXT NOT NULL,
    CHECK (effective_from < effective_to)
);

CREATE TABLE IF NOT EXISTS risk_factors (
    risk_factor_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES insured_assets(asset_id),
    factor_name TEXT NOT NULL,
    factor_value INTEGER,
    factor_multiplier REAL,
    effective_from TEXT NOT NULL,
    effective_to TEXT NOT NULL,
    CHECK (effective_from < effective_to),
    CHECK (factor_value IS NULL OR factor_value BETWEEN 1 AND 100)
);

CREATE TABLE IF NOT EXISTS quotes (
    quote_id TEXT PRIMARY KEY,
    applicant_id TEXT NOT NULL REFERENCES applicants(applicant_id),
    asset_id TEXT NOT NULL REFERENCES insured_assets(asset_id),
    product_code TEXT NOT NULL REFERENCES products(product_code),
    requested_coverage REAL NOT NULL CHECK (requested_coverage > 0),
    risk_score INTEGER CHECK (
        risk_score IS NULL OR risk_score BETWEEN 1 AND 100
    ),
    premium REAL CHECK (premium IS NULL OR premium >= 0),
    decision TEXT NOT NULL CHECK (
        decision IN ('approve', 'refer', 'decline')
    ),
    reason TEXT NOT NULL,
    created_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS underwriting_decisions (
    decision_id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL REFERENCES quotes(quote_id),
    outcome TEXT NOT NULL CHECK (
        outcome IN ('approve', 'refer', 'decline')
    ),
    reason TEXT NOT NULL,
    authority_level TEXT NOT NULL CHECK (
        authority_level IN (
            'system_rules',
            'system_automatic',
            'underwriter',
            'risk_compliance_reviewer',
            'senior_underwriter'
        )
    ),
    decided_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS policies (
    policy_id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL REFERENCES quotes(quote_id),
    applicant_id TEXT NOT NULL REFERENCES applicants(applicant_id),
    asset_id TEXT NOT NULL REFERENCES insured_assets(asset_id),
    product_code TEXT NOT NULL REFERENCES products(product_code),
    coverage_amount REAL NOT NULL CHECK (coverage_amount > 0),
    premium REAL,
    status TEXT NOT NULL CHECK (
        status IN ('issued', 'blocked', 'cancelled')
    ),
    accepted INTEGER NOT NULL CHECK (accepted IN (0, 1)),
    payment_received INTEGER NOT NULL CHECK (payment_received IN (0, 1)),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    CHECK (start_date < end_date)
);

CREATE TABLE IF NOT EXISTS endorsements (
    endorsement_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES policies(policy_id),
    change_type TEXT NOT NULL,
    coverage_delta REAL NOT NULL,
    proposed_coverage REAL NOT NULL,
    prior_asset_id TEXT REFERENCES insured_assets(asset_id),
    replacement_asset_id TEXT REFERENCES insured_assets(asset_id),
    status TEXT NOT NULL CHECK (
        status IN ('pending_review', 'referred', 'approved', 'declined')
    ),
    effective_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS renewals (
    renewal_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES policies(policy_id),
    offered_premium REAL NOT NULL CHECK (offered_premium >= 0),
    status TEXT NOT NULL CHECK (
        status IN (
            'offered',
            'accepted',
            'declined',
            'invalid_offer_for_inactive_policy'
        )
    ),
    response TEXT NOT NULL CHECK (
        response IN ('pending', 'accepted', 'declined')
    ),
    offer_date TEXT NOT NULL,
    renewal_date TEXT NOT NULL,
    CHECK (offer_date < renewal_date)
);

CREATE TABLE IF NOT EXISTS policy_events (
    event_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES policies(policy_id),
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    details TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ground_truth (
    issue_id TEXT PRIMARY KEY,
    issue_type TEXT NOT NULL,
    entity TEXT NOT NULL,
    record_id TEXT NOT NULL,
    expected_decision TEXT NOT NULL,
    details TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_asset_applicant
    ON insured_assets(applicant_id);

CREATE INDEX IF NOT EXISTS idx_quote_applicant
    ON quotes(applicant_id);

CREATE INDEX IF NOT EXISTS idx_policy_applicant_dates
    ON policies(applicant_id, start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_event_policy_date
    ON policy_events(policy_id, event_date);