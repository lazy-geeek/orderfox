/**
 * Feature flag service for gradual rollout capabilities
 */

import { USE_BACKEND_AGGREGATION } from '../config/env.js';

class FeatureFlagService {
  constructor() {
    this.flags = {
      backendAggregation: USE_BACKEND_AGGREGATION,
    };
    
    // Simple gradual rollout based on session ID hash
    this.sessionId = this.generateSessionId();
    this.rolloutPercentage = this.getRolloutPercentage();
  }

  generateSessionId() {
    // Generate a stable session ID for this browser session
    let sessionId = sessionStorage.getItem('orderfox_session_id');
    if (!sessionId) {
      sessionId = Date.now().toString(36) + Math.random().toString(36).substr(2);
      sessionStorage.setItem('orderfox_session_id', sessionId);
    }
    return sessionId;
  }

  getRolloutPercentage() {
    // Get rollout percentage from environment or default to 0
    const rolloutEnv = import.meta.env.VITE_BACKEND_AGGREGATION_ROLLOUT;
    return rolloutEnv ? parseInt(rolloutEnv, 10) : 0;
  }

  hashCode(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash);
  }

  isInRollout(feature) {
    if (feature === 'backendAggregation') {
      // If explicitly enabled via environment, always use it
      if (this.flags.backendAggregation) {
        return true;
      }
      
      // Check if user is in rollout percentage
      const hash = this.hashCode(this.sessionId);
      const userPercentile = hash % 100;
      return userPercentile < this.rolloutPercentage;
    }
    
    return false;
  }

  useBackendAggregation() {
    return this.isInRollout('backendAggregation');
  }

  // For debugging and monitoring
  getDebugInfo() {
    return {
      sessionId: this.sessionId,
      rolloutPercentage: this.rolloutPercentage,
      flags: this.flags,
      backendAggregationEnabled: this.useBackendAggregation()
    };
  }
}

// Export singleton instance
export const featureFlags = new FeatureFlagService();

// Log feature flag status
console.log('Feature Flags Debug Info:', featureFlags.getDebugInfo());

export default featureFlags;