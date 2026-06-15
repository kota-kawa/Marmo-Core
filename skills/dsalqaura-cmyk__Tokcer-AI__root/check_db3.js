import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://gejccutabxtyxsveczvd.supabase.co';
const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlamNjdXRhYnh0eXhzdmVjenZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxMTkxOTUsImV4cCI6MjA5MjY5NTE5NX0.rJfuHK_2HsGaXWoVCKOwNNzfKlPJ-tHAaL8dmdocB1c';

const supabase = createClient(SUPABASE_URL, ANON_KEY);

async function check() {
  console.log("Checking clients table...");
  
  const { data: clients, error: ce } = await supabase
    .from('clients')
    .select('id, email, shop_name, plan, status, payment_method, partner_id, created_at')
    .order('created_at', { ascending: false })
    .limit(10);
  
  if (ce) { console.log("Error:", JSON.stringify(ce)); return; }
  console.log("Count:", clients?.length);
  clients?.slice(0,5).forEach(c => {
    console.log(`  - ${c.email} | ${c.plan} | ${c.status} | ${c.payment_method}`);
  });
}

check();

async function checkAll() {
  // Check if RLS is blocking - try fetching without a user session
  const { data: d1, error: e1 } = await supabase.from('clients').select('count').single();
  console.log("Count result:", d1, e1);
  
  // See if table exists
  const { data: d2, error: e2 } = await supabase.rpc('version');
  console.log("DB Version:", d2, e2);
}

checkAll();
