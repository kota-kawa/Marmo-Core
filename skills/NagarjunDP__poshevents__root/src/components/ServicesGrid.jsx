import React from 'react';
import { FadeUp } from './FadeUp';
import { motion } from 'framer-motion';
import { Play } from 'lucide-react';

const services = [
  { title: "Luxury Wedding Styling", img: "https://images.unsplash.com/photo-1606800052052-a08af7148866?w=700", hasVideo: true },
  { title: "Premium Haldi Carnival", img: "https://images.unsplash.com/photo-1583939003579-730e3918a45a?w=700" },
  { title: "Royal Throne Setups", img: "https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=700", hasVideo: true },
  { title: "Half-Saree & Jasmine Canopy", img: "https://images.unsplash.com/photo-1519225421980-715cb0215aed?w=700" },
  { title: "Baby Showers & Naming", img: "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=700" },
  { title: "Luxury Birthday Soirées", img: "https://images.unsplash.com/photo-1464349153735-7db50ed83c84?w=700", hasVideo: true },
];

export default function ServicesGrid() {
  return (
    <section id="celebrations" className="py-24 bg-cream">
      <div className="container mx-auto px-6 md:px-12">
        <FadeUp>
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-serif text-navy mb-4">Our Signature Experiences</h2>
            <p className="font-sans text-gold tracking-[0.2em] text-sm uppercase">Curated For The Discerning Few</p>
          </div>
        </FadeUp>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 md:gap-12">
          {services.map((service, idx) => (
            <FadeUp key={idx} delay={idx * 0.1}>
              <div className="group cursor-pointer">
                <div className="relative h-[450px] mb-6 overflow-hidden">
                  <motion.img 
                    src={service.img} 
                    alt={service.title}
                    className="w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-105"
                  />
                  {service.hasVideo && (
                    <div className="absolute top-4 right-4 bg-black/40 backdrop-blur-md px-3 py-1.5 rounded-full flex items-center space-x-2 border border-white/20">
                      <Play size={12} className="text-white fill-white" />
                      <span className="text-white text-[10px] font-sans tracking-wider uppercase">Play BTS Reel</span>
                    </div>
                  )}
                  <div className="absolute bottom-0 left-0 right-0 h-0 bg-gold/90 transition-all duration-300 ease-out group-hover:h-2" />
                </div>
                <h3 className="text-2xl font-serif text-navy border-b border-gold/30 pb-4">
                  {service.title}
                </h3>
              </div>
            </FadeUp>
          ))}
        </div>
      </div>
    </section>
  );
}
