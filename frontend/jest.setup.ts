import '@testing-library/jest-dom';

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock fetch
global.fetch = jest.fn();

// Mock console.error to suppress React warnings in tests
const originalConsoleError = console.error;
console.error = (...args: any[]) => {
  // Filter out specific React warnings if needed
  if (/Warning.*not wrapped in act/.test(args[0])) {
    return;
  }
  originalConsoleError.apply(console, args);
};
