import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://gejccutabxtyxsveczvd.supabase.co';
const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlamNjdXRhYnh0eXhzdmVjenZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxMTkxOTUsImV4cCI6MjA5MjY5NTE5NX0.rJfuHK_2HsGaXWoVCKOwNNzfKlPJ-tHAaL8dmdocB1c';
const supabase = createClient(SUPABASE_URL, ANON_KEY);

// Replicate EXACT commission logic from SubscribersTab.jsx
const COMMISSION_RATES = {
  pro:     { starter: 100000, bronze: 100000, silver: 100000, gold: 100000, platinum: 100000 },
  elite:   { starter: 119600, bronze: 119600, silver: 149600, gold: 179500, platinum: 199400 },
  ultimate:{ starter: 249700, bronze: 249700, silver: 299600, gold: 374600, platinum: 449500 }
};
const ANNUAL_BONUSES = { pro: 100000, elite: 250000, ultimate: 500000 };

async function compute() {
  const partnerId = 'cb115ca7-c3fb-4aee-b68b-42540f7e9af2';
  const { data: subs } = await supabase.from('clients').select('*').eq('partner_id', partnerId);
  const { data: payouts } = await supabase.from('payouts').select('*').eq('partner_id', partnerId).order('created_at', { ascending: true });

  console.log("Subscribers:", subs?.map(s => `${s.email} | ${s.plan} | ${s.status} | ${s.created_at?.slice(0,10)}`));
  
  // For each payout period, compute breakdown
  for (const payout of payouts || []) {
    const periodDate = new Date(payout.created_at);
    
    // Subscribers active during this period (created before payout date)
    const activeSubs = (subs || []).filter(s => {
      const created = new Date(s.created_at);
      return created <= periodDate && (s.status === 'active' || s.status === 'paid');
    });
    
    const activeCount = activeSubs.length;
    const eliteCount = activeSubs.filter(s => ['elite','ultimate'].includes(s.plan?.toLowerCase())).length;
    
    // Tier determination
    let tier = 'starter';
    if (activeCount >= 15 && eliteCount >= 5) tier = 'platinum';
    else if (activeCount >= 8 && eliteCount >= 2) tier = 'gold';
    else if (activeCount >= 5 && eliteCount >= 2) tier = 'silver';
    else if (activeCount >= 3) tier = 'bronze';
    
    // Revenue share calculation
    let revenueShare = 0;
    let annualBonuses = 0;
    activeSubs.forEach(s => {
      const plan = s.plan?.toLowerCase();
      if (!plan || plan === 'starter') return;
      const rate = COMMISSION_RATES[plan]?.[tier] || 0;
      // Check if it's new in current period (within 30 days before payout)
      const created = new Date(s.created_at);
      const daysBeforePayout = (periodDate - created) / (1000*60*60*24);
      if (s.billing_cycle === 'Yearly' && daysBeforePayout <= 35) {
        revenueShare += rate * 11;
        annualBonuses += ANNUAL_BONUSES[plan] || 0;
      } else if (s.billing_cycle !== 'Yearly') {
        revenueShare += rate;
      }
    });
    
    // Volume milestone
    const milestoneUnits = activeSubs.filter(s => s.billing_cycle !== 'Yearly').length;
    let volumeBonus = 0;
    if (milestoneUnits >= 15) volumeBonus = 750000;
    else if (milestoneUnits >= 10) volumeBonus = 350000;
    else if (milestoneUnits >= 5) volumeBonus = 150000;
    
    const perfBonus = volumeBonus + annualBonuses;
    
    console.log(`\nPeriod: ${payout.period}`);
    console.log(`  ID: ${payout.id}`);
    console.log(`  Amount (DB): ${payout.amount}`);
    console.log(`  Active subs at time: ${activeCount}, tier: ${tier}`);
    console.log(`  Revenue Share (calc): ${revenueShare}`);
    console.log(`  Performance Bonus (calc): ${perfBonus} [vol:${volumeBonus}, annual:${annualBonuses}]`);
    console.log(`  DIFF from DB amount: ${payout.amount - revenueShare - perfBonus}`);
  }
}

compute();
