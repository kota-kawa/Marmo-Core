import { logPerformance, logInfo } from './logger';

/**
 * Performance monitoring and metrics collection
 */

interface Metric {
  name: string;
  value: number;
  timestamp: number;
  tags?: Record<string, string>;
}

class MetricsCollector {
  private metrics: Metric[] = [];
  private readonly maxMetrics = 1000;

  /**
   * Record a metric
   */
  record(name: string, value: number, tags?: Record<string, string>) {
    const metric: Metric = {
      name,
      value,
      timestamp: Date.now(),
      tags,
    };

    this.metrics.push(metric);

    // Keep only last N metrics
    if (this.metrics.length > this.maxMetrics) {
      this.metrics.shift();
    }

    // Log performance metrics
    logPerformance(name, value, tags);
  }

  /**
   * Get metrics by name
   */
  getMetrics(name: string): Metric[] {
    return this.metrics.filter(m => m.name === name);
  }

  /**
   * Get average value for a metric
   */
  getAverage(name: string): number {
    const metrics = this.getMetrics(name);
    if (metrics.length === 0) return 0;
    
    const sum = metrics.reduce((acc, m) => acc + m.value, 0);
    return sum / metrics.length;
  }

  /**
   * Get percentile for a metric
   */
  getPercentile(name: string, percentile: number): number {
    const metrics = this.getMetrics(name);
    if (metrics.length === 0) return 0;
    
    const sorted = metrics.map(m => m.value).sort((a, b) => a - b);
    const index = Math.ceil((percentile / 100) * sorted.length) - 1;
    return sorted[index];
  }

  /**
   * Get all metrics summary
   */
  getSummary(): Record<string, any> {
    const summary: Record<string, any> = {};
    
    const uniqueNames = [...new Set(this.metrics.map(m => m.name))];
    
    for (const name of uniqueNames) {
      summary[name] = {
        count: this.getMetrics(name).length,
        avg: this.getAverage(name),
        p50: this.getPercentile(name, 50),
        p95: this.getPercentile(name, 95),
        p99: this.getPercentile(name, 99),
      };
    }
    
    return summary;
  }

  /**
   * Clear all metrics
   */
  clear() {
    this.metrics = [];
  }
}

// Singleton instance
export const metrics = new MetricsCollector();

/**
 * Timer utility for measuring execution time
 */
export class Timer {
  private startTime: number;
  private name: string;
  private tags?: Record<string, string>;

  constructor(name: string, tags?: Record<string, string>) {
    this.name = name;
    this.tags = tags;
    this.startTime = Date.now();
  }

  /**
   * Stop timer and record metric
   */
  stop(): number {
    const duration = Date.now() - this.startTime;
    metrics.record(this.name, duration, this.tags);
    return duration;
  }

  /**
   * Get elapsed time without stopping
   */
  elapsed(): number {
    return Date.now() - this.startTime;
  }
}

/**
 * Decorator for measuring function execution time
 */
export function measureTime(metricName?: string) {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;
    const name = metricName || `${target.constructor.name}.${propertyKey}`;

    descriptor.value = async function (...args: any[]) {
      const timer = new Timer(name);
      try {
        const result = await originalMethod.apply(this, args);
        timer.stop();
        return result;
      } catch (error) {
        timer.stop();
        throw error;
      }
    };

    return descriptor;
  };
}

/**
 * Measure async function execution time
 */
export async function measure<T>(
  name: string,
  fn: () => Promise<T>,
  tags?: Record<string, string>
): Promise<T> {
  const timer = new Timer(name, tags);
  try {
    const result = await fn();
    timer.stop();
    return result;
  } catch (error) {
    timer.stop();
    throw error;
  }
}

/**
 * System metrics collection
 */
export function collectSystemMetrics() {
  const memUsage = process.memoryUsage();
  
  metrics.record('system.memory.rss', memUsage.rss, { unit: 'bytes' });
  metrics.record('system.memory.heapTotal', memUsage.heapTotal, { unit: 'bytes' });
  metrics.record('system.memory.heapUsed', memUsage.heapUsed, { unit: 'bytes' });
  metrics.record('system.memory.external', memUsage.external, { unit: 'bytes' });
  
  const cpuUsage = process.cpuUsage();
  metrics.record('system.cpu.user', cpuUsage.user, { unit: 'microseconds' });
  metrics.record('system.cpu.system', cpuUsage.system, { unit: 'microseconds' });
  
  logInfo('System metrics collected', {
    memory: {
      rss: `${(memUsage.rss / 1024 / 1024).toFixed(2)} MB`,
      heapUsed: `${(memUsage.heapUsed / 1024 / 1024).toFixed(2)} MB`,
    },
  });
}

/**
 * Start periodic system metrics collection
 */
export function startMetricsCollection(intervalMs: number = 60000) {
  // Collect immediately
  collectSystemMetrics();
  
  // Then collect periodically
  const interval = setInterval(collectSystemMetrics, intervalMs);
  
  // Cleanup on process exit
  process.on('SIGINT', () => {
    clearInterval(interval);
  });
  
  process.on('SIGTERM', () => {
    clearInterval(interval);
  });
  
  return interval;
}
