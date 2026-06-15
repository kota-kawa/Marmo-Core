import React from 'react';

const LeaderboardTab = ({ 
  t, 
  lang, 
  data = [], 
  countdown = '00:00:00:00', 
  formatCurrency,
  leaderboardFilter,
  setLeaderboardFilter,
  totalPeriodClosings = 0
}) => {
  // Helper to split countdown string safely
  const parts = (countdown || '00:00:00:00').split(':');
  const countdownObj = {
    days: parts[0] || '00',
    hours: parts[1] || '00',
    minutes: parts[2] || '00',
    seconds: parts[3] || '00'
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
      <div className="bg-orange-600/10 border border-orange-500/30 rounded-2xl p-6 space-y-4">
        <div className="flex flex-col sm:flex-row items-center gap-4 justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-600 rounded-xl flex items-center justify-center text-white text-xl">
              <iconify-icon icon="solar:chart-square-bold-duotone"></iconify-icon>
            </div>
            <div>
              <div className="text-[10px] font-black text-orange-500 uppercase tracking-widest">{t('mtdTracking')}</div>
              <div className="text-sm font-bold text-white uppercase">
                 Leaderboard <span className="text-orange-500">Global</span>
              </div>
            </div>
          </div>
          <div className="h-px w-full sm:h-10 sm:w-px bg-zinc-800"></div>
          <div className="text-center sm:text-right">
            <div className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">{t('nextChallenge')}</div>
            <div className="text-sm font-bold text-orange-400 italic">{t('whoIsTop')} 🚀</div>
          </div>
        </div>
        
        {/* Countdown */}
        <div className="border-t border-orange-500/20 pt-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative group">
            <button className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-zinc-100 bg-black/40 hover:bg-black/60 px-4 py-2 rounded-xl border border-zinc-800 transition-all">
              <iconify-icon icon="solar:calendar-linear" className="text-orange-500"></iconify-icon>
              <span>
                {leaderboardFilter === 'minggu_ini' ? t('weekCurrent') :
                 leaderboardFilter === 'minggu_lalu' ? 'Minggu Lalu' :
                 leaderboardFilter === 'bulan_ini' ? 'Bulan Ini (26 - 25)' :
                 'Semua Waktu (All-Time)'}
              </span>
              <iconify-icon icon="solar:alt-arrow-down-bold" className="text-[10px] text-zinc-500"></iconify-icon>
            </button>
            
            {/* Dropdown Menu Overlay */}
            <div className="absolute top-full left-0 mt-2 w-56 bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-20 overflow-hidden">
              <div className="p-1.5 flex flex-col">
                <button onClick={() => setLeaderboardFilter('minggu_ini')} className={`flex items-center gap-3 px-4 py-3 text-[10px] font-black uppercase tracking-widest rounded-xl text-left transition-colors ${leaderboardFilter === 'minggu_ini' ? 'text-orange-500 bg-orange-500/10' : 'text-zinc-400 hover:text-zinc-100 hover:bg-white/5'}`}>
                  <iconify-icon icon="solar:calendar-date-bold-duotone" className="text-base"></iconify-icon>
                  {t('weekCurrent')}
                </button>
                <button onClick={() => setLeaderboardFilter('minggu_lalu')} className={`flex items-center gap-3 px-4 py-3 text-[10px] font-black uppercase tracking-widest rounded-xl text-left transition-colors ${leaderboardFilter === 'minggu_lalu' ? 'text-orange-500 bg-orange-500/10' : 'text-zinc-400 hover:text-zinc-100 hover:bg-white/5'}`}>
                  <iconify-icon icon="solar:calendar-date-bold-duotone" className="text-base"></iconify-icon>
                  Minggu Lalu
                </button>
                <button onClick={() => setLeaderboardFilter('bulan_ini')} className={`flex items-center gap-3 px-4 py-3 text-[10px] font-black uppercase tracking-widest rounded-xl text-left transition-colors ${leaderboardFilter === 'bulan_ini' ? 'text-orange-500 bg-orange-500/10' : 'text-zinc-400 hover:text-zinc-100 hover:bg-white/5'}`}>
                  <iconify-icon icon="solar:calendar-minimalistic-bold-duotone" className="text-base"></iconify-icon>
                  Bulan Ini (26 - 25)
                </button>
                <button onClick={() => setLeaderboardFilter('semua_waktu')} className={`flex items-center gap-3 px-4 py-3 text-[10px] font-black uppercase tracking-widest rounded-xl text-left transition-colors ${leaderboardFilter === 'semua_waktu' ? 'text-orange-500 bg-orange-500/10' : 'text-zinc-400 hover:text-zinc-100 hover:bg-white/5'}`}>
                  <iconify-icon icon="solar:globus-bold-duotone" className="text-base"></iconify-icon>
                  Semua Waktu (All-Time)
                </button>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[9px] font-black text-zinc-500 uppercase tracking-widest mr-1">{lang === 'id' ? 'Berakhir:' : 'Ends in:'}</span>
            {[{v: countdownObj.days, u: 'd'}, {v: countdownObj.hours, u: 'h'}, {v: countdownObj.minutes, u: 'm'}, {v: countdownObj.seconds, u: 's'}].map(({v, u}, i) => (
              <React.Fragment key={u}>
                <div className="bg-black/60 border border-zinc-700 rounded-lg px-2 py-1 min-w-[36px] text-center">
                  <span className="text-sm font-black text-orange-400 font-mono">{v}</span>
                  <span className="text-[7px] font-bold text-zinc-500 ml-0.5">{u}</span>
                </div>
                {i < 3 && <span className="text-zinc-600 font-bold text-xs">:</span>}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Weekly Target Indicator */}
        {(leaderboardFilter === 'minggu_ini' || leaderboardFilter === 'minggu_lalu') && (
          <div className="border-t border-orange-500/20 pt-4 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${totalPeriodClosings >= 5 ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
              <span className="text-xs font-bold text-zinc-100">
                Total Closing {leaderboardFilter === 'minggu_ini' ? 'Minggu Ini' : 'Minggu Lalu'}: <span className={totalPeriodClosings >= 5 ? 'text-green-400' : 'text-red-400'}>{totalPeriodClosings} / 5</span>
              </span>
            </div>
            <div className="text-xs font-bold text-zinc-400">
              {totalPeriodClosings >= 5 ? (
                <span className="text-green-400 flex items-center gap-1">
                  <iconify-icon icon="solar:medal-ribbons-bold" className="text-base"></iconify-icon>
                  Syarat Bonus 300rb Terpenuhi!
                </span>
              ) : (
                <span className="text-red-400 flex items-center gap-1">
                  <iconify-icon icon="solar:danger-bold" className="text-base"></iconify-icon>
                  Kurang {5 - totalPeriodClosings} Closing lagi untuk cairkan bonus!
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-10 pt-4">
        <div className="text-left space-y-1">
          <h2 className="text-2xl font-black text-white uppercase tracking-[0.4em]">{t('eliteRankings')}</h2>
          <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em]">{t('rankDesc')}</p>
        </div>
      </div>

      <div className="bg-zinc-900/20 backdrop-blur-md border border-zinc-800/50 rounded-[40px] overflow-hidden shadow-2xl">
        <div className="divide-y divide-zinc-800/50">
          {(data || []).map((item, index) => (
            <div key={index} className="group flex items-center gap-4 sm:gap-6 px-6 sm:px-10 py-6 sm:py-8 hover:bg-white/[0.01] transition-all duration-300">
              <div className="w-8 sm:w-12 flex justify-center text-2xl sm:text-3xl filter drop-shadow-lg">
                {index === 0 ? "🥇" : index === 1 ? "🥈" : index === 2 ? "🥉" : 
                  <span className="text-base sm:text-xl font-black text-zinc-600">{index + 1}</span>
                }
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 sm:gap-3">
                  <div className="text-sm sm:text-base font-black tracking-tight truncate text-white group-hover:text-orange-400 transition-colors">
                    {item.full_name}
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-1 sm:mt-1.5 text-[8px] sm:text-[10px] font-bold uppercase tracking-widest text-zinc-500">
                  <iconify-icon icon="solar:medal-star-bold-duotone" className="text-[10px] sm:text-xs text-orange-500"></iconify-icon>
                  <span className="truncate">Top Partner</span>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-sm sm:text-lg font-black text-emerald-400 font-mono tracking-tighter">{formatCurrency(item.total_omzet).split(',')[0]}</div>
                <div className="text-[8px] sm:text-[10px] font-black text-zinc-400 uppercase tracking-widest mt-0.5 sm:mt-1 flex items-center justify-end gap-1 sm:gap-1.5">
                  <iconify-icon icon="solar:fire-bold" className="text-orange-500"></iconify-icon>
                  {t('commission')}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default LeaderboardTab;
