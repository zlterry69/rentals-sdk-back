-- RENTALS-BACK: Seed Payment Methods Data
-- Migration: 004_seed_payment_methods.sql

-- Insertar métodos de pago disponibles
INSERT INTO payment_methods (public_id, name, code, type, description, is_active, config) VALUES
-- Pagos tradicionales
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

-- Pagos con criptomonedas
('pm_nowpayments_001', 'NOWPayments', 'nowpayments', 'crypto', 'Pagos con Bitcoin, Ethereum, USDT y otras criptomonedas', true, '{
    "api_url": "https://api.nowpayments.io",
    "webhook_url": "/webhooks/nowpayments",
    "supported_currencies": ["BTC", "ETH", "USDT", "USDC", "LTC", "DOGE"],
    "payment_types": ["crypto"]
}'::jsonb);

-- Insertar algunos estados de proceso adicionales si no existen
INSERT INTO process_status (public_id, code, description) VALUES
('sts_invoice_pending', 'INVOICE_PENDING', 'Factura creada, esperando pago'),
('sts_invoice_paid', 'INVOICE_PAID', 'Factura pagada exitosamente'),
('sts_invoice_expired', 'INVOICE_EXPIRED', 'Factura expirada sin pago'),
('sts_invoice_failed', 'INVOICE_FAILED', 'Error en el procesamiento del pago'),
('sts_invoice_cancelled', 'INVOICE_CANCELLED', 'Factura cancelada por el usuario')
ON CONFLICT (code) DO NOTHING;

-- Insertar bancos/proveedores adicionales para los nuevos métodos
INSERT INTO banks (public_id, code, name, provider_type, status) VALUES
('bnk_mercadopago_001', 'MERCADOPAGO', 'MercadoPago', 'gateway', 'ACTIVE'),
('bnk_izipay_001', 'IZIPAY', 'Izipay', 'gateway', 'ACTIVE')
ON CONFLICT (code) DO NOTHING;

-- Insertar monedas adicionales si no existen
INSERT INTO currencies (public_id, code, name, decimals) VALUES
('cur_btc_001', 'BTC', 'Bitcoin', 8),
('cur_eth_001', 'ETH', 'Ethereum', 18),
('cur_usdt_001', 'USDT', 'Tether USD', 6),
('cur_usdc_001', 'USDC', 'USD Coin', 6),
('cur_ltc_001', 'LTC', 'Litecoin', 8),
('cur_doge_001', 'DOGE', 'Dogecoin', 8)
ON CONFLICT (code) DO NOTHING;
