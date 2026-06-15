import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(process.env.VITE_SUPABASE_URL, process.env.VITE_SUPABASE_ANON_KEY);

async function update() {
  console.log("Updating TikTok Configs...");
  
  const { error: err1 } = await supabase.from('ai_configs').upsert({
    key: 'tiktok_app_id',
    value: '6jvo03ggb4cbo'
  }, { onConflict: 'key' });
  
  if (err1) console.error("Error updating app id:", err1);
  
  const { error: err2 } = await supabase.from('ai_configs').upsert({
    key: 'tiktok_app_secret',
    value: '265a120f8a3485fd562970a653d252111329d33e'
  }, { onConflict: 'key' });

  if (err2) console.error("Error updating secret:", err2);

  console.log("Done.");
}

update();
