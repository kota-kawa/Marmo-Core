import React from 'react';
import { motion } from 'framer-motion';

export default function FeatureStrip() {
  return (
    <section id="about" className="overflow-hidden bg-cream">
      <div className="grid grid-cols-1 lg:grid-cols-2">
        {/* Image Side */}
        <motion.div
          initial={{ opacity: 0, x: -100 }}
          whileInView={{ opacity: 1, x: 0 }}
          transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
          viewport={{ once: true, margin: "-10%" }}
          className="h-[50vh] lg:h-[80vh]"
        >
          <img 
            src="https://images.unsplash.com/photo-1511795409834-ef04bbd61622?w=900" 
            alt="Posh Events Philosophy" 
            className="w-full h-full object-cover"
          />
        </motion.div>

        {/* Text Side */}
        <motion.div
          initial={{ opacity: 0, x: 100 }}
          whileInView={{ opacity: 1, x: 0 }}
          transition={{ duration: 1, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          viewport={{ once: true, margin: "-10%" }}
          className="flex flex-col justify-center px-8 md:px-16 lg:px-24 py-16 lg:py-0"
        >
          <span className="font-sans text-gold tracking-[0.25em] text-sm font-semibold uppercase mb-6">
            OUR PHILOSOPHY
          </span>
          <h2 className="font-serif text-4xl md:text-[4rem] leading-[1.1] text-navy mb-8">
            Bespoke Grandeur,<br />Rooted in Tradition.
          </h2>
          <p className="font-sans text-charcoal/80 leading-relaxed mb-10 max-w-md">
            Every celebration we craft is a living work of art — where South Indian heritage meets opulent contemporary design. From intimate haldi mornings to grand outdoor receptions under the Karnataka sky, Posh Events by Sudee transforms vision into breathtaking reality.
          </p>
          <div>
            <a href="#gallery" className="inline-block px-8 py-3 border border-gold text-navy font-sans text-sm tracking-widest uppercase hover:bg-gold hover:text-white transition-colors">
              Explore Our Work →
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
