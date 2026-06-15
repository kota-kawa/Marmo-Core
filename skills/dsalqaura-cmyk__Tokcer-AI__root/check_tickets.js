import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  'https://gejccutabxtyxsveczvd.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlamNjdXRhYnh0eXhzdmVjenZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxMTkxOTUsImV4cCI6MjA5MjY5NTE5NX0.rJfuHK_2HsGaXWoVCKOwNNzfKlPJ-tHAaL8dmdocB1c'
);

async function check() {
  // Test simple select first
  const { data: t1, error: e1 } = await supabase.from('support_tickets').select('*').limit(3);
  console.log("support_tickets (simple):", t1?.length, e1?.message);

  // Test with join that InternalDashboard uses
  const { data: t2, error: e2 } = await supabase
    .from('support_tickets')
    .select('*, partners(full_name), clients:user_id(shop_name)')
    .order('created_at', { ascending: false });
  console.log("support_tickets (with join):", t2?.length, e2?.message);

  // Test ideas
  const { data: i1, error: ie1 } = await supabase.from('partner_ideas').select('*').limit(3);
  console.log("partner_ideas (simple):", i1?.length, ie1?.message);

  const { data: i2, error: ie2 } = await supabase
    .from('partner_ideas')
    .select('*, partners(full_name)')
    .order('created_at', { ascending: false });
  console.log("partner_ideas (with join):", i2?.length, ie2?.message);
}
check();
