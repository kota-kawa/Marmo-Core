import React from 'react';

const PaymentTab = ({ 
  t, 
  partnerData, 
  formatCurrency 
}) => {
  const totalPayout = (partnerData?.paymentHistory || [])
    .filter(p => p.status === 'paid')
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);
  
  const pendingBalance = Math.max(0, (partnerData?.total_omzet || 0) - totalPayout);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
      {/* GAP 4: Stat Card - Saldo Komisi Akurat */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Pending Balance */}
        <div className="bg-gradient-to-br from-emerald-600/20 to-teal-600/5 backdrop-blur-md border border-emerald-500/20 rounded-[32px] p-8 flex items-center justify-between shadow-2xl group">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-white/5 rounded-full flex items-center justify-center border border-white/10 group-hover:scale-110 transition-transform">
              <iconify-icon icon="solar:wallet-bold-duotone" className="text-3xl text-emerald-500"></iconify-icon>
            </div>
            <div>
              <div className="text-[9px] font-black text-emerald-500 uppercase tracking-[0.3em]">Komisi Berjalan (Siap Cair)</div>
              <div className="text-2xl font-black text-white tracking-tight font-mono">{formatCurrency(pendingBalance)}</div>
              <div className="text-[10px] font-medium text-emerald-400 mt-1">Pencairan dilakukan manual oleh admin setiap tanggal 25</div>
            </div>
          </div>
        </div>

        {/* All-time Gross */}
        <div className="bg-zinc-900/40 backdrop-blur-md border border-zinc-800 rounded-[32px] p-8 flex items-center justify-between shadow-sm group">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-zinc-800/50 rounded-full flex items-center justify-center border border-zinc-700">
              <iconify-icon icon="solar:history-bold-duotone" className="text-3xl text-zinc-500"></iconify-icon>
            </div>
            <div>
              <div className="text-[9px] font-black text-zinc-500 uppercase tracking-[0.3em]">Total Sepanjang Masa</div>
              <div className="text-xl font-bold text-zinc-300 tracking-tight font-mono">{formatCurrency(partnerData?.total_omzet || 0)}</div>
              <div className="text-[10px] font-medium text-zinc-500 mt-1">Akumulasi seluruh komisi</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="group bg-zinc-900/20 backdrop-blur-md border border-zinc-800/50 rounded-[32px] p-8 hover:border-orange-500/30 transition-all duration-500">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-12 h-12 bg-orange-600/10 rounded-2xl flex items-center justify-center border border-orange-500/20">
              <iconify-icon icon="solar:bill-list-bold-duotone" className="text-2xl text-orange-500"></iconify-icon>
            </div>
            <h3 className="text-sm font-black text-white uppercase tracking-[0.3em]">{t('paymentHistory')}</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[10px] font-bold uppercase tracking-widest">
              <thead>
                <tr className="text-zinc-500 border-b border-zinc-800/50">
                  <th className="py-3">{t('period')}</th>
                  <th className="py-3">{t('status')}</th>
                  <th className="py-3 text-right text-emerald-400">{t('amount')}</th>
                </tr>
              </thead>
              <tbody className="text-zinc-200">
                {(partnerData?.paymentHistory || []).map((p, idx) => {
                  // Cek apakah ada data breakdown (kolom baru nullable)
                  const hasBreakdown = p.revenue_share != null || p.performance_bonus != null;
                  const revenueShare = Number(p.revenue_share) || 0;
                  const perfBonus = Number(p.performance_bonus) || 0;

                  return (
                    <React.Fragment key={idx}>
                      {/* Baris utama — identik dengan sebelumnya, tidak ada perubahan */}
                      <tr className={`border-b border-zinc-900/30 group-hover:bg-white/[0.01] ${hasBreakdown ? 'border-b-0' : ''}`}>
                        <td className="py-4 font-black text-white">{p.period}</td>
                        <td className="py-4">
                          <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[9px] font-black uppercase tracking-widest border ${
                            p.status === 'paid'
                              ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                              : 'text-amber-400 bg-amber-500/10 border-amber-500/20'
                          }`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${p.status === 'paid' ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'}`}></span>
                            {p.status}
                          </span>
                        </td>
                        <td className="py-4 text-right text-emerald-400 font-black font-mono text-xs">{formatCurrency(p.amount)}</td>
                      </tr>

                      {/* Baris breakdown — HANYA muncul jika kolom baru ada datanya */}
                      {hasBreakdown && (
                        <tr className="border-b border-zinc-900/30">
                          <td colSpan={3} className="pb-4 pt-1 pl-4">
                            <div className="bg-zinc-950/60 border border-zinc-800/50 rounded-2xl p-4 space-y-3">

                              {/* Label Header */}
                              <div className="text-[9px] font-black text-zinc-500 uppercase tracking-[0.2em] mb-2">
                                Rincian Komisi
                              </div>

                              {/* ── BAGIAN 1: REVENUE SHARE ── */}
                              {revenueShare > 0 && (
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div>
                                    <span className="text-[10px] text-zinc-300 font-bold normal-case tracking-normal">Revenue Share</span>
                                  </div>
                                  <span className="text-[11px] font-black font-mono text-blue-400">{formatCurrency(revenueShare)}</span>
                                </div>
                              )}

                              {/* ── BAGIAN 2: PERFORMANCE BONUS ── */}
                              {/* Hanya tampil jika perfBonus > 0 (variabel yang tercapai) */}
                              {perfBonus > 0 && (
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-amber-500"></div>
                                    <span className="text-[10px] text-zinc-300 font-bold normal-case tracking-normal">Performance Bonus</span>
                                  </div>
                                  <span className="text-[11px] font-black font-mono text-amber-400">{formatCurrency(perfBonus)}</span>
                                </div>
                              )}

                              {/* Divider + Total Confirm */}
                              <div className="pt-2 mt-2 border-t border-zinc-800/50 flex items-center justify-between">
                                <span className="text-[9px] text-zinc-500 font-black uppercase tracking-widest">Total Cair</span>
                                <span className="text-[11px] font-black font-mono text-emerald-400">{formatCurrency(p.amount)}</span>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-6">
          <div className="group bg-zinc-900/20 backdrop-blur-md border border-zinc-800/50 rounded-[32px] p-8 hover:border-orange-500/30 transition-all duration-300">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-12 h-12 bg-orange-600/10 rounded-2xl flex items-center justify-center border border-orange-500/20">
                <iconify-icon icon="solar:info-circle-bold-duotone" className="text-2xl text-orange-500"></iconify-icon>
              </div>
              <h3 className="text-sm font-black text-white uppercase tracking-[0.3em]">{t('paymentInfo')}</h3>
            </div>
            <p className="text-xs leading-loose text-zinc-300 font-medium italic">
              "Komisi partner akan diproses secara manual oleh admin ke rekening Anda yang terdaftar pada tanggal 25 setiap bulannya. Harap pastikan data rekening Anda valid."
            </p>
            <div className="mt-8 pt-8 border-t border-zinc-800/50 flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-zinc-400">
              <span>{t('cyclePeriod')}</span>
              <span className="text-white">{t('monthly')}</span>
            </div>
          </div>

          <div className="bg-gradient-to-br from-orange-600/20 to-amber-600/5 backdrop-blur-md border border-orange-500/20 rounded-[32px] p-8 flex items-center justify-between shadow-2xl group">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-white/5 rounded-full flex items-center justify-center border border-white/10 group-hover:scale-110 transition-transform">
                <iconify-icon icon="solar:wallet-money-bold-duotone" className="text-3xl text-orange-500"></iconify-icon>
              </div>
              <div>
                <div className="text-[9px] font-black text-orange-500 uppercase tracking-[0.3em]">{t('bankStatus')}</div>
                <div className="text-base font-black text-white tracking-tight">
                  {partnerData?.bank_account
                    ? `✅ ${partnerData.bank_name || 'Bank'} · ${partnerData.bank_account}`
                    : '⚠️ Belum diisi — lengkapi di Profile'}
                </div>
              </div>
            </div>
            <iconify-icon icon="solar:check-circle-bold" className="text-emerald-400 text-3xl animate-pulse"></iconify-icon>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PaymentTab;
