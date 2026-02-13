import api from "./api";
import { User, CreateUserData, UpdateUserData, UserFilters } from "@/types/auth";

export const userService = {
  async getUsers(filters?: UserFilters): Promise<User[]> {
    const params = new URLSearchParams();
    if (filters?.role) params.append("role", filters.role);
    if (filters?.isActive !== undefined) params.append("is_active", String(filters.isActive));
    if (filters?.search) params.append("search", filters.search);
    
    const response = await api.get(`/users?${params.toString()}`);
    // El backend retorna paginación: {items: [], total: ...}
    return response.data.items || response.data || [];
  },

  async getUser(id: string): Promise<User> {
    const response = await api.get(`/users/${id}`);
    return response.data;
  },

  async createUser(data: CreateUserData): Promise<User> {
    const response = await api.post("/users", data);
    return response.data;
  },

  async updateUser(id: string, data: UpdateUserData): Promise<User> {
    const response = await api.patch(`/users/${id}`, data);
    return response.data;
  },

  async deleteUser(id: string): Promise<void> {
    await api.delete(`/users/${id}`);
  },
};
