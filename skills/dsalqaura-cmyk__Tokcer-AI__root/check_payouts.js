import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://gejccutabxtyxsveczvd.supabase.co';
const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlamNjdXRhYnh0eXhzdmVjenZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxMTkxOTUsImV4cCI6MjA5MjY5NTE5NX0.rJfuHK_2HsGaXWoVCKOwNNzfKlPJ-tHAaL8dmdocB1c';
const supabase = createClient(SUPABASE_URL, ANON_KEY);

async function check() {
  // Check structure of payouts table
  const { data, error } = await supabase.from('payouts').select('*').limit(3);
  if (error) console.log("Error:", error);
  else { console.log("Payouts columns:", Object.keys(data?.[0] || {})); console.dir(data, { depth: null }); }
}

check();
