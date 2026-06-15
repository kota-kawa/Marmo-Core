import React from 'react';

const OverviewTab = ({ 
  t, 
  orders, 
  products, 
  timeFilter, 
  setTimeFilter, 
  showFilterDropdown, 
  setShowFilterDropdown,
  platformFilter,
  setPlatformFilter,
  showPlatformDropdown,
  setShowPlatformDropdown,
  profile,
  lang,
  setActiveMenu,
  systemBriefing,
  isFetchingBriefing
}) => {
  // --- REAL DATA CALCULATIONS ---
  const platformFilteredOrders = platformFilter === 'all' 
    ? orders 
    : orders.filter(o => (o.platform || '').toLowerCase() === platformFilter.toLowerCase());

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

  // Jika admin dan filter 'Hari Ini' kosong, coba tampilkan semua data agar tidak terlihat blank
  let filteredOrders = getFilteredOrdersByTime(platformFilteredOrders, timeFilter);
  if (filteredOrders.length === 0 && timeFilter === 'Hari Ini' && profile?.role === 'admin') {
      filteredOrders = platformFilteredOrders; // Fallback ke semua data untuk admin jika hari ini kosong
  }

  // Exclude cancelled orders from financial and order volume calculations (cancelled transactions produce Rp 0 and don't count as successful orders)
  const activeAndCompletedOrders = filteredOrders.filter(o => o.status !== 'cancelled');

  const totalRev = activeAndCompletedOrders.reduce((sum, o) => sum + Number(o.total_amount || 0), 0);
  const totalProfit = totalRev * 0.2;
  
  const filteredTikTokOrders = activeAndCompletedOrders.filter(o => (o.platform || '').toLowerCase() === 'tiktok');
  const filteredShopeeOrders = activeAndCompletedOrders.filter(o => (o.platform || '').toLowerCase() === 'shopee');

  const tiktokGMV = filteredTikTokOrders.reduce((sum, o) => sum + Number(o.total_amount || 0), 0);
  const shopeeGMV = filteredShopeeOrders.reduce((sum, o) => sum + Number(o.total_amount || 0), 0);

  const averageOrderValue = activeAndCompletedOrders.length > 0 ? Math.round(totalRev / activeAndCompletedOrders.length) : 0;

  const healthScore = products.length > 0 
    ? Math.round((products.filter(p => p.stock > 0).length / products.length) * 100) 
    : 0;
 
  const recentTransactions = [...platformFilteredOrders]
    .filter(o => o.created_at)
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 3);

  const lowStockProducts = products
    .filter(p => p.stock < 20)
    .sort((a, b) => a.stock - b.stock)
    .slice(0, 3);

  const formatIDR = (val) => {
    if (val >= 1000000000) return `Rp ${(val / 1000000000).toFixed(2)} M`;
    if (val >= 1000000) return `Rp ${(val / 1000000).toFixed(2)} Jt`;
    return `Rp ${val.toLocaleString('id-ID')}`;
  };


  const getFilterLabel = () => t(timeFilter);

  // --- PREMIUM CUSTOM CHART METRICS & STATE ---
  const [hoveredIdx, setHoveredIdx] = React.useState(null);

  const formatIDRShort = (val) => {
    if (val >= 1000000000) return `Rp ${(val / 1000000000).toFixed(1)} M`;
    if (val >= 1000000) return `Rp ${(val / 1000000).toFixed(1)} Jt`;
    if (val >= 1000) return `Rp ${(val / 1000).toFixed(0)}rb`;
    return `Rp ${val}`;
  };

  const getChartData = () => {
    let buckets = [];
    const now = new Date();

    if (timeFilter === 'Hari Ini') {
      const intervals = ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00'];
      buckets = intervals.map(label => ({ label, omzet: 0, profit: 0, ordersCount: 0 }));

      activeAndCompletedOrders.forEach(o => {
        const dateStr = o.order_date || o.created_at;
        if (!dateStr) return;
        const d = new Date(dateStr);
        const hr = d.getHours();
        const bucketIndex = Math.min(Math.floor(hr / 3), 7);
        buckets[bucketIndex].omzet += Number(o.total_amount || 0);
        buckets[bucketIndex].ordersCount += 1;
      });
    } 
    else if (timeFilter === 'Bulan Ini') {
      const intervals = ['Minggu 1', 'Minggu 2', 'Minggu 3', 'Minggu 4'];
      buckets = intervals.map(label => ({ label, omzet: 0, profit: 0, ordersCount: 0 }));

      activeAndCompletedOrders.forEach(o => {
        const dateStr = o.order_date || o.created_at;
        if (!dateStr) return;
        const d = new Date(dateStr);
        const dateNum = d.getDate();
        let bucketIndex = 3;
        if (dateNum <= 7) bucketIndex = 0;
        else if (dateNum <= 14) bucketIndex = 1;
        else if (dateNum <= 21) bucketIndex = 2;
        buckets[bucketIndex].omzet += Number(o.total_amount || 0);
        buckets[bucketIndex].ordersCount += 1;
      });
    } 
    else if (timeFilter === '1 Bulan Terakhir' || timeFilter === '2 Bulan Terakhir') {
      const intervals = ['Minggu 1', 'Minggu 2', 'Minggu 3', 'Minggu 4'];
      buckets = intervals.map(label => ({ label, omzet: 0, profit: 0, ordersCount: 0 }));

      const totalDays = timeFilter === '1 Bulan Terakhir' ? 30 : 60;
      const daysPerBucket = totalDays / 4;

      activeAndCompletedOrders.forEach(o => {
        const dateStr = o.order_date || o.created_at;
        if (!dateStr) return;
        const d = new Date(dateStr);
        const diffTime = Math.abs(now - d);
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
        if (diffDays >= totalDays) return;
        const bucketIndex = Math.min(Math.floor(diffDays / daysPerBucket), 3);
        buckets[3 - bucketIndex].omzet += Number(o.total_amount || 0);
        buckets[3 - bucketIndex].ordersCount += 1;
      });
    } 
    else if (timeFilter === '3 Bulan Terakhir') {
      const monthNamesIndo = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
      const currentMonthIndex = now.getMonth();
      const currentYear = now.getFullYear();
      
      const targetMonths = [];
      for (let i = 2; i >= 0; i--) {
        const d = new Date(currentYear, currentMonthIndex - i, 1);
        targetMonths.push({
          monthIndex: d.getMonth(),
          year: d.getFullYear(),
          label: monthNamesIndo[d.getMonth()]
        });
      }

      buckets = targetMonths.map(m => ({ label: m.label, omzet: 0, profit: 0, ordersCount: 0 }));

      activeAndCompletedOrders.forEach(o => {
        const dateStr = o.order_date || o.created_at;
        if (!dateStr) return;
        const d = new Date(dateStr);
        const m = d.getMonth();
        const y = d.getFullYear();

        const bucketIndex = targetMonths.findIndex(tm => tm.monthIndex === m && tm.year === y);
        if (bucketIndex !== -1) {
          buckets[bucketIndex].omzet += Number(o.total_amount || 0);
          buckets[bucketIndex].ordersCount += 1;
        }
      });
    } 
    else {
      const intervals = ['Periode 1', 'Periode 2', 'Periode 3', 'Periode 4'];
      buckets = intervals.map(label => ({ label, omzet: 0, profit: 0, ordersCount: 0 }));
      activeAndCompletedOrders.forEach((o, idx) => {
        const bucketIndex = idx % 4;
        buckets[bucketIndex].omzet += Number(o.total_amount || 0);
        buckets[bucketIndex].ordersCount += 1;
      });
    }

    buckets.forEach(b => {
      b.profit = b.omzet * 0.2;
      b.margin = b.omzet > 0 ? 20 : 0;
      b.aov = b.ordersCount > 0 ? Math.round(b.omzet / b.ordersCount) : 0;
    });

    return buckets;
  };

  return (
    <div className="relative z-10 space-y-6 pb-12 animate-in fade-in duration-700">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-2">
        <div>
          <h2 className="text-2xl font-semibold text-white tracking-tight">{t('overview')}</h2>
          <p className="text-xs text-zinc-400 mt-1">{t('monitorShop')}</p>
        </div>
        <div className="flex flex-col sm:flex-row items-center gap-2 w-full sm:w-auto z-50">
          {/* Tombol Unduh Manual Book */}
          <a
            href="/Manual_book_Tokcer_AI.pdf"
            download="Manual_book_Tokcer_AI.pdf"
            className="w-full sm:w-auto px-4 py-2 bg-orange-500/10 hover:bg-orange-500/20 border border-orange-500/25 text-orange-400 text-[10px] font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 whitespace-nowrap cursor-pointer shadow-sm uppercase tracking-wider"
          >
            <iconify-icon icon="solar:document-download-bold-duotone" className="text-sm text-orange-500"></iconify-icon>
            Unduh Panduan
          </a>

          {/* Admin Clean Dummy Data Button */}
          {profile?.email === 'admin@tokcer-ai.com' && (
            <button
              onClick={async (e) => {
                if (window.confirm("Bapak yakin ingin menghapus SELURUH data dummy (order, produk, koneksi) di akun admin Bapak? Tindakan ini 100% aman dan tidak memengaruhi akun user lain.")) {
                  try {
                    const target = e.currentTarget;
                    if (target) target.disabled = true;
                    
                    const { supabase } = await import('../../../lib/supabase.js');
                    
                    // Delete orders, products, and marketplace connections for this admin user id
                    const { error: e1 } = await supabase.from('orders').delete().eq('user_id', profile.id);
                    const { error: e2 } = await supabase.from('products').delete().eq('user_id', profile.id);
                    const { error: e3 } = await supabase.from('marketplace_connections').delete().eq('user_id', profile.id);
                    
                    if (e1 || e2 || e3) {
                      alert("Gagal menghapus data: " + (e1?.message || e2?.message || e3?.message));
                      if (target) target.disabled = false;
                    } else {
                      alert("Semua data dummy admin sukses dibersihkan! Halaman akan dimuat ulang.");
                      window.location.reload();
                    }
                  } catch (err) {
                    alert("Error: " + err.message);
                    const target = e.currentTarget;
                    if (target) target.disabled = false;
                  }
                }
              }}
              className="w-full sm:w-auto px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/25 text-rose-400 text-[10px] font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 whitespace-nowrap cursor-pointer shadow-sm uppercase tracking-wider"
            >
              <iconify-icon icon="solar:trash-bin-trash-bold" className="text-sm text-rose-500"></iconify-icon>
              Bersihkan Dummy
            </button>
          )}

          {/* Platform Filter */}
          <div className="relative w-full sm:w-auto">
            <div
              onClick={() => setShowPlatformDropdown(!showPlatformDropdown)}
              className="text-xs text-zinc-300 flex items-center gap-2 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 hover:bg-zinc-700 transition-colors cursor-pointer shadow-sm w-full justify-between sm:justify-start"
            >
              <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest">
                <iconify-icon icon="solar:filter-linear" className="text-orange-500 text-sm"></iconify-icon>
                {platformFilter === 'all' ? t('allPlatforms') : platformFilter}
              </div>
              <iconify-icon icon={showPlatformDropdown ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'} className="sm:ml-2 text-zinc-500"></iconify-icon>
            </div>
            {showPlatformDropdown && (
              <div className="absolute top-full left-0 sm:right-0 mt-2 w-full sm:w-48 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-[60] py-1 overflow-hidden">
                {[['all', t('allPlatforms')], ['TikTok', 'TikTok Shop'], ['Shopee', 'Shopee']].map(([val, label]) => (
                  <div
                    key={val}
                    onClick={() => { setPlatformFilter(val); setShowPlatformDropdown(false); }}
                    className={`px-4 py-2 text-xs cursor-pointer flex items-center gap-2 transition-colors ${platformFilter === val ? 'bg-orange-950/50 text-orange-500 font-medium' : 'text-zinc-300 hover:bg-zinc-700 hover:text-white'}`}
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
              <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest">
                <iconify-icon icon="solar:calendar-linear" className="text-sm text-orange-500"></iconify-icon> 
                {t(timeFilter)}
              </div>
              <iconify-icon icon={showFilterDropdown ? "solar:alt-arrow-up-linear" : "solar:alt-arrow-down-linear"} className="sm:ml-2 text-zinc-400"></iconify-icon>
            </div>
            {showFilterDropdown && (
              <div className="absolute top-full right-0 mt-2 w-full sm:w-48 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-[60] overflow-hidden">
                <div className="py-1">
                  {['Hari Ini', 'Bulan Ini', '1 Bulan Terakhir', '2 Bulan Terakhir', '3 Bulan Terakhir'].map((option) => (
                    <div 
                      key={option}
                      onClick={() => {
                        setTimeFilter(option);
                        setShowFilterDropdown(false);
                      }}
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

      {/* GAP 1: Starter Upgrade Banner */}
      {(profile?.subscription_plan || '').toLowerCase() === 'starter' && (
        <div className="bg-gradient-to-r from-orange-600/20 to-amber-600/10 border border-orange-500/30 rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-lg animate-in slide-in-from-top-4 duration-500">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-orange-500/20 rounded-xl flex items-center justify-center border border-orange-500/30 shrink-0">
              <iconify-icon icon="solar:star-fall-bold-duotone" className="text-2xl text-orange-500 animate-pulse"></iconify-icon>
            </div>
            <div>
              <h3 className="text-white font-bold text-sm md:text-base">Membuka Potensi Penuh Tokcer AI!</h3>
              <p className="text-zinc-400 text-xs md:text-sm mt-0.5">
                Saat ini Anda di paket <span className="font-bold text-orange-400">Starter (Gratis)</span>. Upgrade ke <b>Pro</b> untuk memperluas jangkauan operasional dan menambah jatah Token AI Anda.
              </p>
            </div>
          </div>
          <button 
            onClick={() => setActiveMenu('tab-billing')}
            className="w-full sm:w-auto px-6 py-2.5 bg-orange-500 hover:bg-orange-600 text-white text-xs font-bold rounded-xl transition-all shadow-lg shadow-orange-500/20 flex items-center justify-center gap-2 whitespace-nowrap shrink-0"
          >
            <iconify-icon icon="solar:rocket-bold"></iconify-icon>
            Upgrade Sekarang
          </button>
        </div>
      )}

      {/* Row 1: Top Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Orders Card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 relative overflow-hidden group shadow-sm hover:border-emerald-500/30 transition-all">
          <div className="flex items-center justify-between mb-6">
             <div className="text-xs font-medium text-zinc-400">Total Pesanan ({getFilterLabel()})</div>
             <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                <iconify-icon icon="solar:bag-3-bold" className="text-lg text-emerald-500"></iconify-icon>
             </div>
          </div>
          <div className="text-3xl font-bold text-white tracking-tight mb-2">{activeAndCompletedOrders.length}</div>
          <div className="text-[10px] text-zinc-500 flex items-center gap-1">
             <iconify-icon icon="solar:info-circle-linear"></iconify-icon> Volume transaksi terverifikasi API
          </div>
        </div>

        {/* Revenue Card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 relative overflow-hidden group shadow-sm hover:border-orange-500/30 transition-all">
          <div className="text-xs font-medium text-zinc-400 mb-2">{t('revenueLabel')} ({getFilterLabel()})</div>
          <div className="text-2xl font-bold text-white tracking-tight mb-1">{formatIDR(totalRev)}</div>
          <div className={`text-[10px] flex items-center gap-1 mb-6 ${totalRev > 0 ? 'text-emerald-500' : 'text-zinc-500'}`}>
             <iconify-icon icon="solar:info-circle-linear"></iconify-icon> {totalRev > 0 ? `+12% ${t('vsYesterday')}` : t('noDataToday')}
          </div>
          
          <div className="pt-4 border-t border-zinc-800">
            <div className="text-[10px] text-zinc-500 mb-1">{t('profitLabel')} ({getFilterLabel()})</div>
            <div className={`text-lg font-bold ${totalProfit > 0 ? 'text-emerald-400' : 'text-zinc-600'}`}>{formatIDR(totalProfit)}</div>
            <div className={`text-[8px] flex items-center gap-1 ${totalProfit > 0 ? 'text-emerald-500' : 'text-zinc-500'}`}>
               <iconify-icon icon="solar:info-circle-linear"></iconify-icon> {totalProfit > 0 ? `+8.5% ${t('vsYesterday')}` : t('estMargin')}
            </div>
          </div>
        </div>

        {/* Average Order Value (AOV) Card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 relative overflow-hidden group shadow-sm hover:border-blue-500/30 transition-all">
          <div className="flex items-center justify-between mb-6">
             <div className="text-xs font-medium text-zinc-400">Nilai Transaksi (AOV) ({getFilterLabel()})</div>
             <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
                <iconify-icon icon="solar:calculator-minimalistic-bold" className="text-lg text-blue-500"></iconify-icon>
             </div>
          </div>
          <div className="text-2xl font-bold text-white tracking-tight mb-2">{formatIDR(averageOrderValue)}</div>
          <div className="text-[10px] text-zinc-500 flex items-center gap-1">
             <iconify-icon icon="solar:info-circle-linear"></iconify-icon> Rata-rata belanja per pesanan
          </div>
        </div>

        {/* Health Score */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 relative overflow-hidden group shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="text-xs font-medium text-zinc-400 flex items-center gap-2">
              {t('healthTitle')}
              <iconify-icon icon="solar:shield-check-bold" className="text-amber-500"></iconify-icon>
            </div>
          </div>
          <div className="flex items-end gap-2 mb-4">
             <div className={`text-4xl font-bold tracking-tight ${healthScore > 0 ? 'text-amber-500' : 'text-zinc-600'}`}>{healthScore}</div>
             <div className="text-zinc-500 text-xs mb-1">/100</div>
          </div>
          <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden">
             <div className="bg-amber-500 h-full rounded-full transition-all duration-1000" style={{ width: `${healthScore}%` }}></div>
          </div>
        </div>
      </div>

      {/* Row 2: Charts & Notifications */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Revenue & Profit Performance Chart Section */}
        <div className="lg:col-span-2 bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col justify-between group hover:border-orange-500/20 transition-all duration-300 relative overflow-hidden">
          {/* Glowing Aura Effect */}
          <div className="absolute -top-24 -left-24 w-48 h-48 bg-orange-500/5 rounded-full blur-3xl pointer-events-none group-hover:bg-orange-500/10 transition-all duration-500"></div>
          
          <div className="relative z-10 flex flex-col gap-6">
            {/* Header Title */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-zinc-800/80 pb-4">
              <div>
                <h3 className="text-sm font-bold text-white tracking-tight">Performa Omzet & Profit</h3>
                <p className="text-[10px] text-zinc-500 font-medium mt-0.5">Periode Aktif: {getFilterLabel()}</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 text-[9px] font-bold text-zinc-400 bg-zinc-950/40 px-2 py-1 rounded-md border border-zinc-800/50">
                  <div className="w-2 h-2 bg-orange-500 rounded-sm"></div>
                  Omzet
                </div>
                <div className="flex items-center gap-1.5 text-[9px] font-bold text-zinc-400 bg-zinc-950/40 px-2 py-1 rounded-md border border-zinc-800/50">
                  <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
                  Profit
                </div>
              </div>
            </div>

            {/* KPI Cards Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-zinc-950/40 p-3 rounded-xl border border-zinc-800/50">
              <div className="flex flex-col gap-0.5">
                <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-wider">Total Omzet</span>
                <span className="text-sm font-bold text-white tracking-tight">{formatIDR(totalRev)}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-wider">Estimasi Profit</span>
                <span className="text-sm font-bold text-emerald-400 tracking-tight">{formatIDR(totalProfit)}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-wider">Margin Profit</span>
                <span className="text-sm font-bold text-amber-500 tracking-tight">{totalRev > 0 ? '20%' : '0%'}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-wider">Periode Terbaik</span>
                <span className="text-sm font-bold text-white tracking-tight truncate">
                  {totalRev > 0 ? (() => {
                    const data = getChartData();
                    const maxB = data.reduce((max, b) => b.omzet > max.omzet ? b : max, data[0] || { label: '-' });
                    return maxB.label;
                  })() : '-'}
                </span>
              </div>
            </div>

            {/* Main Visual Chart Body */}
            <div className="relative h-64 w-full pt-4 mt-2">
              {/* Dynamic Y-Axis Guidelines */}
              <div className="absolute inset-x-0 top-0 bottom-8 flex flex-col justify-between pointer-events-none">
                {[1, 2, 3].map((val, i) => {
                  const data = getChartData();
                  const maxVal = Math.max(...data.map(b => b.omzet), 10000);
                  const stepVal = maxVal * (1 - i * 0.33);
                  return (
                    <div key={i} className="w-full flex items-center justify-between text-[8px] font-semibold text-zinc-600 relative h-0">
                      <span className="bg-zinc-900 pr-2 z-10 shrink-0 select-none">{formatIDRShort(stepVal)}</span>
                      <div className="w-full border-t border-zinc-800/80 border-dashed absolute inset-x-0 -z-0"></div>
                    </div>
                  );
                })}
                <div className="w-full flex items-center justify-between text-[8px] font-semibold text-zinc-600 relative h-0">
                  <span className="bg-zinc-900 pr-2 z-10 shrink-0 select-none">Rp 0</span>
                  <div className="w-full border-t border-zinc-800/80 border-dashed absolute inset-x-0 -z-0"></div>
                </div>
              </div>

              {/* Dynamic SVG Trend Line (Profit) */}
              <div className="absolute inset-x-0 bottom-8 h-48 pointer-events-none z-20">
                {(() => {
                  const data = getChartData();
                  const maxVal = Math.max(...data.map(b => b.omzet), 10000);
                  const N = data.length;
                  if (N === 0) return null;

                  const pts = data.map((b, i) => {
                    const x = (i + 0.5) * (100 / N);
                    const y = 100 - (b.profit / maxVal) * 80; // Reserve top space
                    return { x, y };
                  });

                  const pathD = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x}% ${p.y}%`).join(' ');
                  const areaD = `${pathD} L ${pts[pts.length - 1].x}% 100% L ${pts[0].x}% 100% Z`;

                  return (
                    <svg className="absolute inset-0 w-full h-full">
                      <defs>
                        <linearGradient id="profitGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#10b981" stopOpacity="0.1" />
                          <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
                        </linearGradient>
                      </defs>
                      {/* Shaded Area Under Line */}
                      {totalRev > 0 && <path d={areaD} fill="url(#profitGrad)" />}
                      {/* Stroke Line */}
                      {totalRev > 0 && (
                        <path 
                          d={pathD} 
                          fill="none" 
                          stroke="#34d399" 
                          strokeWidth="2.5" 
                          strokeLinejoin="round" 
                          strokeLinecap="round"
                        />
                      )}
                    </svg>
                  );
                })()}
              </div>

              {/* Interactive Column Bars (Omzet) & Dots (Profit) */}
              <div className="absolute inset-x-0 bottom-8 flex items-end justify-between h-48 z-30">
                {getChartData().map((b, i) => {
                  const data = getChartData();
                  const maxVal = Math.max(...data.map(x => x.omzet), 10000);
                  const barHeightPercent = maxVal > 0 ? (b.omzet / maxVal) * 80 : 5;
                  const profitYPercent = maxVal > 0 ? (b.profit / maxVal) * 80 : 5;

                  return (
                    <div 
                      key={i} 
                      className="flex flex-col items-center gap-2 group relative h-full justify-end select-none"
                      style={{ width: `${100 / data.length}%` }}
                      onMouseEnter={() => setHoveredIdx(i)}
                      onMouseLeave={() => setHoveredIdx(null)}
                    >
                      {/* Short Metric Display Above Bar */}
                      {b.omzet > 0 && (
                        <div className="text-[8px] font-bold text-orange-400 mb-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none select-none absolute bottom-full">
                          {formatIDRShort(b.omzet)}
                        </div>
                      )}

                      {/* Bar Container */}
                      <div 
                        className={`w-8 sm:w-10 rounded-t-lg transition-all duration-500 relative cursor-pointer ${
                          hoveredIdx === i ? 'bg-orange-500 shadow-md shadow-orange-500/10' : 'bg-orange-600/30 hover:bg-orange-500/60'
                        }`}
                        style={{ height: `${Math.max(barHeightPercent, 5)}%` }}
                      >
                        {/* Dynamic Green Dot (Profit) */}
                        {b.profit > 0 && (
                          <div 
                            className="absolute left-1/2 -translate-x-1/2 w-2 h-2 bg-emerald-400 rounded-full border border-black shadow-lg shadow-emerald-400/40 z-40 transition-transform duration-300"
                            style={{ 
                              bottom: `calc(${profitYPercent / Math.max(barHeightPercent, 5) * 100}% - 4px)` 
                            }}
                          ></div>
                        )}
                      </div>

                      {/* X-Axis Label */}
                      <span className={`text-[9px] font-bold mt-1 transition-colors select-none ${hoveredIdx === i ? 'text-white' : 'text-zinc-500'}`}>
                        {b.label}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Floating Tooltip Component */}
              {hoveredIdx !== null && (() => {
                const b = getChartData()[hoveredIdx];
                if (!b) return null;
                const N = getChartData().length;
                return (
                  <div 
                    className="absolute z-50 bg-zinc-950/90 border border-zinc-800 rounded-xl p-3 shadow-2xl backdrop-blur-md pointer-events-none animate-in fade-in zoom-in-95 duration-200 select-none w-44"
                    style={{ 
                      left: `${((hoveredIdx + 0.5) * (100 / N))}%`,
                      bottom: '95px',
                      transform: 'translateX(-50%)'
                    }}
                  >
                    {/* Glowing Tip */}
                    <div className="absolute bottom-[-5px] left-1/2 -translate-x-1/2 w-2.5 h-2.5 bg-zinc-950 border-r border-b border-zinc-800 rotate-45"></div>
                    
                    <div className="flex flex-col gap-2">
                      <div className="text-[10px] font-bold text-white border-b border-zinc-800 pb-1 flex justify-between">
                        <span>{b.label}</span>
                        <span className="text-[8px] uppercase tracking-wider text-orange-400 font-black">Detail</span>
                      </div>
                      <div className="flex flex-col gap-1 text-[9px] font-semibold">
                        <div className="flex justify-between">
                          <span className="text-zinc-500">Omzet:</span>
                          <span className="text-white">{formatIDR(b.omzet)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-500">Profit:</span>
                          <span className="text-emerald-400">{formatIDR(b.profit)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-500">Margin:</span>
                          <span className="text-amber-500">{b.margin}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-500">Pesanan:</span>
                          <span className="text-white">{b.ordersCount}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-500">AOV:</span>
                          <span className="text-blue-400">{formatIDR(b.aov)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>

          {/* AI Insight Box Card */}
          <div className="mt-6 p-4 bg-orange-500/5 border border-orange-500/10 rounded-2xl flex items-start gap-3 relative overflow-hidden group hover:border-orange-500/20 transition-all duration-300">
            <div className="w-8 h-8 rounded-xl bg-orange-500/10 flex items-center justify-center border border-orange-500/20 shrink-0">
              <iconify-icon icon="solar:stars-bold-duotone" className="text-lg text-orange-400 animate-pulse"></iconify-icon>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-[9px] font-bold text-orange-400 uppercase tracking-widest">Intelligence Analysis</span>
              <p className="text-[10px] text-zinc-400 leading-relaxed font-medium">
                {totalRev > 0 ? (() => {
                  const data = getChartData();
                  const maxB = data.reduce((max, b) => b.omzet > max.omzet ? b : max, data[0] || { label: '-' });
                  return `Omzet tertinggi terjadi pada ${maxB.label} sebesar ${formatIDR(maxB.omzet)}. Margin profit berada di 20%, menandakan performa masih sehat. Pertahankan HPP dan pantau biaya tambahan agar profit tidak turun.`;
                })() : 'Insight belum tersedia karena data periode ini masih terbatas.'}
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {/* Platform Performance Widget */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 shadow-sm hover:border-orange-500/10 transition-all">
             <div className="flex items-center justify-between mb-6">
                <h3 className="text-[10px] font-black text-white uppercase tracking-[0.2em] flex items-center gap-2">
                   <div className="w-1.5 h-1.5 rounded-full bg-orange-500"></div>
                   KINERJA PLATFORM
                </h3>
             </div>
             <div className="space-y-4">
                 <div className="flex flex-col gap-1 pb-3 border-b border-zinc-800/50">
                    <div className="flex items-center justify-between">
                       <div className="flex items-center gap-2">
                          <iconify-icon icon="ri:tiktok-fill" className="text-zinc-400 text-sm"></iconify-icon>
                          <span className="text-[10px] font-bold text-white">TikTok Shop</span>
                       </div>
                       <span className="text-[10px] text-zinc-400 font-semibold">{filteredTikTokOrders.length} Pesanan</span>
                    </div>
                    <div className="flex justify-between items-center pl-6">
                       <span className="text-[8px] text-zinc-500 font-medium">GMV Terverifikasi</span>
                       <span className="text-xs font-bold text-emerald-400">{formatIDR(tiktokGMV)}</span>
                    </div>
                 </div>
                 <div className="flex flex-col gap-1">
                    <div className="flex items-center justify-between">
                       <div className="flex items-center gap-2">
                          <iconify-icon icon="simple-icons:shopee" className="text-orange-500 text-sm"></iconify-icon>
                          <span className="text-[10px] font-bold text-white">Shopee</span>
                       </div>
                       <span className="text-[10px] text-zinc-400 font-semibold">{filteredShopeeOrders.length} Pesanan</span>
                    </div>
                    <div className="flex justify-between items-center pl-6">
                       <span className="text-[8px] text-zinc-500 font-medium">GMV Terverifikasi</span>
                       <span className="text-xs font-bold text-emerald-400">{formatIDR(shopeeGMV)}</span>
                    </div>
                 </div>
             </div>
          </div>

          {/* Intelligence Briefing Card */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 shadow-sm">
             <div className="flex items-center justify-between mb-6">
                <h3 className="text-[10px] font-black text-white uppercase tracking-[0.2em] flex items-center gap-2">
                   <iconify-icon icon="solar:stars-bold-duotone" className="text-orange-500 text-sm"></iconify-icon>
                   INTELLIGENCE BRIEFING
                </h3>
                {isFetchingBriefing && <iconify-icon icon="solar:spinner-linear" className="text-zinc-500 text-xs animate-spin"></iconify-icon>}
             </div>
             <div className="space-y-3">
                {systemBriefing && systemBriefing.length > 0 ? systemBriefing.map((note, idx) => (
                  <div key={idx} className={`p-3 bg-zinc-800/30 border rounded-xl transition-all ${note.type === 'warning' ? 'border-rose-500/20' : note.type === 'success' ? 'border-emerald-500/20' : 'border-zinc-800'}`}>
                     <div className="flex justify-between items-start mb-1">
                        <p className={`text-[10px] font-bold ${note.type === 'warning' ? 'text-rose-400' : note.type === 'success' ? 'text-emerald-400' : 'text-white'}`}>{note.title}</p>
                     </div>
                     <p className="text-[9px] text-zinc-500 leading-relaxed">{note.desc}</p>
                  </div>
                )) : (
                  <div className="py-8 text-center">
                     <iconify-icon icon="solar:cloud-download-linear" className="text-2xl text-zinc-800 mb-2 animate-bounce"></iconify-icon>
                     <p className="text-[10px] text-zinc-700 italic">Analyzing real-time data...</p>
                  </div>
                )}
             </div>
          </div>
        </div>
      </div>

      {/* Row 3: Transactions & Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Transactions */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6 shadow-sm">
           <div className="flex items-center justify-between mb-6">
              <h3 className="text-sm font-bold text-white">{t('recentTrx')}</h3>
              <button 
                onClick={() => setActiveMenu('tab-omzet')}
                className="text-[10px] font-bold text-orange-500 hover:text-orange-400 uppercase tracking-widest transition-colors"
              >
                {t('viewAll')}
              </button>
           </div>
           <div className="space-y-4">
              {recentTransactions.length > 0 ? recentTransactions.map((trx, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-zinc-800/30 rounded-2xl border border-zinc-800/50">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-zinc-900 flex items-center justify-center border border-zinc-800">
                      <iconify-icon 
                        icon={(trx.platform || '').toLowerCase() === 'tiktok' ? 'ri:tiktok-fill' : 'simple-icons:shopee'} 
                        className={`text-xl ${(trx.platform || '').toLowerCase() === 'shopee' ? 'text-orange-500' : 'text-zinc-400'}`}
                      ></iconify-icon>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-white">{trx.customer_name || t('customer')}</p>
                      <p className="text-[10px] text-zinc-500">#{trx.id?.slice(0, 8).toUpperCase()} • {trx.platform}</p>
                    </div>
                  </div>
                  <div className="text-xs font-bold text-white">Rp {Number(trx.total_amount).toLocaleString('id-ID')}</div>
                </div>
              )) : (
                <div className="py-8 text-center border-2 border-dashed border-zinc-800 rounded-3xl">
                   <iconify-icon icon="solar:wallet-linear" className="text-3xl text-zinc-700 mb-2"></iconify-icon>
                   <p className="text-xs text-zinc-500 italic">{t('noRecentTrx')}</p>
                </div>
              )}
           </div>
        </div>

        {/* Low Stock Alerts */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6 shadow-sm">
           <div className="flex items-center justify-between mb-6">
              <h3 className="text-sm font-bold text-white">{t('lowStock')}</h3>
              <button 
                onClick={() => setActiveMenu('tab-inventory')}
                className="text-[10px] font-bold text-orange-500 hover:text-orange-400 uppercase tracking-widest transition-colors"
              >
                {t('manageInv')}
              </button>
           </div>
           <div className="space-y-4">
              {lowStockProducts.length > 0 ? lowStockProducts.map((prod, idx) => (
                <div key={idx} className="flex items-center justify-between p-4 bg-zinc-800/30 rounded-2xl border border-zinc-800/50 group hover:border-orange-500/30 transition-all">
                  <div>
                    <p className="text-xs font-bold text-white mb-0.5 group-hover:text-orange-500 transition-colors">{prod.name}</p>
                    <p className="text-[10px] text-zinc-500 uppercase tracking-widest">{t('sku')}: {prod.sku || 'N/A'}</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-xs font-bold mb-1 ${prod.stock <= 0 ? 'text-rose-500' : 'text-amber-500'}`}>{prod.stock} Pcs</p>
                    <span className={`text-[8px] font-black uppercase tracking-widest px-2 py-0.5 rounded border ${
                      prod.stock <= 0 ? 'bg-rose-500/10 text-rose-500 border-rose-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                    }`}>
                      {prod.stock <= 0 ? t('outOfStock') : t('runningLow')}
                    </span>
                  </div>
                </div>
              )) : (
                <div className="py-8 text-center border-2 border-dashed border-zinc-800 rounded-3xl">
                   <iconify-icon icon="solar:box-bold" className="text-3xl text-zinc-700 mb-2"></iconify-icon>
                   <p className="text-xs text-zinc-500 italic">{t('stockHealthy')}</p>
                </div>
              )}
           </div>
        </div>
      </div>
    </div>
  );
};

export default OverviewTab;
