import React from 'react';
import { useLandingTranslation } from '../../hooks/useLandingTranslation.js';

const WaitlistCTA = ({ onOpenWaitlist }) => {
  const { t } = useLandingTranslation();

  return (
    <section className="max-w-5xl mx-auto px-6 py-16 md:py-24 text-center relative border-t border-zinc-800">
      <div className="relative rounded-[2rem] md:rounded-[2.5rem] border border-orange-900/50 bg-gradient-to-br from-orange-950/40 to-zinc-900 p-8 md:p-20 overflow-hidden shadow-xl">
        <h2 className="text-3xl md:text-5xl font-semibold text-white mb-4 md:mb-6 tracking-tighter relative z-10">
          {t('ctaTitle')}
        </h2>
        <p className="text-zinc-400 mb-8 md:mb-10 max-w-xl mx-auto text-sm md:text-base font-normal relative z-10 leading-relaxed">
          {t('ctaDesc')}
        </p>
        
        <button onClick={onOpenWaitlist} className="inline-flex items-center justify-center gap-3 w-full md:w-auto bg-orange-600 text-white px-8 py-4 rounded-full text-sm font-medium hover:bg-orange-500 transition-all hover:scale-105 active:scale-95 shadow-lg relative z-10 border border-orange-500">
          {t('ctaBtn')}
          <iconify-icon icon="solar:arrow-right-linear" className="text-lg"></iconify-icon>
        </button>
      </div>
    </section>
  );
};

export default WaitlistCTA;
