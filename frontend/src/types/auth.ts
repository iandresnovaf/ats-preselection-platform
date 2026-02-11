export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'super_admin' | 'consultant' | 'viewer';
  status: 'active' | 'inactive' | 'pending';
  created_at: string;
  last_login?: string;
  // Campos computados
  firstName?: string;
  lastName?: string;
  fullName?: string;
  isActive?: boolean;
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
  role: 'super_admin' | 'consultant' | 'viewer';
}

export interface UpdateUserData {
  email?: string;
  firstName?: string;
  lastName?: string;
  role?: 'super_admin' | 'consultant' | 'viewer';
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
