import api from "./api";

export interface EmailConfig {
  provider: string;
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string;
  use_tls: boolean;
  default_from: string;
  default_from_name: string;
}

export interface ZohoConfig {
  client_id: string;
  client_secret: string;
  refresh_token: string;
  redirect_uri: string;
  job_id_field: string;
  candidate_id_field: string;
  stage_field: string;
}

export interface WhatsAppConfig {
  access_token: string;
  phone_number_id: string;
  verify_token: string;
  app_secret?: string;
  business_account_id?: string;
}

export interface LLMConfig {
  provider: string;
  api_key: string;
  model: string;
  max_tokens: number;
  temperature: number;
  prompt_version: string;
}

export interface SystemStatusData {
  database: boolean;
  redis: boolean;
  whatsapp: boolean | null;
  zoho: boolean | null;
  llm: boolean | null;
  email: boolean | null;
}

export const configApi = {
  // Email
  async getEmailConfig(): Promise<EmailConfig | null> {
    const response = await api.get("/config/email");
    return response.data;
  },

  async saveEmailConfig(data: EmailConfig): Promise<void> {
    await api.post("/config/email", data);
  },

  async testEmailConnection(): Promise<{ success: boolean; message?: string }> {
    const response = await api.post("/config/email/test");
    return response.data;
  },

  // Zoho
  async getZohoConfig(): Promise<ZohoConfig | null> {
    const response = await api.get("/config/zoho");
    return response.data;
  },

  async saveZohoConfig(data: ZohoConfig): Promise<void> {
    await api.post("/config/zoho", data);
  },

  async testZohoConnection(): Promise<{ success: boolean; message?: string }> {
    const response = await api.post("/config/zoho/test");
    return response.data;
  },

  // WhatsApp
  async getWhatsAppConfig(): Promise<WhatsAppConfig | null> {
    const response = await api.get("/config/whatsapp");
    return response.data;
  },

  async saveWhatsAppConfig(data: WhatsAppConfig): Promise<void> {
    await api.post("/config/whatsapp", data);
  },

  async testWhatsAppConnection(): Promise<{ success: boolean; message?: string }> {
    const response = await api.post("/config/whatsapp/test");
    return response.data;
  },

  // LLM
  async getLLMConfig(): Promise<LLMConfig | null> {
    const response = await api.get("/config/llm");
    return response.data;
  },

  async saveLLMConfig(data: LLMConfig): Promise<void> {
    await api.post("/config/llm", data);
  },

  async testLLMConnection(): Promise<{ success: boolean; message?: string }> {
    const response = await api.post("/config/llm/test");
    return response.data;
  },

  // System Status
  async getStatus(): Promise<SystemStatusData> {
    const response = await api.get("/config/status");
    return response.data;
  },
};

export default configApi;
