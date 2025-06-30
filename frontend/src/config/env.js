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
    console.warn(`Environment variable ${name} not set, using default: ${defaultValue}`);
    return defaultValue;
  }
  return value;
};

// API and WebSocket base URLs from environment variables
export const API_BASE_URL = getEnvVar('VITE_APP_API_BASE_URL', 'http://localhost:8000/api/v1');
export const WS_BASE_URL = getEnvVar('VITE_APP_WS_BASE_URL', 'ws://localhost:8080');

// Log current configuration (useful for debugging)
console.log('Frontend Configuration:', {
  API_BASE_URL,
  WS_BASE_URL,
  NODE_ENV: import.meta.env.MODE
});

export default {
  API_BASE_URL,
  WS_BASE_URL
};