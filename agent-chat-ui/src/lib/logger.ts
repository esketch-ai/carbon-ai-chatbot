/**
 * Environment-aware logger utility
 * - Development: logs everything (debug, info, warn, error)
 * - Production: only logs warnings and errors
 */

const isDev = process.env.NODE_ENV !== 'production';

export const logger = {
  /**
   * Debug level logging - only in development
   */
  debug: (...args: unknown[]) => {
    if (isDev) {
      console.debug('[DEBUG]', ...args);
    }
  },

  /**
   * Info level logging - only in development
   */
  info: (...args: unknown[]) => {
    if (isDev) {
      console.log('[INFO]', ...args);
    }
  },

  /**
   * Warning level logging - always logged
   */
  warn: (...args: unknown[]) => {
    console.warn('[WARN]', ...args);
  },

  /**
   * Error level logging - always logged
   */
  error: (...args: unknown[]) => {
    console.error('[ERROR]', ...args);
  },
};

export default logger;
