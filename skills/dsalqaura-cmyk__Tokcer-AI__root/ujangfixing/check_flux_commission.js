import { createClient } from '@supabase/supabase-js';

const supabaseUrl = 'https://gejccutabxtyxsveczvd.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlamNjdXRhYnh0eXhzdmVjenZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxMTkxOTUsImV4cCI6MjA5MjY5NTE5NX0.rJfuHK_2HsGaXWoVCKOwNNzfKlPJ-tHAaL8dmdocB1c';

const supabase = createClient(supabaseUrl, supabaseKey);

async function check() {
  console.log("=== MENGECEK DATA FLUX@MAILINATOR.COM ===");
  
  // 1. Cek di tabel partners
  const { data: partner, error: pError } = await supabase
    .from('partners')
    .select('*')
    .in('email', ['flux@mailinator.com', 'flux1@mailinator.com', 'flux2@mailinator.com', 'userflux@mailinator.com']);
  
  if (pError) console.error("❌ Gagal cek tabel partners:", pError.message);
  else console.log("📊 Data di tabel partners:", partner);

  // 2. Cek di tabel profiles untuk mencari ID flux, flux1, flux2 dan userflux
  const { data: prof, error: pError2 } = await supabase
    .from('profiles')
    .select('*')
    .in('email', ['flux@mailinator.com', 'flux1@mailinator.com', 'flux2@mailinator.com', 'userflux@mailinator.com']);
  
  if (pError2) console.error("❌ Gagal cek tabel profiles:", pError2.message);
  else console.log("📊 Data di tabel profiles:", prof);

  // 3. Cek di tabel clients untuk melihat partner_id
  const { data: cli, error: cError } = await supabase
    .from('clients')
    .select('*')
    .in('email', ['flux1@mailinator.com', 'flux2@mailinator.com']);
  
  if (cError) console.error("❌ Gagal cek tabel clients:", cError.message);
  else console.log("📊 Data di tabel clients:", cli);
}

check();
