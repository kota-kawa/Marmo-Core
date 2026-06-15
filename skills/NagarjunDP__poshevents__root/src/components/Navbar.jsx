import React, { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const links = ['Weddings', 'Celebrations', 'Gallery', 'About', 'Contact'];

  return (
    <div className="fixed top-0 left-0 right-0 z-50">
      {/* Offers Banner */}
      <div className="bg-navy text-gold text-[10px] md:text-xs py-2 font-sans tracking-[0.2em] uppercase shadow-md relative z-50 overflow-hidden flex whitespace-nowrap">
        <div className="animate-[marquee_15s_linear_infinite] md:animate-[marquee_35s_linear_infinite] inline-flex w-full">
          {[...Array(2)].map((_, i) => (
            <span key={i} className="mx-4 whitespace-nowrap flex-shrink-0">
              ✦ EXCLUSIVE OFFER: BOOK YOUR 2025 CELEBRATION NOW TO RECEIVE A COMPLIMENTARY PREMIUM STYLING UPGRADE ✦
            </span>
          ))}
        </div>
      </div>
      
      <header
        className={`transition-all duration-300 ${
          scrolled ? 'bg-cream border-b border-gold py-3 shadow-sm' : 'bg-transparent py-5'
        }`}
      >
        <div className="container mx-auto px-6 md:px-12 flex items-center justify-between relative">
          {/* Left: Logo Mark & Desktop Wordmark */}
          <div className="flex items-center space-x-5">
            <img src="/logo.png" alt="Posh Events" className="h-16 w-auto md:h-20 object-contain" />
            <span className="hidden lg:block font-sans text-navy tracking-[0.3em] font-semibold text-sm uppercase translate-y-[2px]">
              Posh Events By Sudee
            </span>
          </div>

          {/* Absolute Center: Mobile Wordmark */}
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center lg:hidden w-max">
            <span className="font-serif text-gold italic text-[12px] leading-tight pr-1">Unique Style</span>
            <span className="font-sans text-navy tracking-[0.2em] font-semibold text-[11px] uppercase leading-tight">Posh Events</span>
          </div>

          {/* Right: Nav Links & CTA */}
          <div className="hidden md:flex items-center gap-8">
            {links.map((link) => (
              <a key={link} href={`#${link.toLowerCase()}`} className="text-sm font-sans tracking-widest text-navy hover:text-gold transition-colors">
                {link}
              </a>
            ))}
            <a href="#contact" className="px-6 py-2 border border-gold text-navy font-sans text-sm tracking-widest rounded-full hover:bg-gold hover:text-white transition-colors">
              Book Now
            </a>
          </div>

          {/* Mobile Menu Toggle */}
          <div className="md:hidden">
            <button onClick={() => setMobileMenuOpen(true)} className="text-navy focus:outline-none">
              <Menu size={28} />
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: '-100%' }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: '-100%' }}
            transition={{ duration: 0.5, ease: [0.76, 0, 0.24, 1] }}
            className="fixed inset-0 z-50 bg-navy text-cream flex flex-col items-center justify-center"
          >
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="absolute top-6 right-6 text-cream focus:outline-none"
            >
              <X size={32} />
            </button>
            <div className="flex flex-col items-center space-y-8">
              {links.map((link, i) => (
                <motion.a
                  key={link}
                  href={`#${link.toLowerCase()}`}
                  onClick={() => setMobileMenuOpen(false)}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.1 }}
                  className="font-serif text-3xl tracking-widest hover:text-gold transition-colors"
                >
                  {link}
                </motion.a>
              ))}
              <motion.a
                href="#contact"
                onClick={() => setMobileMenuOpen(false)}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + links.length * 0.1 }}
                className="mt-8 px-8 py-3 border border-gold text-gold font-sans tracking-widest uppercase hover:bg-gold hover:text-navy transition-colors"
              >
                Book Now
              </motion.a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
