"use client";

import axios, { AxiosInstance, AxiosError } from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Interceptor para agregar token
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem("access_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Interceptor para manejar errores
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
        return Promise.reject(error);
      }
    );
  }

  // Config API
  async getStatus() {
    const response = await this.client.get("/config/status");
    return response.data;
  }

  // WhatsApp
  async getWhatsAppConfig() {
    const response = await this.client.get("/config/whatsapp");
    return response.data;
  }

  async saveWhatsAppConfig(config: any) {
    const response = await this.client.post("/config/whatsapp", config);
    return response.data;
  }

  async testWhatsAppConnection() {
    const response = await this.client.post("/config/whatsapp/test");
    return response.data;
  }

  // Zoho
  async getZohoConfig() {
    const response = await this.client.get("/config/zoho");
    return response.data;
  }

  async saveZohoConfig(config: any) {
    const response = await this.client.post("/config/zoho", config);
    return response.data;
  }

  async testZohoConnection() {
    const response = await this.client.post("/config/zoho/test");
    return response.data;
  }

  // LLM
  async getLLMConfig() {
    const response = await this.client.get("/config/llm");
    return response.data;
  }

  async saveLLMConfig(config: any) {
    const response = await this.client.post("/config/llm", config);
    return response.data;
  }

  async testLLMConnection() {
    const response = await this.client.post("/config/llm/test");
    return response.data;
  }

  // Email
  async getEmailConfig() {
    const response = await this.client.get("/config/email");
    return response.data;
  }

  async saveEmailConfig(config: any) {
    const response = await this.client.post("/config/email", config);
    return response.data;
  }

  async testEmailConnection() {
    const response = await this.client.post("/config/email/test");
    return response.data;
  }
}

export const configApi = new ApiClient();
