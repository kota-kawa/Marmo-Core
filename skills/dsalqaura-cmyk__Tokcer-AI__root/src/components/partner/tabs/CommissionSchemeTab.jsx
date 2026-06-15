import React from 'react';

const CommissionSchemeTab = () => {
  return (
    <div className="space-y-10 pb-10">
      {/* A. REVENUE SHARE */}
      <div className="section">
        <div className="flex items-center gap-2 font-['Barlow_Condensed',sans-serif] font-extrabold text-[13px] tracking-[0.18em] uppercase text-[#F5A300] mb-4 section-title">A — Revenue Share (Recurring Monthly)</div>
        <div className="bg-[#111111] border border-[rgba(255,255,255,0.06)] rounded-xl overflow-hidden hover:border-[rgba(245,163,0,0.15)] transition-colors">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="bg-[#1A1A1A] border-b border-[rgba(255,255,255,0.05)]">
                  <th className="px-4 py-3 font-['Barlow_Condensed',sans-serif] font-bold text-[11px] tracking-[0.12em] uppercase text-zinc-500">Plan</th>
                  <th className="px-4 py-3"><span className="inline-flex px-2 py-0.5 rounded border bg-[rgba(176,108,42,0.15)] text-[#CD7F32] border-[rgba(176,108,42,0.3)] font-['Barlow_Condensed',sans-serif] font-bold text-[11px] tracking-wider">Bronze</span></th>
                  <th className="px-4 py-3"><span className="inline-flex px-2 py-0.5 rounded border bg-[rgba(150,150,160,0.12)] text-[#A8A8B8] border-[rgba(150,150,160,0.25)] font-['Barlow_Condensed',sans-serif] font-bold text-[11px] tracking-wider">Silver</span></th>
                  <th className="px-4 py-3"><span className="inline-flex px-2 py-0.5 rounded border bg-[rgba(245,163,0,0.12)] text-[#F5A300] border-[rgba(245,163,0,0.25)] font-['Barlow_Condensed',sans-serif] font-bold text-[11px] tracking-wider">Gold</span></th>
                  <th className="px-4 py-3"><span className="inline-flex px-2 py-0.5 rounded border bg-[rgba(120,160,220,0.12)] text-[#88AADD] border-[rgba(120,160,220,0.25)] font-['Barlow_Condensed',sans-serif] font-bold text-[11px] tracking-wider">Platinum</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(255,255,255,0.04)]">
                <tr className="hover:bg-[rgba(245,163,0,0.03)] transition-colors">
                  <td className="px-4 py-3 font-semibold text-white">Pro</td>
                  <td className="px-4 py-3 text-zinc-400">Rp 100K</td>
                  <td className="px-4 py-3 text-zinc-400">Rp 100K</td>
                  <td className="px-4 py-3 text-zinc-400">Rp 100K</td>
                  <td className="px-4 py-3 text-zinc-400">Rp 100K</td>
                </tr>
                <tr className="hover:bg-[rgba(245,163,0,0.03)] transition-colors">
                  <td className="px-4 py-3 font-semibold text-white">Elite</td>
                  <td className="px-4 py-3 text-zinc-400">Rp 119.6K</td>
                  <td className="px-4 py-3 text-zinc-400">Rp 149.6K</td>
                  <td className="px-4 py-3 text-zinc-400">Rp 179.5K</td>
                  <td className="px-4 py-3 text-[#F5A300] font-bold">Rp 199.4K</td>
                </tr>
                <tr className="hover:bg-[rgba(245,163,0,0.03)] transition-colors">
                  <td className="px-4 py-3 font-semibold text-white">Ultimate</td>
                  <td className="px-4 py-3 text-zinc-400">Rp 200K</td>
                  <td className="px-4 py-3 text-zinc-400">Rp 240K</td>
                  <td className="px-4 py-3 text-zinc-400">Rp 300K</td>
                  <td className="px-4 py-3 text-[#F5A300] font-bold">Rp 360K</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <p className="text-[11px] text-zinc-500 mt-3 px-1 leading-relaxed italic">
          ↳ Komisi dibayar selama subscriber aktif. Jika subscriber cancel → komisi berhenti setelah anniversary date mereka. Zero clawback.
        </p>
      </div>

      {/* A2. TIER CRITERIA */}
      <div className="section">
        <div className="flex items-center gap-2 font-['Barlow_Condensed',sans-serif] font-extrabold text-[13px] tracking-[0.18em] uppercase text-[#F5A300] mb-4 section-title">A.2 — Kriteria Tier</div>
        <div className="bg-[#111111] border border-[rgba(255,255,255,0.06)] rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="bg-[#1A1A1A] border-b border-[rgba(255,255,255,0.05)] text-[10px] font-bold uppercase tracking-widest text-zinc-500">
                  <th className="px-4 py-3">Tier</th>
                  <th className="px-4 py-3">Min Closing / Bulan</th>
                  <th className="px-4 py-3">Min Elite / Periode</th>
                  <th className="px-4 py-3">Tier Check</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(255,255,255,0.04)] text-zinc-400">
                <tr>
                  <td className="px-4 py-3"><span className="inline-flex px-2 py-0.5 rounded border bg-[rgba(176,108,42,0.15)] text-[#CD7F32] border-[rgba(176,108,42,0.3)] font-['Barlow_Condensed',sans-serif] font-bold text-[10px]">Bronze</span></td>
                  <td className="px-4 py-3">≥ 3 closing</td>
                  <td className="px-4 py-3 text-zinc-700">—</td>
                  <td className="px-4 py-3 text-[12px] text-zinc-600">Tanggal 1 tiap bulan</td>
                </tr>
                <tr>
                  <td className="px-4 py-3"><span className="inline-flex px-2 py-0.5 rounded border bg-[rgba(150,150,160,0.12)] text-[#A8A8B8] border-[rgba(150,150,160,0.25)] font-['Barlow_Condensed',sans-serif] font-bold text-[10px]">Silver</span></td>
                  <td className="px-4 py-3">≥ 5 closing</td>
                  <td className="px-4 py-3 text-zinc-500">≥ 2 Elite / quarter</td>
                  <td className="px-4 py-3 text-[12px] text-zinc-600">Tanggal 1 tiap bulan</td>
                </tr>
                <tr>
                  <td className="px-4 py-3"><span className="inline-flex px-2 py-0.5 rounded border bg-[rgba(245,163,0,0.12)] text-[#F5A300] border-[rgba(245,163,0,0.25)] font-['Barlow_Condensed',sans-serif] font-bold text-[10px]">Gold</span></td>
                  <td className="px-4 py-3">≥ 8 closing</td>
                  <td className="px-4 py-3 text-zinc-500">≥ 2 Elite / bulan</td>
                  <td className="px-4 py-3 text-[12px] text-zinc-600">Tanggal 1 tiap bulan</td>
                </tr>
                <tr>
                  <td className="px-4 py-3"><span className="inline-flex px-2 py-0.5 rounded border bg-[rgba(120,160,220,0.12)] text-[#88AADD] border-[rgba(120,160,220,0.25)] font-['Barlow_Condensed',sans-serif] font-bold text-[10px]">Platinum</span></td>
                  <td className="px-4 py-3">≥ 15 closing</td>
                  <td className="px-4 py-3 text-zinc-500">≥ 5 Elite / bulan</td>
                  <td className="px-4 py-3 text-[12px] text-zinc-600">Tanggal 1 tiap bulan</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* B. PERFORMANCE BONUS */}
      <div className="section">
        <div className="flex items-center gap-2 font-['Barlow_Condensed',sans-serif] font-extrabold text-[13px] tracking-[0.18em] uppercase text-[#F5A300] mb-4 section-title">B — Performance Bonus</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { emoji: '🏆', name: 'Weekly Top 1', trigger: 'Closing omzet tertinggi dalam satu minggu', value: '+ Rp 300.000' },
            { emoji: '📊', name: 'Volume Milestone', trigger: '≥5 → Rp 150K · ≥10 → Rp 350K · ≥15 → Rp 750K', value: '+ s/d Rp 750.000' },
            { emoji: '📅', name: 'Annual Plan Bonus', trigger: 'Referral beli annual plan (Pro +100K · Elite +250K · Ultimate +500K)', value: '+ s/d Rp 500.000' },
            { emoji: '⬆️', name: 'Tier Upgrade Bonus', trigger: 'Subscriber-mu upgrade tier (Pro→Elite +150K · Elite→Ult +300K)', value: '+ s/d Rp 300.000' },
            { emoji: '🚀', name: 'Fast Start Bonus', trigger: '3 closing pertama dalam 30 hari sejak onboarding (one-time)', value: '+ Rp 300.000' },
            { emoji: '🔁', name: 'Consistency Bonus', trigger: '3 bulan berturut-turut ≥5 closing/bulan (dibayar bulan ke-3)', value: '+ Rp 300.000' }
          ].map((bonus, idx) => (
            <div key={idx} className="bg-[#111111] border border-[rgba(255,255,255,0.06)] rounded-xl p-5 hover:border-[rgba(245,163,0,0.2)] hover:-translate-y-1 transition-all duration-300 shadow-sm group">
              <span className="text-2xl mb-2 block">{bonus.emoji}</span>
              <div className="font-['Barlow_Condensed',sans-serif] font-bold text-[14px] tracking-wider text-white mb-1 group-hover:text-[#F5A300] transition-colors">{bonus.name}</div>
              <div className="text-[12px] text-zinc-500 leading-tight mb-3 h-8">{bonus.trigger}</div>
              <div className="font-['Barlow_Condensed',sans-serif] font-extrabold text-[16px] text-[#F5A300]">{bonus.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* D. ATURAN UTAMA */}
      <div className="section">
        <div className="flex items-center gap-2 font-['Barlow_Condensed',sans-serif] font-extrabold text-[13px] tracking-[0.18em] uppercase text-[#F5A300] mb-4 section-title">D — Aturan Utama</div>
        <div className="space-y-2.5">
          {[
            "Pencatatan data customer baru menggunakan sistem Manual Input di Partner Portal. Pastikan setiap data customer terdaftar untuk validasi klaim.",
            "Zero clawback — komisi yang sudah dibayar tidak akan pernah ditarik kembali dalam kondisi apapun.",
            "Tier dievaluasi tanggal 1 setiap bulan berdasarkan performa bulan sebelumnya. Auto-promote & auto-demote berlaku.",
            "Tokcer AI berhak menonaktifkan Partner yang melakukan misleading claim, spam, atau pelanggaran etika promosi.",
            "Partner tidak diperbolehkan mempromosikan SaaS kompetitor langsung dalam konten yang sama dengan Tokcer AI."
          ].map((rule, idx) => (
            <div key={idx} className="flex items-start gap-4 bg-[#111111] border border-[rgba(255,255,255,0.05)] rounded-lg p-3.5 text-sm text-zinc-300 leading-relaxed shadow-sm">
              <div className="flex-shrink-0 w-6 h-6 bg-[rgba(245,163,0,0.1)] border border-[rgba(245,163,0,0.3)] rounded flex items-center justify-center font-['Barlow_Condensed',sans-serif] font-black text-xs text-[#F5A300]">{idx + 1}</div>
              <div>{rule}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default CommissionSchemeTab;
