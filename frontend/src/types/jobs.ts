export type JobStatus = 'draft' | 'active' | 'paused' | 'closed';
export type EmploymentType = 'full-time' | 'part-time' | 'contract' | 'internship';
export type EducationLevel = 'high-school' | 'associate' | 'bachelor' | 'master' | 'phd' | 'other';

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
  // Nuevos campos
  pdf_url?: string;
  pdf_name?: string;
  required_skills?: string[];
  min_years_experience?: number;
  education_level?: EducationLevel;
  employment_type?: EmploymentType;
  salary_min?: number;
  salary_max?: number;
  // Matching stats
  top_candidates_count?: number;
}

export interface JobFilters {
  status?: JobStatus;
  assigned_consultant_id?: string;
  department?: string;
  location?: string;
  search?: string;
  employment_type?: EmploymentType;
  has_pdf?: boolean;
}

export interface CreateJobData {
  title: string;
  description: string;
  department: string;
  location: string;
  seniority: string;
  sector: string;
  assigned_consultant_id?: string;
  // Nuevos campos
  pdf_url?: string;
  pdf_name?: string;
  required_skills?: string[];
  min_years_experience?: number;
  education_level?: EducationLevel;
  employment_type?: EmploymentType;
  salary_min?: number;
  salary_max?: number;
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
  // Nuevos campos
  pdf_url?: string;
  pdf_name?: string;
  required_skills?: string[];
  min_years_experience?: number;
  education_level?: EducationLevel;
  employment_type?: EmploymentType;
  salary_min?: number;
  salary_max?: number;
}

export interface JobStatistics {
  total_candidates: number;
  by_status: Record<string, number>;
  average_evaluation_score: number;
  top_candidates: number;
}

export interface JobUploadResponse {
  url: string;
  filename: string;
  size: number;
}
