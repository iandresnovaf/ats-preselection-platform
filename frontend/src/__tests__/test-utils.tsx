"""Test utilities for frontend tests."""
import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '@/store/auth';

// Mock API responses
export const mockApi = {
  // Auth mocks
  auth: {
    login: jest.fn(),
    logout: jest.fn(),
    getMe: jest.fn(),
    refreshToken: jest.fn(),
  },
  
  // Jobs mocks
  jobs: {
    list: jest.fn(),
    get: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    close: jest.fn(),
  },
  
  // Candidates mocks
  candidates: {
    list: jest.fn(),
    get: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    evaluate: jest.fn(),
    changeStatus: jest.fn(),
  },
  
  // Evaluations mocks
  evaluations: {
    list: jest.fn(),
    get: jest.fn(),
    create: jest.fn(),
    delete: jest.fn(),
  },
  
  // Reset all mocks
  resetAll: () => {
    Object.values(mockApi.auth).forEach(mock => mock.mockReset?.());
    Object.values(mockApi.jobs).forEach(mock => mock.mockReset?.());
    Object.values(mockApi.candidates).forEach(mock => mock.mockReset?.());
    Object.values(mockApi.evaluations).forEach(mock => mock.mockReset?.());
  },
};

// Create a test query client
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// Wrapper with all providers
interface AllProvidersProps {
  children: React.ReactNode;
}

function AllProviders({ children }: AllProvidersProps) {
  const queryClient = createTestQueryClient();
  
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

// Custom render with providers
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) {
  return render(ui, { wrapper: AllProviders, ...options });
}

// Mock data generators
export const generateMockJob = (overrides = {}) => ({
  id: 'job-1',
  title: 'Senior Software Engineer',
  description: 'We are looking for a senior developer...',
  department: 'Engineering',
  location: 'Remote',
  seniority: 'Senior',
  sector: 'Technology',
  status: 'published',
  is_active: true,
  assigned_consultant_id: 'consultant-1',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  ...overrides,
});

export const generateMockCandidate = (overrides = {}) => ({
  id: 'candidate-1',
  full_name: 'John Doe',
  email: 'john@example.com',
  phone: '+1234567890',
  job_opening_id: 'job-1',
  status: 'new',
  source: 'manual',
  is_duplicate: false,
  duplicate_of_id: null,
  zoho_candidate_id: null,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  ...overrides,
});

export const generateMockEvaluation = (overrides = {}) => ({
  id: 'eval-1',
  candidate_id: 'candidate-1',
  score: 85.5,
  decision: 'PROCEED',
  strengths: ['Python', 'System Design', 'Communication'],
  gaps: ['DevOps', 'Cloud'],
  red_flags: [],
  evidence: 'Strong backend skills demonstrated...',
  llm_provider: 'openai',
  llm_model: 'gpt-4o-mini',
  prompt_version: 'v1.0',
  created_at: '2025-01-01T00:00:00Z',
  ...overrides,
});

export const generateMockUser = (overrides = {}) => ({
  id: 'user-1',
  email: 'admin@example.com',
  full_name: 'Admin User',
  role: 'super_admin',
  status: 'active',
  created_at: '2025-01-01T00:00:00Z',
  last_login: null,
  ...overrides,
});

// Helper to set auth state in store
export function setAuthState(user: any = null, token: string | null = null) {
  const store = useAuthStore.getState();
  store.setUser(user);
  store.setToken(token);
}

// Helper to clear auth state
export function clearAuthState() {
  const store = useAuthStore.getState();
  store.setUser(null);
  store.setToken(null);
}

// Wait for loading to finish
export async function waitForLoadingToFinish() {
  // Wait for next tick to allow React to process
  await new Promise(resolve => setTimeout(resolve, 0));
}

// Re-export testing library utilities
export { screen, waitFor, within } from '@testing-library/react';
export { userEvent } from '@testing-library/user-event';
