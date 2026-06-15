import React from 'react';
import { useLandingTranslation } from '../../hooks/useLandingTranslation.js';

const Testimonial = () => {
  const { t } = useLandingTranslation();

  return (
    <section className="max-w-7xl mx-auto px-6 py-16 md:py-24 border-t border-zinc-800 relative">
      <div className="text-center mb-12 md:mb-16">
        <h2 className="text-3xl md:text-4xl font-semibold text-white tracking-tighter">
          {t('testiTitle')}
        </h2>
        <p className="text-zinc-400 mt-4 text-base font-normal">
          {t('testiDesc')}
        </p>
      </div>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 relative z-10">
        <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-2xl flex flex-col justify-between hover:border-orange-500/50 transition-colors shadow-sm">
          <p className="text-zinc-300 text-sm mb-6 leading-relaxed">
            {t('testi1Quote')}
          </p>
          <div className="flex items-center gap-3 mt-auto">
            <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-xs font-semibold text-zinc-300 border border-zinc-700 shrink-0">AR</div>
            <div>
              <div className="text-sm font-medium text-white">{t('testi1Author')}</div>
              <div className="text-xs text-zinc-500">{t('testi1Role')}</div>
            </div>
          </div>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-2xl flex flex-col justify-between hover:border-orange-500/50 transition-colors shadow-sm">
          <p className="text-zinc-300 text-sm mb-6 leading-relaxed">
            {t('testi2Quote')}
          </p>
          <div className="flex items-center gap-3 mt-auto">
            <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-xs font-semibold text-zinc-300 border border-zinc-700 shrink-0">DK</div>
            <div>
              <div className="text-sm font-medium text-white">{t('testi2Author')}</div>
              <div className="text-xs text-zinc-500">{t('testi2Role')}</div>
            </div>
          </div>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-2xl flex flex-col justify-between hover:border-orange-500/50 transition-colors shadow-sm">
          <p className="text-zinc-300 text-sm mb-6 leading-relaxed">
            {t('testi3Quote')}
          </p>
          <div className="flex items-center gap-3 mt-auto">
            <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-xs font-semibold text-zinc-300 border border-zinc-700 shrink-0">CW</div>
            <div>
              <div className="text-sm font-medium text-white">{t('testi3Author')}</div>
              <div className="text-xs text-zinc-500">{t('testi3Role')}</div>
            </div>
          </div>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-2xl flex flex-col justify-between hover:border-orange-500/50 transition-colors shadow-sm">
          <p className="text-zinc-300 text-sm mb-6 leading-relaxed">
            {t('testi4Quote')}
          </p>
          <div className="flex items-center gap-3 mt-auto">
            <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-xs font-semibold text-zinc-300 border border-zinc-700 shrink-0">BS</div>
            <div>
              <div className="text-sm font-medium text-white">{t('testi4Author')}</div>
              <div className="text-xs text-zinc-500">{t('testi4Role')}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Testimonial;
