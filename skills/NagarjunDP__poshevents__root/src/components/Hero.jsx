import React from 'react';
import { motion } from 'framer-motion';
import { ChevronDown } from 'lucide-react';

export default function Hero() {
  const headline = "Crafting Royal Milestones & Modern Celebrations.";
  const words = headline.split(" ");

  return (
    <section className="relative min-h-[100svh] bg-cream pt-32 lg:pt-0 overflow-hidden flex items-center border-b border-gold/40">
      {/* Deep Velvet Charcoal Block for Split Canvas Luxury */}
      <div className="absolute right-0 top-0 w-full lg:w-[45%] h-full bg-[#111115] -z-10 hidden lg:block" />
      <div className="absolute left-0 bottom-0 w-full h-[30%] bg-gradient-to-t from-[#EAE3D9] to-transparent -z-10 pointer-events-none lg:hidden" />

      {/* Fine Line Decorative Accent Frame */}
      <div className="absolute inset-x-6 inset-y-24 lg:inset-y-12 lg:inset-x-12 border border-gold/20 pointer-events-none -z-0" />

      <div className="container mx-auto px-6 md:px-12 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center lg:min-h-[85vh] relative z-10 mt-8 lg:mt-0">

          {/* Text Column */}
          <div className="relative z-10 flex flex-col justify-center lg:pl-8 xl:pl-12">

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              className="flex items-center space-x-3 mb-6"
            >
              <span className="h-px w-8 bg-gold"></span>
              <p className="font-sans text-gold tracking-[0.3em] text-xs font-semibold uppercase">
                Bespoke Decor & Wedding Styling
              </p>
            </motion.div>

            <h1 className="font-serif text-[11vw] md:text-7xl lg:text-[5.5vw] leading-[1.05] text-navy mb-8 max-w-xl">
              {words.map((word, i) => (
                <motion.span
                  key={i}
                  initial={{ opacity: 0, y: 40 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 * i, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                  className="inline-block mr-3 lg:mr-4"
                >
                  {word}
                </motion.span>
              ))}
            </h1>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1, duration: 1 }}
              className="font-sans text-charcoal/80 leading-relaxed max-w-md mb-8 text-sm md:text-base border-l-2 border-gold/40 pl-4"
            >
              From viral, contemporary Haldi Carnivals to grand, traditional Muhurthams in Bengaluru.
              We turn your vision into breathtaking visual poetry.
            </motion.p>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.2, duration: 1 }}
              className="font-sans text-navy tracking-[0.2em] text-[10px] md:text-xs font-semibold uppercase border border-gold/50 px-6 py-3 w-fit rounded-full hover:bg-gold hover:text-white transition-colors cursor-pointer"
            >
              Discover Our Styling
            </motion.p>
          </div>

          {/* Images Column */}
          <div className="relative h-[55vh] md:h-[65vh] lg:h-[85vh] w-full flex items-center justify-end mt-4 lg:mt-0 pb-10 lg:pb-0">

            {/* Offset Gold Border Frame */}
            <div className="absolute right-4 top-[10%] w-[85%] h-[80%] border border-gold/50 rounded-t-full hidden lg:block z-0" />

            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1.2, delay: 0.5 }}
              className="relative w-[90%] lg:w-[85%] h-[85%] z-10 mt-8 lg:mt-16"
            >
              {/* Vibrant Indian Wedding Main Image (Grand Floral/Lighting) */}
              <img
                src="https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=800"
                alt="Luxury Royal Wedding Setup"
                className="w-full h-full object-cover rounded-t-full shadow-[0_20px_50px_rgba(17,17,21,0.5)]"
              />

              {/* Rotating Circular Luxury Badge */}
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
                className="absolute top-[15%] -left-12 lg:-left-20 w-32 h-32 lg:w-40 lg:h-40 z-30 bg-cream/90 backdrop-blur-sm rounded-full shadow-xl hidden md:flex items-center justify-center border border-gold/20"
              >
                <svg viewBox="0 0 100 100" className="w-full h-full p-2">
                  <path id="circlePath" fill="none" d="M 50, 50 m -35, 0 a 35,35 0 1,1 70,0 a 35,35 0 1,1 -70,0" />
                  <text className="text-[11px] uppercase font-sans tracking-[0.2em] fill-navy font-semibold">
                    <textPath href="#circlePath" startOffset="0%">
                      LUXURY WEDDINGS • PREMIUM STYLING •
                    </textPath>
                  </text>
                </svg>
                {/* Center Star */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-gold text-2xl">✦</span>
                </div>
              </motion.div>

              {/* Offset Small Image (Vibrant Marigold/Yellow Haldi) */}
              <motion.div
                initial={{ opacity: 0, y: 50 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 1, delay: 0.8 }}
                className="absolute -bottom-12 -left-8 lg:-bottom-16 lg:-left-12 w-[55%] lg:w-[50%] aspect-[4/5] z-20 p-2 bg-white shadow-2xl"
              >
                <img
                  src="https://images.unsplash.com/photo-1583939003579-730e3918a45a?w=500"
                  alt="Vibrant Haldi Floral Detail"
                  className="w-full h-full object-cover"
                />
              </motion.div>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Scroll Indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2, duration: 1 }}
        className="absolute bottom-6 left-1/2 -translate-x-1/2 flex flex-col items-center z-20"
      >
        <span className="text-gold text-[10px] font-sans tracking-[0.3em] mb-2 uppercase font-semibold">Scroll</span>
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        >
          <ChevronDown className="text-gold" size={16} />
        </motion.div>
      </motion.div>
    </section>
  );
}
