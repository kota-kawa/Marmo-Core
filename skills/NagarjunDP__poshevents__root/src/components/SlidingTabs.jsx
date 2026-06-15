import React, { useState } from 'react';
import { FadeUp } from './FadeUp';
import { motion, AnimatePresence } from 'framer-motion';

const tabs = [
  {
    id: 'traditional',
    title: 'Traditional Milestones',
    subtitle: 'Coconut-Leaf Seemantham & Royal Muhurtham',
    description: 'Rooted deeply in our rich heritage, we bring ancient traditions to life with authentic South Indian styling, fragrant jasmine accents, and pure gold accents.',
    images: [
      'https://images.unsplash.com/photo-1583939003579-730e3918a45a?w=600',
      'https://images.unsplash.com/photo-1519225421980-715cb0215aed?w=600'
    ]
  },
  {
    id: 'contemporary',
    title: 'Contemporary Productions',
    subtitle: 'Luxury Receptions & Brandings',
    description: 'Modern elegance meets bespoke design. From geometric floral arches to immersive lighting setups, we craft sophisticated spaces for the contemporary celebrant.',
    images: [
      'https://images.unsplash.com/photo-1511795409834-ef04bbd61622?w=600',
      'https://images.unsplash.com/photo-1464349153735-7db50ed83c84?w=600'
    ]
  }
];

export default function SlidingTabs() {
  const [activeTab, setActiveTab] = useState(tabs[0].id);

  return (
    <section className="py-24 bg-white">
      <div className="container mx-auto px-6 md:px-12">
        <FadeUp>
          <div className="flex flex-col items-center mb-16">
            <div className="flex p-1 bg-cream rounded-full border border-gold/20 mb-12">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative px-8 py-3 rounded-full font-sans text-sm tracking-widest uppercase transition-colors ${
                    activeTab === tab.id ? 'text-white' : 'text-navy hover:text-gold'
                  }`}
                >
                  {activeTab === tab.id && (
                    <motion.div
                      layoutId="tab-indicator"
                      className="absolute inset-0 bg-navy rounded-full"
                      transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    />
                  )}
                  <span className="relative z-10">{tab.title}</span>
                </button>
              ))}
            </div>
          </div>
        </FadeUp>

        <div className="relative min-h-[500px]">
          <AnimatePresence mode="wait">
            {tabs.map(
              (tab) =>
                activeTab === tab.id && (
                  <motion.div
                    key={tab.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.5 }}
                    className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center"
                  >
                    <div>
                      <h3 className="text-3xl md:text-4xl font-serif text-navy mb-4">{tab.subtitle}</h3>
                      <div className="w-12 h-px bg-gold mb-6" />
                      <p className="text-charcoal/80 font-sans leading-relaxed mb-8 max-w-lg">
                        {tab.description}
                      </p>
                      <button className="text-gold font-sans uppercase tracking-[0.2em] text-sm border-b border-gold pb-1 hover:text-navy transition-colors">
                        View Portfolio
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      {tab.images.map((img, i) => (
                        <div key={i} className={`h-64 md:h-80 overflow-hidden ${i === 1 ? 'mt-8' : ''}`}>
                          <img src={img} alt={tab.title} className="w-full h-full object-cover" />
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}
