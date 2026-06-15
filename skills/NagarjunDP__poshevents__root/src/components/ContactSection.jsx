import React, { useState } from 'react';
import { Phone, MapPin, Instagram } from 'lucide-react';
import { FadeUp } from './FadeUp';
import { motion, AnimatePresence } from 'framer-motion';

export default function ContactSection() {
  const [step, setStep] = useState(1);

  return (
    <section id="contact" className="py-24 bg-cream">
      <div className="container mx-auto px-6 md:px-12">
        <FadeUp>
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-serif text-navy mb-4">Begin Your Story With Us</h2>
            <p className="font-sans text-gold tracking-[0.2em] text-sm uppercase">Bengaluru, Karnataka · Bookings & Collaborations</p>
          </div>
        </FadeUp>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
          {/* Left Column: Details */}
          <FadeUp delay={0.2} className="flex flex-col justify-center space-y-12">
            <div className="flex items-start space-x-6 group">
              <div className="w-12 h-12 rounded-full border border-gold flex items-center justify-center text-navy group-hover:bg-gold group-hover:text-white transition-colors">
                <Phone size={20} />
              </div>
              <div>
                <h4 className="font-sans text-charcoal/60 text-xs tracking-widest uppercase mb-1">Direct Line</h4>
                <p className="font-serif text-2xl text-navy">+91 78992 43348</p>
              </div>
            </div>
            
            <div className="flex items-start space-x-6 group">
              <div className="w-12 h-12 rounded-full border border-gold flex items-center justify-center text-navy group-hover:bg-gold group-hover:text-white transition-colors">
                <Instagram size={20} />
              </div>
              <div>
                <h4 className="font-sans text-charcoal/60 text-xs tracking-widest uppercase mb-1">Portfolio</h4>
                <p className="font-serif text-2xl text-navy">@posh_events_by_sudee</p>
              </div>
            </div>

            <div className="flex items-start space-x-6 group">
              <div className="w-12 h-12 rounded-full border border-gold flex items-center justify-center text-navy group-hover:bg-gold group-hover:text-white transition-colors">
                <MapPin size={20} />
              </div>
              <div>
                <h4 className="font-sans text-charcoal/60 text-xs tracking-widest uppercase mb-1">Headquarters</h4>
                <p className="font-serif text-2xl text-navy">Bengaluru, Karnataka</p>
              </div>
            </div>
          </FadeUp>

          {/* Right Column: Wizard Form */}
          <FadeUp delay={0.4}>
            <div className="bg-white p-8 md:p-12 border border-gold/30 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-cream">
                <div className="h-full bg-gold transition-all duration-500" style={{ width: step === 1 ? '50%' : '100%' }} />
              </div>
              
              <h3 className="font-serif text-2xl text-navy mb-8 border-b border-gold/20 pb-4">
                {step === 1 ? 'Step 1: Event Details' : 'Step 2: Personal Details'}
              </h3>

              <form onSubmit={(e) => e.preventDefault()} className="space-y-6">
                <AnimatePresence mode="wait">
                  {step === 1 ? (
                    <motion.div
                      key="step1"
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      className="space-y-6"
                    >
                      <div>
                        <label className="block font-sans text-xs tracking-widest text-navy uppercase mb-2">Event Type</label>
                        <select className="w-full bg-cream/50 border border-gold/30 px-4 py-3 text-navy font-sans focus:outline-none focus:border-gold">
                          <option>Luxury Wedding</option>
                          <option>Premium Haldi</option>
                          <option>Half-Saree Ceremony</option>
                          <option>Royal Reception</option>
                          <option>Corporate Branding</option>
                        </select>
                      </div>
                      <div>
                        <label className="block font-sans text-xs tracking-widest text-navy uppercase mb-2">Preferred Venue Type</label>
                        <select className="w-full bg-cream/50 border border-gold/30 px-4 py-3 text-navy font-sans focus:outline-none focus:border-gold">
                          <option>Premium Bengaluru Lawn Resort</option>
                          <option>Five-Star Heritage Hotel</option>
                          <option>Private Estate Enclave</option>
                          <option>Palace Grounds</option>
                          <option>Other / Not decided</option>
                        </select>
                      </div>
                      <div>
                        <label className="block font-sans text-xs tracking-widest text-navy uppercase mb-2">Estimated Date</label>
                        <input type="date" className="w-full bg-cream/50 border border-gold/30 px-4 py-3 text-navy font-sans focus:outline-none focus:border-gold" />
                      </div>
                      <button 
                        onClick={() => setStep(2)}
                        type="button" 
                        className="w-full bg-navy text-gold py-4 font-sans tracking-widest uppercase text-sm hover:bg-gold hover:text-navy transition-colors"
                      >
                        Next Step →
                      </button>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="step2"
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      className="space-y-6"
                    >
                      <div>
                        <label className="block font-sans text-xs tracking-widest text-navy uppercase mb-2">Your Full Name</label>
                        <input type="text" placeholder="e.g. Anjali Sharma" className="w-full bg-cream/50 border border-gold/30 px-4 py-3 text-navy font-sans focus:outline-none focus:border-gold" required />
                      </div>
                      <div>
                        <label className="block font-sans text-xs tracking-widest text-navy uppercase mb-2">Phone Number</label>
                        <input type="tel" placeholder="+91 " className="w-full bg-cream/50 border border-gold/30 px-4 py-3 text-navy font-sans focus:outline-none focus:border-gold" required />
                      </div>
                      <div>
                        <label className="block font-sans text-xs tracking-widest text-navy uppercase mb-2">Vision / Message</label>
                        <textarea rows="3" placeholder="Share your dream aesthetic..." className="w-full bg-cream/50 border border-gold/30 px-4 py-3 text-navy font-sans focus:outline-none focus:border-gold"></textarea>
                      </div>
                      <div className="flex space-x-4">
                        <button 
                          onClick={() => setStep(1)}
                          type="button" 
                          className="w-1/3 bg-cream text-navy border border-gold/50 py-4 font-sans tracking-widest uppercase text-sm hover:bg-gold hover:text-white transition-colors"
                        >
                          ← Back
                        </button>
                        <button 
                          type="submit" 
                          className="w-2/3 bg-gold text-navy py-4 font-sans tracking-widest uppercase text-sm font-semibold hover:bg-navy hover:text-gold transition-colors"
                        >
                          Send Enquiry →
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </form>
            </div>
          </FadeUp>
        </div>
      </div>
    </section>
  );
}
