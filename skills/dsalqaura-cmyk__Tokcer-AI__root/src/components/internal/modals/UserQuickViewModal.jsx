import React, { useState, useEffect } from 'react';
import { supabase } from '../../../lib/supabase.js';

/**
 * UserQuickViewModal
 * ─────────────────────────────────────────────────────────────────────────────
 * Detail lengkap user untuk keperluan follow-up admin:
 *  - Info kontak: WhatsApp, email (klik langsung buka WA/email)
 *  - AI Credits sisa (dari profiles.ai_tokens)
 *  - Status & plan
 *  - Omzet & jumlah order
 *  - Tanggal daftar & expiry
 *  - Platform yang digunakan
 * ─────────────────────────────────────────────────────────────────────────────
 */

const UserQuickViewModal = ({ t, showUserStats, setShowUserStats }) => {
  const [stats, setStats]     = useState({ omzet: 0, orders: 0 });
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!showUserStats?.id) return;

    const fetchData = async () => {
      setLoading(true);
      setProfile(null);
      setStats({ omzet: 0, orders: 0 });

      try {
        // 1. Orders untuk omzet
        const { data: ords } = await supabase
          .from('orders')
          .select('total_amount')
          .eq('user_id', showUserStats.id);

        const totalOrders = ords?.length || 0;
        const totalOmzet  = (ords || []).reduce((acc, curr) => acc + (Number(curr.total_amount) || 0), 0);
        setStats({ omzet: totalOmzet, orders: totalOrders });

        // 2. Profile untuk AI tokens — cari berdasarkan email karena clients.id ≠ profiles.id
        const { data: profileData } = await supabase
          .from('profiles')
          .select('id, ai_tokens, tokens, subscription_plan, full_name')
          .eq('email', showUserStats.email)
          .maybeSingle();

        setProfile(profileData || null);
      } catch (err) {
        console.error('[UserQuickView] fetchData error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [showUserStats]);

  if (!showUserStats) return null;

  const u = showUserStats;

  // Hitung status
  const isExpired   = u.status === 'expired' || (u.status === 'active' && u.expires_at && new Date(u.expires_at) < new Date());
  const daysLeft    = u.expires_at ? Math.ceil((new Date(u.expires_at) - new Date()) / (1000 * 60 * 60 * 24)) : null;
  const isNearExpiry = daysLeft !== null && daysLeft <= 3 && daysLeft > 0;

  // AI credits: coba dari profile yang di-fetch, fallback ke data join yang sudah ada di showUserStats
  const aiCredits = profile?.ai_tokens
    ?? profile?.tokens
    ?? showUserStats.profiles?.ai_tokens
    ?? showUserStats.profiles?.tokens
    ?? '-';

  // WhatsApp number — bersihkan format
  const rawWa = u.whatsapp || '';
  const waNumber = rawWa.replace(/\D/g, '').replace(/^0/, '62');
  const waLink   = waNumber ? `https://wa.me/${waNumber}` : null;

  // Platform list
  const platforms = Array.isArray(u.platforms)
    ? u.platforms
    : (typeof u.platforms === 'string' ? u.platforms.split(',').map(s => s.trim()) : []);

  const formatDate = (d) => d
    ? new Date(d).toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' })
    : '-';

  const formatRp = (n) => 'Rp ' + new Intl.NumberFormat('id-ID').format(n || 0);

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-[110] flex items-center justify-center p-4 animate-in fade-in duration-300">
      <div className="bg-zinc-900 rounded-[2.5rem] max-w-2xl w-full border border-zinc-800 relative overflow-hidden shadow-2xl">

        {/* ── Top accent bar ── */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 to-indigo-500"></div>

        {/* ── Header ── */}
        <div className="p-8 border-b border-zinc-800 flex items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center shrink-0">
              <span className="text-xl font-black text-blue-400">
                {(u.shop_name || u.email || '?').charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h2 className="text-xl font-black text-white tracking-tight">{u.shop_name || u.email}</h2>
              <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mt-0.5">
                ID: {u.id?.substring(0, 8)}...
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowUserStats(null)}
            className="text-zinc-500 hover:text-white transition-all mt-1"
          >
            <iconify-icon icon="solar:close-circle-bold" className="text-3xl"></iconify-icon>
          </button>
        </div>

        {loading ? (
          <div className="p-16 flex flex-col items-center gap-3 text-zinc-500">
            <iconify-icon icon="solar:spinner-linear" className="text-4xl animate-spin text-blue-500"></iconify-icon>
            <p className="text-xs font-black uppercase tracking-widest">Memuat data...</p>
          </div>
        ) : (
          <div className="p-8 space-y-6 max-h-[70vh] overflow-y-auto custom-scrollbar">

            {/* ── Kontak — bagian terpenting untuk follow-up ── */}
            <div className="bg-zinc-950/60 rounded-2xl border border-zinc-800 p-5">
              <p className="text-[9px] font-black text-zinc-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                <iconify-icon icon="solar:phone-bold-duotone" className="text-sm text-blue-400"></iconify-icon>
                Kontak & Follow-Up
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">

                {/* WhatsApp */}
                <div className="flex items-center gap-3 p-3 bg-zinc-900 rounded-xl border border-zinc-800">
                  <div className="w-8 h-8 bg-emerald-500/10 rounded-lg flex items-center justify-center shrink-0">
                    <iconify-icon icon="solar:phone-bold-duotone" className="text-base text-emerald-400"></iconify-icon>
                  </div>
                  <div className="min-w-0">
                    <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest">WhatsApp</p>
                    {rawWa ? (
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-bold text-white truncate">{rawWa}</p>
                        {waLink && (
                          <a
                            href={waLink}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="shrink-0 px-2 py-0.5 bg-emerald-500/10 text-emerald-400 text-[8px] font-black uppercase rounded-md border border-emerald-500/20 hover:bg-emerald-500/20 transition-all"
                          >
                            Chat
                          </a>
                        )}
                      </div>
                    ) : (
                      <p className="text-xs text-zinc-600 italic">Tidak tersedia</p>
                    )}
                  </div>
                </div>

                {/* Email */}
                <div className="flex items-center gap-3 p-3 bg-zinc-900 rounded-xl border border-zinc-800">
                  <div className="w-8 h-8 bg-blue-500/10 rounded-lg flex items-center justify-center shrink-0">
                    <iconify-icon icon="solar:letter-bold-duotone" className="text-base text-blue-400"></iconify-icon>
                  </div>
                  <div className="min-w-0">
                    <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest">Email</p>
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-bold text-white truncate">{u.email || '-'}</p>
                      {u.email && (
                        <a
                          href={`mailto:${u.email}`}
                          className="shrink-0 px-2 py-0.5 bg-blue-500/10 text-blue-400 text-[8px] font-black uppercase rounded-md border border-blue-500/20 hover:bg-blue-500/20 transition-all"
                        >
                          Kirim
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* ── Status & Plan ── */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {/* Plan */}
              <div className="bg-zinc-950/60 rounded-2xl border border-zinc-800 p-4 text-center">
                <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest mb-2">Plan</p>
                <span className="text-xs font-black text-amber-400 uppercase">{u.plan || u.tier || 'Starter'}</span>
              </div>

              {/* Status */}
              <div className="bg-zinc-950/60 rounded-2xl border border-zinc-800 p-4 text-center">
                <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest mb-2">Status</p>
                <span className={`text-xs font-black uppercase ${
                  isExpired ? 'text-red-400' : isNearExpiry ? 'text-orange-400' : 'text-emerald-400'
                }`}>
                  {isExpired ? 'Expired' : isNearExpiry ? `H-${daysLeft}` : (u.status || 'Active')}
                </span>
              </div>

              {/* AI Credits */}
              <div className="bg-zinc-950/60 rounded-2xl border border-zinc-800 p-4 text-center">
                <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest mb-2">AI Credits</p>
                <span className={`text-xs font-black ${
                  aiCredits === '-' ? 'text-zinc-600' :
                  Number(aiCredits) <= 10 ? 'text-red-400' :
                  Number(aiCredits) <= 50 ? 'text-amber-400' : 'text-blue-400'
                }`}>
                  {aiCredits === '-' ? '-' : Number(aiCredits).toLocaleString('id-ID')}
                </span>
                {aiCredits !== '-' && Number(aiCredits) <= 10 && (
                  <p className="text-[8px] text-red-500 mt-1 font-bold">⚠ Hampir habis</p>
                )}
              </div>

              {/* Billing Cycle */}
              <div className="bg-zinc-950/60 rounded-2xl border border-zinc-800 p-4 text-center">
                <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest mb-2">Billing</p>
                <span className="text-xs font-black text-zinc-300 uppercase">{u.billing_cycle || 'Monthly'}</span>
              </div>
            </div>

            {/* ── Omzet & Orders ── */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-zinc-950/60 rounded-2xl border border-zinc-800 p-5 text-center">
                <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest mb-2">Total Omzet</p>
                <p className="text-lg font-black text-white">{formatRp(stats.omzet)}</p>
              </div>
              <div className="bg-zinc-950/60 rounded-2xl border border-zinc-800 p-5 text-center">
                <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest mb-2">Total Orders</p>
                <p className="text-lg font-black text-white">{stats.orders}</p>
              </div>
            </div>

            {/* ── Tanggal ── */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-zinc-950/60 rounded-2xl border border-zinc-800 p-4">
                <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest mb-1">Tanggal Daftar</p>
                <p className="text-xs font-bold text-zinc-300">{formatDate(u.created_at)}</p>
              </div>
              <div className="bg-zinc-950/60 rounded-2xl border border-zinc-800 p-4">
                <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest mb-1">Aktif Hingga</p>
                <p className={`text-xs font-bold ${isExpired ? 'text-red-400' : isNearExpiry ? 'text-orange-400' : 'text-zinc-300'}`}>
                  {formatDate(u.expires_at)}
                  {daysLeft !== null && !isExpired && (
                    <span className="ml-1 text-zinc-600">({daysLeft}h lagi)</span>
                  )}
                </p>
              </div>
            </div>

            {/* ── Platform ── */}
            {platforms.length > 0 && (
              <div className="bg-zinc-950/60 rounded-2xl border border-zinc-800 p-4">
                <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest mb-3">Platform</p>
                <div className="flex flex-wrap gap-2">
                  {platforms.map((p, i) => (
                    <span key={i} className="px-3 py-1 bg-zinc-800 text-zinc-300 text-[9px] font-black uppercase rounded-lg border border-zinc-700">
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* ── Partner Referral ── */}
            {(u.partners?.full_name || u.ref) && (
              <div className="bg-zinc-950/60 rounded-2xl border border-zinc-800 p-4">
                <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest mb-1">Direferral Oleh</p>
                <p className="text-xs font-bold text-amber-400">{u.partners?.full_name || u.ref}</p>
              </div>
            )}

            {/* ── Business Type ── */}
            {u.business_type && (
              <div className="bg-zinc-950/60 rounded-2xl border border-zinc-800 p-4">
                <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest mb-1">Jenis Bisnis</p>
                <p className="text-xs font-bold text-zinc-300">{u.business_type}</p>
              </div>
            )}
          </div>
        )}

        {/* ── Footer actions ── */}
        <div className="p-6 border-t border-zinc-800 bg-zinc-950/50 flex items-center justify-between gap-3">
          {waLink ? (
            <a
              href={waLink}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all shadow-lg shadow-emerald-600/20"
            >
              <iconify-icon icon="solar:phone-bold" className="text-base"></iconify-icon>
              Follow-Up via WA
            </a>
          ) : (
            <span className="text-[9px] text-zinc-600 italic">No. WA tidak tersedia</span>
          )}
          <button
            onClick={() => setShowUserStats(null)}
            className="px-5 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white text-[10px] font-black uppercase tracking-widest rounded-xl border border-zinc-700 transition-all"
          >
            Tutup
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserQuickViewModal;
