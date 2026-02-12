import api from "@/services/api";
import {
  Client,
  ClientFilters,
  CreateClientData,
  UpdateClientData,
  ClientContact,
} from "@/types/rhtools";

export const clientsService = {
  async getClients(filters?: ClientFilters): Promise<Client[]> {
    const params = new URLSearchParams();
    if (filters?.status) params.append("status", filters.status);
    if (filters?.industry) params.append("industry", filters.industry);
    if (filters?.size) params.append("size", filters.size);
    if (filters?.search) params.append("search", filters.search);

    const response = await api.get(`/rhtools/clients?${params.toString()}`);
    return response.data.items || response.data || [];
  },

  async getClient(id: string): Promise<Client> {
    const response = await api.get(`/rhtools/clients/${id}`);
    return response.data;
  },

  async createClient(data: CreateClientData): Promise<Client> {
    const response = await api.post("/rhtools/clients", data);
    return response.data;
  },

  async updateClient(id: string, data: UpdateClientData): Promise<Client> {
    const response = await api.patch(`/rhtools/clients/${id}`, data);
    return response.data;
  },

  async deleteClient(id: string): Promise<void> {
    await api.delete(`/rhtools/clients/${id}`);
  },

  // Contactos del cliente
  async getClientContacts(clientId: string): Promise<ClientContact[]> {
    const response = await api.get(`/rhtools/clients/${clientId}/contacts`);
    return response.data;
  },

  async addContact(clientId: string, contact: Omit<ClientContact, "id" | "client_id" | "created_at" | "updated_at">): Promise<ClientContact> {
    const response = await api.post(`/rhtools/clients/${clientId}/contacts`, contact);
    return response.data;
  },

  async updateContact(clientId: string, contactId: string, contact: Partial<ClientContact>): Promise<ClientContact> {
    const response = await api.patch(`/rhtools/clients/${clientId}/contacts/${contactId}`, contact);
    return response.data;
  },

  async deleteContact(clientId: string, contactId: string): Promise<void> {
    await api.delete(`/rhtools/clients/${clientId}/contacts/${contactId}`);
  },

  // Estadísticas
  async getClientStats(id: string): Promise<{
    total_jobs: number;
    active_jobs: number;
    total_submissions: number;
    total_placements: number;
    pipeline_value: number;
  }> {
    const response = await api.get(`/rhtools/clients/${id}/stats`);
    return response.data;
  },
};
