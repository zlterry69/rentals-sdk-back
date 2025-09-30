-- RENTALS-BACK: Seed Data
-- Migration: 002_seed_data.sql

-- Insert initial currencies
INSERT INTO currencies (public_id, code, name, decimals) VALUES
('cur_8fZk12Qp9L', 'PEN', 'Peruvian Sol', 2),
('cur_9gAl23Rq0M', 'USD', 'US Dollar', 2),
('cur_0hBm34Sr1N', 'USDT', 'Tether USD', 2),
('cur_1iCn45Ts2O', 'USDC', 'USD Coin', 2);

-- Insert initial process statuses
INSERT INTO process_status (public_id, code, description) VALUES
('sts_2jDo56Ut3P', 'PENDING', 'Pago pendiente de confirmación'),
('sts_3kEp67Vu4Q', 'PAID', 'Pago confirmado y procesado'),
('sts_4lFq78Wv5R', 'CONFIRMED', 'Pago verificado y confirmado'),
('sts_5mGr89Xw6S', 'FAILED', 'Pago fallido o rechazado'),
('sts_6nHs90Yx7T', 'LATE', 'Pago vencido y atrasado'),
('sts_7oIt01Zy8U', 'EXPIRED', 'Pago expirado sin procesar');

-- Insert initial banks/providers
INSERT INTO banks (public_id, code, name, provider_type, status) VALUES
('bnk_8pJu12Za9V', 'COINGATE', 'CoinGate', 'gateway', 'ACTIVE'),
('bnk_9qKv23Ab0W', 'NOWPAY', 'NOWPayments', 'gateway', 'ACTIVE'),
('bnk_0rLw34Bc1X', 'ETH', 'Ethereum Network', 'network', 'ACTIVE'),
('bnk_1sMx45Cd2Y', 'TRON', 'TRON Network', 'network', 'ACTIVE'),
('bnk_2tNy56De3Z', 'DOGE', 'Dogecoin Network', 'network', 'ACTIVE'),
('bnk_3uOz67Ef4A', 'BANCO', 'Banco de la Nación', 'bank', 'ACTIVE'),
('bnk_4vPa78Fg5B', 'INTERBANK', 'Interbank', 'bank', 'ACTIVE');

-- Insert sample debtors (for development/testing)
INSERT INTO debtors (public_id, name, document_number, phone, email) VALUES
('deb_5wQb89Gh6C', 'Juan Pérez', '12345678', '+51 999 123 456', 'juan.perez@email.com'),
('deb_6xRc90Hi7D', 'María García', '87654321', '+51 999 654 321', 'maria.garcia@email.com');

-- Insert sample units
INSERT INTO units (public_id, floor, unit_type, label) VALUES
('unt_7ySd01Ij8E', '1', 'apartment', 'Apto 101'),
('unt_8zTe12Jk9F', '2', 'apartment', 'Apto 201'),
('unt_9aUf23Kl0G', '1', 'office', 'Oficina 101');

-- Insert sample leases
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
 (SELECT id FROM currencies WHERE code = 'PEN'), true);

-- Insert sample payments
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
 'Pago de enero 2024 - pendiente confirmación');
