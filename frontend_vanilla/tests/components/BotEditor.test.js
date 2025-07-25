/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { 
  createBotEditor, 
  showBotEditor, 
  hideBotEditor, 
  resetBotForm,
  updateStatusText,
  updatePaperTradingText,
  updateDescriptionCount,
  showFormError,
  showFormSuccess,
  clearFormErrors,
  showFieldError,
  setFormLoading,
  getFormData,
  validateFormData,
  addBotEditorEventListeners
} from '../../src/components/BotEditor.js';

describe('BotEditor Component', () => {
  let modal;
  let mockSymbols;
  let mockBot;

  beforeEach(() => {
    // Clean up DOM
    document.body.innerHTML = '';
    
    // Create mock data
    mockSymbols = [
      { id: 'BTCUSDT', uiName: 'BTC/USDT', volume24hFormatted: '1.2B' },
      { id: 'ETHUSDT', uiName: 'ETH/USDT', volume24hFormatted: '800M' }
    ];
    
    mockBot = {
      id: 'bot1',
      name: 'Test Bot',
      symbol: 'BTCUSDT',
      isActive: true,
      isPaperTrading: true,
      description: 'Test description'
    };

    // Create modal
    modal = createBotEditor();
    document.body.appendChild(modal);
  });

  describe('createBotEditor', () => {
    it('should create modal with proper structure', () => {
      expect(modal).toBeTruthy();
      expect(modal.className).toBe('modal');
      expect(modal.id).toBe('bot-editor-modal');
      
      // Check for modal box
      const modalBox = modal.querySelector('.modal-box');
      expect(modalBox).toBeTruthy();
      
      // Check for title
      const title = modal.querySelector('#modal-title');
      expect(title).toBeTruthy();
      expect(title.textContent).toBe('Create New Bot');
      
      // Check for form
      const form = modal.querySelector('#bot-form');
      expect(form).toBeTruthy();
      
      // Check for required form fields
      const nameInput = modal.querySelector('#bot-name');
      const symbolDropdown = modal._symbolDropdown;
      const activeToggle = modal.querySelector('#bot-active');
      const paperTradingToggle = modal.querySelector('#bot-paper-trading');
      const descriptionTextarea = modal.querySelector('#bot-description');
      
      expect(nameInput).toBeTruthy();
      expect(symbolDropdown).toBeTruthy();
      expect(activeToggle).toBeTruthy();
      expect(paperTradingToggle).toBeTruthy();
      expect(descriptionTextarea).toBeTruthy();
      
      // Check for action buttons
      const saveBtn = modal.querySelector('#save-btn');
      const cancelBtn = modal.querySelector('#cancel-btn');
      
      expect(saveBtn).toBeTruthy();
      expect(cancelBtn).toBeTruthy();
    });

    it('should have correct initial form values', () => {
      const nameInput = modal.querySelector('#bot-name');
      const symbolDropdown = modal._symbolDropdown;
      const activeToggle = modal.querySelector('#bot-active');
      const paperTradingToggle = modal.querySelector('#bot-paper-trading');
      const descriptionTextarea = modal.querySelector('#bot-description');
      
      expect(nameInput.value).toBe('');
      expect(symbolDropdown.getValue()).toBeNull();
      expect(activeToggle.checked).toBe(true);
      expect(paperTradingToggle.checked).toBe(true); // Default to paper trading
      expect(descriptionTextarea.value).toBe('');
    });
  });

  describe('showBotEditor', () => {
    it('should show modal in create mode', () => {
      showBotEditor(modal, { symbols: mockSymbols, mode: 'create' });
      
      expect(modal.classList.contains('modal-open')).toBe(true);
      
      const title = modal.querySelector('#modal-title');
      const saveBtn = modal.querySelector('#save-text');
      
      expect(title.textContent).toBe('Create New Bot');
      expect(saveBtn.textContent).toBe('Create Bot');
    });

    it('should show modal in edit mode', () => {
      showBotEditor(modal, { 
        bot: mockBot, 
        symbols: mockSymbols, 
        mode: 'edit' 
      });
      
      expect(modal.classList.contains('modal-open')).toBe(true);
      
      const title = modal.querySelector('#modal-title');
      const saveBtn = modal.querySelector('#save-text');
      
      expect(title.textContent).toBe(`Edit Bot: ${mockBot.name}`);
      expect(saveBtn.textContent).toBe('Update Bot');
    });

    it('should populate form with bot data in edit mode', () => {
      showBotEditor(modal, { 
        bot: mockBot, 
        symbols: mockSymbols, 
        mode: 'edit' 
      });
      
      const nameInput = modal.querySelector('#bot-name');
      const symbolDropdown = modal._symbolDropdown;
      const activeToggle = modal.querySelector('#bot-active');
      const paperTradingToggle = modal.querySelector('#bot-paper-trading');
      const descriptionTextarea = modal.querySelector('#bot-description');
      
      expect(nameInput.value).toBe(mockBot.name);
      expect(symbolDropdown.getValue()).toBe(mockBot.symbol);
      expect(activeToggle.checked).toBe(mockBot.isActive);
      expect(paperTradingToggle.checked).toBe(mockBot.isPaperTrading);
      expect(descriptionTextarea.value).toBe(mockBot.description);
    });

    it('should populate symbol dropdown', () => {
      showBotEditor(modal, { symbols: mockSymbols, mode: 'create' });
      
      const symbolDropdown = modal._symbolDropdown;
      // Check that options were set on the dropdown
      expect(symbolDropdown._searchableDropdown.options.length).toBe(2);
      expect(symbolDropdown._searchableDropdown.options[0].id).toBe('BTCUSDT');
      expect(symbolDropdown._searchableDropdown.options[0].label).toBe('BTC/USDT (1.2B)');
    });
  });

  describe('hideBotEditor', () => {
    it('should hide modal and reset form', () => {
      // First show the modal
      showBotEditor(modal, { 
        bot: mockBot, 
        symbols: mockSymbols, 
        mode: 'edit' 
      });
      
      expect(modal.classList.contains('modal-open')).toBe(true);
      
      // Hide the modal
      hideBotEditor(modal);
      
      expect(modal.classList.contains('modal-open')).toBe(false);
      
      // Check that form is reset
      const nameInput = modal.querySelector('#bot-name');
      const activeToggle = modal.querySelector('#bot-active');
      
      expect(nameInput.value).toBe('');
      expect(activeToggle.checked).toBe(true);
    });
  });

  describe('resetBotForm', () => {
    it('should reset form to default values', () => {
      // Set some values
      const nameInput = modal.querySelector('#bot-name');
      const activeToggle = modal.querySelector('#bot-active');
      
      nameInput.value = 'Test Name';
      activeToggle.checked = false;
      
      // Reset form
      resetBotForm(modal);
      
      expect(nameInput.value).toBe('');
      expect(activeToggle.checked).toBe(true);
    });
  });

  describe('updateStatusText', () => {
    it('should update status text based on toggle state', () => {
      const activeToggle = modal.querySelector('#bot-active');
      const statusText = modal.querySelector('#status-text');
      
      activeToggle.checked = true;
      updateStatusText(modal);
      expect(statusText.textContent).toBe('Bot will start trading immediately');
      
      activeToggle.checked = false;
      updateStatusText(modal);
      expect(statusText.textContent).toBe('Bot will be created but not start trading');
    });
  });

  describe('updatePaperTradingText', () => {
    it('should update paper trading text based on toggle state', () => {
      const paperTradingToggle = modal.querySelector('#bot-paper-trading');
      const paperTradingText = modal.querySelector('#paper-trading-text');
      
      paperTradingToggle.checked = true;
      updatePaperTradingText(modal);
      expect(paperTradingText.textContent).toBe('Paper trading mode (simulated trades)');
      
      paperTradingToggle.checked = false;
      updatePaperTradingText(modal);
      expect(paperTradingText.textContent).toBe('Live trading mode (real trades)');
    });
  });

  describe('updateDescriptionCount', () => {
    it('should update character count', () => {
      const descriptionTextarea = modal.querySelector('#bot-description');
      const counter = modal.querySelector('#description-count');
      
      descriptionTextarea.value = 'Test description';
      updateDescriptionCount(modal);
      
      expect(counter.textContent).toBe('16');
    });
  });

  describe('showFormError', () => {
    it('should display error message', () => {
      showFormError(modal, 'Test error message');
      
      const errorDiv = modal.querySelector('#form-error');
      const errorMessage = modal.querySelector('#form-error-message');
      
      expect(errorDiv.classList.contains('hidden')).toBe(false);
      expect(errorMessage.textContent).toBe('Test error message');
    });
  });

  describe('showFormSuccess', () => {
    it('should display success message', () => {
      showFormSuccess(modal, 'Test success message');
      
      const successDiv = modal.querySelector('#form-success');
      const successMessage = modal.querySelector('#form-success-message');
      
      expect(successDiv.classList.contains('hidden')).toBe(false);
      expect(successMessage.textContent).toBe('Test success message');
    });
  });

  describe('clearFormErrors', () => {
    it('should hide error and success messages', () => {
      // First show an error
      showFormError(modal, 'Test error');
      
      const errorDiv = modal.querySelector('#form-error');
      expect(errorDiv.classList.contains('hidden')).toBe(false);
      
      // Clear errors
      clearFormErrors(modal);
      
      expect(errorDiv.classList.contains('hidden')).toBe(true);
    });
  });

  describe('showFieldError', () => {
    it('should display field-specific error', () => {
      showFieldError(modal, 'name', 'Name is required');
      
      const nameError = modal.querySelector('#name-error');
      expect(nameError.classList.contains('hidden')).toBe(false);
      expect(nameError.textContent).toBe('Name is required');
    });
  });

  describe('setFormLoading', () => {
    it('should set loading state', () => {
      const saveBtn = modal.querySelector('#save-btn');
      const saveLoading = modal.querySelector('#save-loading');
      const saveText = modal.querySelector('#save-text');
      
      setFormLoading(modal, true);
      
      expect(saveBtn.disabled).toBe(true);
      expect(saveLoading.classList.contains('hidden')).toBe(false);
      expect(saveText.textContent).toBe('Saving...');
    });

    it('should clear loading state', () => {
      const saveBtn = modal.querySelector('#save-btn');
      const saveLoading = modal.querySelector('#save-loading');
      
      setFormLoading(modal, false);
      
      expect(saveBtn.disabled).toBe(false);
      expect(saveLoading.classList.contains('hidden')).toBe(true);
    });
  });

  describe('getFormData', () => {
    it('should extract form data correctly', () => {
      const nameInput = modal.querySelector('#bot-name');
      const symbolDropdown = modal._symbolDropdown;
      const activeToggle = modal.querySelector('#bot-active');
      const paperTradingToggle = modal.querySelector('#bot-paper-trading');
      const descriptionTextarea = modal.querySelector('#bot-description');
      
      // Set options and value for testing
      symbolDropdown.setOptions([{ id: 'BTCUSDT', label: 'BTC/USDT' }]);
      
      nameInput.value = 'Test Bot';
      symbolDropdown.setValue('BTCUSDT');
      activeToggle.checked = false;
      paperTradingToggle.checked = false;
      descriptionTextarea.value = 'Test description';
      
      const formData = getFormData(modal);
      
      expect(formData.name).toBe('Test Bot');
      expect(formData.symbol).toBe('BTCUSDT');
      expect(formData.isActive).toBe(false);
      expect(formData.isPaperTrading).toBe(false);
      expect(formData.description).toBe('Test description');
    });
  });

  describe('validateFormData', () => {
    it('should validate valid form data', () => {
      const validData = {
        name: 'Test Bot',
        symbol: 'BTCUSDT',
        isActive: true,
        description: 'Test description'
      };
      
      const validation = validateFormData(validData);
      
      expect(validation.isValid).toBe(true);
      expect(Object.keys(validation.errors)).toHaveLength(0);
    });

    it('should validate required fields', () => {
      const invalidData = {
        name: '',
        symbol: '',
        isActive: true,
        description: ''
      };
      
      const validation = validateFormData(invalidData);
      
      expect(validation.isValid).toBe(false);
      expect(validation.errors.name).toBe('Bot name is required');
      expect(validation.errors.symbol).toBe('Trading symbol is required');
    });

    it('should validate name length', () => {
      const shortName = {
        name: 'Ab',
        symbol: 'BTCUSDT',
        isActive: true,
        description: ''
      };
      
      const validation = validateFormData(shortName);
      
      expect(validation.isValid).toBe(false);
      expect(validation.errors.name).toBe('Bot name must be at least 3 characters');
    });

    it('should validate description length', () => {
      const longDescription = {
        name: 'Test Bot',
        symbol: 'BTCUSDT',
        isActive: true,
        description: 'A'.repeat(201)
      };
      
      const validation = validateFormData(longDescription);
      
      expect(validation.isValid).toBe(false);
      expect(validation.errors.description).toBe('Description must be less than 200 characters');
    });
  });

  describe('addBotEditorEventListeners', () => {
    it('should handle form submission', () => {
      const mockCallbacks = {
        onSave: vi.fn(),
        onCancel: vi.fn()
      };
      
      addBotEditorEventListeners(modal, mockCallbacks);
      
      // Fill form with valid data
      const nameInput = modal.querySelector('#bot-name');
      const symbolDropdown = modal._symbolDropdown;
      
      // Set options and value for testing
      symbolDropdown.setOptions([{ id: 'BTCUSDT', label: 'BTC/USDT' }]);
      
      nameInput.value = 'Test Bot';
      symbolDropdown.setValue('BTCUSDT');
      
      // Submit form
      const form = modal.querySelector('#bot-form');
      const submitEvent = new Event('submit', { bubbles: true });
      form.dispatchEvent(submitEvent);
      
      expect(mockCallbacks.onSave).toHaveBeenCalledWith({
        name: 'Test Bot',
        symbol: 'BTCUSDT',
        isActive: true,
        isPaperTrading: true,
        description: ''
      });
    });

    it('should handle cancel button click', () => {
      const mockCallbacks = {
        onSave: vi.fn(),
        onCancel: vi.fn()
      };
      
      addBotEditorEventListeners(modal, mockCallbacks);
      
      const cancelBtn = modal.querySelector('#cancel-btn');
      cancelBtn.click();
      
      expect(mockCallbacks.onCancel).toHaveBeenCalledTimes(1);
    });

    it('should handle status toggle change', () => {
      addBotEditorEventListeners(modal, {});
      
      const activeToggle = modal.querySelector('#bot-active');
      const statusText = modal.querySelector('#status-text');
      
      activeToggle.checked = false;
      activeToggle.dispatchEvent(new Event('change'));
      
      expect(statusText.textContent).toBe('Bot will be created but not start trading');
    });

    it('should handle description input for character count', () => {
      addBotEditorEventListeners(modal, {});
      
      const descriptionTextarea = modal.querySelector('#bot-description');
      const counter = modal.querySelector('#description-count');
      
      descriptionTextarea.value = 'Test';
      descriptionTextarea.dispatchEvent(new Event('input'));
      
      expect(counter.textContent).toBe('4');
    });
  });
});