/**
 * BotEditor modal component for creating and editing bots
 * 
 * Features:
 * - DaisyUI modal design
 * - Form validation
 * - Symbol selection from existing symbols
 * - Create/Edit modes
 * - Error handling
 */

import { createSearchableDropdown } from './SearchableDropdown.js';

export function createBotEditor() {
  const modal = document.createElement('div');
  modal.id = 'bot-editor-modal';
  modal.className = 'modal';
  modal.setAttribute('data-testid', 'bot-editor-modal');
  
  modal.innerHTML = `
    <label class="modal-backdrop" for=""></label>
    <div class="modal-box w-11/12 max-w-2xl">
      <div class="flex justify-between items-center mb-6">
        <h3 class="font-bold text-lg" id="modal-title">Create New Bot</h3>
        <button class="btn btn-sm btn-circle btn-ghost" id="close-modal-btn">✕</button>
      </div>
      
      <form id="bot-form" class="space-y-6">
        <!-- Bot Name -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Bot Name *</span>
          </label>
          <input 
            type="text" 
            id="bot-name" 
            name="name"
            placeholder="Enter bot name (e.g., 'My BTC Scalper')" 
            class="input input-bordered w-full" 
            required
            maxlength="50"
            data-testid="bot-name-input"
          />
          <label class="label">
            <span class="label-text-alt text-error hidden" id="name-error"></span>
          </label>
        </div>
        
        <!-- Symbol Selection -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Trading Symbol *</span>
          </label>
          <div id="symbol-dropdown-container"></div>
          <label class="label">
            <span class="label-text-alt text-error hidden" id="symbol-error"></span>
          </label>
        </div>
        
        <!-- Bot Settings -->
        <div class="form-control space-y-4">
          <label class="label">
            <span class="label-text font-semibold">Bot Settings</span>
          </label>
          
          <!-- Active Toggle -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="label-text font-semibold">Active</span>
              <input 
                type="checkbox" 
                id="bot-active" 
                name="isActive"
                class="toggle toggle-success" 
                checked
              />
            </div>
            <p id="status-text" class="text-sm text-base-content/60">Bot will start trading immediately</p>
          </div>
          
          <!-- Paper Trading Toggle -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="label-text font-semibold">Paper Trading</span>
              <input 
                type="checkbox" 
                id="bot-paper-trading" 
                name="isPaperTrading" 
                class="toggle toggle-info" 
                checked 
              />
            </div>
            <p id="paper-trading-text" class="text-sm text-base-content/60">Paper trading mode (simulated trades)</p>
          </div>
        </div>
        
        <!-- Bot Description (Optional) -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Description (Optional)</span>
          </label>
          <textarea 
            id="bot-description" 
            name="description"
            placeholder="Describe your bot's trading strategy..." 
            class="textarea textarea-bordered w-full h-24"
            maxlength="200"
          ></textarea>
          <label class="label">
            <span class="label-text-alt">
              <span id="description-count">0</span>/200 characters
            </span>
          </label>
        </div>
        
        <!-- Error Display -->
        <div class="alert alert-error hidden" id="form-error">
          <span class="text-sm" id="form-error-message"></span>
        </div>
        
        <!-- Success Display -->
        <div class="alert alert-success hidden" id="form-success">
          <span class="text-sm" id="form-success-message"></span>
        </div>
        
        <!-- Modal Actions -->
        <div class="modal-action">
          <button type="button" class="btn btn-ghost" id="cancel-btn" data-testid="cancel-bot-button">Cancel</button>
          <button type="submit" class="btn btn-primary" id="save-btn" data-testid="save-bot-button">
            <span class="loading loading-spinner loading-sm hidden" id="save-loading"></span>
            <span id="save-text">Create Bot</span>
          </button>
        </div>
      </form>
    </div>
  `;
  
  // Create searchable dropdown
  const symbolDropdown = createSearchableDropdown({
    id: 'bot-symbol',
    name: 'symbol',
    placeholder: 'Select a trading pair',
    required: true,
    className: 'w-full',
    testId: 'bot-symbol-dropdown'
  });
  
  // Add dropdown to container
  const dropdownContainer = modal.querySelector('#symbol-dropdown-container');
  dropdownContainer.appendChild(symbolDropdown);
  
  // Store reference to dropdown on modal
  modal._symbolDropdown = symbolDropdown;
  
  return modal;
}

/**
 * Show bot editor modal
 * @param {HTMLElement} modal - Modal element
 * @param {Object} options - Modal options
 */
export function showBotEditor(modal, options = {}) {
  const { bot = null, symbols = [], mode = 'create' } = options;
  
  // Update modal title and button text
  const modalTitle = modal.querySelector('#modal-title');
  const saveBtn = modal.querySelector('#save-text');
  
  if (mode === 'edit' && bot) {
    modalTitle.textContent = `Edit Bot: ${bot.name}`;
    saveBtn.textContent = 'Update Bot';
  } else {
    modalTitle.textContent = 'Create New Bot';
    saveBtn.textContent = 'Create Bot';
  }
  
  // Populate symbol dropdown
  const symbolOptions = symbols.map(symbol => ({
    id: symbol.id,
    label: `${symbol.uiName} (${symbol.volume24hFormatted})`,
    data: symbol
  }));
  
  modal._symbolDropdown.setOptions(symbolOptions);
  
  // Populate form if editing
  if (mode === 'edit' && bot) {
    modal.querySelector('#bot-name').value = bot.name;
    modal._symbolDropdown.setValue(bot.symbol);
    modal.querySelector('#bot-active').checked = bot.isActive;
    modal.querySelector('#bot-paper-trading').checked = bot.isPaperTrading ?? true;
    modal.querySelector('#bot-description').value = bot.description || '';
  } else {
    resetBotForm(modal);
  }
  
  // Update status text
  updateStatusText(modal);
  updatePaperTradingText(modal);
  
  // Show modal
  modal.classList.add('modal-open');
  
  // Focus on name input
  setTimeout(() => {
    modal.querySelector('#bot-name').focus();
  }, 100);
}

/**
 * Hide bot editor modal
 * @param {HTMLElement} modal - Modal element
 */
export function hideBotEditor(modal) {
  modal.classList.remove('modal-open');
  clearFormErrors(modal);
  resetBotForm(modal);
  // Reset loading state as safety measure
  setFormLoading(modal, false);
}

/**
 * Reset bot form to default values
 * @param {HTMLElement} modal - Modal element
 */
export function resetBotForm(modal) {
  const form = modal.querySelector('#bot-form');
  form.reset();
  modal.querySelector('#bot-active').checked = true;
  modal._symbolDropdown.setValue(null);
  updateStatusText(modal);
  updateDescriptionCount(modal);
}

/**
 * Update status text based on toggle state
 * @param {HTMLElement} modal - Modal element
 */
export function updateStatusText(modal) {
  const toggle = modal.querySelector('#bot-active');
  const statusText = modal.querySelector('#status-text');
  
  if (toggle.checked) {
    statusText.textContent = 'Bot will start trading immediately';
  } else {
    statusText.textContent = 'Bot will be created but not start trading';
  }
}

/**
 * Update paper trading text based on toggle state
 * @param {HTMLElement} modal - Modal element
 */
export function updatePaperTradingText(modal) {
  const toggle = modal.querySelector('#bot-paper-trading');
  const text = modal.querySelector('#paper-trading-text');
  
  if (toggle.checked) {
    text.textContent = 'Paper trading mode (simulated trades)';
  } else {
    text.textContent = 'Live trading mode (real trades)';
  }
}

/**
 * Update description character count
 * @param {HTMLElement} modal - Modal element
 */
export function updateDescriptionCount(modal) {
  const textarea = modal.querySelector('#bot-description');
  const counter = modal.querySelector('#description-count');
  counter.textContent = textarea.value.length;
}

/**
 * Show form error
 * @param {HTMLElement} modal - Modal element
 * @param {string} message - Error message
 */
export function showFormError(modal, message) {
  const errorDiv = modal.querySelector('#form-error');
  const errorMessage = modal.querySelector('#form-error-message');
  
  errorMessage.textContent = message;
  errorDiv.classList.remove('hidden');
  
  // Hide success message
  modal.querySelector('#form-success').classList.add('hidden');
}

/**
 * Show form success
 * @param {HTMLElement} modal - Modal element
 * @param {string} message - Success message
 */
export function showFormSuccess(modal, message) {
  const successDiv = modal.querySelector('#form-success');
  const successMessage = modal.querySelector('#form-success-message');
  
  successMessage.textContent = message;
  successDiv.classList.remove('hidden');
  
  // Hide error message
  modal.querySelector('#form-error').classList.add('hidden');
}

/**
 * Clear form errors
 * @param {HTMLElement} modal - Modal element
 */
export function clearFormErrors(modal) {
  modal.querySelector('#form-error').classList.add('hidden');
  modal.querySelector('#form-success').classList.add('hidden');
  
  // Clear field errors
  const errorElements = modal.querySelectorAll('.text-error:not(.hidden)');
  errorElements.forEach(error => error.classList.add('hidden'));
}

/**
 * Show field error
 * @param {HTMLElement} modal - Modal element
 * @param {string} fieldName - Field name
 * @param {string} message - Error message
 */
export function showFieldError(modal, fieldName, message) {
  const errorElement = modal.querySelector(`#${fieldName}-error`);
  if (errorElement) {
    errorElement.textContent = message;
    errorElement.classList.remove('hidden');
  }
}

/**
 * Set form loading state
 * @param {HTMLElement} modal - Modal element
 * @param {boolean} loading - Loading state
 */
export function setFormLoading(modal, loading) {
  const saveBtn = modal.querySelector('#save-btn');
  const saveLoading = modal.querySelector('#save-loading');
  const saveText = modal.querySelector('#save-text');
  
  if (loading) {
    saveBtn.disabled = true;
    saveLoading.classList.remove('hidden');
    saveText.textContent = 'Saving...';
  } else {
    saveBtn.disabled = false;
    saveLoading.classList.add('hidden');
    // Text will be updated by showBotEditor
  }
}

/**
 * Get form data
 * @param {HTMLElement} modal - Modal element
 * @returns {Object} Form data
 */
export function getFormData(modal) {
  const form = modal.querySelector('#bot-form');
  const formData = new FormData(form);
  
  return {
    name: formData.get('name').trim(),
    symbol: modal._symbolDropdown.getValue(),
    isActive: modal.querySelector('#bot-active').checked,
    isPaperTrading: modal.querySelector('#bot-paper-trading').checked,
    description: formData.get('description').trim()
  };
}

/**
 * Validate form data
 * @param {Object} data - Form data
 * @returns {Object} Validation result
 */
export function validateFormData(data) {
  const errors = {};
  
  if (!data.name) {
    errors.name = 'Bot name is required';
  } else if (data.name.length < 3) {
    errors.name = 'Bot name must be at least 3 characters';
  } else if (data.name.length > 50) {
    errors.name = 'Bot name must be less than 50 characters';
  }
  
  if (!data.symbol) {
    errors.symbol = 'Trading symbol is required';
  }
  
  if (data.description && data.description.length > 200) {
    errors.description = 'Description must be less than 200 characters';
  }
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors
  };
}

/**
 * Add bot editor event listeners
 * @param {HTMLElement} modal - Modal element
 * @param {Object} callbacks - Event callbacks
 */
export function addBotEditorEventListeners(modal, callbacks = {}) {
  const {
    onSave = () => {},
    onCancel = () => {}
  } = callbacks;
  
  // Close modal events
  const closeBtn = modal.querySelector('#close-modal-btn');
  const cancelBtn = modal.querySelector('#cancel-btn');
  const backdrop = modal.querySelector('.modal-backdrop');
  
  [closeBtn, cancelBtn, backdrop].forEach(element => {
    if (element) {
      element.addEventListener('click', () => {
        onCancel();
        hideBotEditor(modal);
      });
    }
  });
  
  // Prevent modal close on content click
  modal.querySelector('.modal-box').addEventListener('click', (e) => {
    e.stopPropagation();
  });
  
  // Form submission
  const form = modal.querySelector('#bot-form');
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const formData = getFormData(modal);
    const validation = validateFormData(formData);
    
    // Clear previous errors
    clearFormErrors(modal);
    
    if (!validation.isValid) {
      // Show field errors
      Object.entries(validation.errors).forEach(([field, message]) => {
        showFieldError(modal, field, message);
      });
      return;
    }
    
    // Call save callback
    onSave(formData);
  });
  
  // Status toggle change
  const statusToggle = modal.querySelector('#bot-active');
  statusToggle.addEventListener('change', () => {
    updateStatusText(modal);
  });
  
  // Paper trading toggle change
  const paperTradingToggle = modal.querySelector('#bot-paper-trading');
  paperTradingToggle.addEventListener('change', () => {
    updatePaperTradingText(modal);
  });
  
  // Description character count
  const descriptionTextarea = modal.querySelector('#bot-description');
  descriptionTextarea.addEventListener('input', () => {
    updateDescriptionCount(modal);
  });
  
  // Escape key to close
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('modal-open')) {
      onCancel();
      hideBotEditor(modal);
    }
  });
}