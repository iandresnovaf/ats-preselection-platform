export type CandidateStatus = 
  | 'new' 
  | 'screening' 
  | 'interview' 
  | 'evaluation' 
  | 'offer' 
  | 'hired' 
  | 'rejected';

export type CandidateSource = 
  | 'email' 
  | 'manual' 
  | 'zoho'
  | 'odoo'
  | 'rhtools'
  | 'linkedin' 
  | 'referral' 
  | 'other';

export interface Candidate {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  source: CandidateSource;
  source_email_id?: string;
  status: CandidateStatus;
  job_opening_id: string;
  job_opening?: {
    id: string;
    title: string;
  };
  cv_url?: string;
  linkedin_url?: string;
  portfolio_url?: string;
  years_experience?: number;
  current_company?: string;
  current_position?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
  last_evaluation?: {
    id: string;
    score: number;
    decision: string;
    created_at: string;
  };
}

export interface CandidateFilters {
  job_opening_id?: string;
  status?: CandidateStatus;
  source?: CandidateSource;
  search?: string;
}

export interface CreateCandidateData {
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  job_opening_id: string;
  source?: CandidateSource;
  cv_url?: string;
  linkedin_url?: string;
  portfolio_url?: string;
  years_experience?: number;
  current_company?: string;
  current_position?: string;
  notes?: string;
}

export interface UpdateCandidateData {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  status?: CandidateStatus;
  job_opening_id?: string;
  cv_url?: string;
  linkedin_url?: string;
  portfolio_url?: string;
  years_experience?: number;
  current_company?: string;
  current_position?: string;
  notes?: string;
}

export interface CandidateStatusHistory {
  id: string;
  status: CandidateStatus;
  previous_status?: CandidateStatus;
  changed_by: string;
  changed_by_user?: {
    id: string;
    full_name: string;
  };
  notes?: string;
  created_at: string;
}

export interface CandidateWithHistory extends Candidate {
  status_history: CandidateStatusHistory[];
}
