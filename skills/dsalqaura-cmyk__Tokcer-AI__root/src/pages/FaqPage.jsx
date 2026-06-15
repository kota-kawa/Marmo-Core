import React, { useState } from 'react';
import Navbar from '../components/Navbar.jsx';
import Footer from '../components/Footer.jsx';
import Faq from '../components/landing/Faq.jsx';
import RegisterModal from '../components/modals/RegisterModal.jsx';
import PartnerModal from '../components/modals/PartnerModal.jsx';

const FaqPage = () => {
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [isPartnerOpen, setIsPartnerOpen] = useState(false);

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
      </div>

      <Navbar 
        onOpenPartner={() => setIsPartnerOpen(true)} 
        onOpenWaitlist={() => setIsRegisterOpen(true)} 
      />

      <main className="pt-24 pb-16">
        <Faq />
      </main>

      <Footer />

      <RegisterModal isOpen={isRegisterOpen} onClose={() => setIsRegisterOpen(false)} />
      <PartnerModal isOpen={isPartnerOpen} onClose={() => setIsPartnerOpen(false)} />
    </div>
  );
};

export default FaqPage;
