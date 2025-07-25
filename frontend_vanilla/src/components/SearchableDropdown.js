/**
 * SearchableDropdown Component
 * 
 * A reusable searchable dropdown component using DaisyUI v5 styling.
 * Provides case-insensitive search with partial string matching.
 * 
 * @module SearchableDropdown
 * 
 * @example
 * // Basic usage
 * import { createSearchableDropdown } from './SearchableDropdown.js';
 * 
 * const dropdown = createSearchableDropdown({
 *   id: 'symbol-selector',
 *   name: 'symbol',
 *   placeholder: 'Select a trading pair',
 *   required: true
 * });
 * 
 * // Set options
 * dropdown.setOptions([
 *   { id: 'btcusdt', label: 'BTC/USDT (1.2B)' },
 *   { id: 'ethusdt', label: 'ETH/USDT (800M)' }
 * ]);
 * 
 * // Set value programmatically
 * dropdown.setValue('btcusdt');
 * 
 * // Get current value
 * const selectedValue = dropdown.getValue();
 * 
 * // Get full selected option
 * const selectedOption = dropdown.getSelectedOption();
 * 
 * // Listen for changes
 * dropdown.querySelector('input[type="hidden"]').addEventListener('change', (e) => {
 *   console.log('Selected:', e.target.value);
 * });
 * 
 * // Clean up when component is no longer needed
 * dropdown.destroy();
 * 
 * @example
 * // Advanced usage with form integration
 * const formContainer = document.querySelector('#form-container');
 * const dropdown = createSearchableDropdown({
 *   id: 'my-dropdown',
 *   name: 'selection',
 *   placeholder: 'Choose an option',
 *   required: true,
 *   className: 'w-full',
 *   testId: 'my-dropdown-test'
 * });
 * 
 * formContainer.appendChild(dropdown);
 * 
 * // Form submission will include dropdown value automatically
 * const form = document.querySelector('form');
 * form.addEventListener('submit', (e) => {
 *   const formData = new FormData(form);
 *   const selectedValue = formData.get('selection');
 *   console.log('Form submitted with:', selectedValue);
 * });
 */

/**
 * Creates a searchable dropdown component
 * 
 * @param {Object} options - Configuration options
 * @param {string} options.id - Unique identifier for the component
 * @param {string} options.name - Form field name
 * @param {string} [options.placeholder='Select an option'] - Placeholder text
 * @param {boolean} [options.required=false] - Whether the field is required
 * @param {string} [options.className=''] - Additional CSS classes
 * @param {string} [options.testId=''] - Test identifier for testing
 * @returns {HTMLElement} The searchable dropdown element
 */
export function createSearchableDropdown(options = {}) {
  const {
    id,
    name,
    placeholder = 'Select an option',
    required = false,
    className = '',
    testId = ''
  } = options;

  // Create main container
  const container = document.createElement('div');
  container.className = `searchable-dropdown ${className}`;
  container.style.position = 'relative';
  if (testId) {
    container.setAttribute('data-testid', testId);
  }

  // Create hidden input for form value
  const hiddenInput = document.createElement('input');
  hiddenInput.type = 'hidden';
  hiddenInput.id = id;
  hiddenInput.name = name;
  if (required) {
    hiddenInput.required = true;
  }

  // Create visible display element (styled as input)
  const displayElement = document.createElement('div');
  displayElement.className = 'input input-bordered w-full cursor-pointer flex items-center justify-between';
  displayElement.tabIndex = 0;
  displayElement.setAttribute('role', 'button');
  displayElement.setAttribute('aria-haspopup', 'listbox');
  displayElement.setAttribute('aria-expanded', 'false');
  
  const displayText = document.createElement('span');
  displayText.className = 'searchable-dropdown-display-text text-base-content/60';
  displayText.textContent = placeholder;
  
  const chevronIcon = document.createElement('span');
  chevronIcon.className = 'searchable-dropdown-chevron';
  chevronIcon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
  </svg>`;
  
  displayElement.appendChild(displayText);
  displayElement.appendChild(chevronIcon);

  // Create dropdown container
  const dropdownContainer = document.createElement('div');
  dropdownContainer.className = 'dropdown-container hidden absolute top-full left-0 right-0 z-50 mt-1';
  dropdownContainer.setAttribute('role', 'region');

  // Create search container
  const searchContainer = document.createElement('div');
  searchContainer.className = 'relative mb-2';
  
  // Create search input
  const searchInput = document.createElement('input');
  searchInput.type = 'text';
  searchInput.className = 'input input-bordered input-sm w-full pr-8';
  searchInput.placeholder = 'Search...';
  searchInput.setAttribute('role', 'combobox');
  searchInput.setAttribute('aria-autocomplete', 'list');
  searchInput.setAttribute('aria-controls', `${id}-listbox`);
  searchInput.setAttribute('aria-expanded', 'false');
  
  // Create clear button
  const clearButton = document.createElement('button');
  clearButton.type = 'button';
  clearButton.className = 'btn btn-ghost btn-xs absolute right-1 top-1/2 -translate-y-1/2 hidden z-10';
  clearButton.innerHTML = '✕';
  clearButton.setAttribute('aria-label', 'Clear search');
  
  searchContainer.appendChild(searchInput);
  searchContainer.appendChild(clearButton);

  // Create results container
  const resultsContainer = document.createElement('ul');
  resultsContainer.id = `${id}-listbox`;
  resultsContainer.className = 'menu dropdown-content bg-base-100 rounded-box shadow-lg w-full overflow-y-auto';
  resultsContainer.style.maxHeight = '300px';
  resultsContainer.setAttribute('role', 'listbox');

  // Create no results message
  const noResultsMessage = document.createElement('li');
  noResultsMessage.className = 'menu-item-disabled p-2 text-center text-base-content/60';
  noResultsMessage.textContent = 'No results found';
  noResultsMessage.style.display = 'none';

  // Assemble dropdown container
  dropdownContainer.appendChild(searchContainer);
  dropdownContainer.appendChild(resultsContainer);
  resultsContainer.appendChild(noResultsMessage);

  // Assemble main container
  container.appendChild(hiddenInput);
  container.appendChild(displayElement);
  container.appendChild(dropdownContainer);

  // Store component state
  container._searchableDropdown = {
    options: [],
    filteredOptions: [],
    selectedIndex: -1,
    isOpen: false,
    selectedValue: null,
    debounceTimer: null,
    eventListeners: [],
    placeholder: placeholder
  };

  // Expose methods
  container.setOptions = setOptions.bind(container);
  container.setValue = setValue.bind(container);
  container.getValue = getValue.bind(container);
  container.getSelectedOption = getSelectedOption.bind(container);
  container.destroy = destroy.bind(container);
  container.open = open.bind(container);
  container.close = close.bind(container);

  // Initialize event handlers
  initializeEventHandlers.call(container);

  return container;
}

/**
 * Set the available options for the dropdown
 * @param {Array<Object>} options - Array of option objects
 * @param {string} options[].id - Unique identifier for the option
 * @param {string} options[].label - Display label for the option
 * @param {*} [options[].data] - Additional data associated with the option
 */
function setOptions(options) {
  this._searchableDropdown.options = options || [];
  this._searchableDropdown.filteredOptions = [...this._searchableDropdown.options];
  
  // Re-render if dropdown is open
  if (this._searchableDropdown.isOpen) {
    const searchInput = this.querySelector('input[type="text"]');
    renderResults.call(this, searchInput.value);
  }
}

/**
 * Set the selected value
 * @param {string|null} value - The ID of the option to select, or null to clear
 */
function setValue(value) {
  if (value === null || value === undefined || value === '') {
    // Clear the selection
    const hiddenInput = this.querySelector('input[type="hidden"]');
    const displayText = this.querySelector('.searchable-dropdown-display-text');
    
    this._searchableDropdown.selectedValue = null;
    hiddenInput.value = '';
    displayText.textContent = this._searchableDropdown.placeholder;
    displayText.classList.add('text-base-content/60');
    
    // Dispatch change event
    const changeEvent = new Event('change', { bubbles: true });
    hiddenInput.dispatchEvent(changeEvent);
  } else {
    const option = this._searchableDropdown.options.find(opt => opt.id === value);
    if (option) {
      selectOption.call(this, option);
    }
  }
}

/**
 * Get the current selected value
 * @returns {string|null} The ID of the selected option
 */
function getValue() {
  return this._searchableDropdown.selectedValue;
}

/**
 * Get the full selected option object
 * @returns {Object|null} The selected option object
 */
function getSelectedOption() {
  if (!this._searchableDropdown.selectedValue) return null;
  return this._searchableDropdown.options.find(
    opt => opt.id === this._searchableDropdown.selectedValue
  );
}

/**
 * Open the dropdown
 */
function open() {
  if (this._searchableDropdown.isOpen) return;
  
  const dropdownContainer = this.querySelector('.dropdown-container');
  const displayElement = this.querySelector('[role="button"]');
  const searchInput = this.querySelector('input[type="text"]');
  
  this._searchableDropdown.isOpen = true;
  dropdownContainer.classList.remove('hidden');
  displayElement.setAttribute('aria-expanded', 'true');
  searchInput.setAttribute('aria-expanded', 'true');
  
  // Focus search input
  searchInput.value = '';
  searchInput.focus();
  
  // Initial render with empty search to show all options
  this._searchableDropdown.filteredOptions = [...this._searchableDropdown.options];
  renderResults.call(this, '');
}

/**
 * Close the dropdown
 */
function close() {
  if (!this._searchableDropdown.isOpen) return;
  
  const dropdownContainer = this.querySelector('.dropdown-container');
  const displayElement = this.querySelector('[role="button"]');
  const searchInput = this.querySelector('input[type="text"]');
  
  this._searchableDropdown.isOpen = false;
  dropdownContainer.classList.add('hidden');
  displayElement.setAttribute('aria-expanded', 'false');
  searchInput.setAttribute('aria-expanded', 'false');
  
  // Reset search
  searchInput.value = '';
  this._searchableDropdown.selectedIndex = -1;
}

/**
 * Select an option
 * @param {Object} option - The option to select
 */
function selectOption(option) {
  const hiddenInput = this.querySelector('input[type="hidden"]');
  const displayText = this.querySelector('.searchable-dropdown-display-text');
  
  this._searchableDropdown.selectedValue = option.id;
  hiddenInput.value = option.id;
  displayText.textContent = option.label;
  displayText.classList.remove('text-base-content/60');
  
  // Dispatch change event
  const changeEvent = new Event('change', { bubbles: true });
  hiddenInput.dispatchEvent(changeEvent);
  
  close.call(this);
}

/**
 * Render filtered results
 * @param {string} searchTerm - The search term to filter by
 */
function renderResults(searchTerm) {
  const resultsContainer = this.querySelector('[role="listbox"]');
  const noResultsMessage = resultsContainer.querySelector('.menu-item-disabled');
  
  // Clear existing results (except no results message)
  const existingItems = resultsContainer.querySelectorAll('li:not(.menu-item-disabled)');
  existingItems.forEach(item => item.remove());
  
  // Filter options
  const searchLower = searchTerm.toLowerCase();
  this._searchableDropdown.filteredOptions = this._searchableDropdown.options.filter(option => {
    return option.label.toLowerCase().includes(searchLower) || 
           option.id.toLowerCase().includes(searchLower);
  });
  
  // Show/hide no results message
  if (this._searchableDropdown.filteredOptions.length === 0) {
    noResultsMessage.style.display = 'block';
    return;
  } else {
    noResultsMessage.style.display = 'none';
  }
  
  // Render filtered options
  this._searchableDropdown.filteredOptions.forEach((option, index) => {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.textContent = option.label;
    a.setAttribute('role', 'option');
    a.setAttribute('id', `${this.querySelector('[role="listbox"]').id}-option-${index}`);
    a.className = 'hover:bg-base-200';
    
    li.appendChild(a);
    resultsContainer.insertBefore(li, noResultsMessage);
  });
}

/**
 * Update highlight for keyboard navigation
 */
function updateHighlight() {
  const resultsContainer = this.querySelector('[role="listbox"]');
  const items = resultsContainer.querySelectorAll('li:not(.menu-item-disabled)');
  
  // Remove existing highlights
  items.forEach(item => {
    item.classList.remove('bg-base-200');
    const a = item.querySelector('a');
    if (a) a.setAttribute('aria-selected', 'false');
  });
  
  // Add highlight to selected item
  if (this._searchableDropdown.selectedIndex >= 0 && items[this._searchableDropdown.selectedIndex]) {
    const selectedItem = items[this._searchableDropdown.selectedIndex];
    selectedItem.classList.add('bg-base-200');
    const a = selectedItem.querySelector('a');
    if (a) a.setAttribute('aria-selected', 'true');
    
    // Scroll into view if needed (check if method exists for JSDOM compatibility)
    if (selectedItem.scrollIntoView) {
      selectedItem.scrollIntoView({ block: 'nearest' });
    }
  }
}

/**
 * Initialize event handlers for the component
 */
function initializeEventHandlers() {
  const displayElement = this.querySelector('[role="button"]');
  const searchInput = this.querySelector('input[type="text"]');
  const resultsContainer = this.querySelector('[role="listbox"]');
  
  // Helper to track event listeners
  const addEventListener = (element, event, handler) => {
    element.addEventListener(event, handler);
    this._searchableDropdown.eventListeners.push({ element, event, handler });
  };
  
  // Display element click handler
  const handleDisplayClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (this._searchableDropdown.isOpen) {
      close.call(this);
    } else {
      open.call(this);
    }
  };
  addEventListener(displayElement, 'click', handleDisplayClick);
  
  // Display element keyboard handler
  const handleDisplayKeydown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleDisplayClick(e);
    }
  };
  addEventListener(displayElement, 'keydown', handleDisplayKeydown);
  
  // Search input handler with debouncing
  const handleSearchInput = (e) => {
    const searchTerm = e.target.value;
    const clearButton = this.querySelector('.btn-ghost.btn-xs');
    
    // Show/hide clear button
    if (searchTerm) {
      clearButton.classList.remove('hidden');
    } else {
      clearButton.classList.add('hidden');
    }
    
    // Clear existing debounce timer
    if (this._searchableDropdown.debounceTimer) {
      clearTimeout(this._searchableDropdown.debounceTimer);
    }
    
    // Set new debounce timer
    this._searchableDropdown.debounceTimer = setTimeout(() => {
      renderResults.call(this, searchTerm);
    }, 50);
  };
  addEventListener(searchInput, 'input', handleSearchInput);
  
  // Clear button handler
  const clearButton = this.querySelector('.btn-ghost.btn-xs');
  const handleClearClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    searchInput.value = '';
    clearButton.classList.add('hidden');
    renderResults.call(this, '');
    searchInput.focus();
  };
  addEventListener(clearButton, 'click', handleClearClick);
  
  // Prevent dropdown close when clicking inside
  const handleDropdownClick = (e) => {
    e.stopPropagation();
  };
  addEventListener(this.querySelector('.dropdown-container'), 'click', handleDropdownClick);
  
  // Results container click handler
  const handleResultClick = (e) => {
    const li = e.target.closest('li');
    if (!li || li.classList.contains('menu-item-disabled')) return;
    
    // Find index among non-disabled items
    const nonDisabledItems = Array.from(resultsContainer.children).filter(child => 
      !child.classList.contains('menu-item-disabled')
    );
    const index = nonDisabledItems.indexOf(li);
    const option = this._searchableDropdown.filteredOptions[index];
    
    if (option) {
      selectOption.call(this, option);
    }
  };
  addEventListener(resultsContainer, 'click', handleResultClick);
  
  // Document click handler (close on outside click)
  const handleDocumentClick = (e) => {
    if (!this.contains(e.target) && this._searchableDropdown.isOpen) {
      close.call(this);
    }
  };
  addEventListener(document, 'click', handleDocumentClick);
  
  // ESC key handler
  const handleEscKey = (e) => {
    if (e.key === 'Escape' && this._searchableDropdown.isOpen) {
      close.call(this);
      displayElement.focus();
    }
  };
  addEventListener(document, 'keydown', handleEscKey);
  
  // Keyboard navigation for search input
  const handleSearchKeydown = (e) => {
    const { selectedIndex, filteredOptions } = this._searchableDropdown;
    let newIndex = selectedIndex;
    
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        newIndex = selectedIndex < filteredOptions.length - 1 ? selectedIndex + 1 : 0;
        break;
        
      case 'ArrowUp':
        e.preventDefault();
        newIndex = selectedIndex > 0 ? selectedIndex - 1 : filteredOptions.length - 1;
        break;
        
      case 'Home':
        e.preventDefault();
        newIndex = 0;
        break;
        
      case 'End':
        e.preventDefault();
        newIndex = filteredOptions.length - 1;
        break;
        
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && filteredOptions[selectedIndex]) {
          selectOption.call(this, filteredOptions[selectedIndex]);
        }
        return;
        
      case 'Tab':
        // Let Tab key close dropdown and move to next field
        close.call(this);
        return;
        
      default:
        return;
    }
    
    // Update selected index and highlight
    if (newIndex !== selectedIndex && filteredOptions.length > 0) {
      this._searchableDropdown.selectedIndex = newIndex;
      updateHighlight.call(this);
      
      // Update aria-activedescendant
      const activeId = `${resultsContainer.id}-option-${newIndex}`;
      searchInput.setAttribute('aria-activedescendant', activeId);
    }
  };
  addEventListener(searchInput, 'keydown', handleSearchKeydown);
}

/**
 * Clean up the component and remove event listeners
 */
function destroy() {
  // Check if already destroyed
  if (!this._searchableDropdown) return;
  
  // Remove all event listeners
  this._searchableDropdown.eventListeners.forEach(({ element, event, handler }) => {
    element.removeEventListener(event, handler);
  });
  
  // Clear debounce timer
  if (this._searchableDropdown.debounceTimer) {
    clearTimeout(this._searchableDropdown.debounceTimer);
  }
  
  // Clear references
  this._searchableDropdown = null;
}