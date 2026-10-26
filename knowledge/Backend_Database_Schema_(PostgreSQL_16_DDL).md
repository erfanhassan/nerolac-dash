# Nerolac Operations Dashboard: PostgreSQL 16 DDL Schema

> [!CAUTION]
> **SCHEMA INTEGRITY LOCK ACTIVE**
> This file defines the canonical PostgreSQL 16 database schema for the Nerolac Operations Dashboard.
> Unauthorized modifications without executing the automated test suite (`pytest tests/`) are strictly forbidden by `.agents/rules.md`.

```sql
-- PostgreSQL 16 Production DDL Specification
-- Schema: nerolac_ops

CREATE SCHEMA IF NOT EXISTS nerolac_ops;

-- ============================================================================
-- 1. ENUMS
-- ============================================================================

DO $$ BEGIN
    CREATE TYPE nerolac_ops.user_role_enum AS ENUM (
        'SUPER_ADMIN',
        'FINANCE_MANAGER',
        'SUPPLY_CHAIN_PLANNER',
        'SALES_DIRECTOR',
        'DEPOT_MANAGER',
        'FIELD_OFFICER',
        'AUDITOR'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE nerolac_ops.message_status_enum AS ENUM (
        'RECEIVED',
        'PROCESSING',
        'PARSED',
        'RECONCILED',
        'FAILED',
        'FLAGGED'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE nerolac_ops.forecast_type_enum AS ENUM (
        'STATISTICAL',
        'ML_ENSEMBLE',
        'EXECUTIVE_OVERRIDE',
        'FINAL_CONSENSUS'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE nerolac_ops.ar_ap_type_enum AS ENUM (
        'RECEIVABLE',
        'PAYABLE'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- 2. MASTER TABLES (8 Tables)
-- ============================================================================

-- 2.1 Depots
CREATE TABLE IF NOT EXISTS nerolac_ops.depots (
    depot_id VARCHAR(32) PRIMARY KEY,
    depot_code VARCHAR(32) NOT NULL UNIQUE,
    depot_name VARCHAR(128) NOT NULL,
    region VARCHAR(64) NOT NULL,
    address TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2.2 Users
CREATE TABLE IF NOT EXISTS nerolac_ops.users (
    user_id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(128) NOT NULL,
    role nerolac_ops.user_role_enum NOT NULL DEFAULT 'FIELD_OFFICER',
    depot_id VARCHAR(32) REFERENCES nerolac_ops.depots(depot_id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2.3 Audit Logs
CREATE TABLE IF NOT EXISTS nerolac_ops.audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES nerolac_ops.users(user_id) ON DELETE SET NULL,
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64),
    changes JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2.4 Chart of Accounts
CREATE TABLE IF NOT EXISTS nerolac_ops.chart_of_accounts (
    account_id VARCHAR(32) PRIMARY KEY,
    account_code VARCHAR(32) NOT NULL UNIQUE,
    account_name VARCHAR(128) NOT NULL,
    account_type VARCHAR(32) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2.5 Territories
CREATE TABLE IF NOT EXISTS nerolac_ops.territories (
    territory_id VARCHAR(32) PRIMARY KEY,
    territory_code VARCHAR(32) NOT NULL UNIQUE,
    territory_name VARCHAR(128) NOT NULL,
    depot_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.depots(depot_id) ON DELETE RESTRICT,
    district VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2.6 Employees
CREATE TABLE IF NOT EXISTS nerolac_ops.employees (
    employee_id VARCHAR(32) PRIMARY KEY,
    employee_code VARCHAR(32) NOT NULL UNIQUE,
    full_name VARCHAR(128) NOT NULL,
    department VARCHAR(64) NOT NULL,
    designation VARCHAR(64) NOT NULL,
    depot_id VARCHAR(32) REFERENCES nerolac_ops.depots(depot_id) ON DELETE SET NULL,
    territory_id VARCHAR(32) REFERENCES nerolac_ops.territories(territory_id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2.7 SKUs (Product Catalog)
CREATE TABLE IF NOT EXISTS nerolac_ops.skus (
    sku_id VARCHAR(32) PRIMARY KEY,
    sku_code VARCHAR(32) NOT NULL UNIQUE,
    sku_name VARCHAR(256) NOT NULL,
    category VARCHAR(64) NOT NULL,
    sub_category VARCHAR(64),
    unit_of_measure VARCHAR(16) NOT NULL DEFAULT 'LITERS',
    unit_price NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2.8 Dealers
CREATE TABLE IF NOT EXISTS nerolac_ops.dealers (
    dealer_id VARCHAR(32) PRIMARY KEY,
    dealer_code VARCHAR(32) NOT NULL UNIQUE,
    trade_name VARCHAR(256) NOT NULL,
    territory_id VARCHAR(32) REFERENCES nerolac_ops.territories(territory_id) ON DELETE SET NULL,
    depot_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.depots(depot_id) ON DELETE RESTRICT,
    phone_number VARCHAR(32),
    credit_limit NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    outstanding_balance NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    tier VARCHAR(16) NOT NULL DEFAULT 'GOLD',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 3. TRANSACTIONAL TABLES (11 Tables)
-- ============================================================================

-- 3.1 Financial Actuals
CREATE TABLE IF NOT EXISTS nerolac_ops.financial_actuals (
    actual_id BIGSERIAL PRIMARY KEY,
    depot_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.depots(depot_id) ON DELETE RESTRICT,
    account_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.chart_of_accounts(account_id) ON DELETE RESTRICT,
    amount NUMERIC(14, 2) NOT NULL,
    fiscal_year INT NOT NULL,
    fiscal_month INT NOT NULL,
    transaction_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3.2 Financial Budgets
CREATE TABLE IF NOT EXISTS nerolac_ops.financial_budgets (
    budget_id BIGSERIAL PRIMARY KEY,
    depot_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.depots(depot_id) ON DELETE RESTRICT,
    account_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.chart_of_accounts(account_id) ON DELETE RESTRICT,
    budgeted_amount NUMERIC(14, 2) NOT NULL,
    fiscal_year INT NOT NULL,
    fiscal_month INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3.3 Procurement Register
CREATE TABLE IF NOT EXISTS nerolac_ops.procurement_register (
    procurement_id BIGSERIAL PRIMARY KEY,
    depot_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.depots(depot_id) ON DELETE RESTRICT,
    material_code VARCHAR(64) NOT NULL,
    material_name VARCHAR(128) NOT NULL,
    quantity NUMERIC(14, 2) NOT NULL,
    unit_cost NUMERIC(14, 2) NOT NULL,
    total_cost NUMERIC(14, 2) NOT NULL,
    purchase_date DATE NOT NULL,
    supplier_name VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3.4 AR / AP Aging
CREATE TABLE IF NOT EXISTS nerolac_ops.ar_ap_aging (
    aging_id BIGSERIAL PRIMARY KEY,
    entry_type nerolac_ops.ar_ap_type_enum NOT NULL,
    entity_code VARCHAR(64) NOT NULL,
    depot_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.depots(depot_id) ON DELETE RESTRICT,
    current_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    days_1_30 NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    days_31_60 NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    days_61_90 NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    days_90_plus NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    as_of_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3.5 Employee KPI Scores
CREATE TABLE IF NOT EXISTS nerolac_ops.employee_kpi_scores (
    score_id BIGSERIAL PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.employees(employee_id) ON DELETE CASCADE,
    assessment_period VARCHAR(32) NOT NULL,
    target_score NUMERIC(5, 2) NOT NULL,
    achieved_score NUMERIC(5, 2) NOT NULL,
    weightage NUMERIC(5, 2) NOT NULL DEFAULT 1.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3.6 Manpower Capacity Models
CREATE TABLE IF NOT EXISTS nerolac_ops.manpower_capacity_models (
    capacity_id BIGSERIAL PRIMARY KEY,
    depot_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.depots(depot_id) ON DELETE RESTRICT,
    department VARCHAR(64) NOT NULL,
    required_headcount INT NOT NULL,
    active_headcount INT NOT NULL,
    model_period VARCHAR(32) NOT NULL,
    utilization_rate NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3.7 Historical Sales
CREATE TABLE IF NOT EXISTS nerolac_ops.historical_sales (
    sale_id BIGSERIAL PRIMARY KEY,
    depot_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.depots(depot_id) ON DELETE RESTRICT,
    sku_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.skus(sku_id) ON DELETE RESTRICT,
    dealer_id VARCHAR(32) REFERENCES nerolac_ops.dealers(dealer_id) ON DELETE SET NULL,
    quantity_liters NUMERIC(14, 2) NOT NULL,
    net_revenue NUMERIC(14, 2) NOT NULL,
    sales_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3.8 Demand Forecasts
CREATE TABLE IF NOT EXISTS nerolac_ops.demand_forecasts (
    forecast_id BIGSERIAL PRIMARY KEY,
    depot_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.depots(depot_id) ON DELETE RESTRICT,
    sku_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.skus(sku_id) ON DELETE RESTRICT,
    forecast_date DATE NOT NULL,
    forecast_type nerolac_ops.forecast_type_enum NOT NULL DEFAULT 'STATISTICAL',
    projected_quantity_liters NUMERIC(14, 2) NOT NULL,
    confidence_lower NUMERIC(14, 2),
    confidence_upper NUMERIC(14, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3.9 WhatsApp Raw Messages
CREATE TABLE IF NOT EXISTS nerolac_ops.whatsapp_raw_messages (
    raw_id BIGSERIAL PRIMARY KEY,
    waba_message_id VARCHAR(128) NOT NULL UNIQUE,
    sender_phone VARCHAR(32) NOT NULL,
    raw_payload JSONB NOT NULL,
    status nerolac_ops.message_status_enum NOT NULL DEFAULT 'RECEIVED',
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMPTZ
);

-- 3.10 WhatsApp Parsed Sales
CREATE TABLE IF NOT EXISTS nerolac_ops.whatsapp_parsed_sales (
    parsed_id BIGSERIAL PRIMARY KEY,
    raw_message_id BIGINT NOT NULL REFERENCES nerolac_ops.whatsapp_raw_messages(raw_id) ON DELETE CASCADE,
    dealer_id VARCHAR(32) REFERENCES nerolac_ops.dealers(dealer_id) ON DELETE SET NULL,
    sku_id VARCHAR(32) REFERENCES nerolac_ops.skus(sku_id) ON DELETE SET NULL,
    parsed_quantity NUMERIC(14, 2) NOT NULL,
    parsed_price NUMERIC(14, 2) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3.11 Daily Sales Reconciliations
CREATE TABLE IF NOT EXISTS nerolac_ops.daily_sales_reconciliations (
    reconciliation_id BIGSERIAL PRIMARY KEY,
    reconciliation_date DATE NOT NULL,
    depot_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.depots(depot_id) ON DELETE RESTRICT,
    sap_reported_sales NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    whatsapp_parsed_sales NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    variance NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(32) NOT NULL DEFAULT 'BALANCED',
    reconciled_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 4. COMPOSITE INDEXES
-- ============================================================================

-- 4.1 Financial Actuals: (depot_id, fiscal_year, fiscal_month)
CREATE INDEX IF NOT EXISTS idx_fin_act_depot_time
ON nerolac_ops.financial_actuals(depot_id, fiscal_year, fiscal_month);

-- 4.2 Procurement Register: (material_code, purchase_date)
CREATE INDEX IF NOT EXISTS idx_proc_mat_date
ON nerolac_ops.procurement_register(material_code, purchase_date);

-- 4.3 Employee KPI Scores: (employee_id, assessment_period)
CREATE INDEX IF NOT EXISTS idx_emp_kpi_lookup
ON nerolac_ops.employee_kpi_scores(employee_id, assessment_period);

-- 4.4 Historical Sales: (depot_id, sku_id, sales_date)
CREATE INDEX IF NOT EXISTS idx_sales_depot_sku_date
ON nerolac_ops.historical_sales(depot_id, sku_id, sales_date);

-- 4.5 Demand Forecasts: (depot_id, sku_id, forecast_date, forecast_type)
CREATE INDEX IF NOT EXISTS idx_forecast_lookup
ON nerolac_ops.demand_forecasts(depot_id, sku_id, forecast_date, forecast_type);

-- 4.6 WhatsApp Raw Messages: (status, received_at)
CREATE INDEX IF NOT EXISTS idx_wa_status_received
ON nerolac_ops.whatsapp_raw_messages(status, received_at);
```
