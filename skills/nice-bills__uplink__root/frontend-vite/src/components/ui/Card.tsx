/**
 * Card Component - Playful Design
 */

import { type ReactNode } from 'react';
import { motion } from 'framer-motion';

interface CardProps {
    children: ReactNode;
    className?: string;
    hover?: boolean;
    padding?: 'none' | 'sm' | 'md' | 'lg';
}

const paddings = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
};

export function Card({ children, className = '', hover = true, padding = 'md' }: CardProps) {
    const Component = hover ? motion.div : 'div';
    const hoverProps = hover ? {
        whileHover: { y: -4 },
        transition: { type: 'spring', stiffness: 300, damping: 20 }
    } : {};

    return (
        <Component
            className={`${hover ? 'card' : 'card-static'} ${paddings[padding]} ${className}`}
            {...hoverProps}
        >
            {children}
        </Component>
    );
}

// Stat Card for bento grid
interface StatCardProps {
    label: string;
    value: string | number;
    icon?: ReactNode;
    color?: 'coral' | 'teal' | 'sunny';
}

const colorClasses = {
    coral: 'bg-coral-500/10 text-coral-500',
    teal: 'bg-teal-500/10 text-teal-500',
    sunny: 'bg-sunny-500/20 text-amber-600',
};

export function StatCard({ label, value, icon, color = 'coral' }: StatCardProps) {
    return (
        <Card className="text-center">
            {icon && (
                <div className={`w-12 h-12 rounded-xl ${colorClasses[color]} flex items-center justify-center mx-auto mb-3`}>
                    {icon}
                </div>
            )}
            <div className="text-3xl font-display font-bold text-slate-900 mb-1">{value}</div>
            <div className="text-sm text-slate-500">{label}</div>
        </Card>
    );
}
