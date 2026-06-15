import { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CountdownProps {
  deadline: string;
  className?: string;
}

interface TimeLeft {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  isExpired: boolean;
}

function calculateTimeLeft(deadline: string): TimeLeft {
  const diff = new Date(deadline).getTime() - Date.now();

  if (diff <= 0) {
    return { days: 0, hours: 0, minutes: 0, seconds: 0, isExpired: true };
  }

  return {
    days: Math.floor(diff / (1000 * 60 * 60 * 24)),
    hours: Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
    minutes: Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60)),
    seconds: Math.floor((diff % (1000 * 60)) / 1000),
    isExpired: false,
  };
}

export function Countdown({ deadline, className = '' }: CountdownProps) {
  const [timeLeft, setTimeLeft] = useState<TimeLeft>(calculateTimeLeft(deadline));

  useEffect(() => {
    const timer = setInterval(() => setTimeLeft(calculateTimeLeft(deadline)), 1000);
    return () => clearInterval(timer);
  }, [deadline]);

  if (timeLeft.isExpired) {
    return (
      <span className={cn('flex items-center gap-1.5 text-xs text-muted-foreground', className)}>
        <Clock className="h-3.5 w-3.5" />
        Ended
      </span>
    );
  }

  return (
    <span className={cn('flex items-center gap-1.5 text-xs text-muted-foreground', className)}>
      <Clock className="h-3.5 w-3.5" />
      {timeLeft.days > 0 && <span>{timeLeft.days}d </span>}
      {String(timeLeft.hours).padStart(2, '0')}h {String(timeLeft.minutes).padStart(2, '0')}m
      {timeLeft.days === 0 && ` ${String(timeLeft.seconds).padStart(2, '0')}s`}
    </span>
  );
}
