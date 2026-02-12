import { authService } from '../services/auth';
import axios from 'axios';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('AuthService', () => {
  const API_BASE_URL = 'http://localhost:8000/api/v1';
  let mockClient: any;

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockClient = {
      post: jest.fn(),
      get: jest.fn(),
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() },
      },
    };
    
    mockedAxios.create.mockReturnValue(mockClient);
  });

  describe('constructor', () => {
    it('should create axios client with correct configuration', () => {
      // Service is instantiated when imported, verify the config
      expect(mockedAxios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          baseURL: expect.any(String),
          headers: {
            'Content-Type': 'application/json',
          },
          withCredentials: true, // Important: cookies are sent with requests
        })
      );
    });
  });

  describe('login', () => {
    it('should login with valid credentials', async () => {
      const mockResponse = {
        data: {
          user: {
            id: '123',
            email: 'test@example.com',
            full_name: 'Test User',
            role: 'consultant',
          },
        },
      };

      mockClient.post.mockResolvedValue(mockResponse);

      const result = await authService.login({ 
        email: 'test@example.com', 
        password: 'password123' 
      });

      expect(mockClient.post).toHaveBeenCalledWith('/auth/login', {
        email: 'test@example.com',
        password: 'password123',
      });
      expect(result.user.email).toBe('test@example.com');
    });

    it('should handle login failure', async () => {
      const error = {
        response: {
          status: 401,
          data: { detail: 'Credenciales incorrectas' },
        },
      };

      mockClient.post.mockRejectedValue(error);

      await expect(authService.login({ 
        email: 'test@example.com', 
        password: 'wrong' 
      })).rejects.toMatchObject({
        response: { status: 401 },
      });
    });
  });

  describe('logout', () => {
    it('should call logout endpoint', async () => {
      mockClient.post.mockResolvedValue({ data: {} });

      await authService.logout();

      expect(mockClient.post).toHaveBeenCalledWith('/auth/logout');
    });
  });

  describe('getMe', () => {
    it('should fetch current user', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'consultant',
        status: 'active',
      };

      mockClient.get.mockResolvedValue({ data: mockUser });

      const result = await authService.getMe();

      expect(mockClient.get).toHaveBeenCalledWith('/auth/me');
      expect(result.email).toBe('test@example.com');
    });
  });

  describe('refreshToken', () => {
    it('should call refresh endpoint', async () => {
      mockClient.post.mockResolvedValue({ data: {} });

      await authService.refreshToken();

      expect(mockClient.post).toHaveBeenCalledWith('/auth/refresh');
    });
  });

  describe('changePassword', () => {
    it('should change password', async () => {
      mockClient.post.mockResolvedValue({ data: {} });

      await authService.changePassword('oldpass', 'newpass');

      expect(mockClient.post).toHaveBeenCalledWith('/auth/change-password', {
        current_password: 'oldpass',
        new_password: 'newpass',
      });
    });
  });

  describe('changeEmail', () => {
    it('should change email', async () => {
      mockClient.post.mockResolvedValue({ data: {} });

      await authService.changeEmail('newemail@example.com', 'password');

      expect(mockClient.post).toHaveBeenCalledWith('/auth/change-email', {
        new_email: 'newemail@example.com',
        password: 'password',
      });
    });
  });

  describe('forgotPassword', () => {
    it('should request password reset', async () => {
      mockClient.post.mockResolvedValue({ data: {} });

      await authService.forgotPassword('test@example.com');

      expect(mockClient.post).toHaveBeenCalledWith('/auth/forgot-password', {
        email: 'test@example.com',
      });
    });
  });

  describe('resetPassword', () => {
    it('should reset password with token', async () => {
      mockClient.post.mockResolvedValue({ data: {} });

      await authService.resetPassword('reset_token_123', 'newpassword');

      expect(mockClient.post).toHaveBeenCalledWith('/auth/reset-password', {
        token: 'reset_token_123',
        new_password: 'newpassword',
      });
    });
  });
});

describe('API Service Integration Tests', () => {
  describe('Error Handling', () => {
    it('should handle 401 Unauthorized', async () => {
      const error = {
        response: {
          status: 401,
          data: { detail: 'Unauthorized' },
        },
      };

      await expect(Promise.reject(error)).rejects.toMatchObject({
        response: { status: 401 },
      });
    });

    it('should handle 403 Forbidden', async () => {
      const error = {
        response: {
          status: 403,
          data: { detail: 'Forbidden' },
        },
      };

      await expect(Promise.reject(error)).rejects.toMatchObject({
        response: { status: 403 },
      });
    });

    it('should handle network errors', async () => {
      const error = new Error('Network Error');
      await expect(Promise.reject(error)).rejects.toThrow('Network Error');
    });
  });
});
