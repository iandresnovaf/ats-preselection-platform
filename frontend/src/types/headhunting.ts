/**
 * Types for Headhunting / Applications System
 * Sistema de gestión de aplicaciones y pipeline de selección
 */

// ==================== PIPELINE STAGES ====================

export type PipelineStage = 
  | 'sourcing'           // Recién ingresado
  | 'shortlist'          // Pre-seleccionado
  | 'terna'              // En terna de 3 candidatos
  | 'contact_pending'    // Pendiente de contactar (necesita datos)
  | 'contacted'          // Contactado, esperando respuesta
  | 'interested'         // Respondió positivamente
  | 'not_interested'     // Respondió negativamente
  | 'no_response'        // No respondió (48-72h)
  | 'interview_scheduled' // Entrevista agendada
  | 'interview_done'     // Entrevista realizada
  | 'offer_sent'         // Oferta enviada
  | 'offer_accepted'     // Oferta aceptada
  | 'offer_rejected'     // Oferta rechazada
  | 'hired'              // Contratado
  | 'discarded';         // Descartado por consultor

export const PIPELINE_STAGES: { value: PipelineStage; label: string; order: number; category: string }[] = [
  { value: 'sourcing', label: 'Recién ingresado', order: 1, category: 'initial' },
  { value: 'shortlist', label: 'Pre-seleccionado', order: 2, category: 'initial' },
  { value: 'terna', label: 'En terna', order: 3, category: 'initial' },
  { value: 'contact_pending', label: 'Pendiente de contactar', order: 4, category: 'contact' },
  { value: 'contacted', label: 'Contactado', order: 5, category: 'contact' },
  { value: 'interested', label: 'Interesado', order: 6, category: 'contact' },
  { value: 'not_interested', label: 'No interesado', order: 97, category: 'contact' },
  { value: 'no_response', label: 'Sin respuesta', order: 98, category: 'contact' },
  { value: 'interview_scheduled', label: 'Entrevista agendada', order: 7, category: 'interview' },
  { value: 'interview_done', label: 'Entrevista realizada', order: 8, category: 'interview' },
  { value: 'offer_sent', label: 'Oferta enviada', order: 9, category: 'offer' },
  { value: 'offer_accepted', label: 'Oferta aceptada', order: 10, category: 'offer' },
  { value: 'offer_rejected', label: 'Oferta rechazada', order: 96, category: 'offer' },
  { value: 'hired', label: 'Contratado', order: 11, category: 'final' },
  { value: 'discarded', label: 'Descartado', order: 99, category: 'final' },
];

export function getStageLabel(stage: PipelineStage): string {
  return PIPELINE_STAGES.find(s => s.value === stage)?.label || stage;
}

export function getStageOrder(stage: PipelineStage): number {
  return PIPELINE_STAGES.find(s => s.value === stage)?.order || 0;
}

// ==================== APPLICATION STATUS ====================

export type ApplicationStatus = 
  | 'active'
  | 'on_hold'
  | 'withdrawn'
  | 'hired'
  | 'rejected';

// ==================== CLIENT ====================

export interface Client {
  id: string;
  name: string;
  industry?: string;
  contact_email?: string;
  contact_phone?: string;
  logo_url?: string;
  created_at: string;
  updated_at: string;
}

// ==================== ROLE / VACANCY ====================

export type RoleStatus = 'draft' | 'active' | 'paused' | 'closed';

export interface Role {
  id: string;
  title: string;
  client_id: string;
  client?: Client;
  description: string;
  location: string;
  department?: string;
  seniority?: string;
  sector?: string;
  salary_min?: number;
  salary_max?: number;
  status: RoleStatus;
  required_skills: string[];
  min_years_experience?: number;
  employment_type?: string;
  assigned_consultant_id?: string;
  assigned_consultant?: {
    id: string;
    full_name: string;
    email: string;
  };
  // Counts
  applications_count: number;
  candidates_in_terna: number;
  hired_count: number;
  // Timestamps
  created_at: string;
  updated_at: string;
  published_at?: string;
  closed_at?: string;
}

// ==================== CANDIDATE (Enhanced) ====================

export interface CandidateSummary {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  location?: string;
  photo_url?: string;
  current_company?: string;
  current_position?: string;
  years_experience?: number;
  headline?: string;
  linkedin_url?: string;
  skills?: string[];
}

// ==================== APPLICATION ====================

export interface Application {
  id: string;
  role_id: string;
  role?: Role;
  candidate_id: string;
  candidate?: CandidateSummary;
  stage: PipelineStage;
  status: ApplicationStatus;
  overall_score: number;
  // Metadata
  source: 'manual' | 'email' | 'linkedin' | 'referral' | 'job_board' | 'other';
  source_details?: string;
  // Timestamps
  created_at: string;
  updated_at: string;
  // Stage transitions
  stage_transitions: StageTransition[];
  // Related data
  documents?: ApplicationDocument[];
  assessment_scores?: AssessmentScore[];
  flags?: ApplicationFlag[];
  // Decision
  decision?: ApplicationDecision;
}

export interface StageTransition {
  id: string;
  application_id: string;
  from_stage: PipelineStage | null;
  to_stage: PipelineStage;
  changed_by: string;
  changed_by_user?: {
    id: string;
    full_name: string;
  };
  notes?: string;
  created_at: string;
}

// ==================== DOCUMENTS ====================

export type DocumentType = 
  | 'cv'
  | 'cover_letter'
  | 'test_technical'
  | 'test_psychometric'
  | 'interview_notes'
  | 'reference_check'
  | 'offer_letter'
  | 'contract'
  | 'other';

export interface ApplicationDocument {
  id: string;
  application_id: string;
  type: DocumentType;
  name: string;
  file_url: string;
  file_size?: number;
  mime_type?: string;
  uploaded_by: string;
  uploaded_by_user?: {
    id: string;
    full_name: string;
  };
  processing_status: 'pending' | 'processing' | 'completed' | 'error';
  extracted_text?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

// ==================== ASSESSMENT SCORES ====================

export interface AssessmentScore {
  id: string;
  application_id: string;
  dimension: string;
  score: number; // 0-100
  weight?: number;
  evaluated_by?: string;
  evaluated_by_user?: {
    id: string;
    full_name: string;
  };
  notes?: string;
  created_at: string;
  updated_at: string;
}

// ==================== FLAGS ====================

export type FlagSeverity = 'low' | 'medium' | 'high';
export type FlagCategory = 
  | 'skills_gap'
  | 'experience_mismatch'
  | 'salary_expectation'
  | 'availability'
  | 'relocation'
  | 'culture_fit'
  | 'reference_issue'
  | 'background_check'
  | 'other';

export interface ApplicationFlag {
  id: string;
  application_id: string;
  severity: FlagSeverity;
  category: FlagCategory;
  description: string;
  evidence?: string;
  source: 'ai' | 'manual' | 'system';
  created_by?: string;
  created_by_user?: {
    id: string;
    full_name: string;
  };
  resolved: boolean;
  resolved_at?: string;
  resolved_by?: string;
  resolution_notes?: string;
  created_at: string;
  updated_at: string;
}

// ==================== DECISION ====================

export interface ApplicationDecision {
  id: string;
  application_id: string;
  decision: 'hired' | 'rejected';
  decided_by: string;
  decided_by_user?: {
    id: string;
    full_name: string;
  };
  decision_date: string;
  notes?: string;
  // For rejections
  rejection_reason?: string;
  // For hires
  start_date?: string;
  salary_offered?: number;
  created_at: string;
  updated_at: string;
}

// ==================== POST-HIRE ====================

export type PostHireStatus = 'on_track' | 'at_risk' | 'succeeded' | 'failed';

export interface PostHirePlan {
  id: string;
  application_id: string;
  status: PostHireStatus;
  // 30/60/90/180 days milestones
  milestones: PostHireMilestone[];
  // Manager feedback
  manager_feedback?: ManagerFeedback[];
  // Next review date
  next_review_date?: string;
  created_at: string;
  updated_at: string;
}

export interface PostHireMilestone {
  id: string;
  plan_id: string;
  period_days: 30 | 60 | 90 | 180;
  target_kpis: KPI[];
  achieved_kpis: KPI[];
  status: 'pending' | 'in_progress' | 'completed' | 'missed';
  review_date?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface KPI {
  id: string;
  name: string;
  target_value?: string;
  actual_value?: string;
  status: 'not_measured' | 'below_target' | 'on_target' | 'exceeded';
}

export interface ManagerFeedback {
  id: string;
  plan_id: string;
  manager_id: string;
  manager_name: string;
  period_days: number;
  overall_rating: number; // 1-5
  strengths: string[];
  areas_for_improvement: string[];
  comments?: string;
  submitted_at: string;
}

// ==================== DASHBOARD METRICS ====================

export interface DashboardMetrics {
  // Key metrics
  active_processes: number;
  candidates_in_terna: number;
  hires_this_month: number;
  pending_alerts: number;
  // Pipeline funnel
  pipeline_funnel: PipelineFunnelItem[];
  // Recent activity
  recent_activities: ActivityItem[];
  // Performance
  avg_time_per_stage: Record<PipelineStage, number>; // in days
  conversion_rates: Record<string, number>;
}

export interface PipelineFunnelItem {
  stage: PipelineStage;
  count: number;
  percentage: number;
}

export interface ActivityItem {
  id: string;
  type: 'stage_change' | 'new_application' | 'decision' | 'flag' | 'document' | 'note';
  description: string;
  application_id: string;
  candidate_name: string;
  role_title: string;
  created_at: string;
  created_by?: string;
}

// ==================== REPORTS ====================

export interface ReportFilters {
  date_from?: string;
  date_to?: string;
  client_id?: string;
  role_id?: string;
  consultant_id?: string;
}

export interface HiringReport {
  // Time metrics
  avg_time_to_hire: number; // days
  avg_time_per_stage: Record<PipelineStage, number>;
  // Conversion metrics
  total_applications: number;
  conversion_by_stage: Record<PipelineStage, { in: number; out: number; rate: number }>;
  // By role
  by_role: RoleHiringMetrics[];
  // By client
  by_client: ClientHiringMetrics[];
  // Score distribution
  score_distribution: ScoreDistributionItem[];
  // Risk analysis
  risk_by_category: RiskCategoryItem[];
}

export interface RoleHiringMetrics {
  role_id: string;
  role_title: string;
  client_name: string;
  total_candidates: number;
  in_terna: number;
  hired: number;
  rejected: number;
  avg_time_to_fill?: number;
  conversion_rate: number;
}

export interface ClientHiringMetrics {
  client_id: string;
  client_name: string;
  active_roles: number;
  total_candidates: number;
  hired: number;
  avg_time_to_fill: number;
}

export interface ScoreDistributionItem {
  range: string; // "90-100", "80-89", etc.
  count: number;
  percentage: number;
}

export interface RiskCategoryItem {
  category: FlagCategory;
  total_flags: number;
  by_severity: Record<FlagSeverity, number>;
}

// ==================== FILTERS & QUERIES ====================

export interface ApplicationFilters {
  role_id?: string;
  client_id?: string;
  stage?: PipelineStage;
  status?: ApplicationStatus;
  search?: string;
  min_score?: number;
  has_flags?: boolean;
}

export interface CandidateFilters {
  search?: string;
  location?: string;
  skills?: string[];
  min_years_experience?: number;
  has_applications?: boolean;
}

export interface RoleFilters {
  status?: RoleStatus;
  client_id?: string;
  search?: string;
  assigned_consultant_id?: string;
}
