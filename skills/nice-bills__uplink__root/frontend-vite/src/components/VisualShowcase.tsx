/**
 * Homepage gallery — cohesive navy stills, smooth staggered reveal
 */

import { motion } from 'framer-motion';
import { SHOWCASE_GALLERY } from '@/lib/media';
import { fadeUp } from '@/lib/motion';
import { MediaImage } from './MediaImage';
import { cn } from '@/lib/utils';

const layout = [
  'md:col-span-2 md:row-span-2',
  'md:col-span-1',
  'md:col-span-1',
  'md:col-span-1 md:row-span-2',
  'md:col-span-1',
  'md:col-span-2',
];

export function VisualShowcase() {
  return (
    <section className="section-flow relative z-10 py-24">
      <div className="container">
        <motion.div
          custom={0}
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-80px' }}
          className="mb-12 max-w-2xl"
        >
          <p className="text-xs uppercase tracking-widest text-muted-foreground">
            The network
          </p>
          <h2
            className="mt-2 text-4xl text-foreground md:text-5xl"
            style={{ fontFamily: "'Instrument Serif', serif" }}
          >
            Agents, capital, and{' '}
            <em className="not-italic text-muted-foreground">momentum.</em>
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            One visual language across Genesis — deep focus, on-chain momentum, calm
            glass surfaces over the same cinematic light.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4 md:grid-rows-2 md:auto-rows-[minmax(200px,1fr)]">
          {SHOWCASE_GALLERY.map((item, index) => (
            <motion.figure
              key={item.id}
              custom={index * 0.06}
              variants={fadeUp}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-40px' }}
              className={cn(
                'group relative min-h-[220px] overflow-hidden rounded-2xl liquid-glass',
                layout[index],
              )}
            >
              <MediaImage
                src={item.src}
                alt={item.alt}
                className="absolute inset-0 h-full w-full transition-transform duration-700 ease-smooth group-hover:scale-[1.03]"
                priority={index < 2}
              />
              <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-background/95 via-background/50 to-transparent px-5 py-4">
                <p className="text-sm text-foreground/90">{item.alt}</p>
              </figcaption>
            </motion.figure>
          ))}
        </div>
      </div>
    </section>
  );
}
