-- Update orders table to include shipped_at for health speed calculation
ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipped_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS rating DECIMAL(2,1);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS chat_respon_time INTEGER; -- in minutes
