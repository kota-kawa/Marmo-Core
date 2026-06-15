import winston, { type Logger } from 'winston';
import DailyRotateFile from 'winston-daily-rotate-file';
import path from 'path';

/**
 * Structured logging system using Winston
 */

// Define log levels
const levels = {
  error: 0,
  warn: 1,
  info: 2,
  http: 3,
  debug: 4,
};

// Define colors for each level
const colors = {
  error: 'red',
  warn: 'yellow',
  info: 'green',
  http: 'magenta',
  debug: 'blue',
};

winston.addColors(colors);

// Define log format
const format = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss:ms' }),
  winston.format.errors({ stack: true }),
  winston.format.splat(),
  winston.format.json()
);

// Console format for development
const consoleFormat = winston.format.combine(
  winston.format.colorize({ all: true }),
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss:ms' }),
  winston.format.printf(
    (info) => `${info.timestamp} ${info.level}: ${info.message}${info.stack ? '\n' + info.stack : ''}`
  )
);

// Define transports
const transports: winston.transport[] = [];

// Console transport (always enabled)
transports.push(
  new winston.transports.Console({
    format: consoleFormat,
  })
);

// File transports (only in production or if LOG_TO_FILE is set)
if (process.env.NODE_ENV === 'production' || process.env.LOG_TO_FILE === 'true') {
  const logDir = process.env.LOG_DIR || 'logs';

  // Error logs
  transports.push(
    new DailyRotateFile({
      filename: path.join(logDir, 'error-%DATE%.log'),
      datePattern: 'YYYY-MM-DD',
      level: 'error',
      maxSize: '20m',
      maxFiles: '14d',
      format,
    })
  );

  // Combined logs
  transports.push(
    new DailyRotateFile({
      filename: path.join(logDir, 'combined-%DATE%.log'),
      datePattern: 'YYYY-MM-DD',
      maxSize: '20m',
      maxFiles: '14d',
      format,
    })
  );

  // HTTP logs
  transports.push(
    new DailyRotateFile({
      filename: path.join(logDir, 'http-%DATE%.log'),
      datePattern: 'YYYY-MM-DD',
      level: 'http',
      maxSize: '20m',
      maxFiles: '7d',
      format,
    })
  );
}

// Create logger instance
const logger: Logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  levels,
  format,
  transports,
  exitOnError: false,
});

// Export logger methods
export default logger;

/**
 * Log an error with context
 */
export function logError(message: string, error?: Error | unknown, context?: Record<string, any>) {
  const errorObj = error instanceof Error ? error : new Error(String(error));
  logger.error(message, {
    error: {
      message: errorObj.message,
      stack: errorObj.stack,
      name: errorObj.name,
    },
    ...context,
  });
}

/**
 * Log a warning
 */
export function logWarn(message: string, context?: Record<string, any>) {
  logger.warn(message, context);
}

/**
 * Log info
 */
export function logInfo(message: string, context?: Record<string, any>) {
  logger.info(message, context);
}

/**
 * Log HTTP request
 */
export function logHttp(message: string, context?: Record<string, any>) {
  logger.http(message, context);
}

/**
 * Log debug information
 */
export function logDebug(message: string, context?: Record<string, any>) {
  logger.debug(message, context);
}

/**
 * Log API request
 */
export function logApiRequest(
  method: string,
  path: string,
  statusCode: number,
  duration: number,
  context?: Record<string, any>
) {
  logHttp(`${method} ${path} ${statusCode} ${duration}ms`, {
    method,
    path,
    statusCode,
    duration,
    ...context,
  });
}

/**
 * Log database query
 */
export function logDbQuery(query: string, duration: number, context?: Record<string, any>) {
  logDebug(`DB Query: ${query} (${duration}ms)`, {
    query,
    duration,
    ...context,
  });
}

/**
 * Log indexing progress
 */
export function logIndexing(
  repositoryId: string,
  progress: number,
  currentFile?: string,
  context?: Record<string, any>
) {
  logInfo(`Indexing progress: ${progress}%`, {
    repositoryId,
    progress,
    currentFile,
    ...context,
  });
}

/**
 * Log cache hit/miss
 */
export function logCache(hit: boolean, key: string, context?: Record<string, any>) {
  logDebug(`Cache ${hit ? 'HIT' : 'MISS'}: ${key}`, {
    hit,
    key,
    ...context,
  });
}

/**
 * Log performance metric
 */
export function logPerformance(
  operation: string,
  duration: number,
  context?: Record<string, any>
) {
  logInfo(`Performance: ${operation} took ${duration}ms`, {
    operation,
    duration,
    ...context,
  });
}

/**
 * Create a child logger with default context
 */
export function createChildLogger(defaultContext: Record<string, any>) {
  return {
    error: (message: string, context?: Record<string, any>) =>
      logError(message, undefined, { ...defaultContext, ...context }),
    warn: (message: string, context?: Record<string, any>) =>
      logWarn(message, { ...defaultContext, ...context }),
    info: (message: string, context?: Record<string, any>) =>
      logInfo(message, { ...defaultContext, ...context }),
    http: (message: string, context?: Record<string, any>) =>
      logHttp(message, { ...defaultContext, ...context }),
    debug: (message: string, context?: Record<string, any>) =>
      logDebug(message, { ...defaultContext, ...context }),
  };
}
