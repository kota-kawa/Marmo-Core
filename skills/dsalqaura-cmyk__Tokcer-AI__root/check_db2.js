import { createClient } from '@supabase/supabase-js';
import fs from 'fs';

const env = fs.readFileSync('.env', 'utf8').split('\n').reduce((acc, line) => {
  const [k, v] = line.split('=');
  if (k && v) acc[k.trim()] = v.trim().replace(/['"]/g, '');
  return acc;
}, {});

// Use service role key to bypass RLS
const supabase = createClient(env.VITE_SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY);

async function check() {
  console.log("Checking with SERVICE ROLE...");
  
  const { data: clients, error: ce } = await supabase
    .from('clients')
    .select('id, email, shop_name, plan, status, payment_method, created_at')
    .order('created_at', { ascending: false })
    .limit(10);
  
  console.log("=== CLIENTS TABLE ===");
  if (ce) console.log("Error:", ce);
  else console.dir(clients, { depth: null });

  // Also check transactions table
  const { data: trx, error: te } = await supabase
    .from('transactions')
    .select('id, plan_name, status, created_at')
    .order('created_at', { ascending: false })
    .limit(5);
  
  console.log("\n=== TRANSACTIONS TABLE ===");
  if (te) console.log("Error:", te);
  else console.dir(trx, { depth: null });
}

check();
