/**
 * Tipos para el sistema de Plantillas de Mensajes
 */

export type MessageChannel = "email" | "whatsapp" | "sms";

export interface MessageTemplate {
  template_id: string;
  name: string;
  description?: string;
  channel: MessageChannel;
  subject?: string;
  body: string;
  variables: string[];
  is_active: boolean;
  is_default: boolean;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface TemplateVariable {
  variable_id: string;
  name: string;
  description: string;
  example_value?: string;
  category: string;
  is_active: boolean;
  created_at: string;
}

export interface TemplateFilters {
  channel?: MessageChannel;
  is_active?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface CreateTemplateData {
  name: string;
  description?: string;
  channel: MessageChannel;
  subject?: string;
  body: string;
  variables?: string[];
  is_active?: boolean;
}

export interface UpdateTemplateData {
  name?: string;
  description?: string;
  channel?: MessageChannel;
  subject?: string;
  body?: string;
  variables?: string[];
  is_active?: boolean;
}

export interface TemplatePreview {
  subject?: string;
  body: string;
  rendered_variables: Record<string, string>;
  missing_variables: string[];
  extra_variables: string[];
}

export interface TemplatePreviewRequest {
  variables: Record<string, string>;
}

export interface PaginatedTemplates {
  items: MessageTemplate[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// Categorías de variables
export const VARIABLE_CATEGORIES = {
  candidate: "Candidato",
  role: "Vacante",
  consultant: "Consultor",
  system: "Sistema",
} as const;

// Variables por defecto disponibles
export const DEFAULT_VARIABLES = [
  { name: "candidate_name", label: "Nombre del candidato", category: "candidate" },
  { name: "candidate_email", label: "Email del candidato", category: "candidate" },
  { name: "candidate_phone", label: "Teléfono", category: "candidate" },
  { name: "role_title", label: "Título de la vacante", category: "role" },
  { name: "role_company", label: "Nombre de la empresa", category: "role" },
  { name: "consultant_name", label: "Nombre del consultor", category: "consultant" },
  { name: "consultant_phone", label: "Teléfono del consultor", category: "consultant" },
  { name: "consultant_email", label: "Email del consultor", category: "consultant" },
  { name: "application_date", label: "Fecha de aplicación", category: "system" },
  { name: "current_date", label: "Fecha actual", category: "system" },
];
