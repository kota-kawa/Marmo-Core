import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase.js';
import logo from '../assets/logo.png';
import { useLandingTranslation } from '../hooks/useLandingTranslation.js';

const Navbar = ({ onOpenPartner, onOpenWaitlist, onOpenDemo }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [pricingModalOpen, setPricingModalOpen] = useState(false);
  const navigate = useNavigate();
  const { lang, toggleLang, t } = useLandingTranslation();

  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [storeCount, setStoreCount] = useState(0);

  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen);
  };

  useEffect(() => {
    const fetchUserData = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        setUser(session.user);
        
        // Fetch Profile
        const { data: prof } = await supabase
          .from('profiles')
          .select('*')
          .eq('id', session.user.id)
          .maybeSingle();
        
        if (prof) setProfile(prof);

        // Fetch Store Count
        const { count } = await supabase
          .from('marketplace_connections')
          .select('*', { count: 'exact', head: true })
          .eq('user_id', session.user.id);
        
        setStoreCount(count || 0);
      }
    };
    fetchUserData();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        setUser(session.user);
        fetchUserData();
      } else {
        setUser(null);
        setProfile(null);
        setStoreCount(0);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  // Lock body scroll when mobile menu is open
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
      document.body.style.position = 'fixed';
      document.body.style.width = '100%';
    } else {
      document.body.style.overflow = '';
      document.body.style.position = '';
      document.body.style.width = '';
    }
    return () => {
      document.body.style.overflow = '';
      document.body.style.position = '';
      document.body.style.width = '';
    };
  }, [mobileMenuOpen]);

  return (
    <>
      <nav className="fixed top-0 w-full z-50 bg-black/60 backdrop-blur-md border-b border-zinc-800/50 h-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex justify-between items-center h-16">
          <div className="flex items-center gap-2 shrink-0">
            <img src={logo} alt="Tokcer AI" className="h-8 w-auto" />
          </div>
          
          <div className="hidden xl:flex ml-12 gap-8 items-center text-sm font-medium uppercase tracking-widest text-zinc-400">
            <a href="/#problem" className="hover:text-white transition-colors">{t('navProblem')}</a>
            <a href="/#ecosystem" className="hover:text-white transition-colors">{t('navEcosystem')}</a>
            <a href="/#dashboard" className="text-orange-500 font-bold">{t('navExplore')}</a>
            <a href="/#about-us-hero" className="hover:text-white transition-colors">{t('navAbout')}</a>
            <a href="/#pricing" className="hover:text-white transition-colors text-zinc-400">{t('navPricing')}</a>
          </div>
          
          <div className="hidden xl:flex items-center gap-4">
            <div className="hidden bg-zinc-900 rounded-lg p-1 border border-zinc-800 mr-2">
              <button 
                onClick={() => toggleLang('id')}
                className={`px-3 py-1 text-[10px] font-bold rounded transition-all ${lang === 'id' ? 'bg-orange-600 text-white shadow-sm' : 'text-zinc-500 hover:text-white'}`}
              >
                ID
              </button>
              <button 
                onClick={() => toggleLang('en')}
                className={`px-3 py-1 text-[10px] font-bold rounded transition-all ${lang === 'en' ? 'bg-orange-600 text-white shadow-sm' : 'text-zinc-500 hover:text-white'}`}
              >
                EN
              </button>
            </div>
            {user && window.location.pathname !== '/' ? (
              <div className="flex items-center gap-3">
                {/* Stats Badge */}
                <div className="hidden sm:flex items-center gap-3 px-3 py-1.5 bg-zinc-900/50 border border-zinc-800 rounded-full text-[10px] font-bold">
                  <div className="flex items-center gap-1.5 text-orange-400">
                    <iconify-icon icon="solar:magic-stick-3-bold" className="text-sm"></iconify-icon>
                    <span>{profile?.tokens || 0}</span>
                  </div>
                  <div className="w-px h-3 bg-zinc-800"></div>
                  <div className="flex items-center gap-1.5 text-blue-400">
                    <iconify-icon icon="solar:shop-bold" className="text-sm"></iconify-icon>
                    <span>{storeCount} {t('navStores') || 'Stores'}</span>
                  </div>
                </div>

                <button 
                  onClick={() => navigate('/dashboard')} 
                  className="bg-gradient-to-r from-orange-600 to-amber-600 text-white px-6 py-2 rounded-full text-sm font-bold shadow-lg shadow-orange-900/20 border border-orange-500/50 hover:scale-105 transition-all active:scale-95 flex items-center gap-2"
                >
                  <iconify-icon icon="solar:widget-bold-duotone" className="text-lg"></iconify-icon>
                  {t('navDashboard') || 'Dashboard'}
                </button>
              </div>
            ) : (
              <>
                <button onClick={() => navigate('/login')} className="text-sm font-medium text-zinc-300 hover:text-white transition-colors uppercase tracking-widest px-4">{t('navLogin')}</button>
                <button onClick={onOpenPartner} className="bg-yellow-500 text-black px-6 py-2 rounded-full text-sm font-bold shadow-sm border border-yellow-400 hover:bg-yellow-400 transition-all active:scale-95">{t('navPartner')}</button>
                <button onClick={onOpenWaitlist} className="bg-orange-600 text-white px-6 py-2 rounded-full text-sm font-bold shadow-sm border border-orange-500 hover:bg-orange-500 transition-all active:scale-95">{t('navWaitlist')}</button>
              </>
            )}
          </div>

          <button onClick={toggleMobileMenu} className="xl:hidden flex items-center gap-2 text-zinc-300 hover:text-white p-2 focus:outline-none" aria-label="Toggle menu">
            <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">{mobileMenuOpen ? 'Close' : 'Menu'}</span>
            <iconify-icon icon={mobileMenuOpen ? "solar:close-square-bold-duotone" : "solar:hamburger-menu-bold-duotone"} className="text-3xl text-orange-500"></iconify-icon>
          </button>
        </div>
      </nav>

      {/* Mobile Menu Overlay - Moved OUTSIDE the nav container for absolute positioning safety */}
      {mobileMenuOpen && (
        <div className="xl:hidden fixed inset-0 z-[999] flex flex-col bg-zinc-950 animate-in fade-in slide-in-from-top-4 duration-300">
          {/* Mobile Header Duplicate for closure */}
          <div className="h-16 px-4 flex justify-between items-center border-b border-zinc-800/50 bg-black/80 backdrop-blur-md">
            <img src={logo} alt="Tokcer AI" className="h-8 w-auto" />
            <button onClick={toggleMobileMenu} className="flex items-center gap-2 text-zinc-300 p-2">
              <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Close</span>
              <iconify-icon icon="solar:close-square-bold-duotone" className="text-3xl text-orange-500"></iconify-icon>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto overscroll-contain bg-zinc-950 p-4 sm:p-6 flex flex-col gap-4 sm:gap-6 pb-10" style={{ WebkitOverflowScrolling: 'touch' }}>
            {/* Language Switch */}
            <div className="hidden bg-zinc-900 rounded-2xl p-2 border border-zinc-800 mx-auto w-fit shrink-0">
              <button 
                onClick={() => toggleLang('id')}
                className={`px-10 py-3 text-xs font-black rounded-xl transition-all ${lang === 'id' ? 'bg-orange-600 text-white shadow-xl' : 'text-zinc-500 hover:text-white'}`}
              >
                INDONESIA
              </button>
              <button 
                onClick={() => toggleLang('en')}
                className={`px-10 py-3 text-xs font-black rounded-xl transition-all ${lang === 'en' ? 'bg-orange-600 text-white shadow-xl' : 'text-zinc-500 hover:text-white'}`}
              >
                ENGLISH
              </button>
            </div>

            {/* Navigation Links */}
            <div className="flex flex-col gap-3 shrink-0">
              <p className="text-[10px] font-black text-zinc-600 uppercase tracking-[0.3em] ml-2 mb-2">Navigation</p>
              {[
                { href: "/#problem", label: t('navProblem'), icon: 'solar:danger-triangle-linear' },
                { href: "/#ecosystem", label: t('navEcosystem'), icon: 'solar:globus-linear' },
                { href: "/#dashboard", label: t('navExplore'), special: true, icon: 'solar:widget-linear' },
                { href: "/#about-us-hero", label: t('navAbout'), icon: 'solar:info-circle-linear' }
              ].map((item) => (
                <a 
                  key={item.href}
                  href={item.href} 
                  onClick={toggleMobileMenu} 
                  className={`flex items-center gap-3 py-3 px-4 rounded-xl text-xs sm:text-sm font-black uppercase tracking-[0.15em] sm:tracking-[0.2em] transition-all border ${item.special ? 'text-orange-500 bg-orange-500/5 border-orange-500/20' : 'text-zinc-400 bg-zinc-900/50 border-zinc-800/50 hover:text-white hover:bg-zinc-900'}`}
                >
                  <iconify-icon icon={item.icon} className="text-xl"></iconify-icon>
                  {item.label}
                </a>
              ))}
              <a 
                href="/#pricing"
                onClick={toggleMobileMenu} 
                className="flex items-center gap-3 py-3 px-4 rounded-xl text-xs sm:text-sm font-black uppercase tracking-[0.15em] sm:tracking-[0.2em] text-zinc-400 bg-zinc-900/50 border border-zinc-800/50 hover:text-white hover:bg-zinc-900 text-left w-full"
              >
                <iconify-icon icon="solar:tag-price-linear" className="text-xl"></iconify-icon>
                {t('navPricing')}
              </a>
            </div>
            
            <div className="h-px bg-zinc-900 w-full shrink-0"></div>
            
            {/* Action Buttons */}
            <div className="flex flex-col gap-4 shrink-0">
              <p className="text-[10px] font-black text-zinc-600 uppercase tracking-[0.3em] ml-2">Access</p>
              <button onClick={() => { navigate('/login'); toggleMobileMenu(); }} className="w-full py-3 sm:py-4 bg-zinc-900 border border-zinc-800 rounded-xl text-xs sm:text-sm font-black text-zinc-300 uppercase tracking-[0.15em] sm:tracking-[0.2em] flex items-center justify-center gap-3">
                <iconify-icon icon="solar:user-linear" className="text-xl"></iconify-icon>
                {t('navLogin')}
              </button>
              <button onClick={() => { onOpenPartner(); toggleMobileMenu(); }} className="w-full py-3 sm:py-4 bg-yellow-500 text-black rounded-xl text-xs sm:text-sm font-black uppercase tracking-[0.15em] sm:tracking-[0.2em] shadow-xl shadow-yellow-500/10 border border-yellow-400 flex items-center justify-center gap-3">
                <iconify-icon icon="solar:hand-stars-bold" className="text-xl"></iconify-icon>
                {t('navPartner')}
              </button>
              
              <button onClick={() => { onOpenWaitlist(); toggleMobileMenu(); }} className="w-full py-3 sm:py-4 bg-orange-600 text-white rounded-xl text-xs sm:text-sm font-black uppercase tracking-[0.15em] sm:tracking-[0.2em] shadow-xl shadow-orange-600/10 border border-orange-500 flex items-center justify-center gap-3">
                <iconify-icon icon="solar:rocket-bold" className="text-xl"></iconify-icon>
                {t('navWaitlist')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Pricing Coming Soon Modal */}
      {pricingModalOpen && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-sm px-4" onClick={() => setPricingModalOpen(false)}>
          <div className="relative bg-zinc-900 w-full max-w-sm p-8 rounded-2xl shadow-2xl border border-zinc-800 text-center" onClick={e => e.stopPropagation()}>
            <button onClick={() => setPricingModalOpen(false)} className="absolute top-4 right-4 text-zinc-500 hover:text-white transition-colors">
              <iconify-icon icon="solar:close-circle-linear" className="text-2xl"></iconify-icon>
            </button>
            <div className="w-16 h-16 bg-orange-950/40 border border-orange-800/50 rounded-full flex items-center justify-center mx-auto mb-5">
              <iconify-icon icon="solar:tag-price-bold" className="text-3xl text-orange-400"></iconify-icon>
            </div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-950/30 border border-orange-900/50 mb-4">
              <span className="flex h-1.5 w-1.5 rounded-full bg-orange-500 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
              </span>
              <span className="text-[10px] font-medium text-orange-500 uppercase tracking-widest">
                {t('pricingComingSoonBadge')}
              </span>
            </div>
            <h3 className="text-2xl font-bold text-white tracking-tight mb-3">{t('pricingComingSoonTitle')}</h3>
            <p className="text-zinc-400 text-sm leading-relaxed">{t('pricingComingSoonDesc')}</p>
            <button 
              onClick={() => { setPricingModalOpen(false); onOpenWaitlist(); }}
              className="mt-6 w-full py-3 bg-orange-600 text-white rounded-xl text-sm font-bold hover:bg-orange-500 transition-all border border-orange-500"
            >
              {t('navWaitlist')}
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default Navbar;
