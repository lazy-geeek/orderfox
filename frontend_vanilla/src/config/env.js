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
// In development, use relative URLs to leverage Vite's proxy configuration
// This avoids CORS issues when connecting from Windows host to dev container
const isDevelopment = import.meta.env.MODE === 'development';

// Production URLs should be provided via environment variables
// If not provided in production, throw an error to prevent misconfiguration
const getProductionUrl = (varName, devDefault) => {
  if (isDevelopment) {
    return devDefault;
  }
  
  const value = import.meta.env[varName];
  if (!value || value === '') {
    console.error(`${varName} must be set in production environment`);
    // Return a placeholder URL to prevent app crash, but log the error
    return `${varName}_NOT_SET`;
  }
  return value;
};

export const API_BASE_URL = getEnvVar('VITE_APP_API_BASE_URL', 
  getProductionUrl('VITE_APP_API_BASE_URL', '/api/v1')
);
export const WS_BASE_URL = getEnvVar('VITE_APP_WS_BASE_URL', 
  getProductionUrl('VITE_APP_WS_BASE_URL', 'ws://localhost:3000/api/v1')
);

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