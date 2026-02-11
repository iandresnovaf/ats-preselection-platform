export type EvaluationDecision = 'strong_yes' | 'yes' | 'maybe' | 'no' | 'strong_no';

export interface Evaluation {
  id: string;
  candidate_id: string;
  candidate?: {
    id: string;
    first_name: string;
    last_name: string;
    email: string;
    job_opening?: {
      id: string;
      title: string;
    };
  };
  score: number;
  decision: EvaluationDecision;
  summary?: string;
  strengths?: string[];
  gaps?: string[];
  red_flags?: string[];
  technical_skills?: Record<string, number>;
  soft_skills?: Record<string, number>;
  experience_match?: number;
  education_match?: number;
  cultural_fit?: number;
  overall_recommendation?: string;
  raw_response?: string;
  evaluated_by?: string;
  evaluated_by_user?: {
    id: string;
    full_name: string;
  };
  created_at: string;
  updated_at: string;
}

export interface EvaluationFilters {
  candidate_id?: string;
  decision?: EvaluationDecision;
  job_opening_id?: string;
  start_date?: string;
  end_date?: string;
}

export interface CreateEvaluationData {
  candidate_id: string;
  score: number;
  decision: EvaluationDecision;
  summary?: string;
  strengths?: string[];
  gaps?: string[];
  red_flags?: string[];
  technical_skills?: Record<string, number>;
  soft_skills?: Record<string, number>;
  experience_match?: number;
  education_match?: number;
  cultural_fit?: number;
  overall_recommendation?: string;
}

export interface AIEvaluationRequest {
  candidate_id: string;
  use_llm?: boolean;
  llm_model?: string;
}

export interface AIEvaluationResponse {
  evaluation: Evaluation;
  processing_time_ms: number;
  tokens_used?: number;
}

export interface EvaluationStats {
  total_evaluations: number;
  average_score: number;
  by_decision: Record<EvaluationDecision, number>;
  recent_evaluations: Evaluation[];
}
