-- Buat tabel untuk pendaftar Waitlist
CREATE TABLE waitlist (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  nama text NOT NULL,
  email text NOT NULL UNIQUE,
  phone text NOT NULL,
  affiliate_id text,
  business_type text,
  platforms text[] NOT NULL,
  platform_other text
);

-- Mengaktifkan RLS untuk Waitlist
ALTER TABLE waitlist ENABLE ROW LEVEL SECURITY;

-- Membuat policy agar user anonim dapat melakukan INSERT ke tabel Waitlist
CREATE POLICY "Allow anonymous insert waitlist" ON waitlist
  FOR INSERT WITH CHECK (true);

-- Buat tabel untuk pendaftar Partner
CREATE TABLE partners (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  nama text NOT NULL,
  email text NOT NULL UNIQUE,
  phone text NOT NULL,
  media_link text NOT NULL,
  niche text NOT NULL,
  followers text NOT NULL,
  promo_methods text[] NOT NULL,
  promo_strategy text NOT NULL
);

-- Mengaktifkan RLS untuk Partners
ALTER TABLE partners ENABLE ROW LEVEL SECURITY;

-- Membuat policy agar user anonim dapat melakukan INSERT ke tabel Partners
CREATE POLICY "Allow anonymous insert partners" ON partners
  FOR INSERT WITH CHECK (true);
