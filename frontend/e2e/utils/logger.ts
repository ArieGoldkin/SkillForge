/**
 * E2E Test Logging Utility - Node.js compatible structured logging
 *
 * Provides consistent logging for E2E tests with appropriate log levels
 * and structured data. In CI, outputs JSON for log aggregation.
 * In local development, outputs pretty console messages for debugging.
 *
 * Follows December 2025 best practices:
 * - Structured JSON logging for CI environments
 * - Pretty console output for local development
 * - Log levels: debug, info, warn, error
 * - ISO timestamp formatting
 * - Context objects for structured data
 *
 * @see https://playwright.dev/docs/best-practices
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogContext {
  [key: string]: unknown;
}

interface LogData {
  level: LogLevel;
  message: string;
  timestamp: string;
  context?: LogContext;
}

class Logger {
  private readonly isCI: boolean;

  constructor() {
    // Detect CI environment (GitHub Actions, CircleCI, etc.)
    // Also treat production NODE_ENV as CI for structured logging
    this.isCI = !!process.env.CI || process.env.NODE_ENV === 'production';
  }

  /**
   * Internal logging method that handles output formatting
   */
  private log(level: LogLevel, message: string, context?: LogContext): void {
    const timestamp = new Date().toISOString();
    const logData: LogData = {
      level,
      message,
      timestamp,
      ...(context && { context }),
    };

    if (this.isCI) {
      // CI: Structured JSON logging for log aggregation tools
      // Single line JSON per log entry for easy parsing
      console.log(JSON.stringify(logData));
    } else {
      // Local: Pretty console output for developer experience
      const prefix = `[${level.toUpperCase()}]`;
      const contextStr = context ? ` ${JSON.stringify(context, null, 2)}` : '';

      switch (level) {
        case 'debug':
          console.debug(`${prefix} ${message}${contextStr}`);
          break;
        case 'info':
          console.info(`${prefix} ${message}${contextStr}`);
          break;
        case 'warn':
          console.warn(`${prefix} ${message}${contextStr}`);
          break;
        case 'error':
          console.error(`${prefix} ${message}${contextStr}`);
          break;
      }
    }
  }

  /**
   * Log debug-level messages (detailed diagnostic information)
   */
  debug(message: string, context?: LogContext): void {
    this.log('debug', message, context);
  }

  /**
   * Log info-level messages (general informational messages)
   */
  info(message: string, context?: LogContext): void {
    this.log('info', message, context);
  }

  /**
   * Log warn-level messages (warnings that don't prevent execution)
   */
  warn(message: string, context?: LogContext): void {
    this.log('warn', message, context);
  }

  /**
   * Log error-level messages (errors that may prevent execution)
   */
  error(message: string, context?: LogContext): void {
    this.log('error', message, context);
  }
}

// Create singleton instance
export const logger = new Logger();

/**
 * Log a setup step (for global setup, fixtures, etc.)
 */
export const logSetupStep = (message: string, context?: LogContext): void => {
  logger.info(`Setup: ${message}`, context);
};

/**
 * Log a test step (for test execution steps)
 */
export const logTestStep = (message: string, context?: LogContext): void => {
  logger.info(`Test Step: ${message}`, context);
};

/**
 * Log performance metrics
 */
export const logPerformance = (
  metric: string,
  value: number,
  context?: LogContext
): void => {
  logger.info(`Performance: ${metric}`, { value, ...context });
};

/**
 * Log errors with enhanced context (stack traces, error details)
 */
export const logError = (
  error: Error | string,
  context?: LogContext
): void => {
  const message = error instanceof Error ? error.message : error;
  const errorContext: LogContext = {
    ...(error instanceof Error && {
      stack: error.stack,
      name: error.name,
    }),
    ...context,
  };

  logger.error(message, errorContext);
};
