-- ============================================================================
-- RENTALS-BACK: Setup completo para Supabase
-- Copia y pega este SQL completo en el SQL Editor de Supabase
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLAS PRINCIPALES
-- ============================================================================

-- Catálogo de monedas
CREATE TABLE IF NOT EXISTS currencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    decimals INTEGER NOT NULL DEFAULT 2,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Catálogo de estados de proceso
CREATE TABLE IF NOT EXISTS process_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,
    code TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deudores / inquilinos
CREATE TABLE IF NOT EXISTS debtors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    document_number TEXT,
    phone TEXT,
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unidades (departamentos/oficinas)
CREATE TABLE IF NOT EXISTS units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,
    floor TEXT,
    unit_type TEXT,
    label TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Contratos (lease)
CREATE TABLE IF NOT EXISTS leases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,
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
CREATE TABLE IF NOT EXISTS banks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pagos / recibos
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,
    debtor_id UUID REFERENCES debtors(id) ON DELETE CASCADE,
    lease_id UUID REFERENCES leases(id) ON DELETE SET NULL,
    period TEXT NOT NULL,
    due_date DATE,
    paid_at TIMESTAMPTZ,
    amount NUMERIC(12,2) NOT NULL,
    currency_id UUID REFERENCES currencies(id),
    method TEXT,
    reference TEXT,
    status_id UUID REFERENCES process_status(id),
    meter_start INTEGER,
    meter_end INTEGER,
    notes TEXT,
    s3_key TEXT,
    bank_id UUID REFERENCES banks(id),
    invoice_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- TABLAS DE FACTURACIÓN
-- ============================================================================

-- Tabla de facturas/invoices
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,
    payment_id UUID REFERENCES payments(id) ON DELETE CASCADE,
    invoice_number TEXT UNIQUE NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    currency_id UUID REFERENCES currencies(id),
    origin TEXT NOT NULL,
    metadata JSONB,
    external_id TEXT,
    external_url TEXT,
    webhook_url TEXT,
    status TEXT DEFAULT 'PENDING',
    pdf_s3_key TEXT,
    pdf_url TEXT,
    expires_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Métodos de pago disponibles
CREATE TABLE IF NOT EXISTS payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    icon_url TEXT,
    description TEXT,
    config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Logs de webhooks
CREATE TABLE IF NOT EXISTS webhook_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    event_type TEXT,
    headers JSONB,
    payload JSONB,
    processed BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- ÍNDICES PARA OPTIMIZACIÓN
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_payments_debtor_period ON payments (debtor_id, period);
CREATE INDEX IF NOT EXISTS idx_payments_status_due_date ON payments (status_id, due_date);
CREATE INDEX IF NOT EXISTS idx_leases_debtor ON leases (debtor_id);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments (created_at);
CREATE INDEX IF NOT EXISTS idx_debtors_public_id ON debtors (public_id);
CREATE INDEX IF NOT EXISTS idx_units_public_id ON units (public_id);
CREATE INDEX IF NOT EXISTS idx_leases_public_id ON leases (public_id);
CREATE INDEX IF NOT EXISTS idx_payments_public_id ON payments (public_id);
CREATE INDEX IF NOT EXISTS idx_invoices_payment_id ON invoices (payment_id);
CREATE INDEX IF NOT EXISTS idx_invoices_origin ON invoices (origin);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices (status);
CREATE INDEX IF NOT EXISTS idx_invoices_external_id ON invoices (external_id);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices (created_at);
CREATE INDEX IF NOT EXISTS idx_invoices_public_id ON invoices (public_id);
CREATE INDEX IF NOT EXISTS idx_payment_methods_code ON payment_methods (code);
CREATE INDEX IF NOT EXISTS idx_payment_methods_type ON payment_methods (type);
CREATE INDEX IF NOT EXISTS idx_payment_methods_is_active ON payment_methods (is_active);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_invoice_id ON webhook_logs (invoice_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_provider ON webhook_logs (provider);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_processed ON webhook_logs (processed);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_created_at ON webhook_logs (created_at);

-- ============================================================================
-- TRIGGERS PARA AUDITORÍA
-- ============================================================================

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para updated_at
DROP TRIGGER IF EXISTS update_invoices_updated_at ON invoices;
CREATE TRIGGER update_invoices_updated_at 
    BEFORE UPDATE ON invoices 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_payment_methods_updated_at ON payment_methods;
CREATE TRIGGER update_payment_methods_updated_at 
    BEFORE UPDATE ON payment_methods 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- DATOS INICIALES
-- ============================================================================

-- Monedas
INSERT INTO currencies (public_id, code, name, decimals) VALUES
('cur_8fZk12Qp9L', 'PEN', 'Peruvian Sol', 2),
('cur_9gAl23Rq0M', 'USD', 'US Dollar', 2),
('cur_0hBm34Sr1N', 'USDT', 'Tether USD', 2),
('cur_1iCn45Ts2O', 'USDC', 'USD Coin', 2),
('cur_btc_001', 'BTC', 'Bitcoin', 8),
('cur_eth_001', 'ETH', 'Ethereum', 18),
('cur_ltc_001', 'LTC', 'Litecoin', 8),
('cur_doge_001', 'DOGE', 'Dogecoin', 8)
ON CONFLICT (code) DO NOTHING;

-- Estados de proceso
INSERT INTO process_status (public_id, code, description) VALUES
('sts_2jDo56Ut3P', 'PENDING', 'Pago pendiente de confirmación'),
('sts_3kEp67Vu4Q', 'PAID', 'Pago confirmado y procesado'),
('sts_4lFq78Wv5R', 'CONFIRMED', 'Pago verificado y confirmado'),
('sts_5mGr89Xw6S', 'FAILED', 'Pago fallido o rechazado'),
('sts_6nHs90Yx7T', 'LATE', 'Pago vencido y atrasado'),
('sts_7oIt01Zy8U', 'EXPIRED', 'Pago expirado sin procesar'),
('sts_invoice_pending', 'INVOICE_PENDING', 'Factura creada, esperando pago'),
('sts_invoice_paid', 'INVOICE_PAID', 'Factura pagada exitosamente'),
('sts_invoice_expired', 'INVOICE_EXPIRED', 'Factura expirada sin pago'),
('sts_invoice_failed', 'INVOICE_FAILED', 'Error en el procesamiento del pago'),
('sts_invoice_cancelled', 'INVOICE_CANCELLED', 'Factura cancelada por el usuario')
ON CONFLICT (code) DO NOTHING;

-- Bancos/proveedores
INSERT INTO banks (public_id, code, name, provider_type, status) VALUES
('bnk_8pJu12Za9V', 'COINGATE', 'CoinGate', 'gateway', 'ACTIVE'),
('bnk_9qKv23Ab0W', 'NOWPAY', 'NOWPayments', 'gateway', 'ACTIVE'),
('bnk_0rLw34Bc1X', 'ETH', 'Ethereum Network', 'network', 'ACTIVE'),
('bnk_1sMx45Cd2Y', 'TRON', 'TRON Network', 'network', 'ACTIVE'),
('bnk_2tNy56De3Z', 'DOGE', 'Dogecoin Network', 'network', 'ACTIVE'),
('bnk_3uOz67Ef4A', 'BANCO', 'Banco de la Nación', 'bank', 'ACTIVE'),
('bnk_4vPa78Fg5B', 'INTERBANK', 'Interbank', 'bank', 'ACTIVE'),
('bnk_mercadopago_001', 'MERCADOPAGO', 'MercadoPago', 'gateway', 'ACTIVE'),
('bnk_izipay_001', 'IZIPAY', 'Izipay', 'gateway', 'ACTIVE')
ON CONFLICT (code) DO NOTHING;

-- Métodos de pago
INSERT INTO payment_methods (public_id, name, code, type, description, is_active, config) VALUES
('pm_mercadopago_001', 'MercadoPago', 'mercadopago', 'traditional', 'Pagos con tarjetas, Yape, Plin y transferencias bancarias', true, '{
    "api_url": "https://api.mercadopago.com",
    "webhook_url": "/webhooks/mercadopago",
    "supported_currencies": ["PEN", "USD"],
    "payment_types": ["credit_card", "debit_card", "bank_transfer", "yape", "plin"]
}'::jsonb),
('pm_izipay_001', 'Izipay', 'izipay', 'traditional', 'Procesador de pagos con tarjetas y métodos locales', true, '{
    "api_url": "https://api.izipay.pe",
    "webhook_url": "/webhooks/izipay",
    "supported_currencies": ["PEN", "USD"],
    "payment_types": ["credit_card", "debit_card", "bank_transfer"]
}'::jsonb),
('pm_nowpayments_001', 'NOWPayments', 'nowpayments', 'crypto', 'Pagos con Bitcoin, Ethereum, USDT y otras criptomonedas', true, '{
    "api_url": "https://api.nowpayments.io",
    "webhook_url": "/webhooks/nowpayments",
    "supported_currencies": ["BTC", "ETH", "USDT", "USDC", "LTC", "DOGE"],
    "payment_types": ["crypto"]
}'::jsonb)
ON CONFLICT (code) DO NOTHING;

-- Deudores de ejemplo
INSERT INTO debtors (public_id, name, document_number, phone, email) VALUES
('deb_5wQb89Gh6C', 'Juan Pérez', '12345678', '+51 999 123 456', 'juan.perez@email.com'),
('deb_6xRc90Hi7D', 'María García', '87654321', '+51 999 654 321', 'maria.garcia@email.com')
ON CONFLICT (public_id) DO NOTHING;

-- Unidades de ejemplo
INSERT INTO units (public_id, floor, unit_type, label) VALUES
('unt_7ySd01Ij8E', '1', 'apartment', 'Apto 101'),
('unt_8zTe12Jk9F', '2', 'apartment', 'Apto 201'),
('unt_9aUf23Kl0G', '1', 'office', 'Oficina 101')
ON CONFLICT (public_id) DO NOTHING;

-- Contratos de ejemplo
INSERT INTO leases (public_id, debtor_id, unit_id, start_date, end_date, rent_amount, currency_id, guarantee) VALUES
('lea_0bVg34Lm1H', 
 (SELECT id FROM debtors WHERE public_id = 'deb_5wQb89Gh6C'),
 (SELECT id FROM units WHERE public_id = 'unt_7ySd01Ij8E'),
 '2024-01-01', '2024-12-31', 2500.00,
 (SELECT id FROM currencies WHERE code = 'PEN'), false),
('lea_1cWh45Mn2I',
 (SELECT id FROM debtors WHERE public_id = 'deb_6xRc90Hi7D'),
 (SELECT id FROM units WHERE public_id = 'unt_8zTe12Jk9F'),
 '2024-01-01', '2024-12-31', 2800.00,
 (SELECT id FROM currencies WHERE code = 'PEN'), true)
ON CONFLICT (public_id) DO NOTHING;

-- Pagos de ejemplo
INSERT INTO payments (public_id, debtor_id, lease_id, period, due_date, amount, currency_id, method, status_id, notes) VALUES
('pay_2dXi56No3J',
 (SELECT id FROM debtors WHERE public_id = 'deb_5wQb89Gh6C'),
 (SELECT id FROM leases WHERE public_id = 'lea_0bVg34Lm1H'),
 '2024-01', '2024-01-05', 2500.00,
 (SELECT id FROM currencies WHERE code = 'PEN'),
 'transfer',
 (SELECT id FROM process_status WHERE code = 'PAID'),
 'Pago de enero 2024'),
('pay_3eYj67Op4K',
 (SELECT id FROM debtors WHERE public_id = 'deb_6xRc90Hi7D'),
 (SELECT id FROM leases WHERE public_id = 'lea_1cWh45Mn2I'),
 '2024-01', '2024-01-05', 2800.00,
 (SELECT id FROM currencies WHERE code = 'PEN'),
 'crypto',
 (SELECT id FROM process_status WHERE code = 'PENDING'),
 'Pago de enero 2024 - pendiente confirmación')
ON CONFLICT (public_id) DO NOTHING;

-- ============================================================================
-- VERIFICACIÓN FINAL
-- ============================================================================

-- Mostrar resumen de tablas creadas
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
