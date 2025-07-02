/**
 * Frontend logging utility with debug control
 */

const DEBUG_LOGGING = import.meta.env.VITE_DEBUG_LOGGING === 'true';

export const logger = {
  debug: (...args) => {
    if (DEBUG_LOGGING) {
      console.log(...args);
    }
  },
  
  info: (...args) => {
    if (DEBUG_LOGGING) {
      console.info(...args);
    }
  },
  
  warn: (...args) => {
    if (DEBUG_LOGGING) {
      console.warn(...args);
    }
  },
  
  error: (...args) => {
    // Always log errors
    console.error(...args);
  },
  
  // Always log (for important messages)
  log: (...args) => {
    console.log(...args);
  }
};

export default logger;