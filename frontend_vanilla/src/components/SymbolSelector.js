
function createSymbolSelector() {
  const selector = document.createElement('select');
  selector.className = 'symbol-selector';
  selector.disabled = true;

  return selector;
}

function updateSymbolSelector(selector, symbols, selectedSymbol) {
  selector.innerHTML = ''; // Clear existing options
  selector.disabled = false;

  symbols.forEach(symbol => {
    const option = document.createElement('option');
    option.value = symbol.id;
    option.textContent = `${symbol.uiName}${symbol.volume24hFormatted ? ` (${symbol.volume24hFormatted})` : ''}`;
    if (symbol.id === selectedSymbol) {
      option.selected = true;
    }
    selector.appendChild(option);
  });
}

export { createSymbolSelector, updateSymbolSelector };
