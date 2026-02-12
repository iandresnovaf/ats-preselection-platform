/**
 * RHTools Module Types
 * Tipos para el módulo de gestión de recruitment de RHTools
 */

// ============================================
// Enums y tipos base
// ============================================

export type ATSProvider = 'rhtools' | 'zoho' | 'odoo';

export type ClientStatus = 'active' | 'inactive' | 'prospect';

export type PipelineStageType = 'initial' | 'screening' | 'interview' | 'evaluation' | 'offer' | 'hired' | 'rejected';

export type SubmissionStatus = 'new' | 'in_progress' | 'shortlisted' | 'interview_scheduled' | 'offer_pending' | 'offer_accepted' | 'rejected_by_client' | 'rejected_by_candidate' | 'on_hold' | 'placed';

export type DocumentType = 'cv' | 'cover_letter' | 'evaluation' | 'contract' | 'reference' | 'id_document' | 'other';

export type DocumentStatus = 'uploaded' | 'processing' | 'extracted' | 'error';

export type MessageType = 'email' | 'sms' | 'whatsapp' | 'call' | 'meeting';

// ============================================
// Client
// ============================================

export interface ClientContact {
  id: string;
  client_id: string;
  name: string;
  email: string;
  phone?: string;
  position?: string;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
}

export interface Client {
  id: string;
  name: string;
  legal_name?: string;
  tax_id?: string;
  industry?: string;
  size?: 'startup' | 'sme' | 'enterprise' | 'large_enterprise';
  status: ClientStatus;
  address?: string;
  city?: string;
  country?: string;
  website?: string;
  logo_url?: string;
  notes?: string;
  contract_start_date?: string;
  contract_end_date?: string;
  commission_rate?: number;
  payment_terms?: number;
  created_at: string;
  updated_at: string;
  contacts?: ClientContact[];
  active_jobs_count?: number;
  total_placements?: number;
}

export interface ClientFilters {
  status?: ClientStatus;
  industry?: string;
  size?: string;
  search?: string;
}

export interface CreateClientData {
  name: string;
  legal_name?: string;
  tax_id?: string;
  industry?: string;
  size?: 'startup' | 'sme' | 'enterprise' | 'large_enterprise';
  status?: ClientStatus;
  address?: string;
  city?: string;
  country?: string;
  website?: string;
  logo_url?: string;
  notes?: string;
  commission_rate?: number;
  payment_terms?: number;
  contacts?: Omit<ClientContact, 'id' | 'client_id' | 'created_at' | 'updated_at'>[];
}

export interface UpdateClientData {
  name?: string;
  legal_name?: string;
  tax_id?: string;
  industry?: string;
  size?: 'startup' | 'sme' | 'enterprise' | 'large_enterprise';
  status?: ClientStatus;
  address?: string;
  city?: string;
  country?: string;
  website?: string;
  logo_url?: string;
  notes?: string;
  commission_rate?: number;
  payment_terms?: number;
}

// ============================================
// Pipeline Template & Stages
// ============================================

export interface PipelineStageRule {
  id: string;
  stage_id: string;
  rule_type: 'required_fields' | 'sla_hours' | 'auto_notify' | 'auto_move' | 'approval_required';
  config: Record<string, unknown>;
  created_at: string;
}

export interface PipelineStage {
  id: string;
  template_id: string;
  name: string;
  description?: string;
  type: PipelineStageType;
  order: number;
  sla_hours?: number;
  color: string;
  is_required: boolean;
  allow_reject: boolean;
  allow_return: boolean;
  rules?: PipelineStageRule[];
  created_at: string;
  updated_at: string;
}

export interface PipelineTemplate {
  id: string;
  name: string;
  description?: string;
  is_default: boolean;
  is_active: boolean;
  client_id?: string;
  client?: Client;
  stages: PipelineStage[];
  created_at: string;
  updated_at: string;
}

export interface CreatePipelineTemplateData {
  name: string;
  description?: string;
  is_default?: boolean;
  client_id?: string;
  stages: Omit<PipelineStage, 'id' | 'template_id' | 'created_at' | 'updated_at'>[];
}

export interface UpdatePipelineTemplateData {
  name?: string;
  description?: string;
  is_default?: boolean;
  is_active?: boolean;
  stages?: Partial<PipelineStage>[];
}

// ============================================
// Submission
// ============================================

export interface SubmissionHistory {
  id: string;
  submission_id: string;
  from_stage_id?: string;
  to_stage_id: string;
  changed_by: string;
  changed_by_user?: {
    id: string;
    full_name: string;
    email: string;
  };
  notes?: string;
  reason?: string;
  created_at: string;
}

export interface Submission {
  id: string;
  client_id: string;
  client?: Client;
  job_id?: string;
  job?: {
    id: string;
    title: string;
  };
  candidate_id: string;
  candidate?: {
    id: string;
    first_name: string;
    last_name: string;
    email: string;
    phone?: string;
  };
  consultant_id: string;
  consultant?: {
    id: string;
    full_name: string;
    email: string;
  };
  template_id: string;
  template?: PipelineTemplate;
  current_stage_id: string;
  current_stage?: PipelineStage;
  status: SubmissionStatus;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  salary_expectation?: number;
  proposed_salary?: number;
  currency?: string;
  notes?: string;
  internal_notes?: string;
  sla_deadline?: string;
  is_sla_breached: boolean;
  created_at: string;
  updated_at: string;
  history?: SubmissionHistory[];
  documents_count?: number;
  messages_count?: number;
}

export interface SubmissionFilters {
  client_id?: string;
  job_id?: string;
  candidate_id?: string;
  consultant_id?: string;
  status?: SubmissionStatus;
  current_stage_id?: string;
  priority?: string;
  search?: string;
}

export interface CreateSubmissionData {
  client_id: string;
  job_id?: string;
  candidate_id: string;
  consultant_id: string;
  template_id: string;
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  salary_expectation?: number;
  proposed_salary?: number;
  currency?: string;
  notes?: string;
  internal_notes?: string;
}

export interface UpdateSubmissionData {
  job_id?: string;
  consultant_id?: string;
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  salary_expectation?: number;
  proposed_salary?: number;
  currency?: string;
  notes?: string;
  internal_notes?: string;
}

export interface ChangeStageData {
  to_stage_id: string;
  notes?: string;
  reason?: string;
}

// ============================================
// Document
// ============================================

export interface DocumentExtractedData {
  field_name: string;
  field_value: string;
  confidence: number;
}

export interface Document {
  id: string;
  submission_id?: string;
  candidate_id?: string;
  job_id?: string;
  type: DocumentType;
  name: string;
  original_name: string;
  file_url: string;
  file_size: number;
  mime_type: string;
  status: DocumentStatus;
  extracted_data?: DocumentExtractedData[];
  uploaded_by: string;
  uploader?: {
    id: string;
    full_name: string;
  };
  created_at: string;
  updated_at: string;
}

export interface DocumentFilters {
  submission_id?: string;
  candidate_id?: string;
  job_id?: string;
  type?: DocumentType;
  status?: DocumentStatus;
}

export interface UploadDocumentData {
  file: File;
  type: DocumentType;
  submission_id?: string;
  candidate_id?: string;
  job_id?: string;
}

// ============================================
// Message Template
// ============================================

export interface MessageTemplate {
  id: string;
  name: string;
  subject?: string;
  content: string;
  type: MessageType;
  stage_id?: string;
  is_active: boolean;
  variables: string[];
  created_at: string;
  updated_at: string;
}

export interface CreateMessageTemplateData {
  name: string;
  subject?: string;
  content: string;
  type: MessageType;
  stage_id?: string;
  variables?: string[];
}

// ============================================
// Dashboard Stats
// ============================================

export interface RHToolsDashboardStats {
  total_clients: number;
  active_clients: number;
  total_submissions: number;
  submissions_by_stage: Record<string, number>;
  sla_breaches: number;
  placements_this_month: number;
  pipeline_value: number;
  top_performers: {
    consultant_id: string;
    consultant_name: string;
    submissions_count: number;
    placements_count: number;
  }[];
}
