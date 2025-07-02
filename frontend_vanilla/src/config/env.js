/**
 * Environment configuration for the frontend application.
 * 
 * In Vite, environment variables prefixed with VITE_ are automatically
 * exposed to the client-side code via import.meta.env
 */

// Get environment variables with fallback defaults
const getEnvVar = (name, defaultValue) => {
  const value = import.meta.env[name];
  if (value === undefined || value === '') {
    // Only log missing env vars in development mode
    if (import.meta.env.MODE === 'development' && import.meta.env.VITE_DEBUG_LOGGING === 'true') {
      console.warn(`Environment variable ${name} not set, using default: ${defaultValue}`);
    }
    return defaultValue;
  }
  return value;
};

// API and WebSocket base URLs from environment variables
// In development, use relative URLs to leverage Vite's proxy configuration
// This avoids CORS issues when connecting from Windows host to dev container
const isDevelopment = import.meta.env.MODE === 'development';
export const API_BASE_URL = getEnvVar('VITE_APP_API_BASE_URL', 
  isDevelopment ? '/api/v1' : 'http://localhost:8000/api/v1'
);
export const WS_BASE_URL = getEnvVar('VITE_APP_WS_BASE_URL', 
  isDevelopment ? '/api/v1' : 'ws://localhost:8000/api/v1'
);

// Feature flags
export const USE_BACKEND_AGGREGATION = getEnvVar('VITE_USE_BACKEND_AGGREGATION', 'false') === 'true';

// Log current configuration (useful for debugging)
if (import.meta.env.VITE_DEBUG_LOGGING === 'true') {
  console.log('Frontend Configuration:', {
    API_BASE_URL,
    WS_BASE_URL,
    USE_BACKEND_AGGREGATION,
    NODE_ENV: import.meta.env.MODE
  });
}

export default {
  API_BASE_URL,
  WS_BASE_URL,
  USE_BACKEND_AGGREGATION
};