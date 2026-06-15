import React from 'react';
import { Instagram } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-navy pt-20 pb-10 border-t border-gold text-center relative overflow-hidden">
      <div className="container mx-auto px-6 relative z-10">
        
        {/* Logo Mark */}
        <div className="flex justify-center mb-8">
          <img src="/logo.png" alt="Posh Events" className="w-24 h-auto object-contain" style={{ filter: 'brightness(0) invert(1)' }} />
        </div>
        
        <h2 className="font-sans text-cream tracking-[0.4em] text-lg mb-8 uppercase font-semibold">
          Posh Events By Sudee
        </h2>
        
        <div className="w-24 h-px bg-gold mx-auto mb-8" />
        
        {/* Nav Links */}
        <div className="flex flex-wrap justify-center gap-6 md:gap-12 mb-12">
          {['Weddings', 'Celebrations', 'Gallery', 'About', 'Contact'].map((link) => (
            <a key={link} href={`#${link.toLowerCase()}`} className="text-cream font-sans text-sm tracking-widest hover:text-gold transition-colors uppercase">
              {link}
            </a>
          ))}
        </div>
        
        <div className="flex justify-center mb-12">
          <a href="#" className="w-10 h-10 rounded-full border border-gold/50 flex items-center justify-center text-cream hover:bg-gold hover:text-navy transition-colors">
            <Instagram size={18} />
          </a>
        </div>

        {/* Decorative Divider */}
        <div className="flex justify-center mb-6 opacity-50">
          <svg width="120" height="20" viewBox="0 0 120 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M0 10 H40 M80 10 H120 M60 2 L50 10 L60 18 L70 10 Z" stroke="#C9A84C" strokeWidth="1" />
          </svg>
        </div>
        
        <p className="font-sans text-cream/50 text-xs tracking-widest uppercase">
          © 2025 Posh Events by Sudee. Crafted with love in Bengaluru.
        </p>
      </div>
      
      {/* Background floral abstraction */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full opacity-5 pointer-events-none flex justify-center">
        <svg width="800" height="800" viewBox="0 0 800 800" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="400" cy="400" r="300" stroke="#C9A84C" strokeWidth="1" />
          <circle cx="400" cy="400" r="200" stroke="#C9A84C" strokeWidth="1" />
          <circle cx="400" cy="400" r="100" stroke="#C9A84C" strokeWidth="1" />
        </svg>
      </div>
    </footer>
  );
}
