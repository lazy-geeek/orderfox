import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createSearchableDropdown } from '../../src/components/SearchableDropdown';

describe('SearchableDropdown', () => {
  let container;
  let dropdown;

  beforeEach(() => {
    // Create container for tests
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(() => {
    // Cleanup
    if (dropdown && dropdown.destroy) {
      dropdown.destroy();
    }
    container.remove();
  });

  describe('Component Creation', () => {
    it('should create dropdown with default options', () => {
      dropdown = createSearchableDropdown({
        id: 'test-dropdown',
        name: 'test'
      });
      container.appendChild(dropdown);

      expect(dropdown).toBeDefined();
      expect(dropdown.querySelector('input[type="hidden"]').id).toBe('test-dropdown');
      expect(dropdown.querySelector('input[type="hidden"]').name).toBe('test');
      expect(dropdown.querySelector('.searchable-dropdown-display-text').textContent).toBe('Select an option');
    });

    it('should create dropdown with custom options', () => {
      dropdown = createSearchableDropdown({
        id: 'custom-dropdown',
        name: 'custom',
        placeholder: 'Choose a symbol',
        required: true,
        className: 'custom-class',
        testId: 'custom-test-id'
      });
      container.appendChild(dropdown);

      expect(dropdown.querySelector('input[type="hidden"]').required).toBe(true);
      expect(dropdown.querySelector('.searchable-dropdown-display-text').textContent).toBe('Choose a symbol');
      expect(dropdown.classList.contains('custom-class')).toBe(true);
      expect(dropdown.getAttribute('data-testid')).toBe('custom-test-id');
    });
  });

  describe('Options Management', () => {
    beforeEach(() => {
      dropdown = createSearchableDropdown({
        id: 'test-dropdown',
        name: 'test'
      });
      container.appendChild(dropdown);
    });

    it('should set options correctly', () => {
      const options = [
        { id: 'btc', label: 'BTC/USDT' },
        { id: 'eth', label: 'ETH/USDT' },
        { id: 'bnb', label: 'BNB/USDT' }
      ];

      dropdown.setOptions(options);
      expect(dropdown._searchableDropdown.options).toEqual(options);
    });

    it('should handle empty options', () => {
      dropdown.setOptions([]);
      expect(dropdown._searchableDropdown.options).toEqual([]);
    });

    it('should handle null options', () => {
      dropdown.setOptions(null);
      expect(dropdown._searchableDropdown.options).toEqual([]);
    });
  });

  describe('Value Management', () => {
    beforeEach(() => {
      dropdown = createSearchableDropdown({
        id: 'test-dropdown',
        name: 'test'
      });
      container.appendChild(dropdown);

      const options = [
        { id: 'btc', label: 'BTC/USDT' },
        { id: 'eth', label: 'ETH/USDT' }
      ];
      dropdown.setOptions(options);
    });

    it('should set value correctly', () => {
      dropdown.setValue('btc');
      expect(dropdown.getValue()).toBe('btc');
      expect(dropdown.querySelector('input[type="hidden"]').value).toBe('btc');
      expect(dropdown.querySelector('.searchable-dropdown-display-text').textContent).toBe('BTC/USDT');
    });

    it('should get selected option object', () => {
      dropdown.setValue('eth');
      const selected = dropdown.getSelectedOption();
      expect(selected).toEqual({ id: 'eth', label: 'ETH/USDT' });
    });

    it('should return null for no selection', () => {
      expect(dropdown.getValue()).toBeNull();
      expect(dropdown.getSelectedOption()).toBeNull();
    });
  });

  describe('Dropdown Toggle Behavior', () => {
    beforeEach(() => {
      dropdown = createSearchableDropdown({
        id: 'test-dropdown',
        name: 'test'
      });
      container.appendChild(dropdown);
    });

    it('should open dropdown on display click', () => {
      const displayElement = dropdown.querySelector('[role="button"]');
      displayElement.click();

      expect(dropdown._searchableDropdown.isOpen).toBe(true);
      expect(dropdown.querySelector('.dropdown-container').classList.contains('hidden')).toBe(false);
    });

    it('should close dropdown on second click', () => {
      const displayElement = dropdown.querySelector('[role="button"]');
      
      displayElement.click(); // Open
      expect(dropdown._searchableDropdown.isOpen).toBe(true);
      
      displayElement.click(); // Close
      expect(dropdown._searchableDropdown.isOpen).toBe(false);
      expect(dropdown.querySelector('.dropdown-container').classList.contains('hidden')).toBe(true);
    });

    it('should close dropdown on ESC key', () => {
      dropdown.open();
      
      const escEvent = new KeyboardEvent('keydown', { key: 'Escape' });
      document.dispatchEvent(escEvent);
      
      expect(dropdown._searchableDropdown.isOpen).toBe(false);
    });

    it('should close dropdown on outside click', () => {
      dropdown.open();
      
      const outsideElement = document.createElement('div');
      document.body.appendChild(outsideElement);
      
      outsideElement.click();
      
      expect(dropdown._searchableDropdown.isOpen).toBe(false);
      outsideElement.remove();
    });
  });

  describe('Search Filtering', () => {
    beforeEach(() => {
      dropdown = createSearchableDropdown({
        id: 'test-dropdown',
        name: 'test'
      });
      container.appendChild(dropdown);

      const options = [
        { id: 'btcusdt', label: 'BTC/USDT' },
        { id: 'ethusdt', label: 'ETH/USDT' },
        { id: 'bnbusdt', label: 'BNB/USDT' },
        { id: 'btcbusd', label: 'BTC/BUSD' }
      ];
      dropdown.setOptions(options);
      dropdown.open();
    });

    it('should filter options based on search term', async () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      searchInput.value = 'btc';
      searchInput.dispatchEvent(new Event('input'));

      // Wait for debounce
      await new Promise(resolve => setTimeout(resolve, 60));

      const visibleOptions = dropdown.querySelectorAll('li:not(.menu-item-disabled)');
      expect(visibleOptions.length).toBe(2);
    });

    it('should be case-insensitive', async () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      searchInput.value = 'BTC';
      searchInput.dispatchEvent(new Event('input'));

      await new Promise(resolve => setTimeout(resolve, 60));

      const visibleOptions = dropdown.querySelectorAll('li:not(.menu-item-disabled)');
      expect(visibleOptions.length).toBe(2);
    });

    it('should match partial strings', async () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      searchInput.value = 'usdt';
      searchInput.dispatchEvent(new Event('input'));

      await new Promise(resolve => setTimeout(resolve, 60));

      const visibleOptions = dropdown.querySelectorAll('li:not(.menu-item-disabled)');
      expect(visibleOptions.length).toBe(3);
    });

    it('should show no results message when no matches', async () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      searchInput.value = 'xyz';
      searchInput.dispatchEvent(new Event('input'));

      await new Promise(resolve => setTimeout(resolve, 60));

      const noResultsMessage = dropdown.querySelector('.menu-item-disabled');
      expect(noResultsMessage.style.display).not.toBe('none');
    });

    it('should show all results when search is cleared', async () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      
      // First filter
      searchInput.value = 'btc';
      searchInput.dispatchEvent(new Event('input'));
      await new Promise(resolve => setTimeout(resolve, 60));
      
      // Clear search
      searchInput.value = '';
      searchInput.dispatchEvent(new Event('input'));
      await new Promise(resolve => setTimeout(resolve, 60));

      const visibleOptions = dropdown.querySelectorAll('li:not(.menu-item-disabled)');
      expect(visibleOptions.length).toBe(4);
    });
  });

  describe('Keyboard Navigation', () => {
    beforeEach(() => {
      dropdown = createSearchableDropdown({
        id: 'test-dropdown',
        name: 'test'
      });
      container.appendChild(dropdown);

      const options = [
        { id: 'btc', label: 'BTC/USDT' },
        { id: 'eth', label: 'ETH/USDT' },
        { id: 'bnb', label: 'BNB/USDT' }
      ];
      dropdown.setOptions(options);
      dropdown.open();
    });

    it('should navigate down with ArrowDown', () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      
      const arrowDownEvent = new KeyboardEvent('keydown', { key: 'ArrowDown' });
      searchInput.dispatchEvent(arrowDownEvent);
      
      expect(dropdown._searchableDropdown.selectedIndex).toBe(0);
    });

    it('should navigate up with ArrowUp', () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      
      // First go down
      searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
      searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
      
      // Then go up
      searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp' }));
      
      expect(dropdown._searchableDropdown.selectedIndex).toBe(0);
    });

    it('should select with Enter key', () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      
      // Navigate to first item
      searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
      
      // Select with Enter
      searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
      
      expect(dropdown.getValue()).toBe('btc');
      expect(dropdown._searchableDropdown.isOpen).toBe(false);
    });

    it('should jump to first item with Home key', () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      
      // Navigate to last
      searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'End' }));
      
      // Jump to first
      searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Home' }));
      
      expect(dropdown._searchableDropdown.selectedIndex).toBe(0);
    });

    it('should jump to last item with End key', () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      
      searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'End' }));
      
      expect(dropdown._searchableDropdown.selectedIndex).toBe(2);
    });

    it('should close on Tab key', () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      
      searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));
      
      expect(dropdown._searchableDropdown.isOpen).toBe(false);
    });
  });

  describe('Clear Button', () => {
    beforeEach(() => {
      dropdown = createSearchableDropdown({
        id: 'test-dropdown',
        name: 'test'
      });
      container.appendChild(dropdown);
      dropdown.open();
    });

    it('should show clear button when search has value', () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      const clearButton = dropdown.querySelector('.btn-ghost.btn-xs');
      
      searchInput.value = 'test';
      searchInput.dispatchEvent(new Event('input'));
      
      expect(clearButton.classList.contains('hidden')).toBe(false);
    });

    it('should hide clear button when search is empty', () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      const clearButton = dropdown.querySelector('.btn-ghost.btn-xs');
      
      searchInput.value = '';
      searchInput.dispatchEvent(new Event('input'));
      
      expect(clearButton.classList.contains('hidden')).toBe(true);
    });

    it('should clear search when clear button is clicked', async () => {
      const searchInput = dropdown.querySelector('input[type="text"]');
      const clearButton = dropdown.querySelector('.btn-ghost.btn-xs');
      
      searchInput.value = 'test';
      searchInput.dispatchEvent(new Event('input'));
      
      clearButton.click();
      
      expect(searchInput.value).toBe('');
      expect(clearButton.classList.contains('hidden')).toBe(true);
    });
  });

  describe('Item Selection', () => {
    beforeEach(() => {
      dropdown = createSearchableDropdown({
        id: 'test-dropdown',
        name: 'test'
      });
      container.appendChild(dropdown);

      const options = [
        { id: 'btc', label: 'BTC/USDT' },
        { id: 'eth', label: 'ETH/USDT' }
      ];
      dropdown.setOptions(options);
      dropdown.open();
    });

    it('should select item on click', async () => {
      const changeHandler = vi.fn();
      dropdown.querySelector('input[type="hidden"]').addEventListener('change', changeHandler);
      
      // Need to render results first
      await new Promise(resolve => setTimeout(resolve, 60));
      
      const firstOption = dropdown.querySelector('li:not(.menu-item-disabled) a');
      expect(firstOption).toBeTruthy();
      
      firstOption.click();
      
      expect(dropdown.getValue()).toBe('btc');
      expect(changeHandler).toHaveBeenCalled();
      expect(dropdown._searchableDropdown.isOpen).toBe(false);
    });
  });

  describe('Cleanup', () => {
    it('should clean up event listeners on destroy', () => {
      dropdown = createSearchableDropdown({
        id: 'test-dropdown',
        name: 'test'
      });
      container.appendChild(dropdown);
      
      const eventListenerCount = dropdown._searchableDropdown.eventListeners.length;
      expect(eventListenerCount).toBeGreaterThan(0);
      
      dropdown.destroy();
      
      expect(dropdown._searchableDropdown).toBeNull();
    });
  });
});