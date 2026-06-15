import React from 'react';
import { motion } from 'framer-motion';

export const FadeUp = ({ children, delay = 0, className = '' }) => (
  <motion.div
    initial={{ opacity: 0, y: 28 }}
    whileInView={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.75, ease: [0.16, 1, 0.3, 1], delay }}
    viewport={{ once: true, margin: "-10%" }}
    className={className}
  >
    {children}
  </motion.div>
);
