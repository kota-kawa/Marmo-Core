import React, { useState } from 'react';
import Navbar from '../components/Navbar.jsx';
import Hero from '../components/landing/Hero.jsx';
import Problem from '../components/landing/Problem.jsx';
import Solution from '../components/landing/Solution.jsx';
import Ecosystem from '../components/landing/Ecosystem.jsx';
import Pricing from '../components/landing/Pricing.jsx';
import Testimonial from '../components/landing/Testimonial.jsx';
import AboutUs from '../components/landing/AboutUs.jsx';
import WaitlistCTA from '../components/landing/WaitlistCTA.jsx';
import Footer from '../components/Footer.jsx';
import RegisterModal from '../components/modals/RegisterModal.jsx';
import PartnerModal from '../components/modals/PartnerModal.jsx';
import DemoRegisterModal from '../components/modals/DemoRegisterModal.jsx';

const Landing = () => {
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [isPartnerOpen, setIsPartnerOpen] = useState(false);
  const [isDemoOpen, setIsDemoOpen] = useState(false);

  const openRegister = (plan = null) => {
    setSelectedPlan(plan);
    setIsRegisterOpen(true);
  };

  React.useEffect(() => {
    // Tangkap affiliate ID dari URL (?ref=ID001)
    const params = new URLSearchParams(window.location.search);
    const ref = params.get('ref');
    if (ref) {
      localStorage.setItem('tokcer_affiliate_id', ref);
    }

    // GAP 7: Auto-open modal jika URL mengandung /register (misal dari link referral partner)
    if (window.location.pathname === '/register') {
      setIsRegisterOpen(true);
    }

    // Fallback routing untuk link non-hash (misal dari email lama)
    const path = window.location.pathname;
    if (path === '/partner-agreement') {
      window.location.replace(`/#/partner-agreement${window.location.search}`);
    }
  }, []);

  return (
    <div className="bg-black min-h-screen text-white font-['Inter',sans-serif] selection:bg-orange-500/30 selection:text-orange-200 overflow-x-hidden">
      {/* Premium Background System */}
      <div className="fixed inset-0 -z-10 bg-black overflow-hidden pointer-events-none">
        {/* Modern Grid */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f2937_1px,transparent_1px),linear-gradient(to_bottom,#1f2937_1px,transparent_1px)] bg-[size:4.5rem_4.5rem] [mask-image:radial-gradient(ellipse_80%_80%_at_50%_0%,#000_60%,transparent_100%)] opacity-20"></div>
        
        {/* Dynamic Aura Glows */}
        <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-orange-600/30 blur-[120px] animate-pulse duration-[8000ms]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-amber-500/20 blur-[100px] animate-pulse duration-[10000ms]"></div>
        <div className="absolute top-[30%] right-[10%] w-[30%] h-[30%] rounded-full bg-emerald-500/10 blur-[120px] animate-pulse duration-[12000ms]"></div>
        
        {/* Grain Overlay for Texture */}
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none mix-blend-overlay bg-[url('https://grainy-gradients.vercel.app/noise.svg')]"></div>
      </div>

      <Navbar 
        onOpenPartner={() => setIsPartnerOpen(true)} 
        onOpenWaitlist={() => openRegister()} 
      />
      
      {/* === SECTION 1: Hero / Above the Fold === */}
      <main>
        <Hero />

        {/* === SECTION 2: The Problem === */}
        <Problem />

        {/* === SECTION 3: The Solution === */}
        <Solution />

        {/* === SECTION 4: Our Ecosystem === */}
        <Ecosystem />

        {/* === SECTION 5: Pricing (Coming Soon) === */}
        <Pricing onOpenWaitlist={(plan) => openRegister(plan)} />

        {/* === SECTION 6: Social Proof / Testimonials === */}
        <Testimonial />

        {/* === SECTION 7: About Us === */}
        <AboutUs />

        {/* === SECTION 8: Final CTA === */}
        {/* <WaitlistCTA onOpenWaitlist={() => openRegister()} /> */}
      </main>

      <Footer />

      <RegisterModal isOpen={isRegisterOpen} onClose={() => setIsRegisterOpen(false)} selectedPlan={selectedPlan} />
      <PartnerModal isOpen={isPartnerOpen} onClose={() => setIsPartnerOpen(false)} />
    </div>
  );
};

export default Landing;
