import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import "https://deno.land/std@0.168.0/dotenv/load.ts"

const envFile = await Deno.readTextFile(".env")
const env: Record<string, string> = {}
envFile.split('\n').forEach(line => {
    if(line && line.includes('=')) {
        const [k, v] = line.split('=')
        env[k.trim()] = v.trim()
    }
})

const supabase = createClient(env['VITE_SUPABASE_URL'], env['VITE_SUPABASE_ANON_KEY'])

async function update() {
  console.log("Updating TikTok Configs...");
  
  const { error: err1 } = await supabase.from('ai_configs').upsert({
    key: 'tiktok_app_id',
    value: '6jvo03ggb4cbo'
  }, { onConflict: 'key' });
  
  if (err1) console.log("Error 1:", err1);
  
  const { error: err2 } = await supabase.from('ai_configs').upsert({
    key: 'tiktok_app_secret',
    value: '265a120f8a3485fd562970a653d252111329d33e'
  }, { onConflict: 'key' });

  if (err2) console.log("Error 2:", err2);

  console.log("Done.");
}

update();
