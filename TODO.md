### To-Do List: Frontend Conversion

**Phase 1: Project Scaffolding**
- [x] Create a new directory named `frontend_vanilla` at the root of the project.
- [x] Use `npm create vite@latest` with the `vanilla` template to initialize a new project inside `frontend_vanilla`.
- [x] Review the default Vite structure (`index.html`, `main.js`, `style.css`) and clean out the boilerplate content.
- [x] Create the necessary subdirectories inside `frontend_vanilla`: `components/`, `services/`, and `store/`.

**Phase 2: UI Component Conversion**
- [x] **Consolidate CSS:** Move all CSS from the original `frontend` project's component files into `frontend_vanilla/style.css`.
- [x] **Prefix/Namespace CSS:** Review the consolidated CSS for conflicting class names and apply more specific naming to avoid global scope issues.
- [x] **Convert `App.tsx` Layout:** Create a `layouts/MainLayout.js` module inside `frontend_vanilla` that generates the main application shell and layout.
- [x] **Convert UI Components:** For each React component, create a corresponding JavaScript module inside `frontend_vanilla/components/`. Each module will export a function that creates, updates, and returns a DOM element.
    - [x] `SymbolSelector.tsx` -> `SymbolSelector.js`
    - [x] `CandlestickChart.tsx` -> `CandlestickChart.js` (This will involve installing and using the `echarts` library directly).
    - [x] `OrderBookDisplay.tsx` -> `OrderBookDisplay.js`
    - [x] `ManualTradeForm.tsx` -> `ManualTradeForm.js`
    - [x] `PositionsTable.tsx` -> `PositionsTable.js`
    - [x] `TradingModeToggle.tsx` -> `TradingModeToggle.js`

**Phase 3: State Management Replacement**
- [x] **Create Store:** Create a `store/store.js` module inside `frontend_vanilla`.
- [x] **Implement State Object:** Inside `store.js`, define and export a central `state` object.
- [x] **Implement Pub/Sub:** Create `subscribe` and `notify` functions for reactive state updates.
- [ ] **Create State Mutators:** Create functions for modifying the state (e.g., `setSymbol`, `updateOrderBook`) that call `notify()` after making changes.
- [x] **Translate Slice Logic:** Port the business logic from the Redux slices (`marketDataSlice.ts`, `tradingSlice.ts`) into the new state mutator functions.

**Phase 4: Backend Communication**
- [x] **Create API Client:** Create a `services/apiClient.js` module inside `frontend_vanilla`.
- [x] **Implement HTTP Requests:** Use the native `fetch` API for all HTTP calls.
- [x] **Create WebSocket Service:** Create a `services/websocketService.js` module inside `frontend_vanilla`.
- [x] **Implement WebSocket Logic:** Use the native `WebSocket` API to connect to the backend and update the store on new messages.

**Phase 5: Integration and Application Logic**
- [x] **Develop `main.js`:** This file (the entry point for Vite) will orchestrate the application.
- [x] **Initial Render:** In `main.js`, import the main layout and component modules, render the initial DOM, and append it to the `<div id="app">` in `index.html`.
- [x] **Initial Data Fetch:** Use `apiClient.js` to fetch initial data and populate the store.
- [x] **Establish WebSocket Connection:** Initialize `websocketService.js`.
- [x] **Wire Up Event Handlers:** Add event listeners to the DOM to handle user interactions.

**Phase 6: Cleanup**
- [ ] **Verify Functionality:** Thoroughly test the new Vite-based application.
- [x] **Update Root `package.json`:** Modify the `npm run dev` script to correctly launch the new Vite frontend alongside the backend.
- [ ] **Remove Old Frontend:** Once the new version is confirmed to be working, delete the original `frontend/` directory.
- [ ] **Update `README.md`:** Adjust the project's documentation to reflect the new frontend architecture and setup instructions.
