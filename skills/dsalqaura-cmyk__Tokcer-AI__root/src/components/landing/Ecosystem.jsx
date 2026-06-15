import React from 'react';
import { useLandingTranslation } from '../../hooks/useLandingTranslation.js';

const Ecosystem = () => {
  const { t } = useLandingTranslation();

  return (
    <section id="ecosystem" className="max-w-7xl mx-auto px-6 py-16 md:py-24 border-t border-zinc-800 relative">
      <div className="text-center mb-12 md:mb-16">
        <h2 className="text-3xl md:text-4xl font-semibold text-white tracking-tighter">{t('ecoTitle1')}{t('ecoTitle2')}</h2>
        <p className="text-zinc-400 mt-4 text-base font-normal">
          {t('ecoDesc')}
        </p>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 relative z-10">
        <div className="group relative bg-zinc-900 border border-zinc-800 hover:border-orange-500/50 hover:shadow-md p-6 md:p-8 rounded-2xl flex flex-col items-center text-center gap-3 md:gap-4 transition-all hover:-translate-y-1 cursor-default">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-black group-hover:bg-orange-950/30 flex items-center justify-center transition-colors border border-zinc-800">
            <iconify-icon icon="solar:global-linear" className="text-xl md:text-2xl text-zinc-500 group-hover:text-orange-500 transition-colors"></iconify-icon>
          </div>
          <span className="text-xs md:text-sm font-medium text-white">Market Intel</span>
        </div>
        <div className="group relative bg-zinc-900 border border-zinc-800 hover:border-orange-500/50 hover:shadow-md p-6 md:p-8 rounded-2xl flex flex-col items-center text-center gap-3 md:gap-4 transition-all hover:-translate-y-1 cursor-default">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-black group-hover:bg-orange-950/30 flex items-center justify-center transition-colors border border-zinc-800">
            <iconify-icon icon="solar:settings-linear" className="text-xl md:text-2xl text-zinc-500 group-hover:text-orange-500 transition-colors"></iconify-icon>
          </div>
          <span className="text-xs md:text-sm font-medium text-white">Automation Core</span>
        </div>
        <div className="group relative bg-zinc-900 border border-zinc-800 hover:border-orange-500/50 hover:shadow-md p-6 md:p-8 rounded-2xl flex flex-col items-center text-center gap-3 md:gap-4 transition-all hover:-translate-y-1 cursor-default">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-black group-hover:bg-orange-950/30 flex items-center justify-center transition-colors border border-zinc-800">
            <iconify-icon icon="solar:crown-linear" className="text-xl md:text-2xl text-zinc-500 group-hover:text-orange-500 transition-colors"></iconify-icon>
          </div>
          <span className="text-xs md:text-sm font-medium text-white">Premium Support</span>
        </div>
        <div className="group relative bg-zinc-900 border border-zinc-800 hover:border-orange-500/50 hover:shadow-md p-6 md:p-8 rounded-2xl flex flex-col items-center text-center gap-3 md:gap-4 transition-all hover:-translate-y-1 cursor-default">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-black group-hover:bg-orange-950/30 flex items-center justify-center transition-colors border border-zinc-800">
            <iconify-icon icon="solar:shield-check-linear" className="text-xl md:text-2xl text-zinc-500 group-hover:text-orange-500 transition-colors"></iconify-icon>
          </div>
          <span className="text-xs md:text-sm font-medium text-white">Health Score</span>
        </div>
        <div className="group relative bg-zinc-900 border border-zinc-800 hover:border-orange-500/50 hover:shadow-md p-6 md:p-8 rounded-2xl flex flex-col items-center text-center gap-3 md:gap-4 transition-all hover:-translate-y-1 cursor-default">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-black group-hover:bg-orange-950/30 flex items-center justify-center transition-colors border border-zinc-800">
            <iconify-icon icon="solar:bell-bing-linear" className="text-xl md:text-2xl text-zinc-500 group-hover:text-orange-500 transition-colors"></iconify-icon>
          </div>
          <span className="text-xs md:text-sm font-medium text-white">Keyword Alert</span>
        </div>
        <div className="group relative bg-zinc-900 border border-zinc-800 hover:border-orange-500/50 hover:shadow-md p-6 md:p-8 rounded-2xl flex flex-col items-center text-center gap-3 md:gap-4 transition-all hover:-translate-y-1 cursor-default">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-black group-hover:bg-orange-950/30 flex items-center justify-center transition-colors border border-zinc-800">
            <iconify-icon icon="solar:graph-up-linear" className="text-xl md:text-2xl text-zinc-500 group-hover:text-orange-500 transition-colors"></iconify-icon>
          </div>
          <span className="text-xs md:text-sm font-medium text-white">Forecast Produk</span>
        </div>
        <div className="group relative bg-zinc-900 border border-zinc-800 hover:border-orange-500/50 hover:shadow-md p-6 md:p-8 rounded-2xl flex flex-col items-center text-center gap-3 md:gap-4 transition-all hover:-translate-y-1 cursor-default">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-black group-hover:bg-orange-950/30 flex items-center justify-center transition-colors border border-zinc-800">
            <iconify-icon icon="solar:refresh-circle-linear" className="text-xl md:text-2xl text-zinc-500 group-hover:text-orange-500 transition-colors"></iconify-icon>
          </div>
          <span className="text-xs md:text-sm font-medium text-white">Auto-Winback</span>
        </div>
        <div className="group relative bg-zinc-900 border border-zinc-800 hover:border-orange-500/50 hover:shadow-md p-6 md:p-8 rounded-2xl flex flex-col items-center text-center gap-3 md:gap-4 transition-all hover:-translate-y-1 cursor-default">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-black group-hover:bg-orange-950/30 flex items-center justify-center transition-colors border border-zinc-800">
            <iconify-icon icon="solar:chat-round-line-linear" className="text-xl md:text-2xl text-zinc-500 group-hover:text-orange-500 transition-colors"></iconify-icon>
          </div>
          <span className="text-xs md:text-sm font-medium text-white">WA Integration</span>
        </div>
      </div>
    </section>
  );
};

export default Ecosystem;
