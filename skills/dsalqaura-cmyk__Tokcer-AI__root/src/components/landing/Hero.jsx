import React from 'react';
import DashboardPreview from './DashboardPreview';
import { useLandingTranslation } from '../../hooks/useLandingTranslation.js';

const Hero = () => {
  const { t } = useLandingTranslation();

  return (
    <header className="relative pt-28 pb-16 md:pt-40 md:pb-32 px-6 overflow-hidden">
      {/* Floating Decorative Elements */}
      <div className="absolute bottom-1/4 right-[5%] animate-bounce duration-[4000ms] opacity-20 hidden lg:block">
        <div className="w-20 h-20 bg-orange-500/10 rounded-3xl -rotate-12 flex items-center justify-center border border-orange-500/20 shadow-2xl">
          <iconify-icon icon="simple-icons:shopee" className="text-4xl text-orange-500"></iconify-icon>
        </div>
      </div>

      <div className="max-w-4xl mx-auto text-center mb-20 relative z-10">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 backdrop-blur-md border border-white/10 mb-8 animate-in fade-in slide-in-from-top-4 duration-1000">
          <span className="flex h-2 w-2 rounded-full bg-orange-500 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
          </span>
          <span className="text-[10px] font-black text-zinc-300 uppercase tracking-[0.2em]">{t('heroBadge')}</span>
        </div>
        
        <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold text-white mb-8 leading-[0.9] tracking-tighter animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-100">
          {t('heroTitle1')}<br/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-600 via-amber-400 to-orange-500">{t('heroTitle2')}</span>
        </h1>
        
        <p className="text-zinc-400 text-lg md:text-xl max-w-2xl mx-auto mb-12 leading-relaxed font-normal animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-200">
          {t('heroDesc')}
        </p>

        {/* <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-300">
           <button className="px-8 py-4 bg-orange-600 hover:bg-orange-500 text-white rounded-2xl font-bold text-sm shadow-xl shadow-orange-600/20 transition-all hover:scale-105 active:scale-95">
              Mulai Sekarang — Gratis
           </button>
           <button className="px-8 py-4 bg-zinc-900 hover:bg-zinc-800 text-white border border-zinc-800 rounded-2xl font-bold text-sm transition-all flex items-center gap-2">
              <iconify-icon icon="solar:play-circle-bold" className="text-xl text-orange-500"></iconify-icon>
              Lihat Demo Video
           </button>
        </div> */}
      </div>

      <div id="dashboard" className="max-w-6xl mx-auto relative group z-10">
        <DashboardPreview />
      </div>
    </header>
  );
};

export default Hero;
