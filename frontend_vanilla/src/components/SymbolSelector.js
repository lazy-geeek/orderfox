
function createSymbolSelector() {
  const selector = document.createElement('select');
  selector.className = 'symbol-selector';

  const defaultOption = document.createElement('option');
  defaultOption.value = '';
  defaultOption.textContent = 'Select a symbol...';
  defaultOption.selected = true;
  selector.appendChild(defaultOption);
  selector.disabled = true;

  return selector;
}

function updateSymbolSelector(selector, symbols, selectedSymbol) {
  selector.innerHTML = ''; // Clear existing options
  selector.disabled = false;

  const defaultOption = document.createElement('option');
  defaultOption.value = '';
  defaultOption.textContent = 'Select a symbol...';
  selector.appendChild(defaultOption);

  symbols.forEach(symbol => {
    const option = document.createElement('option');
    option.value = symbol.id;
    option.textContent = `${symbol.uiName}${typeof symbol.volume24h === 'number' && symbol.volume24h > 0 ? ` (${(symbol.volume24h / 1000000).toFixed(2)}M)` : ''}`;
    if (symbol.id === selectedSymbol) {
      option.selected = true;
    }
    selector.appendChild(option);
  });
}

export { createSymbolSelector, updateSymbolSelector };
