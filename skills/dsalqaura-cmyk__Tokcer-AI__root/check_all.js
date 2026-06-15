import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  'https://gejccutabxtyxsveczvd.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlamNjdXRhYnh0eXhzdmVjenZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxMTkxOTUsImV4cCI6MjA5MjY5NTE5NX0.rJfuHK_2HsGaXWoVCKOwNNzfKlPJ-tHAaL8dmdocB1c'
);

async function check() {
  // Support tickets - simple
  const { data: t, error: te } = await supabase.from('support_tickets').select('id, title, status, created_at').limit(5);
  console.log("support_tickets:", t?.length ?? 0, "items |", te?.message || "OK");
  t?.forEach(r => console.log(" -", r.title, "|", r.status));

  // Partner ideas - simple
  const { data: i, error: ie } = await supabase.from('partner_ideas').select('id, title, status, created_at').limit(5);
  console.log("\npartner_ideas:", i?.length ?? 0, "items |", ie?.message || "OK");
  i?.forEach(r => console.log(" -", r.title, "|", r.status));
}
check();
