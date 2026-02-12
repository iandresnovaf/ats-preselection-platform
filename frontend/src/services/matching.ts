import api from "./api";
import { 
  MatchResult, 
  MatchFilters, 
  CreateMatchRequest, 
  MatchResponse,
  BulkMatchResponse,
  GenerateQuestionsRequest,
  GenerateQuestionsResponse,
  InterviewQuestion
} from "@/types/matching";

export const matchingService = {
  async getMatches(filters?: MatchFilters): Promise<MatchResult[]> {
    const params = new URLSearchParams();
    if (filters?.job_opening_id) params.append("job_opening_id", filters.job_opening_id);
    if (filters?.min_score !== undefined) params.append("min_score", String(filters.min_score));
    if (filters?.max_score !== undefined) params.append("max_score", String(filters.max_score));
    if (filters?.decision) params.append("decision", filters.decision);
    if (filters?.skills?.length) {
      filters.skills.forEach(skill => params.append("skills", skill));
    }
    
    const response = await api.get(`/matches?${params.toString()}`);
    return response.data.items || response.data || [];
  },

  async getMatch(id: string): Promise<MatchResult> {
    const response = await api.get(`/matches/${id}`);
    return response.data;
  },

  async createMatch(data: CreateMatchRequest): Promise<MatchResponse> {
    const response = await api.post("/matches", data);
    return response.data;
  },

  async matchCandidateWithJob(candidateId: string, jobOpeningId: string): Promise<MatchResponse> {
    const response = await api.post("/matches/evaluate", {
      candidate_id: candidateId,
      job_opening_id: jobOpeningId
    });
    return response.data;
  },

  async bulkMatch(jobOpeningId: string, candidateIds?: string[]): Promise<BulkMatchResponse> {
    const response = await api.post("/matches/bulk", {
      job_opening_id: jobOpeningId,
      candidate_ids: candidateIds
    });
    return response.data;
  },

  async getTopMatches(jobOpeningId: string, limit: number = 10): Promise<MatchResult[]> {
    const response = await api.get(`/matches/top/${jobOpeningId}?limit=${limit}`);
    return response.data;
  },

  async deleteMatch(id: string): Promise<void> {
    await api.delete(`/matches/${id}`);
  },

  async generateInterviewQuestions(data: GenerateQuestionsRequest): Promise<GenerateQuestionsResponse> {
    const response = await api.post("/matches/generate-questions", data);
    return response.data;
  },

  async getInterviewQuestions(matchId: string): Promise<InterviewQuestion[]> {
    const response = await api.get(`/matches/${matchId}/questions`);
    return response.data;
  }
};
