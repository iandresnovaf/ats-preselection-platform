import api from "@/services/api";
import {
  Submission,
  SubmissionFilters,
  CreateSubmissionData,
  UpdateSubmissionData,
  ChangeStageData,
  SubmissionHistory,
} from "@/types/rhtools";

export const submissionsService = {
  async getSubmissions(filters?: SubmissionFilters): Promise<Submission[]> {
    const params = new URLSearchParams();
    if (filters?.client_id) params.append("client_id", filters.client_id);
    if (filters?.job_id) params.append("job_id", filters.job_id);
    if (filters?.candidate_id) params.append("candidate_id", filters.candidate_id);
    if (filters?.consultant_id) params.append("consultant_id", filters.consultant_id);
    if (filters?.status) params.append("status", filters.status);
    if (filters?.current_stage_id) params.append("current_stage_id", filters.current_stage_id);
    if (filters?.priority) params.append("priority", filters.priority);
    if (filters?.search) params.append("search", filters.search);

    const response = await api.get(`/rhtools/submissions?${params.toString()}`);
    return response.data.items || response.data || [];
  },

  async getSubmission(id: string): Promise<Submission> {
    const response = await api.get(`/rhtools/submissions/${id}`);
    return response.data;
  },

  async createSubmission(data: CreateSubmissionData): Promise<Submission> {
    const response = await api.post("/rhtools/submissions", data);
    return response.data;
  },

  async updateSubmission(id: string, data: UpdateSubmissionData): Promise<Submission> {
    const response = await api.patch(`/rhtools/submissions/${id}`, data);
    return response.data;
  },

  async deleteSubmission(id: string): Promise<void> {
    await api.delete(`/rhtools/submissions/${id}`);
  },

  async changeStage(id: string, data: ChangeStageData): Promise<Submission> {
    const response = await api.post(`/rhtools/submissions/${id}/change-stage`, data);
    return response.data;
  },

  async getHistory(id: string): Promise<SubmissionHistory[]> {
    const response = await api.get(`/rhtools/submissions/${id}/history`);
    return response.data;
  },

  async getSubmissionsByStage(stageId: string): Promise<Submission[]> {
    const response = await api.get(`/rhtools/pipeline-stages/${stageId}/submissions`);
    return response.data;
  },

  async getSubmissionsByClient(clientId: string): Promise<Submission[]> {
    const response = await api.get(`/rhtools/clients/${clientId}/submissions`);
    return response.data;
  },

  async getSubmissionsByCandidate(candidateId: string): Promise<Submission[]> {
    const response = await api.get(`/rhtools/candidates/${candidateId}/submissions`);
    return response.data;
  },

  // Bulk operations
  async bulkUpdateStatus(ids: string[], status: string): Promise<void> {
    await api.post("/rhtools/submissions/bulk-update", { ids, status });
  },

  async bulkChangeStage(ids: string[], stageId: string): Promise<void> {
    await api.post("/rhtools/submissions/bulk-change-stage", { ids, stage_id: stageId });
  },
};
