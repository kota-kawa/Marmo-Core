import React, { useState } from 'react';
import { useLandingTranslation } from '../../hooks/useLandingTranslation.js';

const Pricing = ({ onOpenWaitlist }) => {
  const { t } = useLandingTranslation();
  const [isYearly, setIsYearly] = useState(false);

  const starterFeatures = [
    <><strong>50</strong> Generate Konten AI / Bulan</>,
    <>Integrasi <strong>1</strong> Toko Marketplace</>,
    <>Dashboard Analitik Seller Dasar</>,
    <>Generator Deskripsi Produk AI</>
  ];

  const proFeatures = [
    <><strong>300</strong> Generate Konten AI / Bulan</>,
    <>Integrasi <strong>3</strong> Toko Marketplace</>,
    <>Dashboard Analitik Seller Dasar</>,
    <>Generator Deskripsi Produk AI</>,
    <><strong>Generator Naskah Video TikTok & Reels</strong></>,
    <><strong>Fitur Health Check & Audit Toko</strong></>
  ];

  const eliteFeatures = [
    <><strong>1.000</strong> Generate Konten AI / Bulan</>,
    <>Maksimal Integrasi <strong>10</strong> Toko Marketplace</>,
    <><strong>Dashboard Analitik Seller Lengkap</strong></>,
    <>Generator Deskripsi Produk AI</>,
    <>Generator Naskah Video TikTok & Reels</>,
    <>Fitur Health Check & Audit Toko</>,
    <><strong>Riset Tren Produk Marketplace</strong></>,
    <><strong>Dukungan Prioritas (Fast Response)</strong></>
  ];

  const ultimateFeatures = [
    <><strong>Unlimited</strong> Generate Konten AI / Bulan</>,
    <>Integrasi Toko <strong>Unlimited</strong></>,
    <>Dashboard Analitik Seller Lengkap</>,
    <>Generator Deskripsi Produk AI</>,
    <>Generator Naskah Video TikTok & Reels</>,
    <>Fitur Health Check & Audit Toko</>,
    <>Riset Tren Produk Marketplace</>,
    <>Dukungan Prioritas (Fast Response)</>,
    <><strong>Laporan Analisis Kompetitor Mendalam</strong></>,
    <><strong>Akses Prioritas Fitur Beta & Update</strong></>
  ];

  return (
    <section id="pricing" className="max-w-7xl mx-auto px-4 sm:px-6 py-12 sm:py-16 md:py-24 border-t border-zinc-800 relative">
      <div className="text-center mb-12 md:mb-16">
        <h2 className="text-3xl md:text-4xl font-semibold text-white tracking-tighter mb-8">
          {t('pricingComingSoonTitle')}
        </h2>

        
        {/* Toggle Switch */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4">
          <span className={`text-sm font-bold ${!isYearly ? 'text-white' : 'text-zinc-500'}`}>Bulanan</span>
          <button 
            onClick={() => setIsYearly(!isYearly)}
            className="w-16 h-8 bg-zinc-800 rounded-full p-1 border border-zinc-700 relative transition-colors shrink-0"
          >
            <div className={`w-6 h-6 bg-orange-500 rounded-full shadow-md transition-all ${isYearly ? 'translate-x-8' : 'translate-x-0'}`}></div>
          </button>
          <span className={`text-sm font-bold flex items-center gap-2 ${isYearly ? 'text-white' : 'text-zinc-500'}`}>
            Tahunan
            <span className="bg-orange-500/20 text-orange-500 text-[9px] sm:text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full border border-orange-500/20">Hemat 1 Bulan</span>
          </span>
        </div>
      </div>

      <div className="relative">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 max-w-7xl mx-auto relative">
          {/* Glow effect background */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none -z-10">
            <div className="w-full h-full rounded-full bg-orange-600/5 blur-[120px]"></div>
          </div>

          {/* Card 1 - Starter */}
          <div className="relative bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-2xl sm:rounded-3xl p-5 sm:p-6 md:p-8 flex flex-col items-center text-center gap-4 sm:gap-6 group shadow-xl">
            <div className="w-12 h-12 rounded-2xl bg-zinc-800 flex items-center justify-center">
              <iconify-icon icon="solar:star-linear" className="text-2xl text-zinc-400"></iconify-icon>
            </div>
            <div>
              <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">Starter</p>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-3xl font-black text-white uppercase tracking-tighter">Gratis</span>
              </div>
            </div>
            <div className="w-full space-y-3 text-left">
              {starterFeatures.map((feat, i) => (
                <div key={i} className="flex items-center gap-3 text-xs text-zinc-500 font-medium">
                  <iconify-icon icon="solar:check-circle-bold" className="text-zinc-800 shrink-0"></iconify-icon>
                  <span>{feat}</span>
                </div>
              ))}
            </div>
            <button onClick={() => onOpenWaitlist('starter')} className="w-full py-4 bg-zinc-800 text-white text-[10px] font-black uppercase tracking-widest rounded-2xl border border-zinc-700 hover:bg-zinc-700 transition-all">Pilih Paket</button>
          </div>

          {/* Card 2 - Pro */}
          <div className="relative bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-2xl sm:rounded-3xl p-5 sm:p-6 md:p-8 flex flex-col items-center text-center gap-4 sm:gap-6 group shadow-xl">
            <div className="w-12 h-12 rounded-2xl bg-zinc-800 flex items-center justify-center">
              <iconify-icon icon="solar:box-linear" className="text-2xl text-zinc-400"></iconify-icon>
            </div>
            <div>
              <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">Pro Edition</p>
              <div className="flex flex-col items-center justify-center">
                <span className="text-xs font-bold text-zinc-600 line-through tracking-tighter">Rp {isYearly ? '7.139.000' : '649.000'}</span>
                <div className="flex items-baseline justify-center gap-1">
                  <span className="text-[10px] font-black text-zinc-600 mb-1">RP</span>
                  <span className="text-3xl font-black text-white tracking-tighter">{isYearly ? '5.489' : '499'}k</span>
                  <span className="text-zinc-500 text-[10px] font-black tracking-widest uppercase">/{isYearly ? 'THN' : 'BLN'}</span>
                </div>
              </div>
            </div>
            <div className="w-full space-y-3 text-left">
              {proFeatures.map((feat, i) => (
                <div key={i} className="flex items-center gap-3 text-xs text-zinc-400 font-medium">
                  <iconify-icon icon="solar:check-circle-bold" className="text-orange-500 shrink-0"></iconify-icon>
                  <span className="text-zinc-400">{feat}</span>
                </div>
              ))}
            </div>
            <button onClick={() => onOpenWaitlist('pro')} className="w-full py-4 bg-white text-black text-[10px] font-black uppercase tracking-widest rounded-2xl shadow-lg hover:scale-[1.02] transition-all">Beli Paket</button>
          </div>

          {/* Card 3 - Elite */}
          <div className="relative bg-orange-950/20 backdrop-blur-md border border-orange-500/30 rounded-2xl sm:rounded-3xl p-5 sm:p-6 md:p-8 flex flex-col items-center text-center gap-4 sm:gap-6 group shadow-2xl z-10">
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-orange-600 text-white text-[8px] font-black uppercase tracking-[0.2em] px-4 py-1.5 rounded-full shadow-lg">Most Popular</div>
            <div className="w-12 h-12 rounded-2xl bg-orange-600 flex items-center justify-center shadow-lg shadow-orange-600/30">
              <iconify-icon icon="solar:crown-bold" className="text-2xl text-white"></iconify-icon>
            </div>
            <div>
              <p className="text-[10px] font-black text-orange-500 uppercase tracking-widest mb-2">Elite Edition</p>
              <div className="flex flex-col items-center justify-center">
                <span className="text-xs font-bold text-orange-800/60 line-through tracking-tighter">Rp {isYearly ? '13.739.000' : '1.249.000'}</span>
                <div className="flex items-baseline justify-center gap-1">
                  <span className="text-[10px] font-black text-orange-800 mb-1">RP</span>
                  <span className="text-3xl font-black text-white tracking-tighter">{isYearly ? '10.989' : '999'}k</span>
                  <span className="text-orange-600 text-[10px] font-black tracking-widest uppercase">/{isYearly ? 'THN' : 'BLN'}</span>
                </div>
              </div>
            </div>
            <div className="w-full space-y-3 text-left">
              {eliteFeatures.map((feat, i) => (
                <div key={i} className="flex items-center gap-3 text-xs text-zinc-300 font-medium">
                  <iconify-icon icon="solar:check-circle-bold" className="text-orange-500 shrink-0"></iconify-icon>
                  <span className="text-zinc-300">{feat}</span>
                </div>
              ))}
            </div>
            <button onClick={() => onOpenWaitlist('elite')} className="w-full py-4 bg-orange-600 text-white text-[10px] font-black uppercase tracking-widest rounded-2xl shadow-xl shadow-orange-600/20 hover:bg-orange-500 transition-all">Beli Paket</button>
          </div>

          {/* Card 4 - Ultimate */}
          <div className="relative bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-2xl sm:rounded-3xl p-5 sm:p-6 md:p-8 flex flex-col items-center text-center gap-4 sm:gap-6 group shadow-xl">
            <div className="w-12 h-12 rounded-2xl bg-zinc-800 flex items-center justify-center">
              <iconify-icon icon="solar:magic-stick-3-bold" className="text-2xl text-zinc-400"></iconify-icon>
            </div>
            <div>
              <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">Ultimate Edition</p>
              <div className="flex flex-col items-center justify-center">
                <span className="text-xs font-bold text-zinc-600 line-through tracking-tighter">Rp {isYearly ? '27.489.000' : '2.499.000'}</span>
                <div className="flex items-baseline justify-center gap-1">
                  <span className="text-[10px] font-black text-zinc-600 mb-1">RP</span>
                  <span className="text-3xl font-black text-white tracking-tighter">{isYearly ? '21.989' : '1.999'}k</span>
                  <span className="text-zinc-500 text-[10px] font-black tracking-widest uppercase">/{isYearly ? 'THN' : 'BLN'}</span>
                </div>
              </div>
            </div>
            <div className="w-full space-y-3 text-left">
              {ultimateFeatures.map((feat, i) => (
                <div key={i} className="flex items-center gap-3 text-xs text-zinc-400 font-medium">
                  <iconify-icon icon="solar:check-circle-bold" className="text-orange-500 shrink-0"></iconify-icon>
                  <span className="text-zinc-400">{feat}</span>
                </div>
              ))}
            </div>
            <button onClick={() => onOpenWaitlist('ultimate')} className="w-full py-4 bg-orange-600 text-white text-[10px] font-black uppercase tracking-widest rounded-2xl shadow-xl shadow-orange-600/20 hover:bg-orange-500 transition-all">Beli Paket</button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Pricing;
