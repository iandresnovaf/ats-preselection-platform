import api from "./api";
import { JobOpening, JobFilters, CreateJobData, UpdateJobData, JobStatistics } from "@/types/jobs";

export const jobService = {
  async getJobs(filters?: JobFilters): Promise<JobOpening[]> {
    const params = new URLSearchParams();
    if (filters?.status) params.append("status", filters.status);
    if (filters?.assigned_consultant_id) params.append("assigned_consultant_id", filters.assigned_consultant_id);
    if (filters?.department) params.append("department", filters.department);
    if (filters?.location) params.append("location", filters.location);
    if (filters?.search) params.append("search", filters.search);
    
    const response = await api.get(`/jobs?${params.toString()}`);
    // El backend retorna paginación: {items: [], total: ...}
    return response.data.items || response.data || [];
  },

  async getJob(id: string): Promise<JobOpening> {
    const response = await api.get(`/jobs/${id}`);
    return response.data;
  },

  async createJob(data: CreateJobData): Promise<JobOpening> {
    const response = await api.post("/jobs", data);
    return response.data;
  },

  async updateJob(id: string, data: UpdateJobData): Promise<JobOpening> {
    const response = await api.patch(`/jobs/${id}`, data);
    return response.data;
  },

  async deleteJob(id: string): Promise<void> {
    await api.delete(`/jobs/${id}`);
  },

  async closeJob(id: string): Promise<JobOpening> {
    const response = await api.post(`/jobs/${id}/close`);
    return response.data;
  },

  async getJobStatistics(id: string): Promise<JobStatistics> {
    const response = await api.get(`/jobs/${id}/statistics`);
    return response.data;
  },

  async publishJob(id: string): Promise<JobOpening> {
    const response = await api.post(`/jobs/${id}/publish`);
    return response.data;
  },

  async pauseJob(id: string): Promise<JobOpening> {
    const response = await api.post(`/jobs/${id}/pause`);
    return response.data;
  },

  async activateJob(id: string): Promise<JobOpening> {
    const response = await api.post(`/jobs/${id}/activate`);
    return response.data;
  },
};
