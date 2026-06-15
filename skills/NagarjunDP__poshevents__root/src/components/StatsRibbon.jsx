import React, { useState, useEffect, useRef } from 'react';
import { motion, useInView } from 'framer-motion';

const useCountUp = (end, duration = 2000) => {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  useEffect(() => {
    if (isInView) {
      let start = 0;
      const increment = end / (duration / 16);
      const timer = setInterval(() => {
        start += increment;
        if (start >= end) {
          setCount(end);
          clearInterval(timer);
        } else {
          setCount(Math.ceil(start));
        }
      }, 16);
      return () => clearInterval(timer);
    }
  }, [isInView, end, duration]);

  return { count, ref };
};

const StatItem = ({ end, suffix, label }) => {
  const { count, ref } = useCountUp(end);
  return (
    <div ref={ref} className="flex flex-col items-center text-center">
      <span className="font-serif text-5xl md:text-6xl text-gold mb-2">
        {count}{suffix}
      </span>
      <span className="font-sans text-cream/80 text-xs md:text-sm tracking-[0.2em] uppercase">
        {label}
      </span>
    </div>
  );
};

export default function StatsRibbon() {
  return (
    <section className="w-full bg-navy py-16 border-y border-gold/30">
      <div className="container mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 divide-x-0 md:divide-x divide-gold/30">
          <StatItem end={200} suffix="+" label="Events Crafted" />
          <StatItem end={8} suffix="+" label="Years of Excellence" />
          <StatItem end={500} suffix="+" label="Happy Families" />
          <StatItem end={1} suffix="" label="Bengaluru's #1 Studio" />
        </div>
      </div>
    </section>
  );
}
