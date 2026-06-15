/**
 * Badge Component - Playful Design
 */

import type { ReactNode } from 'react';

export interface BadgeProps {
    variant?: 'default' | 'active' | 'completed' | 'funding';
    children: ReactNode;
    className?: string;
}

const variantClasses = {
    default: 'bg-slate-100 text-slate-600',
    active: 'badge-active',
    completed: 'badge-completed',
    funding: 'badge-funding',
};

export function Badge({ variant = 'default', children, className = '' }: BadgeProps) {
    return (
        <span className={`badge ${variantClasses[variant]} ${className}`}>
            {children}
        </span>
    );
}

export function ActiveBadge() {
    return (
        <Badge variant="active">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
            Active
        </Badge>
    );
}

export function CompletedBadge() {
    return <Badge variant="completed">Completed</Badge>;
}

export function FundingBadge() {
    return <Badge variant="funding">🎯 Funding</Badge>;
}
