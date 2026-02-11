export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  fullName: string;
  role: 'admin' | 'recruiter' | 'viewer';
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface CreateUserData {
  email: string;
  firstName: string;
  lastName: string;
  password: string;
  role: 'admin' | 'recruiter' | 'viewer';
}

export interface UpdateUserData {
  email?: string;
  firstName?: string;
  lastName?: string;
  role?: 'admin' | 'recruiter' | 'viewer';
  isActive?: boolean;
}

export interface UserFilters {
  role?: string;
  isActive?: boolean;
  search?: string;
}

export interface ApiError {
  detail: string;
  message?: string;
  errors?: Record<string, string[]>;
}
