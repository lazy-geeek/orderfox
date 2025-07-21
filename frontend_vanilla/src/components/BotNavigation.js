/**
 * BotNavigation component for sidebar navigation
 * 
 * Features:
 * - DaisyUI menu structure
 * - Bot management navigation
 * - Current view state management
 * - Responsive design
 */

export function createBotNavigation() {
  const navigation = document.createElement('div');
  navigation.className = 'flex flex-col h-full';
  navigation.setAttribute('data-testid', 'bot-navigation');
  
  // Navigation header
  const header = document.createElement('div');
  header.className = 'flex items-center gap-3 mb-6 px-2';
  header.innerHTML = `
    <div class="text-2xl">🤖</div>
    <div>
      <h2 class="text-lg font-bold">Bot Management</h2>
      <p class="text-sm text-base-content/60">Manage your trading bots</p>
    </div>
  `;
  
  // Navigation menu
  const menu = document.createElement('ul');
  menu.className = 'menu menu-md flex-1';
  
  // Menu items
  const menuItems = [
    {
      id: 'bots',
      label: 'My Bots',
      icon: '🤖',
      active: true,
      action: 'show-bot-list'
    },
    {
      id: 'create-bot',
      label: 'Create Bot',
      icon: '➕',
      active: false,
      action: 'create-bot'
    },
    {
      id: 'trading-view',
      label: 'Trading View',
      icon: '📊',
      active: false,
      action: 'show-trading',
      disabled: true
    }
  ];
  
  menuItems.forEach(item => {
    const listItem = document.createElement('li');
    
    const link = document.createElement('a');
    link.className = `flex items-center gap-3 ${item.active ? 'active' : ''} ${item.disabled ? 'disabled' : ''}`;
    link.setAttribute('data-action', item.action);
    link.setAttribute('data-item-id', item.id);
    
    if (item.disabled) {
      link.setAttribute('disabled', 'true');
    }
    
    link.innerHTML = `
      <span class="text-lg">${item.icon}</span>
      <span class="flex-1">${item.label}</span>
      ${item.disabled ? '<span class="text-xs opacity-50">Select bot first</span>' : ''}
    `;
    
    listItem.appendChild(link);
    menu.appendChild(listItem);
  });
  
  // Bot info section (shown when bot is selected)
  const botInfo = document.createElement('div');
  botInfo.id = 'selected-bot-info';
  botInfo.className = 'hidden mt-auto p-4 bg-base-200 rounded-lg';
  botInfo.innerHTML = `
    <div class="flex items-center gap-3 mb-2">
      <div class="w-2 h-2 bg-success rounded-full"></div>
      <span class="font-semibold" id="selected-bot-name">No bot selected</span>
    </div>
    <div class="text-sm text-base-content/60">
      <div>Symbol: <span id="selected-bot-symbol">-</span></div>
      <div>Status: <span id="selected-bot-status">-</span></div>
    </div>
  `;
  
  // Footer with settings
  const footer = document.createElement('div');
  footer.className = 'mt-auto pt-4 border-t border-base-300';
  footer.innerHTML = `
    <ul class="menu menu-sm">
      <li><a href="#" class="flex items-center gap-2">
        <span>⚙️</span>
        <span>Settings</span>
      </a></li>
      <li><a href="#" class="flex items-center gap-2">
        <span>❓</span>
        <span>Help</span>
      </a></li>
    </ul>
  `;
  
  navigation.appendChild(header);
  navigation.appendChild(menu);
  navigation.appendChild(botInfo);
  navigation.appendChild(footer);
  
  return navigation;
}

/**
 * Update navigation active state
 * @param {HTMLElement} navigation - Navigation element
 * @param {string} activeItemId - ID of the active menu item
 */
export function updateNavigationState(navigation, activeItemId) {
  const menuItems = navigation.querySelectorAll('[data-item-id]');
  menuItems.forEach(item => {
    const itemId = item.getAttribute('data-item-id');
    if (itemId === activeItemId) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });
}

/**
 * Show selected bot info in navigation
 * @param {HTMLElement} navigation - Navigation element
 * @param {Object} bot - Bot data
 */
export function showSelectedBotInfo(navigation, bot) {
  const botInfo = navigation.querySelector('#selected-bot-info');
  const nameElement = navigation.querySelector('#selected-bot-name');
  const symbolElement = navigation.querySelector('#selected-bot-symbol');
  const statusElement = navigation.querySelector('#selected-bot-status');
  
  if (bot) {
    nameElement.textContent = bot.name;
    symbolElement.textContent = bot.symbol;
    statusElement.textContent = bot.isActive ? 'Active' : 'Inactive';
    statusElement.className = bot.isActive ? 'text-success' : 'text-warning';
    
    // Update status indicator
    const statusDot = navigation.querySelector('.w-2.h-2');
    statusDot.className = `w-2 h-2 rounded-full ${bot.isActive ? 'bg-success' : 'bg-warning'}`;
    
    botInfo.classList.remove('hidden');
    
    // Enable trading view
    const tradingViewItem = navigation.querySelector('[data-item-id="trading-view"]');
    tradingViewItem.classList.remove('disabled');
    tradingViewItem.removeAttribute('disabled');
    tradingViewItem.querySelector('.text-xs').textContent = '';
  } else {
    botInfo.classList.add('hidden');
    
    // Disable trading view
    const tradingViewItem = navigation.querySelector('[data-item-id="trading-view"]');
    tradingViewItem.classList.add('disabled');
    tradingViewItem.setAttribute('disabled', 'true');
    tradingViewItem.querySelector('.text-xs').textContent = 'Select bot first';
  }
}

/**
 * Add navigation event listeners
 * @param {HTMLElement} navigation - Navigation element
 * @param {Function} onNavigate - Navigation callback
 */
export function addNavigationEventListeners(navigation, onNavigate) {
  navigation.addEventListener('click', (e) => {
    const menuItem = e.target.closest('[data-action]');
    if (menuItem && !menuItem.hasAttribute('disabled')) {
      const action = menuItem.getAttribute('data-action');
      const itemId = menuItem.getAttribute('data-item-id');
      
      // Update active state
      updateNavigationState(navigation, itemId);
      
      // Call navigation callback
      if (onNavigate) {
        onNavigate(action, itemId);
      }
    }
  });
}