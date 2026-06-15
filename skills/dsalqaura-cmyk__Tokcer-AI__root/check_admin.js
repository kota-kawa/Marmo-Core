import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://gejccutabxtyxsveczvd.supabase.co';
const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlamNjdXRhYnh0eXhzdmVjenZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxMTkxOTUsImV4cCI6MjA5MjY5NTE5NX0.rJfuHK_2HsGaXWoVCKOwNNzfKlPJ-tHAaL8dmdocB1c';

const supabase = createClient(SUPABASE_URL, ANON_KEY);

async function check() {
  // 1. Login sebagai admin
  const { data: auth, error: authErr } = await supabase.auth.signInWithPassword({
    email: 'admin@tokcer-ai.com',
    password: 'Tokcer@dm1n2024!'
  });
  
  if (authErr) { console.log("Login gagal:", authErr.message); return; }
  console.log("Login OK, user_id:", auth.user?.id);
  
  // 2. Cek profil admin
  const { data: profile, error: pe } = await supabase
    .from('profiles')
    .select('id, email, role')
    .eq('id', auth.user?.id)
    .maybeSingle();
  console.log("Profile admin:", profile, pe?.message);
  
  // 3. Cek clients sebagai admin (dengan session aktif)
  const { data: clients, error: ce } = await supabase
    .from('clients')
    .select('id, email, shop_name, plan, status, payment_method, created_at')
    .order('created_at', { ascending: false })
    .limit(10);
  
  console.log("Clients (as admin):", clients?.length, ce?.message);
  clients?.slice(0,5).forEach(c => {
    console.log(`  ${c.email} | ${c.plan} | ${c.status}`);
  });
}

check();
