import React from 'react';

const MarketIntelTab = ({ 
  t, 
  profile,
  lang, 
  platformFilter, 
  setShowPlatformDropdown, 
  showPlatformDropdown, 
  setPlatformFilter, 
  viralTopics = [], 
  bestsellerProducts = [],
  viralVideos = [],
  liveStreams = [],
  fetchGlobalMarketTrends, 
  trendCustomInput, 
  setTrendCustomInput, 
  setTrendSampleKey, 
  setTrendCustomResult, 
  isSearchingTrend, 
  setTrendPrompt, 
  handleAnalyzeTrend, 
  isTrendAnalyzing, 
  trendSampleKey, 
  trendResult, 
  liveSummary 
}) => {
  // Trigger fetch on load
  React.useEffect(() => {
    if (viralTopics.length === 0) fetchGlobalMarketTrends();
  }, [viralTopics.length, fetchGlobalMarketTrends]);

  const plan = (profile?.subscription_plan || 'starter').toLowerCase();
  const isBasicLocked = profile && (plan === 'starter' || plan === 'pro');
  const isUltimateLocked = profile && plan !== 'ultimate'; // Deep Analysis locked for Elite/Starter

  return (
    <div className="relative z-10 space-y-6">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
        <div>
          <h2 className="text-2xl font-semibold text-white tracking-tight">{t('marketIntelTitle')}</h2>
          <p className="text-sm text-zinc-400 mt-1">{t('monitorShop')}</p>
        </div>
        <div className="relative w-full sm:w-auto">
          <div 
            onClick={() => !isBasicLocked && setShowPlatformDropdown(!showPlatformDropdown)}
            className={`text-xs text-zinc-300 flex items-center gap-2 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 hover:bg-zinc-700 transition-colors cursor-pointer shadow-sm w-full justify-between sm:justify-start ${isBasicLocked ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <div className="flex items-center gap-2">
              <iconify-icon icon="solar:filter-linear" className="text-orange-500"></iconify-icon>
              {platformFilter === 'all' ? t('allPlatforms') : platformFilter}
            </div>
            <iconify-icon icon={showPlatformDropdown ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'} className="sm:ml-2 text-zinc-500"></iconify-icon>
          </div>
          {showPlatformDropdown && (
            <div className="absolute top-full right-0 mt-2 w-full sm:w-48 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-50 py-1 overflow-hidden">
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
      </header>

      {/* Content Area with Conditional Lock */}
      <div className="relative space-y-6">
        {isBasicLocked && (
          <div className="absolute inset-0 z-[60] bg-zinc-950/20 backdrop-blur-[6px] rounded-[2rem] flex items-center justify-center border border-zinc-800/50 shadow-2xl overflow-hidden">
             <div className="text-center p-8 bg-zinc-900/80 backdrop-blur-xl rounded-3xl border border-zinc-800 shadow-2xl max-w-sm animate-in zoom-in-95 duration-300">
                <div className="w-16 h-16 bg-indigo-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-indigo-500/20">
                  <iconify-icon icon="solar:globus-bold-duotone" className="text-4xl text-indigo-500"></iconify-icon>
                </div>
                <h3 className="text-xl font-black text-white uppercase tracking-tight mb-2">Market Intel Locked</h3>
                <p className="text-xs text-zinc-400 leading-relaxed mb-6">
                  Fitur intelijen pasar global dan tren viral hanya tersedia untuk member **ELITE** ke atas. Raih keunggulan kompetitif sekarang!
                </p>
                <button className="px-8 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-[10px] font-black uppercase tracking-widest rounded-xl shadow-lg shadow-indigo-600/20 active:scale-95 transition-all">
                  UPGRADE TO ELITE
                </button>
             </div>
          </div>
        )}

        {/* Radar Trend AI - Sample Data */}
        <div className={`bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm ${isBasicLocked ? 'opacity-30' : ''}`}>
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center">
            <iconify-icon icon="solar:radar-linear" className="text-white text-xl"></iconify-icon>
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">{t('trendRadarAI')}</h3>
            <p className="text-[10px] text-zinc-500">Sample data — powered by AI Market Intelligence</p>
          </div>
        </div>

        {/* Manual Search Input */}
        <div className="mb-5">
          <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">🔍 {lang === 'id' ? 'Cari Kategori / Niche Manual' : 'Search Custom Category / Niche'}</div>
          <div className="flex gap-2">
            <div className={`flex-1 flex items-center gap-2 bg-black border rounded-xl px-3 py-2.5 transition-all ${
              isSearchingTrend ? 'border-indigo-500/50 ring-1 ring-indigo-500/30' : 'border-zinc-800 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500/30'
            }`}>
              <iconify-icon icon="solar:magnifer-linear" className="text-zinc-500 text-base shrink-0"></iconify-icon>
              <input
                type="text"
                value={trendCustomInput}
                onChange={(e) => { setTrendCustomInput(e.target.value); if (e.target.value) { setTrendSampleKey(null); setTrendCustomResult(null); } }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && trendCustomInput.trim()) {
                     setTrendPrompt(trendCustomInput.trim());
                     handleAnalyzeTrend();
                  }
                }}
                placeholder={lang === 'id' ? 'Ketik kategori produk... (tekan Enter)' : 'Type product category... (press Enter)'}
                className="flex-1 bg-transparent text-sm text-white placeholder:text-zinc-600 focus:outline-none"
              />
              {trendCustomInput && (
                <button onClick={() => { setTrendCustomInput(''); setTrendCustomResult(null); }} className="text-zinc-600 hover:text-zinc-400 transition-colors">
                  <iconify-icon icon="solar:close-circle-linear" className="text-base"></iconify-icon>
                </button>
              )}
            </div>
            <button
              onClick={() => {
                 if (!trendCustomInput.trim()) return;
                 setTrendPrompt(trendCustomInput.trim());
                 handleAnalyzeTrend();
              }}
              disabled={!trendCustomInput.trim() || isTrendAnalyzing}
              className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold rounded-xl transition-all shrink-0"
            >
              {isTrendAnalyzing ? (
                <iconify-icon icon="solar:spinner-linear" className="text-base animate-spin"></iconify-icon>
              ) : (
                <iconify-icon icon="solar:radar-linear" className="text-base"></iconify-icon>
              )}
              {lang === 'id' ? 'Analisa' : 'Analyze'}
            </button>
          </div>
        </div>

        {/* Divider */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 h-px bg-zinc-800"></div>
          <span className="text-[10px] text-zinc-600 uppercase tracking-widest">{lang === 'id' ? 'atau pilih contoh' : 'or choose sample'}</span>
          <div className="flex-1 h-px bg-zinc-800"></div>
        </div>

        {/* Sample Category Pills */}
        <div className="flex flex-wrap gap-2 mb-5">
          {[
            { key: 'running', label: '👟 Sepatu Lari' },
            { key: 'skincare', label: '✨ Skincare Pria' },
            { key: 'thrifting', label: '👔 Outfit Thrifting' },
            { key: 'gadget', label: '🎮 Gadget Gaming' },
            { key: 'supplement', label: '💊 Suplemen Kesehatan' },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => { 
                setTrendSampleKey(trendSampleKey === key ? null : key); 
                if(trendSampleKey !== key) {
                  setTrendPrompt(label);
                  handleAnalyzeTrend();
                }
              }}
              className={`px-3 py-1.5 text-xs rounded-full border font-medium transition-all ${
                trendSampleKey === key
                  ? 'bg-indigo-600 border-indigo-500 text-white'
                  : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:border-indigo-500 hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* AI Result Rendering */}
        {(() => {
          let d = {
              trend: 'Data analisis belum tersedia.',
              demo: 'Data analisis belum tersedia.',
              top5: ['Memuat...'],
              risk: 'Data analisis belum tersedia.',
              strategy: 'Data analisis belum tersedia.'
          };
          
          // Use AI result if available
          if (trendResult) {
            try {
              // Try to parse JSON from AI response
              const cleanJson = trendResult.replace(/```json|```/g, '').trim();
              const aiData = JSON.parse(cleanJson);
              d = { ...d, ...aiData };
            } catch (e) {
              console.error("AI Parse Error:", e);
              // Fallback to trendResult as string if parsing fails
              return <div className="text-xs text-zinc-400 p-4 bg-zinc-800 rounded-xl whitespace-pre-wrap">{trendResult}</div>;
            }
          } else if (!isTrendAnalyzing) return null;

          return (
            <div className="space-y-4 border-t border-zinc-800 pt-5 animate-in fade-in duration-700">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-orange-600/10 border border-orange-500/20 rounded-xl p-4">
                  <p className="text-[10px] font-bold text-orange-400 uppercase tracking-widest mb-2">🔥 Tren Terkini</p>
                  <p className="text-sm text-zinc-200">{d.trend}</p>
                </div>
                <div className="bg-blue-600/10 border border-blue-500/20 rounded-xl p-4">
                  <p className="text-[10px] font-bold text-blue-400 uppercase tracking-widest mb-2">🎯 Target Demografi</p>
                  <p className="text-sm text-zinc-200">{d.demo}</p>
                </div>
              </div>
              <div className="bg-zinc-800 border border-zinc-700 rounded-xl p-4">
                <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">💡 Top 5 Produk Potensial</p>
                <div className="space-y-1.5">
                  {Array.isArray(d.top5) ? d.top5.map((item, i) => (
                    <p key={i} className="text-sm text-zinc-200">{item}</p>
                  )) : <p className="text-sm text-zinc-200">{d.top5}</p>}
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-rose-600/10 border border-rose-500/20 rounded-xl p-4">
                  <p className="text-[10px] font-bold text-rose-400 uppercase tracking-widest mb-2">⚠️ Risiko</p>
                  <p className="text-sm text-zinc-200">{d.risk}</p>
                </div>
                <div className="bg-emerald-600/10 border border-emerald-500/20 rounded-xl p-4">
                  <p className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest mb-2">🚀 Strategi</p>
                  <p className="text-sm text-zinc-200">{d.strategy}</p>
                </div>
              </div>
            </div>
          );
        })()}
      </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Viral Topics & Bestselling Products */}
        <div className="space-y-6">
          {/* Weekly Viral Topics */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-sm font-semibold text-white uppercase tracking-widest flex items-center gap-2">
                <iconify-icon icon="solar:fire-bold" className="text-orange-500"></iconify-icon>
                {t('weeklyViralTopics')}
              </h3>
              <span className="text-[10px] text-zinc-500 font-mono">LIVE FEED</span>
            </div>
            <div className="space-y-4">
              {(viralTopics.length > 0 ? viralTopics : [
                { topic: 'Baju Koko Modern Premium', platform: 'TikTok', trend_percent: '+142%', volume: '45K' },
                { topic: 'Gamis Ceruty Syari', platform: 'Shopee', trend_percent: '+85%', volume: '62K' },
              ]).map((t, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-black border border-zinc-800 rounded-xl animate-in slide-in-from-bottom-2 duration-500" style={{ animationDelay: `${i * 100}ms` }}>
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center ${t.platform === 'TikTok' ? 'text-zinc-300' : 'text-orange-500'}`}>
                      <iconify-icon icon={t.platform === 'TikTok' ? 'ri:tiktok-fill' : 'simple-icons:shopee'}></iconify-icon>
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white">{t.topic}</div>
                      <div className="text-[10px] text-zinc-500 capitalize">{t.platform} Trends • {t.volume || '10K'} Pencarian</div>
                    </div>
                  </div>
                  <div className="text-xs font-black text-emerald-500">{t.trend_percent}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Top Bestselling Products Card (Dinamis & Riil!) */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-sm font-semibold text-white uppercase tracking-widest flex items-center gap-2">
                <iconify-icon icon="solar:cart-bold" className="text-emerald-500"></iconify-icon>
                {lang === 'id' ? 'Produk Bestseller Riil' : 'Real Bestselling Products'}
              </h3>
              <span className="text-[10px] text-zinc-500 font-mono">SALES ENGINE</span>
            </div>
            <div className="space-y-4">
              {bestsellerProducts.length > 0 ? (
                bestsellerProducts.map((p, i) => (
                  <div key={i} className="p-3 bg-black border border-zinc-800 rounded-xl flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${p.platform === 'TikTok' ? 'bg-zinc-800 text-zinc-300' : 'bg-orange-950/30 text-orange-500'}`}>
                        <iconify-icon icon={p.platform === 'TikTok' ? 'ri:tiktok-fill' : 'simple-icons:shopee'} className="text-xl"></iconify-icon>
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-white truncate">{p.name}</div>
                        <div className="text-[10px] text-zinc-400 mt-0.5">{p.price} • {p.platform} Shop</div>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-xs font-black text-emerald-500">{p.sales}</div>
                      <div className="text-[9px] text-zinc-500 font-mono">{p.revenue}</div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-6 text-zinc-500 text-xs">
                  <iconify-icon icon="solar:graph-down-linear" className="text-2xl mb-2"></iconify-icon>
                  <div>Pilih platform filter oranye di atas untuk sinkronisasi Bestseller.</div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Deep Analysis (Videos & Lives Spy) */}
        <div className="space-y-6 relative">
          {/* ULTIMATE LOCK for Deep Analysis */}
          {isUltimateLocked && (
            <div className="absolute inset-0 z-30 bg-zinc-950/40 backdrop-blur-sm rounded-2xl flex items-center justify-center border border-zinc-800/50 shadow-xl overflow-hidden">
              <div className="text-center p-6 bg-zinc-900/90 backdrop-blur-xl rounded-2xl border border-zinc-800 shadow-xl max-w-xs animate-in zoom-in-95 duration-300">
                <div className="w-12 h-12 bg-orange-500/10 rounded-xl flex items-center justify-center mx-auto mb-3 border border-orange-500/20">
                  <iconify-icon icon="solar:crown-bold-duotone" className="text-2xl text-orange-500"></iconify-icon>
                </div>
                <h4 className="text-sm font-black text-white uppercase tracking-tight mb-1">Deep Analysis Locked</h4>
                <p className="text-[10px] text-zinc-400 leading-relaxed mb-4">
                  Analisis kompetitor mendalam, TikTok Live Spy, & Video Conversion Tracker hanya tersedia untuk member **ULTIMATE**.
                </p>
                <button className="px-6 py-2 bg-gradient-to-r from-orange-500 to-orange-700 text-white text-[9px] font-black uppercase tracking-widest rounded-lg shadow-lg active:scale-95 transition-all">
                  UPGRADE TO ULTIMATE
                </button>
              </div>
            </div>
          )}
          
          <div className={`bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm ${isUltimateLocked ? 'opacity-40 grayscale' : ''}`}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-sm font-semibold text-white uppercase tracking-widest flex items-center gap-2">
                <iconify-icon icon="solar:chart-line-up-bold" className="text-indigo-500"></iconify-icon>
                {t('liveDataSampling')}
              </h3>
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/20"></div>
              </div>
            </div>

            <div className="space-y-5">
              {/* Dynamic Video & Content Spy */}
              {viralVideos.length > 0 && (
                <div className="space-y-3">
                  <p className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">🎥 Viral Video Tracker</p>
                  {viralVideos.map((v, i) => (
                    <div key={i} className="p-3 bg-black border border-zinc-800 rounded-xl">
                      <div className="text-xs font-bold text-white">{v.title}</div>
                      <div className="flex justify-between items-center text-[10px] text-zinc-500 mt-1.5">
                        <span>{v.creator} • {v.views}</span>
                        <span className="text-emerald-500 font-bold">{v.conversion}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Dynamic Live Streaming Spy */}
              {liveStreams.length > 0 && (
                <div className="space-y-3 pt-2">
                  <p className="text-[10px] font-bold text-rose-400 uppercase tracking-widest">🎙️ Competitor Live Streams</p>
                  {liveStreams.map((l, i) => (
                    <div key={i} className="p-3 bg-black border border-zinc-800 rounded-xl flex justify-between items-center">
                      <div>
                        <div className="text-xs font-bold text-white truncate max-w-[180px] sm:max-w-[260px]">{l.title}</div>
                        <div className="text-[10px] text-zinc-500 mt-0.5">{l.duration} • {l.viewers}</div>
                      </div>
                      <span className="text-xs font-black text-rose-500 shrink-0">{l.sales_est}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Competitor Price Tracker Analysis */}
              <div className="p-4 bg-indigo-600/10 border border-indigo-500/20 rounded-xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-2 opacity-5">
                  <iconify-icon icon="solar:graph-bold" className="text-4xl text-indigo-400"></iconify-icon>
                </div>
                <p className="text-[11px] text-indigo-300 font-bold mb-1 uppercase tracking-wider">Deep Competitor Insight</p>
                <p className="text-xs text-zinc-300 leading-relaxed italic">
                  {liveSummary || (lang === 'id' 
                    ? '"Menganalisis pergerakan harga dan stok kompetitor secara mendalam..." '
                    : '"Deep analysis of competitor pricing and stock movements..." ')
                  }
                </p>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center text-[10px]">
                  <span className="text-zinc-500">Competitor Price Tracker</span>
                  <span className="text-emerald-500 font-bold">ACTIVE</span>
                </div>
                <div className="w-full bg-zinc-800 rounded-full h-1">
                  <div className="bg-indigo-500 h-1 rounded-full" style={{ width: '100%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketIntelTab;
