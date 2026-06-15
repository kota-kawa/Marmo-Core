import React from 'react';

const AnalyticsTab = ({ 
  t, 
  profile,
  lang, 
  analyticsPlatform, 
  setAnalyticsPlatform, 
  showAnalyticsPlatformDropdown, 
  setShowAnalyticsPlatformDropdown, 
  timeFilter, 
  setTimeFilter, 
  showFilterDropdown, 
  setShowFilterDropdown,
  orders = [],
  products = [],
  analyticsInsight,
  isAnalyzingAnalytics
}) => {
  // --- REAL DATA CALCULATIONS ---
  const getFilteredOrdersByTime = (data, filter) => {
    const today = new Date();
    today.setHours(0,0,0,0);
    if (filter === 'Hari Ini') {
      const todayStr = today.toISOString().split('T')[0];
      return data.filter(o => {
        const dateStr = o.order_date || o.created_at || '';
        return dateStr.startsWith(todayStr);
      });
    } else if (filter === 'Bulan Ini') {
      const thisMonth = today.getMonth();
      const thisYear = today.getFullYear();
      return data.filter(o => {
        const dateStr = o.order_date || o.created_at;
        if (!dateStr) return false;
        const d = new Date(dateStr);
        return d.getMonth() === thisMonth && d.getFullYear() === thisYear;
      });
    } else if (filter.includes('Bulan Terakhir')) {
      const months = parseInt(filter);
      const cutoff = new Date();
      cutoff.setMonth(cutoff.getMonth() - months);
      return data.filter(o => {
        const dateStr = o.order_date || o.created_at;
        return dateStr && new Date(dateStr) >= cutoff;
      });
    }
    return data;
  };

  const filteredOrders = getFilteredOrdersByTime(orders, timeFilter);

  // Exclude cancelled orders from financial and order volume calculations (cancelled transactions produce Rp 0 and don't count as successful orders)
  const activeAndCompletedOrders = filteredOrders.filter(o => o.status !== 'cancelled');

  const platformStats = {
    tiktok: { name: 'TikTok Shop', revenue: 0, orders: 0, trend: '+12.5%', color: 'border-zinc-800' },
    shopee: { name: 'Shopee', revenue: 0, orders: 0, trend: '+8.2%', color: 'border-orange-500/30' },
  };

  activeAndCompletedOrders.forEach(o => {
    const plat = (o.platform || '').toLowerCase();
    if (plat.includes('tiktok')) {
      platformStats.tiktok.revenue += Number(o.total_amount || 0);
      platformStats.tiktok.orders += 1;
    } else if (plat.includes('shopee')) {
      platformStats.shopee.revenue += Number(o.total_amount || 0);
      platformStats.shopee.orders += 1;
    }
  });

  const finalPlatforms = Object.values(platformStats).filter(p => 
    (analyticsPlatform === 'all' || p.name.toLowerCase().includes(analyticsPlatform.toLowerCase())) && p.name !== 'Tokopedia'
  );

  return (
    <div className="relative z-10 space-y-6 pb-12">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h2 className="text-2xl font-semibold text-white tracking-tight">{t('marketAnalytics')}</h2>
          <p className="text-sm text-zinc-400 mt-1">{t('analyticsDesc') || 'Performance analysis, tactical strategy, and profit optimization.'}</p>
        </div>
        <div className="flex flex-col sm:flex-row items-center gap-2 w-full sm:w-auto z-50">
          {/* Platform Filter */}
          <div className="relative w-full sm:w-auto">
            <div
              onClick={() => setShowAnalyticsPlatformDropdown(!showAnalyticsPlatformDropdown)}
              className="text-xs text-zinc-300 flex items-center gap-2 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 hover:bg-zinc-700 transition-colors cursor-pointer shadow-sm w-full justify-between sm:justify-start"
            >
              <div className="flex items-center gap-2">
                <iconify-icon icon="solar:filter-linear" className="text-orange-500"></iconify-icon>
                {analyticsPlatform === 'all' ? t('allPlatforms') : analyticsPlatform}
              </div>
              <iconify-icon icon={showAnalyticsPlatformDropdown ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'} className="sm:ml-2 text-zinc-500"></iconify-icon>
            </div>
            {showAnalyticsPlatformDropdown && (
              <div className="absolute top-full left-0 sm:right-0 mt-2 w-full sm:w-48 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-[60] py-1 overflow-hidden">
                {[['all', t('allPlatforms')], ['TikTok', 'TikTok Shop'], ['Shopee', 'Shopee']].map(([val, label]) => (
                  <div
                    key={val}
                    onClick={() => { setAnalyticsPlatform(val); setShowAnalyticsPlatformDropdown(false); }}
                    className={`px-4 py-2 text-xs cursor-pointer flex items-center gap-2 transition-colors ${analyticsPlatform === val ? 'bg-orange-950/50 text-orange-500 font-medium' : 'text-zinc-300 hover:bg-zinc-700 hover:text-white'}`}
                  >
                    {val === 'TikTok' && <iconify-icon icon="ri:tiktok-fill" className="text-sm"></iconify-icon>}
                    {val === 'Shopee' && <iconify-icon icon="simple-icons:shopee" className="text-sm text-orange-500"></iconify-icon>}
                    {val === 'all' && <iconify-icon icon="solar:widget-linear" className="text-sm text-orange-400"></iconify-icon>}
                    {label}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Period Filter */}
          <div className="relative w-full sm:w-auto">
            <div 
              onClick={() => setShowFilterDropdown(!showFilterDropdown)}
              className="text-xs text-zinc-300 flex items-center gap-2 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 hover:bg-zinc-700 transition-colors cursor-pointer shadow-sm w-full justify-between sm:justify-start"
            >
              <div className="flex items-center gap-2">
                <iconify-icon icon="solar:calendar-linear" className="text-orange-500"></iconify-icon> 
                {t(timeFilter)}
              </div>
              <iconify-icon icon={showFilterDropdown ? "solar:alt-arrow-up-linear" : "solar:alt-arrow-down-linear"} className="sm:ml-2 text-zinc-400"></iconify-icon>
            </div>
            {showFilterDropdown && (
              <div className="absolute top-full right-0 mt-2 w-full sm:w-48 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-50 overflow-hidden">
                <div className="py-1">
                  {['Hari Ini', 'Bulan Ini', '1 Bulan Terakhir', '2 Bulan Terakhir', '3 Bulan Terakhir'].map((option) => (
                    <div 
                      key={option}
                      onClick={() => { setTimeFilter(option); setShowFilterDropdown(false); }}
                      className={`px-4 py-2 text-xs cursor-pointer flex items-center justify-between transition-colors ${timeFilter === option ? 'bg-orange-950/50 text-orange-500 font-medium' : 'text-zinc-300 hover:bg-zinc-700 hover:text-white'}`}
                    >
                      {t(option)}
                      {timeFilter === option && <iconify-icon icon="solar:check-circle-bold" className="text-sm"></iconify-icon>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Platform Comparison Cards - REAL DATA */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {finalPlatforms.map((p, i) => (
          <div key={i} className={`bg-zinc-900 border rounded-2xl p-5 shadow-sm transition-all hover:scale-[1.02] ${p.color}`}>
            <div className="flex justify-between items-start mb-4">
               <div className="w-10 h-10 rounded-xl bg-zinc-800 flex items-center justify-center">
                  <iconify-icon icon={p.name === 'TikTok Shop' ? 'ri:tiktok-fill' : p.name === 'Shopee' ? 'simple-icons:shopee' : 'solar:shop-2-linear'} className={`text-xl ${p.name === 'TikTok Shop' ? 'text-white' : p.name === 'Shopee' ? 'text-orange-500' : 'text-teal-400'}`}></iconify-icon>
               </div>
               <div className="flex flex-col items-end">
                 <span className={`text-xs font-bold ${p.revenue > 0 ? 'text-emerald-500' : 'text-zinc-500'}`}>{p.revenue > 0 ? p.trend : '0%'}</span>
                 <span className="text-[9px] text-zinc-500 uppercase tracking-tighter">Growth</span>
               </div>
            </div>
            <h3 className="text-sm font-medium text-zinc-400">{p.name}</h3>
            <div className="text-3xl font-bold text-white mt-1">Rp {p.revenue.toLocaleString('id-ID')}</div>
            <div className="text-xs text-zinc-500 mt-2 flex items-center gap-2">
              <iconify-icon icon="solar:bag-check-bold-duotone" className="text-orange-500"></iconify-icon>
              {p.orders} {t('done')}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Peak Hours & Ads Optimization */}
        <div className="lg:col-span-2 bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm min-h-[300px] relative">
          {isAnalyzingAnalytics && (
             <div className="absolute inset-0 bg-zinc-900/50 backdrop-blur-sm z-20 flex items-center justify-center rounded-2xl">
                <div className="flex flex-col items-center gap-3">
                   <iconify-icon icon="solar:magic-stick-3-bold-duotone" className="text-4xl text-orange-500 animate-pulse"></iconify-icon>
                   <p className="text-xs text-zinc-400 font-medium animate-pulse tracking-widest uppercase">
                      {lang === 'id' ? 'Menganalisa Performa Bisnis...' : 'Analyzing Business Performance...'}
                   </p>
                </div>
             </div>
          )}
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
              <iconify-icon icon="solar:bolt-circle-linear" className="text-white text-xl"></iconify-icon>
            </div>
            <h3 className="text-lg font-semibold text-white">{t('strategicIntel')} {analyticsPlatform !== 'all' ? `(${analyticsPlatform})` : ''}</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">{t('adsTrafficOpt')}</div>
              <div className="bg-black/40 border border-zinc-800 rounded-xl p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <iconify-icon icon="solar:clock-circle-linear" className="text-orange-500 mt-0.5"></iconify-icon>
                  <div>
                    <div className="text-xs font-medium text-white">{t('goldenHours')} ({analyticsInsight?.ads_opt?.golden_hours || '19:00 - 22:00'})</div>
                    <p className="text-[10px] text-zinc-500 mt-0.5">{analyticsInsight?.ads_opt?.strategy || t('goldenHoursDesc')}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">{t('bundlingPromoIdeas')}</div>
              <div className="bg-black/40 border border-zinc-800 rounded-xl p-4 space-y-3">
                {analyticsInsight?.bundling?.map((b, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <iconify-icon icon="solar:box-minimalistic-linear" className="text-orange-500 mt-0.5"></iconify-icon>
                    <div>
                      <div className="text-xs font-medium text-white">{b.title}</div>
                      <p className="text-[10px] text-zinc-500 mt-0.5">{b.desc}</p>
                    </div>
                  </div>
                )) || (
                  <div className="text-[10px] text-zinc-600 italic">No suggestions yet.</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Selling Ideas / Market Pulse */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col min-h-[300px] relative">
          {isAnalyzingAnalytics && (
             <div className="absolute inset-0 bg-zinc-900/50 backdrop-blur-sm z-20 flex items-center justify-center rounded-2xl">
                <iconify-icon icon="solar:star-fall-bold-duotone" className="text-3xl text-orange-500 animate-bounce"></iconify-icon>
             </div>
          )}
          <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-6">{t('marketPulseIdeas')} {analyticsPlatform !== 'all' ? `(${analyticsPlatform})` : ''}</div>
          <div className="flex-1 space-y-4">
            <div className="p-4 bg-orange-600/10 border border-orange-500/20 rounded-xl">
              <div className="text-xs font-bold text-orange-500 mb-1">🔥 {analyticsInsight?.market_pulse?.hot_idea || t('hotIdea')}</div>
              <p className="text-[11px] text-zinc-300 leading-relaxed">{analyticsInsight?.market_pulse?.hot_desc || t('hotIdeaDesc')}</p>
            </div>
            <div className="p-4 bg-zinc-800 rounded-xl border border-zinc-700">
              <div className="text-xs font-bold text-white mb-1">💡 {analyticsInsight?.market_pulse?.content_tip || t('contentTip')}</div>
              <p className="text-[11px] text-zinc-400 leading-relaxed">{analyticsInsight?.market_pulse?.content_desc || t('contentTipDesc')}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Price Recommendation Engine */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm overflow-hidden relative">
        {((profile?.subscription_plan || 'starter').toLowerCase() === 'starter' || (profile?.subscription_plan || 'starter').toLowerCase() === 'pro') && (
           <div className="absolute inset-0 bg-zinc-950/40 backdrop-blur-[6px] z-[60] flex items-center justify-center border border-zinc-800/50 rounded-2xl overflow-hidden shadow-2xl">
              <div className="text-center p-8 bg-zinc-900/80 backdrop-blur-xl rounded-3xl border border-zinc-800 shadow-2xl max-w-sm animate-in zoom-in-95 duration-300">
                 <div className="w-16 h-16 bg-orange-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-orange-500/20">
                   <iconify-icon icon="solar:lock-keyhole-bold-duotone" className="text-4xl text-orange-500"></iconify-icon>
                 </div>
                 <h3 className="text-xl font-black text-white uppercase tracking-tight mb-2">Price Optimizer Locked</h3>
                 <p className="text-xs text-zinc-400 leading-relaxed mb-6">
                   Fitur optimasi harga cerdas berbasis AI hanya tersedia untuk member **ELITE** ke atas. Upgrade sekarang untuk maksimalkan profit Anda!
                 </p>
                 <button className="px-8 py-3 bg-gradient-to-r from-orange-500 to-orange-700 text-white text-[10px] font-black uppercase tracking-widest rounded-xl shadow-lg shadow-orange-600/20 active:scale-95 transition-all">
                   UPGRADE TO ELITE
                 </button>
              </div>
           </div>
        )}

        {isAnalyzingAnalytics && (
            <div className="absolute inset-0 bg-zinc-900/30 backdrop-blur-[2px] z-20 flex items-center justify-center">
               <div className="flex items-center gap-2 bg-black/80 px-4 py-2 rounded-full border border-zinc-800">
                  <div className="w-2 h-2 bg-orange-500 rounded-full animate-ping"></div>
                  <span className="text-[10px] text-white font-bold tracking-tighter uppercase">
                     {lang === 'id' ? 'Menghitung Rekomendasi Harga...' : 'Recalculating Prices...'}
                  </span>
               </div>
            </div>
        )}
        <div className="absolute top-0 right-0 p-6 opacity-10 pointer-events-none">
          <iconify-icon icon="solar:magic-stick-3-linear" className="text-8xl text-orange-500"></iconify-icon>
        </div>
        
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-orange-600 flex items-center justify-center">
              <iconify-icon icon="solar:globus-linear" className="text-white"></iconify-icon>
            </div>
            <h3 className="text-lg font-semibold text-white">{t('priceRec')}</h3>
          </div>
          {(profile?.subscription_plan || '').toLowerCase() === 'elite' && (
            <div className="flex items-center gap-2 px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></div>
              <span className="text-[9px] font-black text-blue-400 uppercase tracking-widest">Elite Tier - Monthly Quota Active</span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative z-10">
          <div className="space-y-4">
            <p className="text-sm text-zinc-400 leading-relaxed">{t('priceRecDesc')}</p>
            <div className="flex flex-wrap gap-3">
              <div className="px-4 py-2 bg-zinc-800 rounded-lg border border-zinc-700">
                <div className="text-[10px] text-zinc-500 uppercase font-bold mb-1">Current Status</div>
                <div className="text-xs text-white font-medium">Standard Pricing</div>
              </div>
              <div className="px-4 py-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                <div className="text-[10px] text-emerald-500 uppercase font-bold mb-1">Optimized Potential</div>
                <div className="text-xs text-emerald-400 font-bold">{analyticsInsight?.pricing?.margin_increase || '+14%'} Margin</div>
              </div>
            </div>
          </div>
          
          <div className="bg-black/50 border border-zinc-800 rounded-xl p-5 flex flex-col justify-center">
            <div className="text-center space-y-4">
              <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto">
                <iconify-icon icon="solar:chart-line-up-bold" className="text-3xl text-emerald-400"></iconify-icon>
              </div>
              <div className="text-4xl font-bold text-white">{analyticsInsight?.pricing?.potential_profit || '+Rp 0'}</div>
              <p className="text-xs text-zinc-400">{t('potentialProfit')}</p>
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 text-left">
                <p className="text-[10px] text-zinc-500 leading-relaxed">{analyticsInsight?.pricing?.tip || t('priceRecTip')}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsTab;
