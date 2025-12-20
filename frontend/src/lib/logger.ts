/* eslint-disable no-console -- Logger utility is designed to use console methods for structured logging in both development and production environments */

/**
 * Frontend logging utility - structured logging for production
 *
 * Provides consistent logging across the application with appropriate
 * log levels and structured data. In development, logs to console.
 * In production, could be sent to analytics/monitoring services.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogContext {
  [key: string]: unknown
}

class Logger {
  private isDevelopment = import.meta.env.DEV

  private log(level: LogLevel, message: string, context?: LogContext): void {
    const timestamp = new Date().toISOString()
    const logData = {
      level,
      message,
      timestamp,
      context,
    }

    if (this.isDevelopment) {
      // Development: pretty console output
      const prefix = `[${level.toUpperCase()}]`
      switch (level) {
        case 'debug':
          console.debug(`${prefix} ${message}`, context || '')
          break
        case 'info':
          console.info(`${prefix} ${message}`, context || '')
          break
        case 'warn':
          console.warn(`${prefix} ${message}`, context || '')
          break
        case 'error':
          console.error(`${prefix} ${message}`, context || '')
          break
      }
    } else {
      // Production: structured logging (could send to analytics)
      console.log(JSON.stringify(logData))
    }
  }

  debug(message: string, context?: LogContext): void {
    this.log('debug', message, context)
  }

  info(message: string, context?: LogContext): void {
    this.log('info', message, context)
  }

  warn(message: string, context?: LogContext): void {
    this.log('warn', message, context)
  }

  error(message: string, context?: LogContext): void {
    this.log('error', message, context)
  }
}

// Create singleton instance
export const logger = new Logger()

// Convenience functions for common use cases
export const logPerformance = (metric: string, value: number, context?: LogContext) => {
  logger.info(`Performance: ${metric}`, { value, ...context })
}

export const logError = (error: Error | string, context?: LogContext) => {
  const message = error instanceof Error ? error.message : error
  const errorContext = error instanceof Error ? { stack: error.stack, ...context } : context
  logger.error(message, errorContext)
}

export const logWebVitals = (
  metric: string,
  value: number,
  rating: string,
  context?: LogContext
) => {
  logger.info(`Web Vitals: ${metric}`, { value, rating, ...context })
}
