import React, { useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';

const OverviewSection = ({ 
  t, 
  revenuePeriod, 
  setRevenuePeriod, 
  chartRef, 
  RECENT_ACTIVITY,
  adminClients = [],
  adminPartners = [],
  globalStats = { totalRevenue: 0, totalOrders: 0, activeUsers: 0, activePartners: 0 }
}) => {
  const chartInstance = useRef(null);

  // Calculate Distribution (Show Partners if exist, otherwise show Client Plans)
  const hasPartners = adminPartners.length > 0;
  const distributionData = hasPartners 
    ? adminPartners.reduce((acc, p) => {
        let currentTier = p.tier?.toLowerCase();
        if (!currentTier) {
          const omzet = Number(p.total_omzet || 0);
          if (omzet >= 50000000) currentTier = 'platinum';
          else if (omzet >= 25000000) currentTier = 'gold';
          else if (omzet >= 10000000) currentTier = 'silver';
          else currentTier = 'bronze';
        }
        if (currentTier === 'platinum') acc.Platinum++;
        else if (currentTier === 'gold') acc.Gold++;
        else if (currentTier === 'silver') acc.Silver++;
        else acc.Bronze++;
        return acc;
      }, { Platinum: 0, Gold: 0, Silver: 0, Bronze: 0 })
    : adminClients.reduce((acc, c) => {
        const plan = c.plan?.toLowerCase() || 'starter';
        if (plan === 'ultimate') acc.Ultimate++;
        else if (plan === 'elite') acc.Elite++;
        else if (plan === 'pro') acc.Pro++;
        else acc.Starter++;
        return acc;
      }, { Ultimate: 0, Elite: 0, Pro: 0, Starter: 0 });

  const chartItems = hasPartners 
    ? [
        { label: 'Platinum', color: '#2563eb', count: distributionData.Platinum },
        { label: 'Gold', color: '#fbbf24', count: distributionData.Gold },
        { label: 'Silver', color: '#9ca3af', count: distributionData.Silver },
        { label: 'Bronze', color: '#ea580c', count: distributionData.Bronze }
      ]
    : [
        { label: 'Ultimate', color: '#9333ea', count: distributionData.Ultimate },
        { label: 'Elite', color: '#f59e0b', count: distributionData.Elite },
        { label: 'Pro', color: '#3b82f6', count: distributionData.Pro },
        { label: 'Starter', color: '#6b7280', count: distributionData.Starter }
      ];

  useEffect(() => {
    if (!chartRef.current) return;

    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = chartRef.current.getContext('2d');
    chartInstance.current = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: chartItems.map(i => i.label),
        datasets: [{
          data: chartItems.map(i => i.count),
          backgroundColor: chartItems.map(i => i.color),
          borderWidth: 0,
          cutout: '80%'
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        maintainAspectRatio: false
      }
    });

    return () => {
      if (chartInstance.current) chartInstance.current.destroy();
    };
  }, [adminPartners, adminClients]);

  const getRelativeTime = (date) => {
    if (!date) return '-';
    const now = new Date();
    const then = new Date(date);
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };
  // Subscription Revenue based on period — exclude partner complimentary accounts
  const partnerEmails = new Set((adminPartners || []).map(p => p.email).filter(Boolean));

  const getFilteredClients = () => {
    const today = new Date();
    today.setHours(0,0,0,0);
    
    return adminClients.filter(c => {
      if (c.status !== 'active') return false;
      // Exclude partner complimentary accounts (partner email = client email)
      if (partnerEmails.has(c.email)) return false;
      const dateStr = c.created_at;
      if (!dateStr) return false;
      const d = new Date(dateStr);
      
      if (revenuePeriod === 'daily') {
        return d >= today;
      } else if (revenuePeriod === 'weekly') {
        const weekAgo = new Date();
        weekAgo.setDate(weekAgo.getDate() - 7);
        return d >= weekAgo;
      } else if (revenuePeriod === 'monthly') {
        const monthAgo = new Date();
        monthAgo.setMonth(monthAgo.getMonth() - 1);
        return d >= monthAgo;
      }
      return true;
    });
  };

  const periodRevenue = getFilteredClients().reduce((acc, c) => {
    let basePrice = 0;
    if (c.plan === 'ultimate') basePrice = 1999000;
    else if (c.plan === 'elite') basePrice = 999000;
    else if (c.plan === 'pro') basePrice = 499000;
    
    const isYearly = c.billing_cycle === 'Yearly';
    return acc + (isYearly ? (basePrice * 11) : basePrice);
  }, 0);

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-zinc-900/50 p-8 rounded-[2.5rem] border border-zinc-800 mb-8 overflow-hidden relative group">
        <div className="absolute top-0 left-0 w-full h-full bg-blue-600/[0.03] pointer-events-none"></div>
        <div className="flex justify-between items-center mb-8 relative z-10">
          <div>
            <h3 className="font-black text-xl text-white uppercase tracking-tight">{t('financialHub')}</h3>
            <p className="text-sm text-zinc-500 font-medium">Live income analytics from {globalStats.activeUsers} subscribers</p>
          </div>
          <div className="flex bg-zinc-950 p-1 rounded-xl border border-zinc-800">
            {['daily', 'weekly', 'monthly'].map(p => (
              <button key={p} onClick={() => setRevenuePeriod(p)} className={`px-4 py-1.5 text-[9px] font-black uppercase tracking-widest rounded-lg transition-all ${revenuePeriod === p ? 'bg-zinc-800 text-blue-400 shadow-lg' : 'text-zinc-600 hover:text-zinc-400'}`}>{t(p)}</button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative z-10">
          <div className="p-6 bg-zinc-950 rounded-2xl border border-zinc-800/50">
            <p className="text-zinc-500 text-[10px] font-black uppercase tracking-[0.2em] mb-3">{t('grossIncome')}</p>
            <h2 className="text-2xl font-black text-white tracking-tighter">Rp {new Intl.NumberFormat('id-ID').format(globalStats.totalRevenue || 0)}</h2>
            <p className="text-[10px] font-bold text-blue-400 mt-1">Periode ini: Rp {new Intl.NumberFormat('id-ID').format(periodRevenue)}</p>
            <div className="mt-3 flex items-center gap-2">
                <span className="text-[9px] font-black bg-green-500/10 text-green-500 px-2 py-0.5 rounded tracking-widest">SUBSCRIPTION</span>
            </div>
          </div>
          <div className="p-6 bg-zinc-950 rounded-2xl border border-zinc-800/50">
            <p className="text-zinc-500 text-[10px] font-black uppercase tracking-[0.2em] mb-3">Active Subscribers</p>
            <h2 className="text-2xl font-black text-white tracking-tighter">{globalStats.activeUsers}</h2>
            <div className="mt-4 flex items-center gap-2">
                <span className="text-[9px] font-black bg-blue-500/10 text-blue-500 px-2 py-0.5 rounded tracking-widest">USERS</span>
            </div>
          </div>
          <div className="p-6 bg-zinc-950 rounded-2xl border border-zinc-800/50">
            <p className="text-zinc-500 text-[10px] font-black uppercase tracking-[0.2em] mb-3">{t('partnerPayouts')}</p>
            <div className="flex justify-between items-end">
              <div>
                <p className="text-[8px] font-black text-zinc-500 uppercase mb-1">{t('paid')}</p>
                <h2 className="text-lg font-black text-white tracking-tighter">Rp {new Intl.NumberFormat('id-ID').format(globalStats.totalPaid)}</h2>
              </div>
              <div className="text-right">
                <p className="text-[8px] font-black text-amber-500 uppercase mb-1">{t('pending')}</p>
                <h2 className="text-lg font-black text-amber-500 tracking-tighter">Rp {new Intl.NumberFormat('id-ID').format(globalStats.totalPending)}</h2>
              </div>
            </div>
          </div>
          <div className="p-6 bg-blue-600 rounded-2xl shadow-xl shadow-blue-600/20 text-white">
            <p className="text-blue-100 text-[10px] font-black uppercase tracking-[0.2em] mb-3">{t('activePartners')}</p>
            <h2 className="text-2xl font-black tracking-tighter">{globalStats.activePartners}</h2>
            <div className="mt-4 flex items-center gap-2">
                <span className="text-[9px] font-black bg-white/20 text-white px-2 py-0.5 rounded tracking-widest">TOTAL</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="bg-zinc-900/50 p-8 rounded-[2.5rem] border border-zinc-800 lg:col-span-2">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-black text-white uppercase tracking-tight">
              {hasPartners ? t('tierDist') : 'SUBSCRIPTION PLAN DISTRIBUTION'}
            </h3>
            <span className="text-[10px] font-black bg-blue-500/10 text-blue-400 px-3 py-1 rounded-full border border-blue-500/20 uppercase tracking-tighter">{t('liveMonitor')}</span>
          </div>
          <div className="flex flex-col md:flex-row items-center gap-8 md:h-40">
            <div className="w-40 h-40 relative shrink-0">
              <canvas ref={chartRef}></canvas>
            </div>
            <div className="flex-1 grid grid-cols-2 gap-x-6 gap-y-4 w-full">
              {chartItems.map((t_item) => (
                <div key={t_item.label} className="flex items-center justify-between bg-zinc-950/50 p-3 rounded-xl border border-zinc-800">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: t_item.color }}></span>
                    <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">{t_item.label}</span>
                  </div>
                  <span className="font-black text-white text-xs">{t_item.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-zinc-900/50 p-8 rounded-[2.5rem] border border-zinc-800">
            <h3 className="font-black text-white uppercase tracking-tight mb-6">{t('recentActivity')}</h3>
            <div className="space-y-6 max-h-[300px] overflow-y-auto custom-scrollbar pr-2">
                {RECENT_ACTIVITY.length > 0 ? RECENT_ACTIVITY.map((act, i) => (
                    <div key={i} className="flex gap-4 relative animate-in fade-in slide-in-from-right-2 duration-300">
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 z-10 ${act.type === 'user' ? 'bg-blue-500' : act.type === 'ticket' ? 'bg-rose-500' : 'bg-amber-500'}`}>
                            <iconify-icon icon={act.type === 'user' ? 'solar:user-bold' : act.type === 'ticket' ? 'solar:bug-bold' : 'solar:handshake-bold'} className="text-[10px] text-white"></iconify-icon>
                        </div>
                        <div className="flex-1">
                            <div className="flex justify-between items-start">
                                <p className="text-[11px] font-black text-white tracking-tight leading-none uppercase truncate max-w-[120px]">{act.user}</p>
                                <span className="text-[8px] font-bold text-zinc-600 uppercase whitespace-nowrap">{getRelativeTime(act.time)}</span>
                            </div>
                            <p className="text-[10px] text-zinc-500 font-medium mt-1 uppercase tracking-tight line-clamp-1">{act.action}</p>
                        </div>
                    </div>
                )) : (
                  <div className="py-10 text-center text-zinc-600 text-[10px] font-bold uppercase tracking-widest italic">No recent activity</div>
                )}
            </div>
        </div>
      </div>
    </div>
  );
};

export default OverviewSection;
