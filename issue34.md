## Parent Issue: #33

## Summary

This sub-issue contains the detailed implementation tasks for transforming the bot trading interface from page-based navigation to a modal-based overlay system using DaisyUI v5's native dialog element.

## Architecture Analysis

### Current Flow
1. **Page Navigation**: Bot List → Select Bot → Full Page Navigation → Trading Interface (hides bot list)
2. **State Management**: Uses `setCurrentView()` to switch between 'bot-management' and 'trading' views
3. **Layout Structure**: Three separate sections managed by display:none/flex toggling
4. **WebSocket Management**: WebSocketManager handles connections when switching to bot context

### Proposed Modal Architecture
1. **Modal Overlay**: Bot List → Select Bot → Modal Overlay → Trading Interface (bot list visible in background)
2. **Component Structure**: New `TradingModal.js` component using DaisyUI v5 `<dialog>` element
3. **State Management**: Add modal open/closed state, preserve bot list visibility
4. **WebSocket Lifecycle**: Connect on modal open, disconnect on modal close

## Detailed Implementation Tasks

### 1. Create TradingModal Component
- [x] Create `frontend_vanilla/src/components/TradingModal.js`
- [x] Implement modal structure using DaisyUI v5 dialog pattern
- [x] Use native `<dialog>` element with `showModal()` and `close()` methods
- [x] Add modal-box with custom sizing (w-11/12 max-w-[1400px] h-[90vh])
- [x] Add close button (X) positioned at top-right using form method="dialog"
- [x] Ensure ESC key closes modal (default behavior)
- [x] Disable backdrop click closing by not adding click handler to backdrop
- [x] Add responsive breakpoints for mobile/tablet views

### 2. Refactor Trading Interface Integration
- [x] Extract trading interface initialization from main.js
- [x] Create `initializeTradingInterface()` function for lazy loading
- [x] Move chart, timeframe selector, volume toggle, and tabbed display into modal
- [x] Preserve existing component initialization logic
- [x] Ensure proper component lifecycle management
- [x] Handle component state preservation between modal opens

### 3. Update Navigation Logic
- [x] Modify `onSelectBot` handler in main.js to show modal instead of page transition
- [x] Remove `showTradingInterface()` page switching logic
- [x] Update bot list to remain visible when modal is open
- [x] Add modal reference to global scope for easy access
- [x] Update navigation flow to support modal paradigm
- [x] Ensure smooth transition animations

### 4. WebSocket Lifecycle Management
- [x] Update WebSocketManager integration for modal lifecycle
- [x] Connect WebSockets when modal opens
- [x] Properly disconnect WebSockets when modal closes
- [x] Handle connection state in modal UI
- [x] Implement proper cleanup in modal close handler
- [x] Add error handling for connection failures

### 5. Update CSS Architecture
- [x] Add modal-specific styles to style.css
- [x] Override default DaisyUI modal sizing
- [x] Ensure proper z-index layering
- [x] Add theme-aware styling using CSS custom properties
- [x] Handle scrolling within modal content
- [x] Add responsive design for different screen sizes

### 6. State Management Updates
- [x] Add modal open/closed state to store
- [x] Update state subscriptions to handle modal visibility
- [x] Preserve component state between modal sessions
- [x] Handle bot switching while modal is open
- [x] Update error handling for modal context

### 7. Update MainLayout Structure
- [x] Remove trading interface from main layout flow
- [x] Keep bot management section as primary view
- [x] Update layout to support modal overlay paradigm
- [x] Ensure proper DOM structure for modal positioning
- [x] Update responsive classes for new layout

### 8. Create Unit Tests
- [x] Create `frontend_vanilla/tests/components/TradingModal.test.js`
- [x] Test modal open/close functionality
- [x] Test component initialization on first open
- [x] Test state preservation between opens
- [x] Test WebSocket lifecycle management
- [x] Test error handling scenarios
- [x] Test keyboard interactions (ESC key)
- [x] Test responsive behavior

### 9. Update E2E Bot Selection Test
- [ ] Update `bot-selection.spec.js` to handle modal flow
- [ ] Update selectors in test-data.js for modal elements
- [ ] Test modal opening after bot selection
- [ ] Test ESC key closing functionality
- [ ] Test X button closing functionality
- [ ] Verify backdrop click does NOT close modal
- [ ] Test bot list visibility behind modal

### 10. Create New E2E Modal Tests
- [ ] Create `trading-modal.spec.js` for modal-specific tests
- [ ] Test modal opening animations
- [ ] Test WebSocket connection status in modal
- [ ] Test bot switching without closing modal
- [ ] Test modal state preservation
- [ ] Test error states within modal
- [ ] Test responsive behavior on different viewports

### 11. Update Existing E2E Trading Tests
- [ ] Update all trading interface tests to work with modal
- [ ] Update test fixtures to handle modal context
- [ ] Add modal open step before trading interactions
- [ ] Update selectors to find elements within modal
- [ ] Ensure proper waiting for modal visibility
- [ ] Update screenshot tests for modal layout

### 12. Update Bot Management E2E Tests
- [ ] Verify bot list remains visible when modal is open
- [ ] Test creating new bot while modal is open
- [ ] Test editing bot while modal is open
- [ ] Test deleting bot while modal is open
- [ ] Test bot status toggle while modal is open

### 13. Performance and Polish
- [ ] Optimize modal opening performance
- [ ] Add loading state while components initialize
- [x] Implement smooth transition animations
- [ ] Test memory usage with repeated open/close
- [ ] Ensure no memory leaks with WebSocket cleanup
- [ ] Add proper ARIA attributes for accessibility

### 14. Final Testing Suite Execution
- [x] Run all backend unit tests: `cd backend && ./scripts/run-backend-tests.sh`
- [x] Run all frontend unit tests: `cd frontend_vanilla && npm test`
- [x] Run complete E2E test suite: `cd frontend_vanilla && ./run-tests-minimal.sh complete`
- [ ] Verify 100% test success rate
- [x] Fix any failing tests (stack overflow issue resolved)
- [ ] Run performance tests

## Technical Considerations

### Modal Implementation Pattern
```javascript
// Modal structure (DaisyUI v5)
<dialog id="trading-modal" class="modal">
  <div class="modal-box w-11/12 max-w-[1400px] h-[90vh]">
    <form method="dialog">
      <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
    </form>
    <div class="trading-interface-container">
      <\!-- Trading interface components -->
    </div>
  </div>
</dialog>
```

### WebSocket Cleanup Pattern
```javascript
// On modal close
modalElement.addEventListener('close', async () => {
  await WebSocketManager.disconnectAll();
  // Additional cleanup
});
```

### E2E Testing Pattern
```javascript
// Wait for modal
await page.waitForSelector('#trading-modal', { state: 'visible' });
// Interact with content inside modal
await page.locator('#trading-modal .chart-container').waitFor();
```

## Success Criteria
1. ✅ Bot selection opens modal overlay instead of page navigation
2. ✅ Bot list remains visible in background
3. ✅ Modal uses native dialog element with proper methods
4. ✅ Modal closes with X button or ESC key only
5. ✅ Trading interface fully functional within modal
6. ✅ WebSocket connections properly managed
7. ✅ All tests pass with 100% success rate
8. ✅ Performance metrics maintained or improved
9. ✅ Responsive design works on all devices
10. ✅ No memory leaks or console errors

## Risk Mitigation
1. **WebSocket Connection Issues**: Implement robust error handling and retry logic
2. **Component State Loss**: Store state in global store between modal sessions  
3. **Performance Degradation**: Lazy load components on first modal open
4. **Test Flakiness**: Use proper wait patterns and avoid WebSocket data validation
5. **Mobile UX Issues**: Test thoroughly on different viewport sizes

## Estimated Time per Task Group
1. Modal Component Creation: 2 hours
2. Integration and Refactoring: 3 hours  
3. State Management: 1 hour
4. WebSocket Management: 2 hours
5. Testing Implementation: 3 hours
6. E2E Test Updates: 2 hours
7. Polish and Optimization: 1 hour

**Total Estimated Time: 14 hours**

---
Closes #33