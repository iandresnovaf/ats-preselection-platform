import axios, { AxiosInstance } from 'axios';
import { LoginCredentials, LoginResponse, User } from '@/types/auth';

// Usar el proxy de Next.js para evitar problemas de CORS y cookies cross-origin
const API_BASE_URL = typeof window !== 'undefined'
  ? '/api/v1'  // Client-side: usar proxy de Next.js
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1');  // Server-side

class AuthService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      // Importante: incluir credenciales para que las cookies httpOnly se envíen
      withCredentials: true,
    });
  }

  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await this.client.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  }

  async logout(): Promise<void> {
    // El backend eliminará las cookies httpOnly
    await this.client.post('/auth/logout');
  }

  async getMe(): Promise<User> {
    const response = await this.client.get<User>('/auth/me');
    return response.data;
  }

  async refreshToken(): Promise<void> {
    // El backend refresca automáticamente usando la cookie httpOnly
    // No necesitamos enviar el refresh token manualmente
    await this.client.post('/auth/refresh');
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await this.client.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  async changeEmail(newEmail: string, password: string): Promise<void> {
    await this.client.post('/auth/change-email', {
      new_email: newEmail,
      password: password,
    });
  }

  async forgotPassword(email: string): Promise<void> {
    await this.client.post('/auth/forgot-password', { email });
  }

  async resetPassword(token: string, newPassword: string): Promise<void> {
    await this.client.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    });
  }
}

export const authService = new AuthService();
