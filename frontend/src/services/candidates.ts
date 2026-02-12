import api from "./api";
import { 
  Candidate, 
  CandidateFilters, 
  CreateCandidateData, 
  UpdateCandidateData,
  CandidateWithHistory,
  CandidateStatus
} from "@/types/candidates";
import { Evaluation } from "@/types/evaluations";

export const candidateService = {
  async getCandidates(filters?: CandidateFilters): Promise<Candidate[]> {
    const params = new URLSearchParams();
    if (filters?.job_opening_id) params.append("job_opening_id", filters.job_opening_id);
    if (filters?.status) params.append("status", filters.status);
    if (filters?.source) params.append("source", filters.source);
    if (filters?.search) params.append("search", filters.search);
    
    const response = await api.get(`/candidates?${params.toString()}`);
    // El backend retorna paginación: {items: [], total: ...}
    return response.data.items || response.data || [];
  },

  async getCandidate(id: string): Promise<CandidateWithHistory> {
    const response = await api.get(`/candidates/${id}`);
    return response.data;
  },

  async createCandidate(data: CreateCandidateData): Promise<Candidate> {
    const response = await api.post("/candidates", data);
    return response.data;
  },

  async updateCandidate(id: string, data: UpdateCandidateData): Promise<Candidate> {
    const response = await api.patch(`/candidates/${id}`, data);
    return response.data;
  },

  async deleteCandidate(id: string): Promise<void> {
    await api.delete(`/candidates/${id}`);
  },

  async evaluateCandidate(id: string, useAI: boolean = false): Promise<Evaluation> {
    const response = await api.post(`/candidates/${id}/evaluate`, { use_ai: useAI });
    return response.data;
  },

  async changeStatus(id: string, status: CandidateStatus, notes?: string): Promise<Candidate> {
    const response = await api.patch(`/candidates/${id}/status`, { status, notes });
    return response.data;
  },

  async getCandidateEvaluations(id: string): Promise<Evaluation[]> {
    const response = await api.get(`/candidates/${id}/evaluations`);
    return response.data;
  },

  async uploadCV(id: string, file: File): Promise<{ cv_url: string }> {
    const formData = new FormData();
    formData.append("file", file);
    
    const response = await api.post(`/candidates/${id}/upload-cv`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  async getCandidatesByJob(jobId: string): Promise<Candidate[]> {
    const response = await api.get(`/jobs/${jobId}/candidates`);
    return response.data;
  },
};
