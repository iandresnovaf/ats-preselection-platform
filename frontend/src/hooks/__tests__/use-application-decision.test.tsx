/**
 * Tests para el hook useApplicationDecision
 */
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useApplicationDecision } from './use-application-decision';

// Mock axios
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    patch: jest.fn(),
    post: jest.fn(),
  })),
}));

// Mock toast
jest.mock('@/hooks/use-toast', () => ({
  toast: jest.fn(),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useApplicationDecision', () => {
  it('should initialize with modal closed', () => {
    const { result } = renderHook(() => useApplicationDecision(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isContactModalOpen).toBe(false);
    expect(result.current.pendingCandidate).toBeNull();
  });

  it('should open modal when continuing without contact data', async () => {
    const { result } = renderHook(() => useApplicationDecision(), {
      wrapper: createWrapper(),
    });

    const candidateInfo = {
      candidate_id: '123',
      full_name: 'John Doe',
      email: undefined,
      phone: undefined,
    };

    act(() => {
      result.current.makeConsultantDecision('app-123', { decision: 'continue' }, candidateInfo);
    });

    await waitFor(() => {
      expect(result.current.isContactModalOpen).toBe(true);
      expect(result.current.pendingCandidate).toEqual(candidateInfo);
    });
  });

  it('should not open modal when candidate has complete data', async () => {
    const { result } = renderHook(() => useApplicationDecision(), {
      wrapper: createWrapper(),
    });

    const candidateInfo = {
      candidate_id: '123',
      full_name: 'John Doe',
      email: 'john@example.com',
      phone: '+1234567890',
    };

    act(() => {
      result.current.makeConsultantDecision('app-123', { decision: 'continue' }, candidateInfo);
    });

    await waitFor(() => {
      expect(result.current.isContactModalOpen).toBe(false);
    });
  });

  it('should close modal when calling closeContactModal', () => {
    const { result } = renderHook(() => useApplicationDecision(), {
      wrapper: createWrapper(),
    });

    // Simular que el modal está abierto
    act(() => {
      result.current.makeConsultantDecision('app-123', { decision: 'continue' }, {
        candidate_id: '123',
        full_name: 'John Doe',
      });
    });

    act(() => {
      result.current.closeContactModal();
    });

    expect(result.current.isContactModalOpen).toBe(false);
    expect(result.current.pendingCandidate).toBeNull();
  });
});
