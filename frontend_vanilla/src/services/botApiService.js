/**
 * Bot API Service
 * 
 * Handles all bot-related API calls to the backend
 * Provides methods for CRUD operations and bot management
 * 
 * Features:
 * - Full CRUD operations for bots
 * - Error handling and validation
 * - Consistent API response format
 * - Status toggle operations
 * - Async/await patterns
 */

import { API_BASE_URL } from '../config/env.js';

/**
 * Fetch all bots from the backend
 * @returns {Promise<Array>} Array of bot objects
 */
export async function fetchBots() {
  try {
    const response = await fetch(`${API_BASE_URL}/bots`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to fetch bots');
    }

    const data = await response.json();
    return data.bots || [];
  } catch (error) {
    console.error('Error fetching bots:', error);
    throw error;
  }
}

/**
 * Create a new bot
 * @param {Object} botData - Bot data object
 * @param {string} botData.name - Bot name
 * @param {string} botData.symbol - Trading symbol
 * @param {boolean} botData.isActive - Bot active status
 * @param {string} [botData.description] - Bot description
 * @returns {Promise<Object>} Created bot object
 */
export async function createBot(botData) {
  try {
    // Validate required fields
    if (!botData.name || !botData.symbol) {
      throw new Error('Bot name and symbol are required');
    }

    const response = await fetch(`${API_BASE_URL}/bots`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: botData.name.trim(),
        symbol: botData.symbol,
        isActive: botData.isActive !== undefined ? botData.isActive : true,
        isPaperTrading: botData.isPaperTrading !== undefined ? botData.isPaperTrading : true,
        description: botData.description ? botData.description.trim() : null,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to create bot');
    }

    const createdBot = await response.json();
    return createdBot;
  } catch (error) {
    console.error('Error creating bot:', error);
    throw error;
  }
}

/**
 * Update an existing bot
 * @param {string} botId - Bot ID
 * @param {Object} botData - Updated bot data
 * @returns {Promise<Object>} Updated bot object
 */
export async function updateBot(botId, botData) {
  try {
    if (!botId) {
      throw new Error('Bot ID is required');
    }

    const response = await fetch(`${API_BASE_URL}/bots/${botId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: botData.name ? botData.name.trim() : undefined,
        symbol: botData.symbol,
        isActive: botData.isActive,
        isPaperTrading: botData.isPaperTrading,
        description: botData.description ? botData.description.trim() : undefined,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to update bot');
    }

    const updatedBot = await response.json();
    return updatedBot;
  } catch (error) {
    console.error('Error updating bot:', error);
    throw error;
  }
}

/**
 * Delete a bot
 * @param {string} botId - Bot ID
 * @returns {Promise<void>}
 */
export async function deleteBot(botId) {
  try {
    if (!botId) {
      throw new Error('Bot ID is required');
    }

    const response = await fetch(`${API_BASE_URL}/bots/${botId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to delete bot');
    }

    // DELETE request typically doesn't return content
    return;
  } catch (error) {
    console.error('Error deleting bot:', error);
    throw error;
  }
}

/**
 * Toggle bot active status
 * @param {string} botId - Bot ID
 * @param {boolean} isActive - New active status
 * @returns {Promise<Object>} Updated bot object
 */
export async function toggleBotStatus(botId, isActive) {
  try {
    if (!botId) {
      throw new Error('Bot ID is required');
    }

    const response = await fetch(`${API_BASE_URL}/bots/${botId}/status?is_active=${isActive}`, {
      method: 'PATCH',
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to toggle bot status');
    }

    const updatedBot = await response.json();
    return updatedBot;
  } catch (error) {
    console.error('Error toggling bot status:', error);
    throw error;
  }
}

/**
 * Get bot by ID
 * @param {string} botId - Bot ID
 * @returns {Promise<Object>} Bot object
 */
export async function getBotById(botId) {
  try {
    if (!botId) {
      throw new Error('Bot ID is required');
    }

    const response = await fetch(`${API_BASE_URL}/bots/${botId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to fetch bot');
    }

    const bot = await response.json();
    return bot;
  } catch (error) {
    console.error('Error fetching bot:', error);
    throw error;
  }
}

/**
 * Get bot statistics
 * @returns {Promise<Object>} Bot statistics object
 */
export async function getBotStats() {
  try {
    const response = await fetch(`${API_BASE_URL}/bots/stats`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to fetch bot statistics');
    }

    const stats = await response.json();
    return stats;
  } catch (error) {
    console.error('Error fetching bot stats:', error);
    throw error;
  }
}

/**
 * Validate bot data before sending to API
 * @param {Object} botData - Bot data to validate
 * @returns {Object} Validation result
 */
export function validateBotData(botData) {
  const errors = {};
  
  // Name validation
  if (!botData.name || typeof botData.name !== 'string') {
    errors.name = 'Bot name is required';
  } else if (botData.name.trim().length < 3) {
    errors.name = 'Bot name must be at least 3 characters';
  } else if (botData.name.trim().length > 50) {
    errors.name = 'Bot name must be less than 50 characters';
  }
  
  // Symbol validation
  if (!botData.symbol || typeof botData.symbol !== 'string') {
    errors.symbol = 'Trading symbol is required';
  }
  
  // Description validation (optional)
  if (botData.description && typeof botData.description === 'string' && botData.description.trim().length > 200) {
    errors.description = 'Description must be less than 200 characters';
  }
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors
  };
}

/**
 * Format bot data for API submission
 * @param {Object} botData - Raw bot data
 * @returns {Object} Formatted bot data
 */
export function formatBotDataForApi(botData) {
  return {
    name: botData.name ? botData.name.trim() : '',
    symbol: botData.symbol || '',
    isActive: botData.isActive !== undefined ? Boolean(botData.isActive) : true,
    isPaperTrading: botData.isPaperTrading !== undefined ? Boolean(botData.isPaperTrading) : true,
    description: botData.description ? botData.description.trim() : null,
  };
}

/**
 * Handle API errors consistently
 * @param {Error} error - Error object
 * @returns {string} User-friendly error message
 */
export function handleApiError(error) {
  if (error.message) {
    return error.message;
  }
  
  if (error.response && error.response.data) {
    return error.response.data.detail || error.response.data.message || 'An error occurred';
  }
  
  return 'An unexpected error occurred';
}

/**
 * Check if bot name is unique (client-side validation)
 * @param {string} name - Bot name to check
 * @param {Array} existingBots - Array of existing bots
 * @param {string} [excludeBotId] - Bot ID to exclude from check (for updates)
 * @returns {boolean} True if name is unique
 */
export function isBotNameUnique(name, existingBots, excludeBotId = null) {
  if (!name || !Array.isArray(existingBots)) {
    return false;
  }
  
  const trimmedName = name.trim().toLowerCase();
  
  return !existingBots.some(bot => 
    bot.id !== excludeBotId && 
    bot.name.toLowerCase() === trimmedName
  );
}

/**
 * Filter bots by status
 * @param {Array} bots - Array of bot objects
 * @param {boolean} isActive - Filter by active status
 * @returns {Array} Filtered bots
 */
export function filterBotsByStatus(bots, isActive) {
  if (!Array.isArray(bots)) {
    return [];
  }
  
  return bots.filter(bot => bot.isActive === isActive);
}

/**
 * Sort bots by creation date (newest first)
 * @param {Array} bots - Array of bot objects
 * @returns {Array} Sorted bots
 */
export function sortBotsByCreatedAt(bots) {
  if (!Array.isArray(bots)) {
    return [];
  }
  
  return [...bots].sort((a, b) => {
    const dateA = new Date(a.createdAt);
    const dateB = new Date(b.createdAt);
    return dateB - dateA; // Newest first
  });
}