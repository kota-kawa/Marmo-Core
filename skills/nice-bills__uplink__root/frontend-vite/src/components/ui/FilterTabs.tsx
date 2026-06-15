import { cn } from '@/lib/utils';

interface FilterTabsProps<T extends string> {
  options: readonly T[];
  value: T;
  onChange: (value: T) => void;
  labels?: Partial<Record<T, string>>;
  className?: string;
}

export function FilterTabs<T extends string>({
  options,
  value,
  onChange,
  labels,
  className,
}: FilterTabsProps<T>) {
  return (
    <div
      className={cn(
        'liquid-glass inline-flex flex-wrap gap-1 rounded-full p-1',
        className,
      )}
      role="tablist"
    >
      {options.map((option) => (
        <button
          key={option}
          type="button"
          role="tab"
          aria-selected={value === option}
          onClick={() => onChange(option)}
          className={cn(
            'rounded-full px-4 py-2 text-sm capitalize transition-colors',
            value === option
              ? 'bg-foreground/10 text-foreground'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {labels?.[option] ?? option}
        </button>
      ))}
    </div>
  );
}
