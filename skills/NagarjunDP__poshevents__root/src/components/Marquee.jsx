import React from 'react';

export default function Marquee() {
  const texts = [
    "LUXURY WEDDINGS",
    "PREMIUM HALDI CEREMONIES",
    "ROYAL THRONE SETUPS",
    "HALF-SAREE CELEBRATIONS",
    "BABY SHOWERS",
    "BIRTHDAY EVENTS",
    "OUTDOOR NIGHT RECEPTIONS",
    "BENGALURU'S FINEST EVENT STUDIO"
  ];

  return (
    <div className="w-full bg-navy py-4 overflow-hidden border-y border-gold flex whitespace-nowrap">
      <div className="animate-marquee inline-flex">
        {[...Array(2)].map((_, i) => (
          <div key={i} className="flex items-center space-x-8 px-4">
            {texts.map((text, idx) => (
              <React.Fragment key={idx}>
                <span className="text-gold font-sans text-sm md:text-base tracking-[0.25em] whitespace-nowrap uppercase">
                  {text}
                </span>
                <span className="text-gold opacity-50">✦</span>
              </React.Fragment>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
