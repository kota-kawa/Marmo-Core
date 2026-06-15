import { createClient } from '@supabase/supabase-js';
import fs from 'fs';

const env = fs.readFileSync('.env', 'utf8').split('\n').reduce((acc, line) => {
  const [k, v] = line.split('=');
  if (k && v) acc[k.trim()] = v.trim().replace(/['"]/g, '');
  return acc;
}, {});

const supabase = createClient(env.VITE_SUPABASE_URL, env.VITE_SUPABASE_ANON_KEY);

async function check() {
  const { data: clients, error } = await supabase
    .from('clients')
    .select('*')
    .eq('email', 'flux1@mailinator.com');

  const { data: profiles, error: pe } = await supabase
    .from('profiles')
    .select('*')
    .eq('email', 'flux1@mailinator.com');
    
  console.log("=== FLUX1 CLIENT ===");
  console.log(clients);
  console.log("=== FLUX1 PROFILE ===");
  console.log(profiles);
}

check();
