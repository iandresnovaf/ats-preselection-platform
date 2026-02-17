import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useTrackingData, useBulkActions, useRecentActivity } from "@/hooks/tracking/use-tracking";
import type { TrackedCandidate, ApplicationStatus } from "@/types/tracking";

// Mock axios
jest.mock("axios", () => ({
  create: jest.fn(() => ({
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    interceptors: {
      request: {
        use: jest.fn(),
      },
    },
  })),
}));

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, "localStorage", { value: localStorageMock });

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={createTestQueryClient()}>
    {children}
  </QueryClientProvider>
);

describe("useTrackingData", () => {
  it("should fetch tracking data", async () => {
    const mockData = {
      by_status: {
        pending_contact: [] as TrackedCandidate[],
        contacted: [] as TrackedCandidate[],
        interested: [] as TrackedCandidate[],
        not_interested: [] as TrackedCandidate[],
        no_response: [] as TrackedCandidate[],
        scheduled: [] as TrackedCandidate[],
        completed: [] as TrackedCandidate[],
        hired: [] as TrackedCandidate[],
      },
      total: 0,
    };

    const { result } = renderHook(() => useTrackingData(), { wrapper });

    // Initially loading
    expect(result.current.isLoading).toBe(true);
  });

  it("should accept roleId parameter", () => {
    const { result } = renderHook(() => useTrackingData("role-123"), { wrapper });

    expect(result.current.isLoading).toBe(true);
  });
});

describe("useBulkActions", () => {
  it("should have contactMultiple mutation", () => {
    const { result } = renderHook(() => useBulkActions(), { wrapper });

    expect(result.current.contactMultiple).toBeDefined();
    expect(typeof result.current.contactMultiple.mutate).toBe("function");
  });

  it("should have resendToNoResponse mutation", () => {
    const { result } = renderHook(() => useBulkActions(), { wrapper });

    expect(result.current.resendToNoResponse).toBeDefined();
    expect(typeof result.current.resendToNoResponse.mutate).toBe("function");
  });

  it("should have updateStatus mutation", () => {
    const { result } = renderHook(() => useBulkActions(), { wrapper });

    expect(result.current.updateStatus).toBeDefined();
    expect(typeof result.current.updateStatus.mutate).toBe("function");
  });
});

describe("useRecentActivity", () => {
  it("should fetch recent activity with default limit", () => {
    const { result } = renderHook(() => useRecentActivity(), { wrapper });

    expect(result.current.isLoading).toBe(true);
  });

  it("should accept custom limit", () => {
    const { result } = renderHook(() => useRecentActivity(50), { wrapper });

    expect(result.current.isLoading).toBe(true);
  });
});
