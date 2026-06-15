import { cn } from '@/lib/utils';

interface ProgressProps {
  value: number;
  className?: string;
  size?: 'sm' | 'md';
}

export function Progress({ value, className, size = 'md' }: ProgressProps) {
  const clamped = Math.min(Math.max(value, 0), 100);

  return (
    <div
      className={cn(
        'w-full overflow-hidden rounded-full bg-secondary/80',
        size === 'sm' ? 'h-1' : 'h-1.5',
        className,
      )}
    >
      <div
        className="h-full rounded-full bg-foreground/90 transition-all duration-500 ease-out"
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
