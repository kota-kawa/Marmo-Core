import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { supabase } from '../lib/supabase.js';

const PartnerAgreement = () => {
  const [searchParams] = useSearchParams();
  const applicationId = searchParams.get('id');
  
  const [partnerData, setPartnerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [refCode, setRefCode] = useState('');
  const [countdown, setCountdown] = useState(5);

  // Rate komisi — sumber kebenaran sama dengan CommissionSchemeTab di Partner Dashboard
  const [commissionRates, setCommissionRates] = useState({
    pro:      { bronze: 100000, silver: 100000, gold: 100000, platinum: 100000 },
    elite:    { bronze: 119600, silver: 149600, gold: 179500, platinum: 199400 },
    ultimate: { bronze: 200000, silver: 240000, gold: 300000, platinum: 360000 }
  });

  useEffect(() => {
    // Fetch rate komisi dari ai_configs agar selalu sinkron dengan sistem
    const fetchRates = async () => {
      try {
        const { data } = await supabase
          .from('ai_configs')
          .select('value')
          .eq('key', 'commission_rates_v3')
          .maybeSingle();
        if (data?.value) {
          const parsed = JSON.parse(data.value);
          setCommissionRates(parsed);
        }
      } catch (err) {
        // Pakai fallback default jika gagal
        console.warn('Gagal fetch commission rates, pakai default.');
      }
    };
    fetchRates();
  }, []);

  useEffect(() => {
    let timer;
    if (isSuccess && countdown > 0) {
      timer = setInterval(() => setCountdown(prev => prev - 1), 1000);
    } else if (isSuccess && countdown === 0) {
      window.location.href = window.location.origin;
    }
    return () => clearInterval(timer);
  }, [isSuccess, countdown]);

  useEffect(() => {
    const fetchPartner = async () => {
      if (!applicationId) {
        setLoading(false);
        return;
      }
      const { data, error } = await supabase
        .from('partner_applications')
        .select('*')
        .eq('id', applicationId)
        .single();
      
      if (data) setPartnerData(data);
      setLoading(false);
    };
    fetchPartner();
  }, [applicationId]);

  const handleSubmit = async () => {
    if (!agreed || !applicationId) return;
    
    setIsSubmitting(true);
    try {
      const { error } = await supabase
        .from('partner_applications')
        .update({ 
          status: 'agreed',
          agreed_at: new Date().toISOString()
        })
        .eq('id', applicationId);
      
      if (error) throw error;

      const tsShort = Date.now().toString().slice(-6);
      const generatedCode = `TKC-AGR-${tsShort}`;

      // [PERBAIKAN UJANG]: Pastikan data partner tercipta di tabel partners
      if (partnerData?.email) {
        const { data: existingPartner } = await supabase
          .from('partners')
          .select('id')
          .eq('email', partnerData.email)
          .maybeSingle();

        if (existingPartner) {
          // Jika sudah ada, tinggal update kodenya
          const { error: updateError } = await supabase
            .from('partners')
            .update({ referral_code: generatedCode })
            .eq('email', partnerData.email);
          
          if (updateError) throw updateError;
          console.log("Partner ditemukan, mengupdate kode referral.");
        } else {
          // Jika belum ada, buat baru
          // CATATAN: id TIDAK diisi — akan diisi saat admin approve via rpc_activate_partner
          // yang membuat auth user terlebih dahulu dan menggunakan UUID dari auth.users
          const { error: insertError } = await supabase
            .from('partners')
            .insert([{
              full_name: partnerData.nama || partnerData.full_name || 'Partner Tanpa Nama',
              email: partnerData.email,
              whatsapp: partnerData.whatsapp || partnerData.phone,
              referral_code: generatedCode,
              status: 'pending'
            }]);
          
          if (insertError) {
            // Jika gagal insert (misal FK constraint), tidak apa-apa
            // Data partner akan dibuat saat admin approve via rpc_activate_partner
            console.warn("Gagal pre-insert partner (akan dibuat saat admin approve):", insertError.message);
          } else {
            console.log("Pre-insert partner berhasil dengan status pending.");
          }
        }
      }

      setRefCode(generatedCode);
      setIsSuccess(true);
    } catch (err) {
      alert("Gagal memproses persetujuan: " + (err.message || "Error tidak diketahui"));
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
        <div className="text-orange-500 animate-pulse font-mono tracking-widest text-sm">LOADING AGREEMENT...</div>
      </div>
    );
  }

  if (!partnerData && !loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex flex-col items-center justify-center p-6 text-center">
        <h2 className="text-2xl font-bold text-white mb-4">Link Tidak Valid</h2>
        <p className="text-zinc-500 max-w-md">Mohon maaf, tautan persetujuan partner tidak ditemukan atau sudah kedaluwarsa.</p>
        <a href="/" className="mt-8 text-orange-500 font-bold border-b border-orange-500">Kembali ke Beranda</a>
      </div>
    );
  }

  return (
    <div className="agreement-page bg-[#0A0A0A] text-white font-['Barlow',sans-serif] min-h-screen relative overflow-x-hidden">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=Barlow:wght@300;400;500;600&display=swap');
        
        :root {
          --black: #0A0A0A;
          --black-2: #111111;
          --black-3: #1A1A1A;
          --black-4: #222222;
          --orange: #F5A300;
          --orange-dim: #C48200;
          --orange-glow: rgba(245,163,0,0.15);
          --orange-glow-sm: rgba(245,163,0,0.08);
          --white: #FFFFFF;
          --gray: #888888;
          --gray-dim: #555555;
          --green: #22C55E;
          --green-bg: rgba(34,197,94,0.1);
          --red: #EF4444;
        }

        .agreement-page::before {
          content: '';
          position: fixed;
          inset: 0;
          background-image:
            linear-gradient(rgba(245,163,0,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(245,163,0,0.04) 1px, transparent 1px);
          background-size: 48px 48px;
          pointer-events: none;
          z-index: 0;
        }

        .agreement-page::after {
          content: '';
          position: fixed;
          top: -30%;
          left: 50%;
          transform: translateX(-50%);
          width: 900px;
          height: 500px;
          background: radial-gradient(ellipse, rgba(245,163,0,0.08) 0%, transparent 70%);
          pointer-events: none;
          z-index: 0;
        }

        .section-title::after {
          content: '';
          flex: 1;
          height: 1px;
          background: linear-gradient(90deg, rgba(245,163,0,0.3), transparent);
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }

        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(24px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .hero { animation: fadeUp 0.8s ease both; }
        .section { animation: fadeUp 0.8s ease both; }
      `}</style>

      {/* HEADER */}
      <header className="relative z-10 flex items-center justify-between px-6 md:px-12 py-5 border-b border-[rgba(245,163,0,0.15)] bg-[rgba(10,10,10,0.9)] backdrop-blur-xl sticky top-0">
        <div className="header-logo">
          <span className="font-['Barlow_Condensed',sans-serif] font-black text-2xl text-[#F5A300] tracking-wider">⚡ TOKCER AI</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[rgba(245,163,0,0.08)] border border-[rgba(245,163,0,0.25)] font-['Barlow_Condensed',sans-serif] font-semibold text-[10px] md:text-xs tracking-widest uppercase text-[#F5A300]">
          <span className="w-1.5 h-1.5 bg-[#22C55E] rounded-full shadow-[0_0_6px_#22C55E] animate-[pulse_2s_infinite]"></span>
          Partner Agreement
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="relative z-10 max-w-3xl mx-auto px-6 py-16 md:py-20 pb-32">
        
        {/* HERO */}
        <div className="hero text-center mb-16">
          <div className="inline-block font-['Barlow_Condensed',sans-serif] font-bold text-[11px] tracking-[0.2em] uppercase text-[#F5A300] bg-[rgba(245,163,0,0.08)] border border-[rgba(245,163,0,0.2)] px-3 py-1.5 rounded mb-5">Langkah Terakhir</div>
          <h1 className="font-['Barlow_Condensed',sans-serif] font-black text-4xl md:text-5xl lg:text-[52px] leading-[1.05] tracking-tight mb-4">Baca & Setujui<br /><span className="text-[#F5A300]">Skema Komisi</span></h1>
          <p className="text-[15px] text-zinc-400 leading-relaxed max-w-lg mx-auto">Baca seluruh skema komisi di bawah ini. Setelah kamu klik <em>"Saya Setuju"</em>, partner link dan Partner Portal kamu langsung aktif.</p>
        </div>

        {/* IDENTITY BOX (DYNAMIC) */}
        <div className="section mb-10">
          <div className="flex items-center gap-2 font-['Barlow_Condensed',sans-serif] font-extrabold text-[13px] tracking-[0.18em] uppercase text-[#F5A300] mb-4 section-title">Identitas Partner</div>
          <div className="bg-[#1A1A1A] border border-[rgba(245,163,0,0.15)] rounded-xl p-5 md:p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-[11px] uppercase tracking-widest text-zinc-500 font-['Barlow_Condensed',sans-serif] font-semibold">Nama Lengkap</label>
              <div className="text-[15px] text-white font-medium">{partnerData.nama || 'Partner Name'}</div>
            </div>
            <div className="space-y-1">
              <label className="text-[11px] uppercase tracking-widest text-zinc-500 font-['Barlow_Condensed',sans-serif] font-semibold">Email Terdaftar</label>
              <div className="text-[15px] text-white font-medium">{partnerData.email || 'partner@email.com'}</div>
            </div>
            <div className="space-y-1">
              <label className="text-[11px] uppercase tracking-widest text-zinc-500 font-['Barlow_Condensed',sans-serif] font-semibold">Niche Konten</label>
              <div className="text-[15px] text-[#F5A300] font-bold uppercase tracking-wide">{partnerData.niche || 'N/A'}</div>
            </div>
            <div className="space-y-1">
              <label className="text-[11px] uppercase tracking-widest text-zinc-500 font-['Barlow_Condensed',sans-serif] font-semibold">No. WhatsApp</label>
              <div className="text-[15px] text-white font-medium">{partnerData.phone || '08123xxx'}</div>
            </div>
          </div>
        </div>

        {/* A. REVENUE SHARE */}
        <div className="section mb-10">
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
                  {['pro', 'elite', 'ultimate'].map((plan) => {
                    const r = commissionRates[plan] || {};
                    const fmt = (v) => v >= 1000 ? `Rp ${(v/1000).toFixed(v % 1000 === 0 ? 0 : 1)}K` : `Rp ${v}`;
                    return (
                      <tr key={plan} className="hover:bg-[rgba(245,163,0,0.03)] transition-colors">
                        <td className="px-4 py-3 font-semibold text-white capitalize">{plan}</td>
                        <td className="px-4 py-3 text-zinc-400">{fmt(r.bronze || 0)}</td>
                        <td className="px-4 py-3 text-zinc-400">{fmt(r.silver || 0)}</td>
                        <td className="px-4 py-3 text-zinc-400">{fmt(r.gold || 0)}</td>
                        <td className="px-4 py-3 text-[#F5A300] font-bold">{fmt(r.platinum || 0)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
          <p className="text-[11px] text-zinc-500 mt-3 px-1 leading-relaxed italic">
            ↳ Komisi dibayar selama subscriber aktif. Jika subscriber cancel → komisi berhenti setelah anniversary date mereka. Zero clawback.
          </p>
        </div>

        {/* A2. TIER CRITERIA */}
        <div className="section mb-10">
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
                    <td className="px-4 py-3"><span className="inline-flex px-2 py-0.5 rounded border bg-zinc-800 text-zinc-400 border-zinc-700 font-['Barlow_Condensed',sans-serif] font-bold text-[10px]">Starter</span></td>
                    <td className="px-4 py-3">≥ 1 closing</td>
                    <td className="px-4 py-3 text-zinc-700">—</td>
                    <td className="px-4 py-3 text-[12px] text-zinc-600">Tanggal 1 tiap bulan</td>
                  </tr>
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
        <div className="section mb-12">
          <div className="flex items-center gap-2 font-['Barlow_Condensed',sans-serif] font-extrabold text-[13px] tracking-[0.18em] uppercase text-[#F5A300] mb-4 section-title">B — Performance Bonus (6 Komponen)</div>
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
        <div className="section mb-12">
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

        <div className="h-px bg-gradient-to-r from-transparent via-[rgba(255,255,255,0.06)] to-transparent my-10"></div>

        {/* AGREEMENT FORM */}
        <div className="section mt-10">
          <div className="flex items-center gap-2 font-['Barlow_Condensed',sans-serif] font-extrabold text-[13px] tracking-[0.18em] uppercase text-[#F5A300] mb-4 section-title">Persetujuan</div>

          <div className="bg-gradient-to-br from-[rgba(245,163,0,0.06)] to-[rgba(245,163,0,0.02)] border border-[rgba(245,163,0,0.25)] rounded-2xl p-7 md:p-8 mb-6 shadow-2xl">
            <p className="text-sm text-zinc-400 leading-relaxed mb-6">
              Dengan mencentang kotak di bawah dan mengklik tombol <strong className="text-white">Saya Setuju & Aktifkan Akun</strong>, kamu menyatakan bahwa kamu telah membaca, memahami, dan menyetujui seluruh skema komisi dan aturan Tokcer AI Partner Program yang tertera di atas. Persetujuan ini bersifat <strong className="text-white">mengikat secara digital</strong> (setara PKS digital) dan dicatat beserta timestamp serta alamat IP kamu.
            </p>

            <label className="flex items-start gap-4 cursor-pointer select-none group" htmlFor="agreeCheck">
              <input 
                type="checkbox" 
                id="agreeCheck" 
                className="hidden" 
                checked={agreed} 
                onChange={() => setAgreed(!agreed)} 
              />
              <div className={`flex-shrink-0 w-6 h-6 border-2 rounded-md flex items-center justify-center mt-0.5 transition-all duration-200 ${agreed ? 'bg-[#F5A300] border-[#F5A300]' : 'bg-[#1A1A1A] border-zinc-700'}`}>
                {agreed && <span className="text-[#0A0A0A] font-black text-sm">✓</span>}
              </div>
              <span className="text-[14px] text-zinc-200 leading-relaxed group-hover:text-white transition-colors">
                ✅ Saya sudah membaca dan menyetujui <strong className="text-[#F5A300]">Skema Komisi Tokcer AI Partner Program</strong>, termasuk semua aturan dan ketentuan yang berlaku.
              </span>
            </label>
          </div>

          <button 
            onClick={handleSubmit}
            disabled={!agreed || isSubmitting}
            className="group relative flex items-center justify-center gap-3 w-full py-5 bg-[#F5A300] disabled:bg-[#222222] text-[#0A0A0A] disabled:text-zinc-600 font-['Barlow_Condensed',sans-serif] font-black text-xl tracking-widest uppercase rounded-xl transition-all duration-300 disabled:cursor-not-allowed hover:bg-[#FFB800] hover:-translate-y-1 hover:shadow-[0_8px_32_rgba(245,163,0,0.3)] active:translate-y-0 shadow-lg"
          >
            {isSubmitting ? (
               <span className="flex items-center gap-2">
                 <svg className="animate-spin h-5 w-5 text-[#0A0A0A]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                 Memproses...
               </span>
            ) : (
              <>
                <span>Saya Setuju & Aktifkan Akun</span>
                <span className="text-2xl group-hover:translate-x-1.5 transition-transform">→</span>
              </>
            )}
          </button>

          <p className="text-center text-[12px] text-zinc-600 mt-5 font-medium">
            🔒 Data kamu dienkripsi dan disimpan secara aman. Timestamp dan IP dicatat untuk verifikasi digital.
          </p>
        </div>

      </main>

      {/* FOOTER */}
      <footer className="relative z-10 text-center py-10 px-6 border-t border-[rgba(255,255,255,0.05)] text-[12px] text-zinc-600">
        <strong className="text-white tracking-wide">⚡ Tokcer AI</strong> &nbsp;·&nbsp; tokcer-ai.com &nbsp;·&nbsp; Affiliator Program v3 &nbsp;·&nbsp; April 2026<br />
        <div className="mt-3 flex items-center justify-center gap-3">
          <a href="/" className="text-[#F5A300] hover:text-[#FFB800] transition-colors">Kembali ke Website</a>
          <span className="text-zinc-800">·</span>
          <a href="#" className="text-zinc-600 hover:text-white transition-colors">Privasi</a>
          <span className="text-zinc-800">·</span>
          <a href="#" className="text-zinc-600 hover:text-white transition-colors">Syarat & Ketentuan</a>
        </div>
      </footer>

      {/* SUCCESS OVERLAY (Dipindah ke paling bawah agar tidak tertimpa z-index) */}
      {isSuccess && (
        <div className="fixed inset-0 bg-[rgba(10,10,10,0.95)] z-[9999] flex flex-col items-center justify-center text-center p-10 animate-in fade-in duration-500">
          <div className="w-20 h-20 bg-[rgba(34,197,94,0.1)] border-2 border-[#22C55E] rounded-full flex items-center justify-center text-4xl mb-6 scale-in duration-500">✓</div>
          <h2 className="font-['Barlow_Condensed',sans-serif] font-black text-4xl mb-3">Welcome, <span className="text-[#F5A300]">Partner!</span></h2>
          <p className="text-sm text-zinc-400 max-w-md leading-relaxed">Agreement kamu sudah tercatat. Partner link & Partner Portal akan dikirim ke Email kamu dalam beberapa menit.</p>
          <div className="font-['Barlow_Condensed',sans-serif] font-bold text-sm tracking-widest text-[#F5A300] bg-[rgba(245,163,0,0.08)] border border-[rgba(245,163,0,0.2)] px-4 py-2 rounded-lg mt-6 uppercase">REF: {refCode}</div>
          <p className="text-[10px] text-zinc-600 mt-6 italic">Timestamp & data kamu sudah disimpan secara aman.</p>
        </div>
      )}
    </div>
  );
};

export default PartnerAgreement;
