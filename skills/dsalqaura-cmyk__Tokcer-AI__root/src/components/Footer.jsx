import React from 'react';
import logo from '../assets/logo.png';
import { useLandingTranslation } from '../hooks/useLandingTranslation.js';

const Footer = () => {
  const { t } = useLandingTranslation();

  return (
    <footer className="border-t border-zinc-800 bg-black">
      <div className="max-w-7xl mx-auto px-6 py-10 md:py-14">
        <div className="flex flex-col md:flex-row justify-between items-start gap-8 mb-8">
          {/* Brand */}
          <div className="flex flex-col items-start gap-3">
            <img src={logo} alt="Tokcer AI" className="h-7 w-auto opacity-80 hover:opacity-100 transition-opacity" />
            <p className="text-xs font-normal text-zinc-500 max-w-xs leading-relaxed">{t('footerCopyright')}</p>
          </div>

          {/* Contact Us */}
          <div className="flex flex-col items-start md:items-center gap-2">
            <p className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-1">{t('footerContact')}</p>
            <a 
              href="mailto:helpdesk@tokcer-ai.com" 
              className="text-sm text-zinc-400 hover:text-orange-400 transition-colors flex items-center gap-2"
            >
              <iconify-icon icon="solar:letter-linear" className="text-base text-orange-500 shrink-0"></iconify-icon>
              helpdesk@tokcer-ai.com
            </a>
          </div>

          {/* Social & Links */}
          <div className="flex flex-col items-start md:items-end gap-5">
            <div className="flex items-center gap-4 text-zinc-400">
              <a href="https://www.threads.net/@tokcer.ai" target="_blank" rel="noreferrer" aria-label="Threads" className="hover:text-orange-500 hover:-translate-y-1 transition-all duration-300"><iconify-icon icon="ri:threads-fill" className="text-xl"></iconify-icon></a>
              <a href="https://www.facebook.com/people/Tokcer-AI/pfbid0Mkhk7baY3aFeZCszK1wnHHQKfjeo8g1xojppDEAs3XDPZFvtmQvxE1QXFPtMhVqjl/" target="_blank" rel="noreferrer" aria-label="Facebook" className="hover:text-orange-500 hover:-translate-y-1 transition-all duration-300"><iconify-icon icon="mdi:facebook" className="text-xl"></iconify-icon></a>
              <a href="https://www.tiktok.com/@tokcer.ai" target="_blank" rel="noreferrer" aria-label="TikTok" className="hover:text-orange-500 hover:-translate-y-1 transition-all duration-300"><iconify-icon icon="ri:tiktok-fill" className="text-xl"></iconify-icon></a>
              <a href="https://www.instagram.com/tokcer.ai/" target="_blank" rel="noreferrer" aria-label="Instagram" className="hover:text-orange-500 hover:-translate-y-1 transition-all duration-300"><iconify-icon icon="mdi:instagram" className="text-xl"></iconify-icon></a>
              <a href="https://www.youtube.com/@tokcer_AI" target="_blank" rel="noreferrer" aria-label="YouTube" className="hover:text-orange-500 hover:-translate-y-1 transition-all duration-300"><iconify-icon icon="mdi:youtube" className="text-xl"></iconify-icon></a>
            </div>
            
            <div className="flex flex-wrap justify-end gap-6 md:gap-8 text-[10px] font-bold uppercase tracking-widest text-zinc-500">
              <a href="/faq" className="hover:text-white transition-colors">FAQ</a>
              <a href="/privacy" className="hover:text-white transition-colors">{t('footerPrivacy')}</a>
              <a href="/terms" className="hover:text-white transition-colors">{t('footerTerms')}</a>
              <a href="/refund" className="hover:text-white transition-colors text-orange-500/80">Refund Policy</a>
            </div>
          </div>
        </div>

        <div className="border-t border-zinc-900 pt-6 text-center">
          <p className="text-xs text-zinc-600">© 2026 Tokcer AI. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
