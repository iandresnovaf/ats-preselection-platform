import { useAuthStore, transformUser } from '../store/auth';
import { authService } from '../services/auth';

// Mock auth service
jest.mock('../services/auth');

describe('Auth Store', () => {
  beforeEach(() => {
    // Clear the store and localStorage before each test
    const store = useAuthStore.getState();
    store.logout();
    localStorage.clear();
    jest.clearAllMocks();
  });

  describe('transformUser', () => {
    it('should transform backend user to frontend format', () => {
      const backendUser = {
        id: '123',
        email: 'test@example.com',
        full_name: 'John Doe',
        role: 'consultant',
        status: 'active',
        created_at: '2024-01-01',
      };

      const result = transformUser(backendUser);

      expect(result.id).toBe('123');
      expect(result.email).toBe('test@example.com');
      expect(result.fullName).toBe('John Doe');
      expect(result.firstName).toBe('John');
      expect(result.lastName).toBe('Doe');
      expect(result.isActive).toBe(true);
    });

    it('should handle single word names', () => {
      const backendUser = {
        full_name: 'John',
      };

      const result = transformUser(backendUser);

      expect(result.firstName).toBe('John');
      expect(result.lastName).toBe('');
    });

    it('should handle null user', () => {
      const result = transformUser(null);
      expect(result).toBeNull();
    });
  });

  describe('login', () => {
    it('should successfully login and set user state', async () => {
      const mockResponse = {
        access_token: 'test_access_token',
        refresh_token: 'test_refresh_token',
        token_type: 'bearer',
        expires_in: 1800,
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
      expect(state.token).toBe('test_access_token');
      expect(state.refreshToken).toBe('test_refresh_token');
      expect(state.error).toBeNull();
    });

    it('should handle login failure', async () => {
      const error = {
        response: {
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
      expect(state.error).toBe('Credenciales incorrectas');
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
      // First login
      useAuthStore.setState({
        user: { id: '123', email: 'test@test.com' } as any,
        token: 'test_token',
        refreshToken: 'refresh_token',
        isAuthenticated: true,
      });

      (authService.logout as jest.Mock).mockResolvedValue(undefined);

      const store = useAuthStore.getState();
      await store.logout();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
      expect(state.token).toBeNull();
      expect(state.refreshToken).toBeNull();
    });

    it('should handle logout even when service fails', async () => {
      useAuthStore.setState({
        isAuthenticated: true,
        token: 'test_token',
      });

      (authService.logout as jest.Mock).mockRejectedValue(new Error('Logout failed'));

      const store = useAuthStore.getState();
      await store.logout();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.token).toBeNull();
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

      useAuthStore.setState({ token: 'valid_token' });

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
      (authService.refreshToken as jest.Mock).mockResolvedValue(null);

      useAuthStore.setState({
        token: 'invalid_token',
        refreshToken: 'refresh_token',
        isAuthenticated: true,
      });

      const store = useAuthStore.getState();
      await store.fetchUser();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
    });

    it('should not fetch if no token', async () => {
      useAuthStore.setState({ token: null });

      const store = useAuthStore.getState();
      await store.fetchUser();

      expect(authService.getMe).not.toHaveBeenCalled();
    });
  });

  describe('refreshAccessToken', () => {
    it('should refresh token successfully', async () => {
      const mockResponse = {
        access_token: 'new_access_token',
        refresh_token: 'new_refresh_token',
      };

      (authService.refreshToken as jest.Mock).mockResolvedValue(mockResponse);

      useAuthStore.setState({ refreshToken: 'old_refresh_token' });

      const store = useAuthStore.getState();
      const newToken = await store.refreshAccessToken();

      expect(newToken).toBe('new_access_token');
      expect(useAuthStore.getState().token).toBe('new_access_token');
    });

    it('should return null if no refresh token', async () => {
      useAuthStore.setState({ refreshToken: null });

      const store = useAuthStore.getState();
      const result = await store.refreshAccessToken();

      expect(result).toBeNull();
    });

    it('should handle refresh failure', async () => {
      (authService.refreshToken as jest.Mock).mockRejectedValue(new Error('Invalid token'));

      useAuthStore.setState({ refreshToken: 'invalid_token' });

      const store = useAuthStore.getState();
      const result = await store.refreshAccessToken();

      expect(result).toBeNull();
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
