-- RENTALS-BACK: Add Invoices Table
-- Migration: 003_add_invoices_table.sql

-- Tabla de facturas/invoices para manejar múltiples métodos de pago
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,           -- inv_...
    payment_id UUID REFERENCES payments(id) ON DELETE CASCADE,
    
    -- Información básica de la factura
    invoice_number TEXT UNIQUE NOT NULL,      -- Número de factura secuencial
    amount NUMERIC(12,2) NOT NULL,
    currency_id UUID REFERENCES currencies(id),
    
    -- Origen del pago (mercadopago, izipay, nowpayments)
    origin TEXT NOT NULL,                     -- 'mercadopago', 'izipay', 'nowpayments'
    
    -- Metadata del SDK (response completo del proveedor)
    metadata JSONB,                           -- Response del SDK (MercadoPago, Izipay, NOWPayments)
    
    -- URLs y referencias externas
    external_id TEXT,                         -- ID del proveedor externo
    external_url TEXT,                        -- URL de pago del proveedor
    webhook_url TEXT,                         -- URL del webhook
    
    -- Estados de la factura
    status TEXT DEFAULT 'PENDING',            -- 'PENDING', 'PAID', 'FAILED', 'EXPIRED', 'CANCELLED'
    
    -- Archivos PDF
    pdf_s3_key TEXT,                         -- Clave del PDF en S3
    pdf_url TEXT,                            -- URL pre-firmada del PDF
    
    -- Fechas importantes
    expires_at TIMESTAMPTZ,                  -- Cuándo expira el pago
    paid_at TIMESTAMPTZ,                     -- Cuándo se completó el pago
    
    -- Auditoría
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla para manejar los métodos de pago disponibles
CREATE TABLE payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id TEXT UNIQUE NOT NULL,          -- pm_...
    
    -- Información del método
    name TEXT NOT NULL,                      -- 'MercadoPago', 'Izipay', 'NOWPayments'
    code TEXT UNIQUE NOT NULL,               -- 'mercadopago', 'izipay', 'nowpayments'
    type TEXT NOT NULL,                      -- 'traditional', 'crypto'
    
    -- Configuración
    is_active BOOLEAN DEFAULT TRUE,
    icon_url TEXT,                           -- URL del ícono
    description TEXT,                        -- Descripción del método
    
    -- Configuración específica del proveedor
    config JSONB,                            -- API keys, URLs, etc.
    
    -- Auditoría
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla para logs de webhooks
CREATE TABLE webhook_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
    
    -- Información del webhook
    provider TEXT NOT NULL,                  -- 'mercadopago', 'izipay', 'nowpayments'
    event_type TEXT,                         -- Tipo de evento del webhook
    
    -- Datos del webhook
    headers JSONB,                           -- Headers de la request
    payload JSONB,                           -- Payload completo del webhook
    
    -- Estado del procesamiento
    processed BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    
    -- Auditoría
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX idx_invoices_payment_id ON invoices (payment_id);
CREATE INDEX idx_invoices_origin ON invoices (origin);
CREATE INDEX idx_invoices_status ON invoices (status);
CREATE INDEX idx_invoices_external_id ON invoices (external_id);
CREATE INDEX idx_invoices_created_at ON invoices (created_at);
CREATE INDEX idx_invoices_public_id ON invoices (public_id);

CREATE INDEX idx_payment_methods_code ON payment_methods (code);
CREATE INDEX idx_payment_methods_type ON payment_methods (type);
CREATE INDEX idx_payment_methods_is_active ON payment_methods (is_active);

CREATE INDEX idx_webhook_logs_invoice_id ON webhook_logs (invoice_id);
CREATE INDEX idx_webhook_logs_provider ON webhook_logs (provider);
CREATE INDEX idx_webhook_logs_processed ON webhook_logs (processed);
CREATE INDEX idx_webhook_logs_created_at ON webhook_logs (created_at);

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para updated_at
CREATE TRIGGER update_invoices_updated_at 
    BEFORE UPDATE ON invoices 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_methods_updated_at 
    BEFORE UPDATE ON payment_methods 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comentarios para documentar las tablas
COMMENT ON TABLE invoices IS 'Facturas generadas para pagos con diferentes proveedores';
COMMENT ON TABLE payment_methods IS 'Métodos de pago disponibles en el sistema';
COMMENT ON TABLE webhook_logs IS 'Logs de webhooks recibidos de los proveedores de pago';

COMMENT ON COLUMN invoices.origin IS 'Proveedor de pago: mercadopago, izipay, nowpayments';
COMMENT ON COLUMN invoices.metadata IS 'Response completo del SDK del proveedor';
COMMENT ON COLUMN invoices.pdf_s3_key IS 'Clave del archivo PDF en S3';
COMMENT ON COLUMN payment_methods.type IS 'Tipo de pago: traditional o crypto';
COMMENT ON COLUMN payment_methods.config IS 'Configuración específica del proveedor (API keys, etc.)';
