export type JobStatus = 'draft' | 'active' | 'paused' | 'closed';

export interface JobOpening {
  id: string;
  title: string;
  description: string;
  department: string;
  location: string;
  seniority: string;
  sector: string;
  status: JobStatus;
  created_by: string;
  assigned_consultant_id?: string;
  assigned_consultant?: {
    id: string;
    full_name: string;
    email: string;
  };
  candidate_count?: number;
  created_at: string;
  updated_at: string;
  published_at?: string;
  closed_at?: string;
}

export interface JobFilters {
  status?: JobStatus;
  assigned_consultant_id?: string;
  department?: string;
  location?: string;
  search?: string;
}

export interface CreateJobData {
  title: string;
  description: string;
  department: string;
  location: string;
  seniority: string;
  sector: string;
  assigned_consultant_id?: string;
}

export interface UpdateJobData {
  title?: string;
  description?: string;
  department?: string;
  location?: string;
  seniority?: string;
  sector?: string;
  status?: JobStatus;
  assigned_consultant_id?: string;
}

export interface JobStatistics {
  total_candidates: number;
  by_status: Record<string, number>;
  average_evaluation_score: number;
  top_candidates: number;
}
