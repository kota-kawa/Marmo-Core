import React, { useState } from 'react';

const SubscribersTab = ({ 
  t, 
  lang, 
  subscribers,
  formatCurrency 
}) => {
  // GAP 9: State untuk Pencarian dan Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const safeSubs = subscribers || [];
  // GAP 9: Filter logic
  // Hitung hari sejak terdaftar untuk menentukan jatuh tempo
  const getDaysSinceRegistered = (dateStr) => {
    if (!dateStr) return null;
    const created = new Date(dateStr);
    const now = new Date();
    return Math.floor((now - created) / (1000 * 60 * 60 * 24));
  };

  // Cek apakah subscriber masuk H-3 atau H-7 (asumsi langganan 30 hari)
  const isNearExpiry = (sub, days) => {
    const d = getDaysSinceRegistered(sub.created_at);
    if (d === null) return false;
    const daysLeft = 30 - (d % 30);
    return daysLeft <= days && (sub.status === 'active' || sub.status === 'paid' || sub.status === 'near_expiry');
  };

  const filteredSubs = safeSubs.filter(sub => {
    const matchesSearch = (sub.shop_name || '').toLowerCase().includes(searchQuery.toLowerCase()) || 
                          (sub.email || '').toLowerCase().includes(searchQuery.toLowerCase());
    if (!matchesSearch) return false;
    
    if (statusFilter === 'active') return sub.status === 'active' || sub.status === 'paid';
    if (statusFilter === 'waiting') return sub.status === 'waiting_payment';
    if (statusFilter === 'expired') return sub.status === 'expired';
    if (statusFilter === 'h3') return isNearExpiry(sub, 3);
    if (statusFilter === 'h7') return isNearExpiry(sub, 7);
    return true;
  });

  const activeSubs = safeSubs.filter(s => s.status === 'active' || s.status === 'paid');
  const cancelledCount = safeSubs.filter(s => s.status === 'cancelled' || s.status === 'returned').length;
  
  // 🏮 OFFICIAL COMMISSION RATES (A — REVENUE SHARE)
  const COMMISSION_RATES = {
    pro: { starter: 100000, bronze: 100000, silver: 100000, gold: 100000, platinum: 100000 },
    elite: { starter: 119600, bronze: 119600, silver: 149600, gold: 179500, platinum: 199400 },
    ultimate: { starter: 249700, bronze: 249700, silver: 299600, gold: 374600, platinum: 449500 }
  };

  // 🏆 ANNUAL PLAN BONUSES (B.3 — PERFORMANCE BONUS - ONE TIME ONLY)
  const ANNUAL_BONUSES = { pro: 100000, elite: 250000, ultimate: 500000 };

  // 📅 CALCULATION PERIOD LOGIC (RULE #4: 26th - 25th)
  const getPeriod = () => {
    const now = new Date();
    const day = now.getDate();
    const month = now.getMonth();
    const year = now.getFullYear();
    
    let start, end;
    if (day >= 26) {
      start = new Date(year, month, 26, 0, 0, 0);
      end = new Date(year, month + 1, 25, 23, 59, 59);
    } else {
      start = new Date(year, month - 1, 26, 0, 0, 0);
      end = new Date(year, month, 25, 23, 59, 59);
    }
    return { start, end };
  };

  const period = getPeriod();
  const isNewInPeriod = (dateStr) => {
    if (!dateStr) return false;
    const d = new Date(dateStr);
    return d >= period.start && d <= period.end;
  };

  // 🛡️ TIER IDENTIFICATION (A.2 — KRITERIA TIER)
  // Based on current active count for the evaluated month
  const activeCount = activeSubs.length;
  const eliteCount = activeSubs.filter(s => ['elite', 'ultimate'].includes(s.plan?.toLowerCase())).length;

  let currentTier = 'starter';
  if (activeCount >= 15 && eliteCount >= 5) currentTier = 'platinum';
  else if (activeCount >= 8 && eliteCount >= 2) currentTier = 'gold';
  else if (activeCount >= 5 && eliteCount >= 2) currentTier = 'silver';
  else if (activeCount >= 3) currentTier = 'bronze';

  // 📊 COMMISSION CALCULATION LOGIC (RULES #4, #5, #6)
  const calculateItemCommission = (sub) => {
    if (sub.status !== 'active' && sub.status !== 'paid') return 0;
    const plan = sub.plan?.toLowerCase() || 'starter';
    if (plan === 'starter') return 0;

    const baseRate = COMMISSION_RATES[plan]?.[currentTier] || 0;
    const isNew = isNewInPeriod(sub.created_at);
    
    // Yearly Logic: Only paid in the closing month (Rule #6)
    if (sub.billing_cycle === 'Yearly') {
      if (isNew) {
        const annualBonus = ANNUAL_BONUSES[plan] || 0;
        return (baseRate * 11) + annualBonus;
      }
      return 0; // Already paid upfront in closing month
    }

    return baseRate; // Monthly recurring
  };

  // 💰 TOTALS (MTD PACE)
  const totalCommissionMTD = activeSubs.reduce((acc, curr) => acc + calculateItemCommission(curr), 0);

  // 🏆 MILESTONE CALCULATION (RULE #5: Monthly always counts, Annual only in closing month)
  const milestoneUnits = activeSubs.filter(s => {
    if (s.billing_cycle === 'Yearly') return isNewInPeriod(s.created_at);
    return true; // Monthly counts every month
  }).length;

  let volumeMilestone = 0;
  if (milestoneUnits >= 15) volumeMilestone = 750000;
  else if (milestoneUnits >= 10) volumeMilestone = 350000;
  else if (milestoneUnits >= 5) volumeMilestone = 150000;

  const bonusProgress = Math.min(100, (milestoneUnits / 5) * 100);

  const getPlanBadge = (plan) => {
    switch(plan?.toLowerCase()) {
      case 'ultimate': return 'text-orange-400 bg-orange-500/10 border-orange-500/20';
      case 'elite': return 'text-purple-400 bg-purple-500/10 border-purple-500/20';
      case 'pro': return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
      default: return 'text-zinc-400 bg-zinc-500/10 border-zinc-500/20';
    }
  };

  const getRelativeTime = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    
    if (diff < 60) return lang === 'id' ? 'baru saja' : 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + (lang === 'id' ? ' mnt lalu' : 'm ago');
    if (diff < 86400) return Math.floor(diff / 3600) + (lang === 'id' ? ' jam lalu' : 'h ago');
    return Math.floor(diff / 86400) + (lang === 'id' ? ' hari lalu' : 'd ago');
  };

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700">
      {/* 🚀 Stats Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="relative group overflow-hidden bg-zinc-900/40 backdrop-blur-md border border-zinc-800/50 p-5 rounded-2xl">
          <div className="text-[10px] font-black text-zinc-400 uppercase tracking-[0.2em] mb-3">{t('totalSubs')}</div>
          <div className="text-3xl font-black text-white font-mono tracking-tighter">{safeSubs.length}</div>
        </div>
        
        <div className="relative group overflow-hidden bg-zinc-900/40 backdrop-blur-md border border-zinc-800/50 p-5 rounded-2xl border-l-orange-500/50">
          <div className="flex justify-between items-start mb-3">
            <div className="text-[10px] font-black text-zinc-400 uppercase tracking-[0.2em]">{t('activeUser')}</div>
            <span className={`px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-widest border ${
              currentTier === 'platinum' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20 shadow-[0_0_10px_rgba(59,130,246,0.3)]' :
              currentTier === 'gold' ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
              currentTier === 'silver' ? 'bg-zinc-100/10 text-zinc-100 border-zinc-100/20' :
              'bg-zinc-800 text-zinc-500 border-zinc-700'
            }`}>
              {currentTier}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-3xl font-black text-white font-mono tracking-tighter">{activeCount}</div>
            <div className="text-[9px] font-bold text-zinc-500 uppercase tracking-tighter">
              {eliteCount} Elite/Ult
            </div>
          </div>
        </div>

        <div className="relative group overflow-hidden bg-zinc-900/40 backdrop-blur-md border border-zinc-800/50 p-5 rounded-2xl border-l-emerald-500/50">
          <div className="text-[10px] font-black text-zinc-400 uppercase tracking-[0.2em] mb-3">
            {t('commission')} 
            <span className="text-[8px] text-zinc-500 ml-2">(26 - 25)</span>
          </div>
          <div className="text-3xl font-black text-emerald-400 font-mono tracking-tighter">{formatCurrency(totalCommissionMTD)}</div>
        </div>

        <div className={`relative group overflow-hidden backdrop-blur-md border p-5 rounded-2xl transition-all duration-500 ${milestoneUnits >= 5 ? 'bg-emerald-600/10 border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.1)]' : 'bg-zinc-900/40 border-zinc-800/50 grayscale'}`}>
          <div className="flex justify-between items-start mb-3">
            <div className={`text-[10px] font-black uppercase tracking-[0.2em] ${milestoneUnits >= 5 ? 'text-emerald-500' : 'text-zinc-500'}`}>{t('performanceBonus')}</div>
            <iconify-icon icon={milestoneUnits >= 5 ? "solar:lock-unlock-bold-duotone" : "solar:lock-bold-duotone"} className={milestoneUnits >= 5 ? "text-emerald-500" : "text-zinc-500"}></iconify-icon>
          </div>
          <div className="text-3xl font-black text-white font-mono tracking-tighter mb-4">{formatCurrency(volumeMilestone)}</div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-[8px] font-black uppercase tracking-widest text-zinc-500">
              <span>{milestoneUnits >= 5 ? 'Bonus Unlocked' : 'Unlock Progress'}</span>
              <span>{milestoneUnits}/5 Units</span>
            </div>
            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all duration-1000 ${milestoneUnits >= 5 ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-zinc-700'}`}
                style={{ width: `${bonusProgress}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* 📊 Customer List Header & Filters */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 px-2">
          <div className="flex items-center gap-3 shrink-0">
            <h3 className="text-xs font-black text-white uppercase tracking-[0.3em] flex items-center gap-3">
              <div className="w-8 h-0.5 bg-orange-600 rounded-full"></div>
              {t('customerList')}
            </h3>
            <span className="text-[10px] font-black text-orange-500 bg-orange-500/10 px-3 py-1.5 rounded-full border border-orange-500/20 uppercase tracking-widest">
              {t('private')} 🔒
            </span>
          </div>
          
          {/* GAP 9: Filter & Search Controls */}
          <div className="flex flex-col sm:flex-row items-center gap-2 w-full sm:w-auto">
            <div className="relative w-full sm:w-64">
              <input 
                type="text" 
                placeholder="Cari nama toko / email..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50"
              />
              <iconify-icon icon="solar:magnifer-linear" className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"></iconify-icon>
            </div>
            <select 
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full sm:w-auto bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2 text-xs text-white focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50 appearance-none"
            >
              <option value="all">Semua Status</option>
              <option value="active">🟢 Aktif / Paid</option>
              <option value="waiting">🟡 Waiting Payment</option>
              <option value="h7">🟠 Jatuh Tempo H-7</option>
              <option value="h3">🔴 Jatuh Tempo H-3</option>
              <option value="expired">⚫ Expired</option>
            </select>
          </div>
        </div>

        <div className="bg-zinc-900/20 backdrop-blur-md border border-zinc-800/50 rounded-[32px] overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white/5 text-[10px] text-zinc-500 font-black uppercase tracking-[0.25em] border-b border-zinc-800/50">
                  <th className="px-8 py-6">{t('shopName')}</th>
                  <th className="px-8 py-6">{t('plan')}</th>
                  <th className="px-8 py-6">{t('status')}</th>
                  <th className="px-8 py-6">{lang === 'id' ? 'Terdaftar' : 'Registered'}</th>
                  <th className="px-8 py-6 text-right">{t('commission')}</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {filteredSubs.length > 0 ? (
                  filteredSubs.map((s, idx) => {
                  const currentComm = calculateItemCommission(s);
                  const isNew = isNewInPeriod(s.created_at);
                  const isYearly = s.billing_cycle === 'Yearly';

                  return (
                    <tr key={s.id} className={`group border-b border-zinc-900/50 hover:bg-white/[0.01] transition-all duration-300 ${idx === filteredSubs.length - 1 ? 'border-none' : ''}`}>
                      <td className="px-4 sm:px-8 py-4 sm:py-6">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl sm:rounded-2xl bg-zinc-800 flex items-center justify-center text-zinc-100 font-black text-[10px] sm:text-xs border border-zinc-700 group-hover:border-orange-500/50 transition-colors">
                            {s.shop_name?.charAt(0) || '?'}
                          </div>
                          <div className="flex flex-col min-w-0">
                            <span className="font-bold text-zinc-100 text-xs sm:text-sm truncate group-hover:text-white transition-colors">{s.shop_name}</span>
                            <span className="text-[8px] sm:text-[10px] text-zinc-400 font-medium truncate">{s.email}</span>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 sm:px-8 py-4 sm:py-6">
                        <div className="flex flex-col gap-1">
                          <span className={`px-2 sm:px-3 py-1 rounded-full text-[8px] sm:text-[9px] font-black uppercase tracking-widest border shadow-sm w-fit ${getPlanBadge(s.plan)}`}>
                            {s.plan}
                          </span>
                          {isYearly && (
                            <span className={`text-[7px] font-black uppercase tracking-tighter ml-1 ${isNew ? 'text-orange-500' : 'text-zinc-600'}`}>
                              {isNew ? 'Annual Bonus 💎' : 'Upfront Paid'}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 sm:px-8 py-4 sm:py-6">
                        {(() => {
                          const isExpired = s.status === 'expired' || (s.status === 'active' && s.expires_at && new Date(s.expires_at) < new Date());
                          const isNearExpiry = s.status === 'active' && s.expires_at && new Date(s.expires_at).getTime() - new Date().getTime() < 3 * 24 * 60 * 60 * 1000;
                          
                          let displayStatus = t('status' + s.status.charAt(0).toUpperCase() + s.status.slice(1)) || s.status;
                          let statusClasses = 'text-zinc-500 bg-zinc-800 border-zinc-700';
                          let dotColor = 'bg-zinc-500';

                          if (isExpired) {
                            displayStatus = 'EXPIRED';
                            statusClasses = 'text-rose-400 bg-rose-500/10 border-rose-500/20';
                            dotColor = 'bg-rose-500 animate-pulse';
                          } else if (isNearExpiry) {
                            displayStatus = 'JATUH TEMPO (H-3)';
                            statusClasses = 'text-amber-400 bg-amber-500/10 border-amber-500/20';
                            dotColor = 'bg-amber-500 animate-pulse';
                          } else if (s.status === 'active' || s.status === 'paid') {
                            statusClasses = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
                            dotColor = 'bg-emerald-500';
                          } else if (s.status === 'pending') {
                            statusClasses = 'text-amber-400 bg-amber-500/10 border-amber-500/20';
                            dotColor = 'bg-amber-500';
                          }

                          return (
                            <span className={`inline-flex items-center gap-1.5 sm:gap-2 text-[8px] sm:text-[10px] font-black uppercase tracking-widest px-2 sm:px-3 py-1 sm:py-1.5 rounded-full border ${statusClasses}`}>
                              <span className={`h-1 w-1 sm:h-1.5 sm:w-1.5 rounded-full ${dotColor}`}></span>
                              {displayStatus}
                            </span>
                          );
                        })()}
                      </td>
                      <td className="px-4 sm:px-8 py-4 sm:py-6">
                        <span className={`text-[10px] sm:text-xs font-bold ${getRelativeTime(s.created_at) === (lang === 'id' ? 'baru saja' : 'just now') ? 'text-emerald-400' : 'text-zinc-400'}`}>
                          {getRelativeTime(s.created_at)}
                        </span>
                      </td>
                      <td className={`px-4 sm:px-8 py-4 sm:py-6 text-right font-mono font-black text-[10px] sm:text-sm group-hover:text-emerald-300 transition-colors ${currentComm === 0 ? 'text-zinc-600' : 'text-zinc-100'}`}>
                        {currentComm === 0 && isYearly && !isNew ? 'PROCESSED' : formatCurrency(currentComm)}
                      </td>
                    </tr>
                  );
                })
                ) : (
                  <tr>
                    <td colSpan="5" className="px-8 py-12 text-center text-zinc-500 text-xs">
                      Tidak ada data klien yang sesuai dengan filter pencarian.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SubscribersTab;



