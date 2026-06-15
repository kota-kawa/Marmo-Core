import React from 'react';
import { useLandingTranslation } from '../../hooks/useLandingTranslation.js';
import partnerN from '../../assets/partner_n.png';
import partnerLbs from '../../assets/partner_lbs.png';

const AboutUs = () => {
  const { t } = useLandingTranslation();

  return (
    <>
      <section id="about-us-hero" className="w-full max-w-3xl mx-auto px-6 pt-16 pb-16 md:pt-24 md:pb-20 text-center border-t border-zinc-800">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900 border border-zinc-800 mb-8">
          <span className="flex h-2 w-2 rounded-full bg-orange-500 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
          </span>
          <span className="text-xs font-medium text-zinc-300 uppercase tracking-widest">{t('aboutHeroBadge')}</span>
        </div>
        
        <h2 className="text-4xl md:text-5xl lg:text-6xl font-semibold tracking-tighter text-white mb-6 leading-tight">
          {t('aboutHeroTitle1')}<span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-amber-400">{t('aboutHeroTitle2')}</span>{t('aboutHeroTitle3')}
        </h2>
        
        <p className="text-base md:text-lg text-zinc-400 max-w-xl mx-auto leading-relaxed">
          {t('aboutHeroDesc')}
        </p>
      </section>
      
      <section id="about-us-story" className="w-full max-w-3xl mx-auto px-6 py-16 border-t border-zinc-800">
        <p className="text-xs font-medium text-zinc-500 uppercase tracking-widest mb-8 flex items-center gap-2">
          <iconify-icon icon="solar:lightbulb-linear" className="text-base"></iconify-icon>
          {t('aboutStoryTag')}
        </p>
        <p className="text-base md:text-lg text-zinc-300 leading-relaxed">
          {t('aboutStoryDesc1')}<strong className="font-semibold text-white">{t('aboutStoryDesc2')}</strong>{t('aboutStoryDesc3')}<strong className="font-semibold text-white">{t('aboutStoryDesc4')}</strong>
        </p>
      </section>
      
      <section id="about-us-vision" className="w-full max-w-3xl mx-auto px-6 py-16 border-t border-zinc-800">
        <div className="mb-16">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-widest mb-6 flex items-center gap-2">
            <iconify-icon icon="solar:target-linear" className="text-base"></iconify-icon>
            {t('aboutVisionTag')}
          </p>
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 md:p-8 shadow-sm relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-orange-950/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <p className="text-base md:text-lg text-zinc-100 leading-relaxed relative z-10">
              {t('aboutVisionDesc')}
            </p>
          </div>
        </div>
    
        <div>
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-widest mb-6 flex items-center gap-2">
            <iconify-icon icon="solar:rocket-linear" className="text-base"></iconify-icon>
            {t('aboutMissionTag')}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 hover:border-orange-500/50 hover:shadow-sm transition-all duration-300">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-medium text-orange-500 bg-orange-950/50 px-2.5 py-1 rounded-md border border-orange-900/50">01</span>
                <iconify-icon icon="solar:chat-square-code-linear" className="text-zinc-500 text-lg"></iconify-icon>
              </div>
              <p className="text-sm text-zinc-300 leading-relaxed">
                {t('aboutMission1')}
              </p>
            </div>
    
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 hover:border-orange-500/50 hover:shadow-sm transition-all duration-300">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-medium text-orange-500 bg-orange-950/50 px-2.5 py-1 rounded-md border border-orange-900/50">02</span>
                <iconify-icon icon="solar:magic-stick-3-linear" className="text-zinc-500 text-lg"></iconify-icon>
              </div>
              <p className="text-sm text-zinc-300 leading-relaxed">
                {t('aboutMission2')}
              </p>
            </div>
    
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 hover:border-orange-500/50 hover:shadow-sm transition-all duration-300">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-medium text-orange-500 bg-orange-950/50 px-2.5 py-1 rounded-md border border-orange-900/50">03</span>
                <iconify-icon icon="solar:chart-line-up-linear" className="text-zinc-500 text-lg"></iconify-icon>
              </div>
              <p className="text-sm text-zinc-300 leading-relaxed">
                {t('aboutMission3')}
              </p>
            </div>
    
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 hover:border-orange-500/50 hover:shadow-sm transition-all duration-300">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-medium text-orange-500 bg-orange-950/50 px-2.5 py-1 rounded-md border border-orange-900/50">04</span>
                <iconify-icon icon="solar:layers-linear" className="text-zinc-500 text-lg"></iconify-icon>
              </div>
              <p className="text-sm text-zinc-300 leading-relaxed">
                {t('aboutMission4')}
              </p>
            </div>
          </div>
        </div>
      </section>
      
      <section id="about-us-team" className="w-full max-w-3xl mx-auto px-6 py-16 border-t border-zinc-800">
        <p className="text-xs font-medium text-zinc-500 uppercase tracking-widest mb-8 flex items-center gap-2">
          <iconify-icon icon="solar:users-group-rounded-linear" className="text-base"></iconify-icon>
          {t('aboutTeamTag')}
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 md:p-8 flex flex-col items-center text-center">
             <a href="https://www.linkedin.com/in/rickyprasetya/" target="_blank" rel="noreferrer" className="inline-flex items-center justify-center px-2.5 py-1 rounded-md bg-zinc-800 border border-zinc-700 text-[10px] font-medium text-zinc-300 mb-4 uppercase tracking-widest hover:bg-zinc-700 hover:text-white transition-colors duration-300">
              Product Architect
            </a>
            
            <h3 className="text-base font-semibold text-white tracking-tight mb-1">Ricky Prasetya</h3>
            <p className="text-xs text-zinc-500 mb-4">Founder</p>
            <p className="text-sm text-zinc-400 leading-relaxed">
              {t('aboutTeamFounderRole')}
            </p>
          </div>
    
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 md:p-8 flex flex-col items-center text-center">
            <a href="https://www.linkedin.com/in/iman-salqaura-63b1b4b4/" target="_blank" rel="noreferrer" className="inline-flex items-center justify-center px-2.5 py-1 rounded-md bg-zinc-800 border border-zinc-700 text-[10px] font-medium text-zinc-300 mb-4 uppercase tracking-widest hover:bg-zinc-700 hover:text-white transition-colors duration-300">
              Product Executor
            </a>
            <h3 className="text-base font-semibold text-white tracking-tight mb-1">Iman Salqaura</h3>
            <p className="text-xs text-zinc-500 mb-4">Chief Technology Officer</p>
            <p className="text-sm text-zinc-400 leading-relaxed">
              {t('aboutTeamCTORole')}
            </p>
          </div>
        </div>
      </section>
      
      <section id="about-us-partners" className="w-full max-w-3xl mx-auto px-6 py-16 border-t border-zinc-800">
        <p className="text-xs font-medium text-zinc-500 uppercase tracking-widest mb-8 flex items-center gap-2">
          <iconify-icon icon="solar:handshake-linear" className="text-base"></iconify-icon>
          {t('aboutPartnersTag')}
        </p>
        
        {/* Infinite scrolling marquee container */}
        <div className="relative w-full overflow-hidden py-4 mask-gradient">
          <style>{`
            @keyframes marquee {
              0% { transform: translateX(0); }
              100% { transform: translateX(-50%); }
            }
            .animate-marquee {
              display: flex;
              width: max-content;
              animation: marquee 15s linear infinite;
            }
            .animate-marquee:hover {
              animation-play-state: paused;
            }
            .mask-gradient {
              mask-image: linear-gradient(to right, transparent, white 20%, white 80%, transparent);
              -webkit-mask-image: linear-gradient(to right, transparent, white 20%, white 80%, transparent);
            }
          `}</style>
          
          <div className="animate-marquee flex gap-16 items-center">
            {/* Slide group 1 */}
            <div className="flex gap-16 items-center justify-around shrink-0 min-w-full">
              <div className="h-12 flex items-center justify-center transition-all duration-300 hover:scale-[1.05]">
                <img src={partnerN} alt="Partner Node" className="h-9 md:h-10 object-contain" />
              </div>
              <div className="h-12 flex items-center justify-center transition-all duration-300 hover:scale-[1.05]">
                <img src={partnerLbs} alt="Partner LBS" className="h-8 md:h-9 object-contain" />
              </div>
            </div>
            {/* Slide group 2 (Duplicate for infinite seamless scrolling) */}
            <div className="flex gap-16 items-center justify-around shrink-0 min-w-full" aria-hidden="true">
              <div className="h-12 flex items-center justify-center transition-all duration-300 hover:scale-[1.05]">
                <img src={partnerN} alt="Partner Node" className="h-9 md:h-10 object-contain" />
              </div>
              <div className="h-12 flex items-center justify-center transition-all duration-300 hover:scale-[1.05]">
                <img src={partnerLbs} alt="Partner LBS" className="h-8 md:h-9 object-contain" />
              </div>
            </div>
          </div>
        </div>
      </section>
      
      <section id="about-us-footer" className="w-full max-w-3xl mx-auto px-6 pt-8 pb-12 text-center flex flex-col items-center">
        <div className="flex gap-2 text-zinc-600 mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-zinc-600"></span>
          <span className="w-1.5 h-1.5 rounded-full bg-zinc-600"></span>
          <span className="w-1.5 h-1.5 rounded-full bg-zinc-600"></span>
        </div>
        <p className="text-sm md:text-base text-zinc-500 leading-relaxed max-w-md">
          {t('aboutFooterDesc1')}<strong className="font-semibold text-white">{t('aboutFooterDesc2')}</strong>{t('aboutFooterDesc3')}
        </p>
      </section>
    </>
  );
};

export default AboutUs;
