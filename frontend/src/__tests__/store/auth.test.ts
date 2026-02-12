import { useAuthStore } from '../store/auth';
import { authService } from '../services/auth';

// Mock auth service
jest.mock('../services/auth');

describe('Auth Store', () => {
  beforeEach(() => {
    // Clear the store before each test
    const store = useAuthStore.getState();
    store.logout();
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  describe('login', () => {
    it('should successfully login and set user state', async () => {
      const mockResponse = {
        user: {
          id: '123',
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'consultant',
          status: 'active',
          created_at: '2024-01-01',
        },
      };

      (authService.login as jest.Mock).mockResolvedValue(mockResponse);

      const store = useAuthStore.getState();
      await store.login('test@example.com', 'password123');

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.user?.email).toBe('test@example.com');
      expect(state.user?.fullName).toBe('Test User');
      expect(state.error).toBeNull();
    });

    it('should handle login failure with 401', async () => {
      const error = {
        response: {
          status: 401,
          data: {
            detail: 'Credenciales incorrectas',
          },
        },
      };

      (authService.login as jest.Mock).mockRejectedValue(error);

      const store = useAuthStore.getState();
      
      await expect(store.login('test@example.com', 'wrongpassword')).rejects.toThrow();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
      expect(state.error).toBe('Credenciales inválidas. Por favor, verifica tu email y contraseña.');
    });

    it('should handle login failure with 429', async () => {
      const error = {
        response: {
          status: 429,
        },
      };

      (authService.login as jest.Mock).mockRejectedValue(error);

      const store = useAuthStore.getState();
      
      await expect(store.login('test@example.com', 'password')).rejects.toThrow();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.error).toBe('Demasiados intentos. Por favor, intenta más tarde.');
    });

    it('should handle network errors', async () => {
      (authService.login as jest.Mock).mockRejectedValue(new Error('Network Error'));

      const store = useAuthStore.getState();
      
      await expect(store.login('test@example.com', 'password')).rejects.toThrow();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
    });
  });

  describe('logout', () => {
    it('should clear auth state on logout', async () => {
      // First set authenticated state
      useAuthStore.setState({
        user: { id: '123', email: 'test@test.com' } as any,
        isAuthenticated: true,
      });

      (authService.logout as jest.Mock).mockResolvedValue(undefined);

      const store = useAuthStore.getState();
      await store.logout();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
    });

    it('should handle logout even when service fails', async () => {
      useAuthStore.setState({
        isAuthenticated: true,
        user: { id: '123' } as any,
      });

      (authService.logout as jest.Mock).mockRejectedValue(new Error('Logout failed'));

      const store = useAuthStore.getState();
      await store.logout();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
    });
  });

  describe('fetchUser', () => {
    it('should fetch and set user data', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'consultant',
        status: 'active',
      };

      (authService.getMe as jest.Mock).mockResolvedValue(mockUser);

      const store = useAuthStore.getState();
      await store.fetchUser();

      const state = useAuthStore.getState();
      expect(state.user?.email).toBe('test@example.com');
      expect(state.isAuthenticated).toBe(true);
    });

    it('should handle 401 and clear auth', async () => {
      const error = {
        response: {
          status: 401,
        },
      };

      (authService.getMe as jest.Mock).mockRejectedValue(error);

      useAuthStore.setState({
        isAuthenticated: true,
        user: { id: '123' } as any,
      });

      const store = useAuthStore.getState();
      await store.fetchUser();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
    });

    it('should handle 403 error', async () => {
      const error = {
        response: {
          status: 403,
        },
      };

      (authService.getMe as jest.Mock).mockRejectedValue(error);

      const store = useAuthStore.getState();
      await store.fetchUser();

      const state = useAuthStore.getState();
      expect(state.error).toBe('No tienes permisos para acceder a este recurso');
    });
  });

  describe('checkAuth', () => {
    it('should return true when authenticated', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'consultant',
        status: 'active',
      };

      (authService.getMe as jest.Mock).mockResolvedValue(mockUser);

      const store = useAuthStore.getState();
      const result = await store.checkAuth();

      expect(result).toBe(true);
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });

    it('should return false when not authenticated', async () => {
      const error = {
        response: {
          status: 401,
        },
      };

      (authService.getMe as jest.Mock).mockRejectedValue(error);

      const store = useAuthStore.getState();
      const result = await store.checkAuth();

      expect(result).toBe(false);
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });
  });

  describe('setUser', () => {
    it('should set user and authentication state', () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
      } as any;

      const store = useAuthStore.getState();
      store.setUser(mockUser);

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
    });

    it('should clear authentication when setting null user', () => {
      useAuthStore.setState({
        user: { id: '123' } as any,
        isAuthenticated: true,
      });

      const store = useAuthStore.getState();
      store.setUser(null);

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      useAuthStore.setState({ error: 'Some error' });

      const store = useAuthStore.getState();
      store.clearError();

      expect(useAuthStore.getState().error).toBeNull();
    });
  });
});
