import axios, { AxiosInstance } from 'axios';
import { User, CreateUserData, UpdateUserData, UserFilters } from '@/types/auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class UserService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add token
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  async getUsers(filters?: UserFilters): Promise<User[]> {
    const params = new URLSearchParams();
    
    if (filters?.role) {
      params.append('role', filters.role);
    }
    if (filters?.isActive !== undefined) {
      params.append('is_active', String(filters.isActive));
    }
    if (filters?.search) {
      params.append('search', filters.search);
    }

    const response = await this.client.get<User[]>(`/users?${params.toString()}`);
    return response.data;
  }

  async getUser(id: string): Promise<User> {
    const response = await this.client.get<User>(`/users/${id}`);
    return response.data;
  }

  async createUser(data: CreateUserData): Promise<User> {
    const response = await this.client.post<User>('/users', data);
    return response.data;
  }

  async updateUser(id: string, data: UpdateUserData): Promise<User> {
    const response = await this.client.patch<User>(`/users/${id}`, data);
    return response.data;
  }

  async deleteUser(id: string): Promise<void> {
    await this.client.delete(`/users/${id}`);
  }

  async activateUser(id: string): Promise<User> {
    const response = await this.client.post<User>(`/users/${id}/activate`);
    return response.data;
  }

  async deactivateUser(id: string): Promise<User> {
    const response = await this.client.post<User>(`/users/${id}/deactivate`);
    return response.data;
  }
}

export const userService = new UserService();
