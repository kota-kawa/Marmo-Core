import React from 'react';
import { useLandingTranslation } from '../../hooks/useLandingTranslation.js';

const Problem = () => {
  const { t } = useLandingTranslation();

  return (
    <section id="problem" className="max-w-7xl mx-auto px-6 py-16 md:py-24 relative">
      <div className="grid md:grid-cols-2 gap-10 md:gap-20 items-center border-t border-zinc-800 pt-16 md:pt-24">
        
        <div className="relative group order-2 md:order-1 w-full aspect-[4/3] md:aspect-auto md:h-[400px] rounded-2xl border border-zinc-800 bg-zinc-900 overflow-hidden shadow-xl flex flex-col">
          <div className="absolute -inset-4 bg-gradient-to-r from-rose-900/20 to-orange-900/20 rounded-3xl blur-2xl opacity-50 group-hover:opacity-100 transition duration-700 -z-10"></div>
          <div className="w-full h-8 bg-zinc-800 border-b border-zinc-700 flex items-center px-4 gap-2 z-20 shrink-0">
            <div className="w-2.5 h-2.5 rounded-full bg-zinc-600"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-zinc-600"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-zinc-600"></div>
          </div>
          <div className="flex-1 relative bg-black overflow-hidden p-4 md:p-6 flex flex-col gap-4">
            <div className="w-full flex items-center justify-between opacity-70">
              <div className="w-24 md:w-32 h-3 bg-zinc-800 rounded-full"></div>
              <div className="flex gap-2">
                <div className="w-8 h-3 bg-zinc-800 rounded-full"></div>
                <div className="w-8 h-3 bg-zinc-800 rounded-full"></div>
              </div>
            </div>
            <div className="flex gap-3 md:gap-4 shrink-0">
              <div className="flex-1 bg-zinc-900 rounded-xl p-3 md:p-4 border border-zinc-800 shadow-sm relative overflow-hidden">
                <div className="w-8 h-8 bg-orange-950/50 rounded-lg mb-3 flex items-center justify-center"><iconify-icon icon="solar:chart-2-linear" className="text-orange-500 text-sm"></iconify-icon></div>
                <div className="w-16 md:w-20 h-2 bg-zinc-700 rounded-full mb-2"></div>
                <div className="w-10 md:w-14 h-3 md:h-4 bg-zinc-600 rounded-full"></div>
              </div>
              <div className="flex-1 bg-zinc-900 rounded-xl p-3 md:p-4 border border-zinc-800 shadow-sm relative overflow-hidden">
                <div className="w-8 h-8 bg-rose-950/50 rounded-lg mb-3 flex items-center justify-center"><iconify-icon icon="solar:graph-down-linear" className="text-rose-500 text-sm"></iconify-icon></div>
                <div className="w-16 md:w-20 h-2 bg-zinc-700 rounded-full mb-2"></div>
                <div className="w-10 md:w-14 h-3 md:h-4 bg-zinc-600 rounded-full"></div>
              </div>
            </div>
            <div className="flex-1 bg-zinc-900 rounded-xl border border-zinc-800 shadow-sm p-4 flex items-end gap-1.5 md:gap-3 relative overflow-hidden">
              <div className="w-full bg-rose-900/50 rounded-t border-t border-rose-800" style={{ height: '65%' }}></div>
              <div className="w-full bg-rose-800/80 rounded-t border-t border-rose-700" style={{ height: '45%' }}></div>
              <div className="w-full bg-orange-900/50 rounded-t border-t border-orange-800" style={{ height: '25%' }}></div>
              <div className="w-full bg-rose-900/50 rounded-t border-t border-rose-800" style={{ height: '50%' }}></div>
              <div className="w-full bg-orange-900/50 rounded-t border-t border-orange-800" style={{ height: '35%' }}></div>
              <div className="w-full bg-rose-800 rounded-t border-t-2 border-rose-600" style={{ height: '80%' }}></div>
            </div>
          </div>
          <div className="h-3 md:h-4 w-full bg-zinc-800 border-t border-zinc-700 z-20 relative shrink-0"></div>
        </div>

        <div className="order-1 md:order-2">
          <h2 className="text-3xl md:text-4xl font-semibold text-white mb-6 md:mb-8 tracking-tighter leading-tight">
            {t('probTitle1')} <span className="text-rose-500">{t('probTitle2')}</span>
          </h2>
          <div className="space-y-4 md:space-y-6">
            <div className="relative p-5 md:p-6 rounded-2xl border border-zinc-800 bg-zinc-900 shadow-sm hover:border-rose-900/50 transition-colors group">
              <div className="absolute top-0 left-0 w-1 h-full bg-rose-500 rounded-l-2xl"></div>
              <div className="flex gap-4">
                <div className="mt-1 text-rose-500 bg-rose-950/50 p-2 rounded-lg h-fit shrink-0 border border-rose-900/50"><iconify-icon icon="solar:document-text-linear" className="text-xl"></iconify-icon></div>
                <div>
                  <h3 className="text-base font-semibold text-white mb-2">{t('prob1Title')}</h3>
                  <p className="text-sm text-zinc-400 leading-relaxed font-normal">
                    {t('prob1Desc')}
                  </p>
                </div>
              </div>
            </div>
            <div className="relative p-5 md:p-6 rounded-2xl border border-zinc-800 bg-zinc-900 shadow-sm hover:border-orange-900/50 transition-colors group">
              <div className="absolute top-0 left-0 w-1 h-full bg-orange-500 rounded-l-2xl"></div>
              <div className="flex gap-4">
                <div className="mt-1 text-orange-500 bg-orange-950/50 p-2 rounded-lg h-fit shrink-0 border border-orange-900/50"><iconify-icon icon="solar:eye-closed-linear" className="text-xl"></iconify-icon></div>
                <div>
                  <h3 className="text-base font-semibold text-white mb-2">{t('prob2Title')}</h3>
                  <p className="text-sm text-zinc-400 leading-relaxed font-normal">
                    {t('prob2Desc')}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Problem;
