/**
 * Hooks para el sistema de Plantillas de Mensajes
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import type {
  MessageTemplate,
  TemplateVariable,
  MessageChannel,
  TemplateFilters,
  CreateTemplateData,
  UpdateTemplateData,
  TemplatePreview,
  TemplatePreviewRequest,
} from "@/types/message-templates";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

// ==================== TEMPLATES ====================

export function useTemplates(filters?: TemplateFilters) {
  return useQuery({
    queryKey: ["message-templates", filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.channel) params.append("channel", filters.channel);
      if (filters?.is_active !== undefined) params.append("is_active", String(filters.is_active));
      if (filters?.search) params.append("search", filters.search);
      if (filters?.page) params.append("page", String(filters.page));
      if (filters?.page_size) params.append("page_size", String(filters.page_size));
      
      const { data } = await api.get(`/message-templates?${params.toString()}`);
      return data;
    },
    staleTime: 60 * 1000,
  });
}

export function useTemplate(id: string | null) {
  return useQuery({
    queryKey: ["message-templates", id],
    queryFn: async (): Promise<MessageTemplate> => {
      const { data } = await api.get(`/message-templates/${id}`);
      return data;
    },
    enabled: !!id,
    staleTime: 60 * 1000,
  });
}

export function useCreateTemplate() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (payload: CreateTemplateData) => {
      const { data } = await api.post("/message-templates", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["message-templates"] });
    },
  });
}

export function useUpdateTemplate() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: string;
      payload: UpdateTemplateData;
    }) => {
      const { data } = await api.patch(`/message-templates/${id}`, payload);
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["message-templates"] });
      queryClient.invalidateQueries({ queryKey: ["message-templates", variables.id] });
    },
  });
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/message-templates/${id}`);
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["message-templates"] });
    },
  });
}

export function useDuplicateTemplate() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post(`/message-templates/${id}/duplicate`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["message-templates"] });
    },
  });
}

export function usePreviewTemplate(id: string | null) {
  return useMutation({
    mutationFn: async (variables: Record<string, string>): Promise<TemplatePreview> => {
      if (!id) throw new Error("Template ID is required");
      const { data } = await api.post(`/message-templates/${id}/preview`, { variables });
      return data;
    },
  });
}

// ==================== VARIABLES ====================

export function useTemplateVariables(category?: string) {
  return useQuery({
    queryKey: ["template-variables", category],
    queryFn: async (): Promise<TemplateVariable[]> => {
      const params = new URLSearchParams();
      if (category) params.append("category", category);
      
      const { data } = await api.get(`/message-templates/variables?${params.toString()}`);
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutos, no cambian frecuentemente
  });
}

// ==================== CHANNEL HELPERS ====================

export function useChannelLabel(channel: MessageChannel) {
  const labels: Record<MessageChannel, string> = {
    email: "Email",
    whatsapp: "WhatsApp",
    sms: "SMS",
  };
  return labels[channel] || channel;
}

export function useChannelIcon(channel: MessageChannel) {
  // Retorna la clase de color para badges
  const colors: Record<MessageChannel, string> = {
    email: "bg-blue-100 text-blue-800",
    whatsapp: "bg-green-100 text-green-800",
    sms: "bg-purple-100 text-purple-800",
  };
  return colors[channel] || "bg-gray-100 text-gray-800";
}
