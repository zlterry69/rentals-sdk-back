-- RENTALS-BACK: Initial Database Schema
-- Migration: 001_initial_schema.sql

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Catálogo de monedas
CREATE TABLE currencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,      -- cur_...
    code TEXT UNIQUE NOT NULL,           -- 'PEN','USD','USDT','USDC'
    name TEXT NOT NULL,
    decimals INTEGER NOT NULL DEFAULT 2,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Catálogo de estados de proceso
CREATE TABLE process_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,      -- sts_...
    code TEXT UNIQUE NOT NULL,           -- 'PENDING','PAID','CONFIRMED','FAILED','LATE','EXPIRED'
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deudores / inquilinos
CREATE TABLE debtors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,      -- deb_...
    name TEXT NOT NULL,
    document_number TEXT,
    phone TEXT,
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unidades (departamentos/oficinas)
CREATE TABLE units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,      -- unt_...
    floor TEXT,
    unit_type TEXT,
    label TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Contratos (lease)
CREATE TABLE leases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,      -- lea_...
    debtor_id UUID REFERENCES debtors(id) ON DELETE CASCADE,
    unit_id UUID REFERENCES units(id) ON DELETE SET NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    rent_amount NUMERIC(12,2) NOT NULL,
    currency_id UUID REFERENCES currencies(id),
    guarantee BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bancos / proveedores / redes cripto
CREATE TABLE banks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,      -- bnk_...
    code TEXT UNIQUE NOT NULL,           -- 'COINGATE','NOWPAY','ETH','TRON','DOGE'
    name TEXT NOT NULL,
    provider_type TEXT NOT NULL,         -- 'gateway'|'network'|'bank'
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pagos / recibos
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,      -- pay_...
    debtor_id UUID REFERENCES debtors(id) ON DELETE CASCADE,
    lease_id UUID REFERENCES leases(id) ON DELETE SET NULL,
    period TEXT NOT NULL,                 -- 'YYYY-MM'
    due_date DATE,
    paid_at TIMESTAMPTZ,
    amount NUMERIC(12,2) NOT NULL,
    currency_id UUID REFERENCES currencies(id),
    method TEXT,                          -- 'cash'|'transfer'|'crypto'
    reference TEXT,                       -- nro operación / tx hash
    status_id UUID REFERENCES process_status(id),
    meter_start INTEGER,
    meter_end INTEGER,
    notes TEXT,
    s3_key TEXT,                          -- recibo en S3
    bank_id UUID REFERENCES banks(id),    -- proveedor/red
    invoice_id TEXT,                      -- id de invoice del gateway
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX idx_payments_debtor_period ON payments (debtor_id, period);
CREATE INDEX idx_payments_status_due_date ON payments (status_id, due_date);
CREATE INDEX idx_leases_debtor ON leases (debtor_id);
CREATE INDEX idx_payments_created_at ON payments (created_at);
CREATE INDEX idx_debtors_public_id ON debtors (public_id);
CREATE INDEX idx_units_public_id ON units (public_id);
CREATE INDEX idx_leases_public_id ON leases (public_id);
CREATE INDEX idx_payments_public_id ON payments (public_id);

-- Comentarios para documentar las tablas
COMMENT ON TABLE currencies IS 'Catálogo de monedas soportadas';
COMMENT ON TABLE process_status IS 'Estados del proceso de pago';
COMMENT ON TABLE debtors IS 'Deudores o inquilinos del sistema';
COMMENT ON TABLE units IS 'Unidades habitacionales o de oficina';
COMMENT ON TABLE leases IS 'Contratos de alquiler';
COMMENT ON TABLE banks IS 'Bancos, proveedores de pago y redes cripto';
COMMENT ON TABLE payments IS 'Pagos y recibos del sistema';
