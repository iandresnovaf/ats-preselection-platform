import { Candidate } from "./candidates";
import { JobOpening } from "./jobs";

export type MatchDecision = 'PROCEED' | 'REVIEW' | 'REJECT';

export interface MatchBreakdown {
  skills_match: number;
  experience_match: number;
  education_match: number;
  overall_score: number;
}

export interface MatchResult {
  id: string;
  candidate_id: string;
  job_opening_id: string;
  candidate?: Candidate;
  job_opening?: JobOpening;
  score: number;
  decision: MatchDecision;
  breakdown: MatchBreakdown;
  strengths: string[];
  gaps: string[];
  red_flags: string[];
  reasoning?: string;
  created_at: string;
  updated_at: string;
}

export interface MatchFilters {
  job_opening_id?: string;
  min_score?: number;
  max_score?: number;
  decision?: MatchDecision;
  skills?: string[];
}

export interface CreateMatchRequest {
  candidate_id: string;
  job_opening_id: string;
}

export interface MatchResponse {
  match: MatchResult;
  processing_time_ms: number;
}

export interface BulkMatchResponse {
  matches: MatchResult[];
  total_processed: number;
  processing_time_ms: number;
}

export interface InterviewQuestion {
  id: string;
  question: string;
  category: 'gap' | 'strength' | 'technical' | 'behavioral';
  context?: string;
}

export interface GenerateQuestionsRequest {
  match_id: string;
  count?: number;
  focus_areas?: ('gaps' | 'strengths' | 'technical' | 'behavioral')[];
}

export interface GenerateQuestionsResponse {
  questions: InterviewQuestion[];
  generated_at: string;
}
