/**
 * BotList component for displaying and managing bots
 * 
 * Features:
 * - DaisyUI card-based design
 * - Bot status indicators
 * - Edit/Delete actions
 * - Empty state handling
 * - Responsive grid layout
 */

export function createBotList() {
  const container = document.createElement('div');
  container.className = 'w-full';
  container.setAttribute('data-testid', 'bot-list');
  
  // Header section
  const header = document.createElement('div');
  header.className = 'flex justify-between items-center mb-6';
  header.innerHTML = `
    <div>
      <h1 class="text-2xl font-bold">My Trading Bots</h1>
      <p class="text-base-content/60">Manage your automated trading strategies</p>
    </div>
    <button class="btn btn-primary" id="create-bot-btn" data-testid="new-bot-button">
      <span class="text-lg">➕</span>
      New Bot
    </button>
  `;
  
  // Loading state
  const loadingState = document.createElement('div');
  loadingState.id = 'bot-list-loading';
  loadingState.className = 'flex justify-center items-center py-12';
  loadingState.innerHTML = `
    <div class="flex flex-col items-center gap-4">
      <span class="loading loading-spinner loading-lg"></span>
      <p class="text-base-content/60">Loading your bots...</p>
    </div>
  `;
  
  // Empty state
  const emptyState = document.createElement('div');
  emptyState.id = 'bot-list-empty';
  emptyState.className = 'text-center py-12 hidden';
  emptyState.innerHTML = `
    <div class="text-6xl mb-4">🤖</div>
    <h2 class="text-xl font-semibold mb-2">No bots yet</h2>
    <p class="text-base-content/60 mb-6">Create your first trading bot to get started</p>
    <button class="btn btn-primary" id="create-first-bot-btn">
      <span class="text-lg">➕</span>
      Create Your First Bot
    </button>
  `;
  
  // Bot grid container
  const botGrid = document.createElement('div');
  botGrid.id = 'bot-grid';
  botGrid.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 hidden';
  
  // Stats section
  const statsSection = document.createElement('div');
  statsSection.id = 'bot-stats';
  statsSection.className = 'grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 hidden';
  
  const statsItems = [
    { label: 'Total Bots', value: '0', id: 'total-bots', color: 'text-primary' },
    { label: 'Active Bots', value: '0', id: 'active-bots', color: 'text-success' },
    { label: 'Inactive Bots', value: '0', id: 'inactive-bots', color: 'text-warning' }
  ];
  
  statsItems.forEach(stat => {
    const statCard = document.createElement('div');
    statCard.className = 'stat bg-base-200 rounded-lg';
    statCard.innerHTML = `
      <div class="stat-value ${stat.color}" id="${stat.id}">${stat.value}</div>
      <div class="stat-title">${stat.label}</div>
    `;
    statsSection.appendChild(statCard);
  });
  
  container.appendChild(header);
  container.appendChild(statsSection);
  container.appendChild(loadingState);
  container.appendChild(emptyState);
  container.appendChild(botGrid);
  
  return container;
}

/**
 * Create a bot card element
 * @param {Object} bot - Bot data
 * @returns {HTMLElement} Bot card element
 */
export function createBotCard(bot) {
  const card = document.createElement('div');
  card.className = 'card bg-base-100 shadow-lg hover:shadow-xl transition-shadow duration-200';
  card.setAttribute('data-bot-id', bot.id);
  card.setAttribute('data-testid', 'bot-card');
  
  const statusColor = bot.isActive ? 'success' : 'warning';
  const statusText = bot.isActive ? 'Active' : 'Inactive';
  const statusIcon = bot.isActive ? '🟢' : '🟡';
  
  card.innerHTML = `
    <div class="card-body">
      <div class="flex justify-between items-start mb-3">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-lg">${statusIcon}</span>
          <span class="badge badge-${statusColor}" data-testid="bot-status">${statusText}</span>
          <span class="badge badge-${bot.isPaperTrading ? 'info' : 'error'}">
            ${bot.isPaperTrading ? '📝 Paper' : '💰 Live'}
          </span>
        </div>
        <div class="dropdown dropdown-end">
          <div tabindex="0" role="button" class="btn btn-ghost btn-sm btn-circle" data-testid="bot-menu-button">
            <span class="text-lg">⋮</span>
          </div>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
            <li><a class="edit-bot-btn" data-bot-id="${bot.id}" data-testid="edit-bot-button">
              <span>✏️</span>
              Edit Bot
            </a></li>
            <li><a class="toggle-bot-btn" data-bot-id="${bot.id}" data-testid="toggle-bot-button">
              <span>${bot.isActive ? '⏸️' : '▶️'}</span>
              ${bot.isActive ? 'Deactivate' : 'Activate'}
            </a></li>
            <li><a class="delete-bot-btn text-error" data-bot-id="${bot.id}" data-testid="delete-bot-button">
              <span>🗑️</span>
              Delete Bot
            </a></li>
          </ul>
        </div>
      </div>
      
      <h3 class="card-title text-lg mb-2" data-testid="bot-name">${bot.name}</h3>
      
      <div class="flex items-center gap-2 mb-4">
        <div class="badge badge-outline" data-testid="bot-symbol">${bot.symbol}</div>
        <div class="text-sm text-base-content/60">
          Created: ${new Date(bot.createdAt).toLocaleDateString()}
        </div>
      </div>
      
      <div class="card-actions justify-end">
        <button class="btn btn-sm btn-outline select-bot-btn" data-bot-id="${bot.id}">
          Select Bot
        </button>
        <button class="btn btn-sm btn-primary edit-bot-btn" data-bot-id="${bot.id}">
          Edit
        </button>
      </div>
    </div>
  `;
  
  return card;
}

/**
 * Update bot list display
 * @param {HTMLElement} container - Bot list container
 * @param {Array} bots - Array of bot objects
 * @param {Object} options - Display options
 */
export function updateBotList(container, bots, options = {}) {
  const { loading = false, error = null } = options;
  
  const loadingState = container.querySelector('#bot-list-loading');
  const emptyState = container.querySelector('#bot-list-empty');
  const botGrid = container.querySelector('#bot-grid');
  const statsSection = container.querySelector('#bot-stats');
  
  // Hide all states first
  loadingState.classList.add('hidden');
  emptyState.classList.add('hidden');
  botGrid.classList.add('hidden');
  statsSection.classList.add('hidden');
  
  if (loading) {
    loadingState.classList.remove('hidden');
    return;
  }
  
  if (error) {
    // Show error state
    emptyState.classList.remove('hidden');
    emptyState.innerHTML = `
      <div class="text-6xl mb-4">❌</div>
      <h2 class="text-xl font-semibold mb-2">Error loading bots</h2>
      <p class="text-base-content/60 mb-6">${error}</p>
      <button class="btn btn-primary" id="retry-load-btn">
        <span class="text-lg">🔄</span>
        Retry
      </button>
    `;
    return;
  }
  
  if (!bots || bots.length === 0) {
    emptyState.classList.remove('hidden');
    return;
  }
  
  // Show stats and bot grid
  statsSection.classList.remove('hidden');
  botGrid.classList.remove('hidden');
  
  // Update stats
  const totalBots = bots.length;
  const activeBots = bots.filter(bot => bot.isActive).length;
  const inactiveBots = totalBots - activeBots;
  
  container.querySelector('#total-bots').textContent = totalBots;
  container.querySelector('#active-bots').textContent = activeBots;
  container.querySelector('#inactive-bots').textContent = inactiveBots;
  
  // Clear existing bot cards
  botGrid.innerHTML = '';
  
  // Create bot cards
  bots.forEach(bot => {
    const card = createBotCard(bot);
    botGrid.appendChild(card);
  });
}

/**
 * Add bot list event listeners
 * @param {HTMLElement} container - Bot list container
 * @param {Object} callbacks - Event callbacks
 */
export function addBotListEventListeners(container, callbacks = {}) {
  const {
    onCreateBot = () => {},
    onEditBot = () => {},
    onDeleteBot = () => {},
    onToggleBot = () => {},
    onSelectBot = () => {},
    onRetryLoad = () => {}
  } = callbacks;
  
  container.addEventListener('click', (e) => {
    const target = e.target.closest('button, a');
    if (!target) return;
    
    const botId = target.getAttribute('data-bot-id');
    
    if (target.id === 'create-bot-btn' || target.id === 'create-first-bot-btn') {
      onCreateBot();
    } else if (target.classList.contains('edit-bot-btn')) {
      onEditBot(botId);
    } else if (target.classList.contains('delete-bot-btn')) {
      onDeleteBot(botId);
    } else if (target.classList.contains('toggle-bot-btn')) {
      onToggleBot(botId);
    } else if (target.classList.contains('select-bot-btn')) {
      onSelectBot(botId);
    } else if (target.id === 'retry-load-btn') {
      onRetryLoad();
    }
  });
}

/**
 * Get bot by ID from the displayed list
 * @param {HTMLElement} container - Bot list container
 * @param {string} botId - Bot ID
 * @returns {HTMLElement|null} Bot card element
 */
export function getBotCardById(container, botId) {
  return container.querySelector(`[data-bot-id="${botId}"]`);
}

/**
 * Update bot card status
 * @param {HTMLElement} container - Bot list container
 * @param {string} botId - Bot ID
 * @param {boolean} isActive - New active status
 */
export function updateBotCardStatus(container, botId, isActive) {
  const card = getBotCardById(container, botId);
  if (!card) return;
  
  const statusIcon = card.querySelector('.text-lg');
  const statusBadge = card.querySelector('.badge');
  const toggleBtn = card.querySelector('.toggle-bot-btn');
  
  statusIcon.textContent = isActive ? '🟢' : '🟡';
  statusBadge.className = `badge badge-${isActive ? 'success' : 'warning'}`;
  statusBadge.textContent = isActive ? 'Active' : 'Inactive';
  
  toggleBtn.innerHTML = `
    <span>${isActive ? '⏸️' : '▶️'}</span>
    ${isActive ? 'Deactivate' : 'Activate'}
  `;
}

/**
 * Remove bot card from display
 * @param {HTMLElement} container - Bot list container
 * @param {string} botId - Bot ID
 */
export function removeBotCard(container, botId) {
  const card = getBotCardById(container, botId);
  if (card) {
    card.remove();
  }
}