import api from "./api";
import { 
  Evaluation, 
  EvaluationFilters, 
  CreateEvaluationData,
  AIEvaluationRequest,
  AIEvaluationResponse,
  EvaluationStats
} from "@/types/evaluations";

export const evaluationService = {
  async getEvaluations(filters?: EvaluationFilters): Promise<Evaluation[]> {
    const params = new URLSearchParams();
    if (filters?.candidate_id) params.append("candidate_id", filters.candidate_id);
    if (filters?.decision) params.append("decision", filters.decision);
    if (filters?.job_opening_id) params.append("job_opening_id", filters.job_opening_id);
    if (filters?.start_date) params.append("start_date", filters.start_date);
    if (filters?.end_date) params.append("end_date", filters.end_date);
    
    const response = await api.get(`/evaluations?${params.toString()}`);
    // El backend retorna paginación: {items: [], total: ...}
    return response.data.items || response.data || [];
  },

  async getEvaluation(id: string): Promise<Evaluation> {
    const response = await api.get(`/evaluations/${id}`);
    return response.data;
  },

  async createEvaluation(data: CreateEvaluationData): Promise<Evaluation> {
    const response = await api.post("/evaluations", data);
    return response.data;
  },

  async updateEvaluation(id: string, data: Partial<CreateEvaluationData>): Promise<Evaluation> {
    const response = await api.patch(`/evaluations/${id}`, data);
    return response.data;
  },

  async deleteEvaluation(id: string): Promise<void> {
    await api.delete(`/evaluations/${id}`);
  },

  async evaluateWithAI(request: AIEvaluationRequest): Promise<AIEvaluationResponse> {
    const response = await api.post("/evaluations/ai-evaluate", request);
    return response.data;
  },

  async getEvaluationStats(): Promise<EvaluationStats> {
    const response = await api.get("/evaluations/stats");
    return response.data;
  },

  async compareCandidates(candidateIds: string[]): Promise<Evaluation[]> {
    const response = await api.post("/evaluations/compare", { candidate_ids: candidateIds });
    return response.data;
  },
};
