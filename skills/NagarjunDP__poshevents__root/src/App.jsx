import React, { useState, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';

// Sections
import Loader from './components/Loader';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Marquee from './components/Marquee';
import ServicesGrid from './components/ServicesGrid';
import CuratedSlider from './components/CuratedSlider';
import SlidingTabs from './components/SlidingTabs';
import FeatureStrip from './components/FeatureStrip';
import Testimonials from './components/Testimonials';
import StatsRibbon from './components/StatsRibbon';
import ContactSection from './components/ContactSection';
import Footer from './components/Footer';

function App() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const hasVisited = sessionStorage.getItem('posh_visited');
    if (hasVisited) {
      setLoading(false);
    } else {
      setTimeout(() => {
        setLoading(false);
        sessionStorage.setItem('posh_visited', 'true');
      }, 2800);
    }
  }, []);

  return (
    <div className="bg-cream min-h-screen text-charcoal">
      <AnimatePresence>
        {loading && <Loader />}
      </AnimatePresence>

      {!loading && (
        <>
          <Navbar />
          <main>
            <Hero />
            <Marquee />
            <ServicesGrid />
            <SlidingTabs />
            <CuratedSlider />
            <FeatureStrip />
            <Testimonials />
            <StatsRibbon />
            <ContactSection />
          </main>
          <Footer />
        </>
      )}
    </div>
  );
}

export default App;
