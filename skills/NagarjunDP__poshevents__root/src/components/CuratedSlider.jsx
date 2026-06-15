import React from 'react';
import { FadeUp } from './FadeUp';

export default function CuratedSlider() {
  return (
    <section className="py-24 bg-navy text-cream overflow-hidden">
      <div className="container mx-auto px-6 md:px-12">
        <FadeUp>
          <div className="flex justify-between items-end mb-16">
            <div>
              <h2 className="text-4xl md:text-5xl font-serif mb-4">As Curated For Icons</h2>
              <p className="font-sans text-gold tracking-[0.2em] text-sm uppercase">Exclusive Client Showcases</p>
            </div>
            <div className="hidden md:flex space-x-4">
              {/* Fake navigation for visual aesthetic */}
              <div className="w-12 h-12 rounded-full border border-gold/30 flex items-center justify-center text-gold cursor-pointer hover:bg-gold hover:text-navy transition-colors">←</div>
              <div className="w-12 h-12 rounded-full border border-gold flex items-center justify-center text-gold cursor-pointer hover:bg-gold hover:text-navy transition-colors">→</div>
            </div>
          </div>
        </FadeUp>

        <div className="flex space-x-8 overflow-x-auto pb-12 snap-x snap-mandatory hide-scrollbar">
          {/* Highlight Item */}
          <div className="min-w-[85vw] md:min-w-[60vw] lg:min-w-[45vw] snap-center group cursor-pointer relative">
            <div className="h-[60vh] overflow-hidden relative">
              <img 
                src="https://images.unsplash.com/photo-1519741497674-611481863552?w=900" 
                alt="Rudra Master's Golden Vibes" 
                className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-105"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-navy/90 via-navy/20 to-transparent" />
            </div>
            <div className="absolute bottom-0 left-0 p-8 w-full">
              <div className="flex items-center space-x-3 mb-4">
                <span className="px-3 py-1 bg-gold text-navy text-[10px] font-sans tracking-widest uppercase font-semibold">Celebrity Wedding</span>
                <span className="text-gold text-xs font-sans tracking-widest">BENGALURU</span>
              </div>
              <h3 className="text-3xl font-serif mb-2">Rudra Master's Golden Vibes</h3>
              <p className="text-cream/80 font-sans text-sm mb-4">Haldi & Sangeeth Decor</p>
              <p className="text-cream/60 font-sans text-xs uppercase tracking-widest max-w-sm">
                Pure sophistication and bespoke brilliance. An opulent blend of marigold cascades and ambient lighting creating an unforgettable royal aesthetic.
              </p>
            </div>
          </div>

          <div className="min-w-[85vw] md:min-w-[60vw] lg:min-w-[45vw] snap-center group cursor-pointer relative">
            <div className="h-[60vh] overflow-hidden relative">
              <img 
                src="https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=900" 
                alt="The Royal Residency Reception" 
                className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-105"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-navy/90 via-navy/20 to-transparent" />
            </div>
            <div className="absolute bottom-0 left-0 p-8 w-full">
              <div className="flex items-center space-x-3 mb-4">
                <span className="px-3 py-1 bg-gold/20 text-gold border border-gold/50 text-[10px] font-sans tracking-widest uppercase font-semibold">Grand Reception</span>
              </div>
              <h3 className="text-3xl font-serif mb-2">The Royal Palace Reception</h3>
              <p className="text-cream/80 font-sans text-sm mb-4">Floral Canopy & Throne</p>
            </div>
          </div>
        </div>
      </div>
      <style dangerouslySetInnerHTML={{__html: `
        .hide-scrollbar::-webkit-scrollbar { display: none; }
        .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
      `}} />
    </section>
  );
}
