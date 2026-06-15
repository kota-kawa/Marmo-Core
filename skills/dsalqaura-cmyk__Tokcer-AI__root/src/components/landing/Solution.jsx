import React from 'react';
import { useLandingTranslation } from '../../hooks/useLandingTranslation.js';

const Solution = () => {
  const { t } = useLandingTranslation();

  return (
    <section className="max-w-7xl mx-auto px-6 py-16 md:py-24 border-t border-zinc-800 relative overflow-hidden">
      <div className="grid md:grid-cols-2 gap-12 md:gap-20 items-center">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-6 text-xs font-medium tracking-widest text-orange-500 uppercase bg-orange-950/30 border border-orange-900/50 rounded-full">
            {t('solSubtitle')}
          </div>
          <h2 className="text-3xl md:text-4xl font-semibold text-white mb-6 tracking-tighter leading-tight">
            {t('solTitle1')}<br/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-amber-400">{t('solTitle2')}</span>
          </h2>
          <p className="text-zinc-400 text-base md:text-lg leading-relaxed mb-8 font-normal">
            {t('solDesc')}
          </p>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="border-l-2 border-orange-500 bg-gradient-to-r from-orange-950/30 to-transparent p-4 rounded-r-xl">
              <div className="text-2xl font-semibold text-white tracking-tight mb-1">3x</div>
              <div className="text-xs font-medium text-zinc-500 uppercase tracking-widest">
                {t('solStat1')}
              </div>
            </div>
            <div className="border-l-2 border-amber-500 bg-gradient-to-r from-amber-950/30 to-transparent p-4 rounded-r-xl">
              <div className="text-2xl font-semibold text-white tracking-tight mb-1">99%</div>
              <div className="text-xs font-medium text-zinc-500 uppercase tracking-widest">
                {t('solStat2')}
              </div>
            </div>
          </div>
        </div>
        
        <div className="relative group">
          <div className="absolute -inset-4 bg-gradient-to-l from-orange-900/20 to-amber-900/20 rounded-3xl blur-2xl opacity-50 group-hover:opacity-100 transition duration-700 -z-10"></div>
          
          <div className="w-full h-[350px] md:h-[450px] bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden shadow-xl flex flex-col group-hover:border-orange-500/50 transition-all duration-700 relative">
            <div className="h-12 md:h-14 border-b border-zinc-800 flex items-center px-4 md:px-6 justify-between bg-black shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-6 h-6 md:w-8 md:h-8 bg-orange-950/50 rounded flex items-center justify-center"><iconify-icon icon="solar:pie-chart-2-linear" className="text-orange-500 text-xs md:text-sm"></iconify-icon></div>
                <div className="w-20 md:w-24 h-2.5 md:h-3 bg-zinc-700 rounded-full"></div>
              </div>
              <div className="w-24 md:w-32 h-5 md:h-6 bg-zinc-800 rounded-full"></div>
            </div>
            <div className="flex-1 p-4 md:p-6 flex gap-4 md:gap-6 relative bg-zinc-900">
              <div className="w-12 md:w-24 flex flex-col gap-3 shrink-0">
                <div className="w-full h-6 md:h-8 bg-zinc-800 rounded-md"></div>
                <div className="w-full h-6 md:h-8 bg-zinc-800/50 rounded-md"></div>
                <div className="w-full h-6 md:h-8 bg-zinc-800/50 rounded-md"></div>
                <div className="w-full h-6 md:h-8 bg-zinc-800/50 rounded-md"></div>
              </div>
              
              <div className="flex-1 flex flex-col gap-3 md:gap-4 min-w-0">
                <div className="flex gap-3 md:gap-4 shrink-0">
                  <div className="flex-1 h-20 md:h-24 bg-zinc-900 border border-zinc-800 shadow-sm rounded-xl p-3 md:p-4 flex flex-col justify-between">
                    <div className="w-12 md:w-16 h-2 bg-zinc-700 rounded-full"></div>
                    <div className="w-20 md:w-24 h-4 md:h-6 bg-orange-500 rounded-full"></div>
                  </div>
                  <div className="flex-1 h-20 md:h-24 bg-zinc-900 border border-zinc-800 shadow-sm rounded-xl p-3 md:p-4 flex flex-col justify-between">
                    <div className="w-12 md:w-16 h-2 bg-zinc-700 rounded-full"></div>
                    <div className="w-20 md:w-24 h-4 md:h-6 bg-amber-500 rounded-full"></div>
                  </div>
                </div>
                <div className="flex-1 bg-zinc-900 border border-zinc-800 shadow-sm rounded-xl flex items-end p-3 md:p-4 gap-1 md:gap-2">
                  <div className="flex-1 bg-orange-900/50 rounded-t border-t border-orange-800 h-1/3"></div>
                  <div className="flex-1 bg-orange-800/80 rounded-t border-t border-orange-700 h-2/3"></div>
                  <div className="flex-1 bg-orange-900/50 rounded-t border-t border-orange-800 h-1/2"></div>
                  <div className="flex-1 bg-orange-500 rounded-t border-t-2 border-orange-400 h-full shadow-sm"></div>
                  <div className="flex-1 bg-orange-900/50 rounded-t border-t border-orange-800 h-[80%]"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Solution;
