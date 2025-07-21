
export function createMainLayout() {
  // Create DaisyUI drawer layout
  const drawerWrapper = document.createElement('div');
  drawerWrapper.className = 'drawer lg:drawer-open';
  drawerWrapper.style.height = '100vh';

  // Hidden checkbox for mobile drawer toggle
  const drawerToggle = document.createElement('input');
  drawerToggle.id = 'drawer-toggle';
  drawerToggle.type = 'checkbox';
  drawerToggle.className = 'drawer-toggle';
  drawerToggle.checked = true; // Make sidebar open by default
  drawerWrapper.appendChild(drawerToggle);

  // Main drawer content
  const drawerContent = document.createElement('div');
  drawerContent.className = 'drawer-content flex flex-col';
  
  // Header with mobile menu button
  const navbar = document.createElement('div');
  navbar.className = 'navbar bg-base-200 w-full shadow-md';
  
  const navbarStart = document.createElement('div');
  navbarStart.className = 'navbar-start';
  
  // Mobile menu button (hidden on large screens)
  const mobileMenuBtn = document.createElement('label');
  mobileMenuBtn.setAttribute('for', 'drawer-toggle');
  mobileMenuBtn.className = 'btn btn-square btn-ghost drawer-button lg:hidden';
  mobileMenuBtn.innerHTML = `
    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
    </svg>
  `;
  navbarStart.appendChild(mobileMenuBtn);
  
  // Logo/Title
  const logo = document.createElement('div');
  logo.className = 'btn btn-ghost text-xl font-bold';
  logo.textContent = 'OrderFox';
  navbarStart.appendChild(logo);
  
  navbar.appendChild(navbarStart);
  
  // Header controls
  const navbarEnd = document.createElement('div');
  navbarEnd.className = 'navbar-end gap-4';
  
  const themeSwitcherPlaceholder = document.createElement('div');
  themeSwitcherPlaceholder.id = 'theme-switcher-placeholder';
  themeSwitcherPlaceholder.textContent = 'ThemeSwitcher';
  
  navbarEnd.appendChild(themeSwitcherPlaceholder);
  
  navbar.appendChild(navbarEnd);
  drawerContent.appendChild(navbar);
  
  // Main content area (trading interface)
  const mainContent = document.createElement('div');
  mainContent.id = 'main-content';
  mainContent.setAttribute('data-testid', 'trading-interface');
  mainContent.className = 'flex-1 p-4 bg-base-100 overflow-auto';
  mainContent.style.display = 'none'; // Hidden by default until bot is selected
  
  // Bot selection prompt (shown when no bot is selected)
  const botSelectionPrompt = document.createElement('div');
  botSelectionPrompt.id = 'bot-selection-prompt';
  botSelectionPrompt.className = 'flex-1 flex items-center justify-center bg-base-100';
  botSelectionPrompt.innerHTML = `
    <div class="text-center">
      <div class="text-6xl mb-4">🤖</div>
      <h2 class="text-2xl font-bold mb-2">Welcome to OrderFox</h2>
      <p class="text-base-content/60 mb-6">Select a bot from the sidebar to start trading</p>
      <div class="btn btn-primary" onclick="document.getElementById('drawer-toggle').checked = true;">
        View Bots
      </div>
    </div>
  `;
  
  // Bot management section (shown when in bot management mode)
  const botManagementSection = document.createElement('div');
  botManagementSection.id = 'bot-management-section';
  botManagementSection.className = 'flex-1 p-4 bg-base-100 overflow-auto';
  botManagementSection.style.display = 'none'; // Hidden by default
  
  // Bot list placeholder
  const botListPlaceholder = document.createElement('div');
  botListPlaceholder.id = 'bot-list-placeholder';
  botListPlaceholder.className = 'w-full';
  botListPlaceholder.textContent = 'BotList will be inserted here';
  botManagementSection.appendChild(botListPlaceholder);
  
  // Main trading content with side-by-side layout
  const tradingContentWrapper = document.createElement('div');
  tradingContentWrapper.className = 'trading-content-wrapper flex flex-col lg:flex-row gap-4 h-full';
  
  // Left Section - Chart (flexible width)
  const leftSection = document.createElement('div');
  leftSection.className = 'left-section flex-1 min-w-0'; // min-w-0 prevents flex overflow issues
  
  const candlestickChartPlaceholder = document.createElement('div');
  candlestickChartPlaceholder.id = 'candlestick-chart-placeholder';
  candlestickChartPlaceholder.textContent = 'CandlestickChart';
  leftSection.appendChild(candlestickChartPlaceholder);
  
  // Right Section - Tabbed Trading Tables (fixed/min width)
  const rightSection = document.createElement('div');
  rightSection.className = 'right-section w-full lg:w-96 flex-shrink-0';
  
  const tabbedTradingPlaceholder = document.createElement('div');
  tabbedTradingPlaceholder.id = 'tabbed-trading-placeholder';
  tabbedTradingPlaceholder.textContent = 'TabbedTradingDisplay';
  rightSection.appendChild(tabbedTradingPlaceholder);
  
  tradingContentWrapper.appendChild(leftSection);
  tradingContentWrapper.appendChild(rightSection);
  
  mainContent.appendChild(tradingContentWrapper);
  
  drawerContent.appendChild(botSelectionPrompt);
  drawerContent.appendChild(botManagementSection);
  drawerContent.appendChild(mainContent);
  
  // Drawer side (sidebar)
  const drawerSide = document.createElement('div');
  drawerSide.className = 'drawer-side';
  
  // Overlay for mobile
  const drawerOverlay = document.createElement('label');
  drawerOverlay.setAttribute('for', 'drawer-toggle');
  drawerOverlay.setAttribute('aria-label', 'close sidebar');
  drawerOverlay.className = 'drawer-overlay';
  drawerSide.appendChild(drawerOverlay);
  
  // Sidebar content
  const sidebarContent = document.createElement('div');
  sidebarContent.className = 'menu p-4 w-80 min-h-full bg-base-200 text-base-content';
  
  // Bot navigation placeholder
  const botNavigationPlaceholder = document.createElement('div');
  botNavigationPlaceholder.id = 'bot-navigation-placeholder';
  botNavigationPlaceholder.textContent = 'BotNavigation will be inserted here';
  sidebarContent.appendChild(botNavigationPlaceholder);
  
  drawerSide.appendChild(sidebarContent);
  
  drawerWrapper.appendChild(drawerContent);
  drawerWrapper.appendChild(drawerSide);
  
  return drawerWrapper;
}
