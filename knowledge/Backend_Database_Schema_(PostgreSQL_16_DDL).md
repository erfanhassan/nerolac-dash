# Nerolac Operations Dashboard: PostgreSQL 16 DDL Schema

> [!CAUTION]
> **SCHEMA INTEGRITY LOCK ACTIVE**
> This file defines the canonical PostgreSQL 16 database schema for the Nerolac Operations Dashboard.
> Unauthorized modifications without executing the automated test suite (`pytest tests/`) are strictly forbidden by `.agents/rules.md`.

```sql
-- PostgreSQL 16 Production DDL Specification
-- Schema: nerolac_ops

CREATE SCHEMA IF NOT EXISTS nerolac_ops;

-- 1. Plants and Production Facilities
CREATE TABLE IF NOT EXISTS nerolac_ops.production_plants (
    plant_id VARCHAR(32) PRIMARY KEY,
    plant_code VARCHAR(16) NOT NULL UNIQUE,
    plant_name VARCHAR(128) NOT NULL,
    location_city VARCHAR(64) NOT NULL,
    state VARCHAR(64) NOT NULL,
    operational_capacity_liters_day NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    current_status VARCHAR(24) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Product Catalog
CREATE TABLE IF NOT EXISTS nerolac_ops.products (
    product_id VARCHAR(32) PRIMARY KEY,
    sku_code VARCHAR(32) NOT NULL UNIQUE,
    product_name VARCHAR(256) NOT NULL,
    category VARCHAR(64) NOT NULL, -- 'DECORATIVE', 'INDUSTRIAL', 'AUTOMOTIVE', 'POWDER_COATING'
    finish_type VARCHAR(64) NOT NULL, -- 'GLOSS', 'MATTE', 'SATIN', 'METALLIC'
    base_unit VARCHAR(16) NOT NULL DEFAULT 'LITERS',
    unit_price NUMERIC(10, 2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Dealers and Distribution Network
CREATE TABLE IF NOT EXISTS nerolac_ops.dealers (
    dealer_id VARCHAR(32) PRIMARY KEY,
    dealer_code VARCHAR(32) NOT NULL UNIQUE,
    trade_name VARCHAR(256) NOT NULL,
    gstin VARCHAR(20) NOT NULL UNIQUE,
    region VARCHAR(32) NOT NULL, -- 'NORTH', 'SOUTH', 'EAST', 'WEST'
    city VARCHAR(64) NOT NULL,
    credit_limit NUMERIC(14, 2) NOT NULL DEFAULT 500000.00,
    outstanding_balance NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    tier VARCHAR(16) NOT NULL DEFAULT 'GOLD', -- 'PLATINUM', 'GOLD', 'SILVER'
    is_verified BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. Inventory Tracking
CREATE TABLE IF NOT EXISTS nerolac_ops.inventory_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    plant_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.production_plants(plant_id) ON DELETE RESTRICT,
    product_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.products(product_id) ON DELETE RESTRICT,
    batch_number VARCHAR(64) NOT NULL,
    quantity_liters NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    reserved_liters NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_plant_product_batch UNIQUE (plant_id, product_id, batch_number)
);

-- 5. Order Management
CREATE TABLE IF NOT EXISTS nerolac_ops.orders (
    order_id VARCHAR(32) PRIMARY KEY,
    order_number VARCHAR(32) NOT NULL UNIQUE,
    dealer_id VARCHAR(32) NOT NULL REFERENCES nerolac_ops.dealers(dealer_id) ON DELETE RESTRICT,
    total_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    order_status VARCHAR(32) NOT NULL DEFAULT 'SUBMITTED', -- 'SUBMITTED', 'CONFIRMED', 'DISPATCHED', 'DELIVERED', 'CANCELLED'
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for optimal query performance
CREATE INDEX IF NOT EXISTS idx_inventory_plant ON nerolac_ops.inventory_snapshots(plant_id);
CREATE INDEX IF NOT EXISTS idx_inventory_product ON nerolac_ops.inventory_snapshots(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_dealer ON nerolac_ops.orders(dealer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON nerolac_ops.orders(order_status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON nerolac_ops.orders(created_at);
```
