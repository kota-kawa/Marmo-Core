import type { ReactNode } from 'react';

interface PageHeaderProps {
  kicker?: string;
  title: ReactNode;
  description?: string;
  className?: string;
}

export function PageHeader({ kicker, title, description, className = '' }: PageHeaderProps) {
  return (
    <header className={`mb-12 animate-fade-rise ${className}`}>
      {kicker && (
        <p className="text-xs uppercase tracking-widest text-muted-foreground">{kicker}</p>
      )}
      <h1
        className="mt-2 text-4xl font-normal leading-[1.05] tracking-tight text-foreground md:text-5xl lg:text-6xl"
        style={{ fontFamily: "'Instrument Serif', serif" }}
      >
        {title}
      </h1>
      {description && (
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
          {description}
        </p>
      )}
    </header>
  );
}
