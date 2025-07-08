// Global test setup
import { vi } from 'vitest'

// Mock window methods that might not be available in test environment
global.ResizeObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock window.addEventListener
Object.defineProperty(window, 'addEventListener', {
  value: vi.fn(),
  writable: true
})

// Mock window.dispatchEvent
Object.defineProperty(window, 'dispatchEvent', {
  value: vi.fn(),
  writable: true
})