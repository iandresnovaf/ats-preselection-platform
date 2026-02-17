/**
 * Types for Candidate Tracking Dashboard
 */

export type ApplicationStatus = 
  | 'pending_contact'      // Falta email/teléfono
  | 'contacted'            // Enviado mensaje
  | 'interested'           // Respondió SÍ
  | 'not_interested'       // Respondió NO
  | 'no_response'          // Sin respuesta 48h
  | 'scheduled'            // Entrevista agendada
  | 'completed'            // Proceso completado
  | 'hired';               // Contratado

export type ActivityType = 
  | 'candidate_responded'
  | 'message_sent'
  | 'status_changed'
  | 'contact_attempt'
  | 'reminder_sent'
  | 'interview_scheduled';

export interface TrackedCandidate {
  id: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  linkedin_url?: string;
  status: ApplicationStatus;
  role_id: string;
  role_title: string;
  client_name: string;
  source: string;
  last_contact_at?: string;
  response_at?: string;
  response_message?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
  // Campos calculados
  is_missing_contact: boolean;
  days_without_response?: number;
}

export interface RoleStats {
  total_candidates: number;
  pending_contact: number;
  contacted: number;
  interested: number;
  not_interested: number;
  no_response: number;
  scheduled: number;
  completed: number;
  hired: number;
}

export interface VacanteSummary {
  role_id: string;
  role_title: string;
  client_name: string;
  client_logo?: string;
  stats: RoleStats;
  last_activity_at?: string;
  progress_percentage: number;
}

export interface TrackingFilters {
  role_id?: string;
  status?: ApplicationStatus[];
  date_from?: Date;
  date_to?: Date;
  has_response?: boolean | null;
  search?: string;
}

export interface ActivityItem {
  id: string;
  type: ActivityType;
  candidate_id: string;
  candidate_name: string;
  role_id: string;
  role_title: string;
  message?: string;
  previous_status?: ApplicationStatus;
  new_status?: ApplicationStatus;
  created_at: string;
  created_by?: string;
}

export interface BulkActionResult {
  success: boolean;
  processed: number;
  failed: number;
  errors?: string[];
}

export interface TrackingStats {
  total_candidates: number;
  response_rate: string;        // % que respondieron
  interest_rate: string;        // % interesados
  avg_response_time: string;    // Tiempo promedio de respuesta
  conversion_rate: string;      // % contratados
  by_role: VacanteSummary[];
}

export interface CommunicationHistory {
  id: string;
  candidate_id: string;
  type: 'email' | 'whatsapp' | 'sms' | 'call';
  direction: 'outbound' | 'inbound';
  content: string;
  status: 'sent' | 'delivered' | 'read' | 'failed';
  sent_at: string;
  read_at?: string;
}

export interface CandidateTimeline {
  id: string;
  candidate_id: string;
  type: 'status_change' | 'message' | 'note' | 'interview';
  title: string;
  description?: string;
  created_at: string;
  created_by?: string;
  metadata?: Record<string, unknown>;
}

export interface ContactCandidateData {
  candidate_ids: string[];
  message_template?: string;
  channel: 'email' | 'whatsapp';
}

export interface ResendReminderData {
  candidate_ids: string[];
  custom_message?: string;
}
