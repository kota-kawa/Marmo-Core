import React, { useState, useEffect } from 'react';
import { FadeUp } from './FadeUp';
import { motion, AnimatePresence } from 'framer-motion';

const testimonials = [
  {
    text: "Sudee transformed our wedding into something out of a dream. Every petal, every light, every throne — pure perfection. Bengaluru has never seen anything like it.",
    author: "Priya & Arjun R.",
    event: "Wedding 2024"
  },
  {
    text: "Our daughter's half-saree ceremony was breathtaking. The jasmine canopy alone had our guests in tears. Posh Events is in a league of their own.",
    author: "Mrs. Lakshmi Venkatesh",
    event: "Half-Saree 2023"
  },
  {
    text: "The Blue Haldi Carnival theme was absolutely one-of-a-kind. So many compliments, so many memories. Truly luxury at its finest.",
    author: "Divya M.",
    event: "Haldi Event 2024"
  }
];

export default function Testimonials() {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent((prev) => (prev + 1) % testimonials.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <section className="py-24 bg-cream relative">
      <div className="container mx-auto px-6 md:px-12 text-center">
        <FadeUp>
          <h2 className="text-4xl md:text-5xl font-serif text-navy mb-16">Words From Our Beloved Clients</h2>
        </FadeUp>

        <div className="max-w-4xl mx-auto relative h-64 md:h-48">
          <AnimatePresence mode="wait">
            <motion.div
              key={current}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
              className="absolute inset-0 flex flex-col items-center justify-center"
            >
              <span className="text-6xl text-gold font-serif leading-none mb-4">"</span>
              <p className="text-xl md:text-2xl font-serif italic text-navy mb-8 leading-relaxed">
                {testimonials[current].text}
              </p>
              <div className="flex flex-col items-center">
                <span className="font-sans text-charcoal tracking-widest uppercase text-sm font-semibold">
                  — {testimonials[current].author}
                </span>
                <span className="font-sans text-gold tracking-wider uppercase text-xs mt-1">
                  {testimonials[current].event}
                </span>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Dots */}
        <div className="flex justify-center space-x-3 mt-8">
          {testimonials.map((_, idx) => (
            <button
              key={idx}
              onClick={() => setCurrent(idx)}
              className={`w-2 h-2 rounded-full transition-all duration-300 ${
                idx === current ? 'bg-gold w-6' : 'bg-gold/30 hover:bg-gold/60'
              }`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
