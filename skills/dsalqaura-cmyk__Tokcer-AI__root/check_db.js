import { createClient } from '@supabase/supabase-js';
import fs from 'fs';

const env = fs.readFileSync('.env', 'utf8').split('\n').reduce((acc, line) => {
  const [k, v] = line.split('=');
  if (k && v) acc[k.trim()] = v.trim().replace(/['"]/g, '');
  return acc;
}, {});

const supabase = createClient(env.VITE_SUPABASE_URL, env.VITE_SUPABASE_ANON_KEY);

async function check() {
  // Check clients table directly
  const { data: clients, error: ce } = await supabase
    .from('clients')
    .select('id, email, shop_name, plan, status, payment_method, created_at')
    .order('created_at', { ascending: false })
    .limit(10);
  
  console.log("=== CLIENTS TABLE ===");
  if (ce) console.log("Error:", ce);
  else console.dir(clients, { depth: null });
}

check();
