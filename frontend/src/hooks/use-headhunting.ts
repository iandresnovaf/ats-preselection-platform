/**
 * Hooks para el sistema de Headhunting
 * Usa TanStack Query para caching y manejo de estado
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import type {
  Application,
  ApplicationFilters,
  CandidateSummary,
  CandidateFilters,
  Role,
  RoleFilters,
  DashboardMetrics,
  HiringReport,
  ReportFilters,
  PostHirePlan,
  StageTransition,
  ApplicationDocument,
  ApplicationFlag,
  AssessmentScore,
  ApplicationDecision,
  PipelineStage,
} from "@/types/headhunting";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Cliente axios configurado
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor para agregar token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ==================== DASHBOARD ====================

export function useDashboardMetrics() {
  return useQuery({
    queryKey: ["dashboard", "metrics"],
    queryFn: async (): Promise<DashboardMetrics> => {
      const { data } = await api.get("/headhunting/dashboard/metrics");
      return data;
    },
    staleTime: 30 * 1000, // 30 segundos
  });
}

// ==================== APPLICATIONS ====================

export function useApplications(filters?: ApplicationFilters) {
  return useQuery({
    queryKey: ["applications", filters],
    queryFn: async (): Promise<Application[]> => {
      const params = new URLSearchParams();
      if (filters?.role_id) params.append("role_id", filters.role_id);
      if (filters?.client_id) params.append("client_id", filters.client_id);
      if (filters?.stage) params.append("stage", filters.stage);
      if (filters?.status) params.append("status", filters.status);
      if (filters?.search) params.append("search", filters.search);
      if (filters?.min_score) params.append("min_score", String(filters.min_score));
      if (filters?.has_flags) params.append("has_flags", String(filters.has_flags));
      
      const { data } = await api.get(`/headhunting/applications?${params.toString()}`);
      return data;
    },
    staleTime: 30 * 1000,
  });
}

export function useApplication(id: string | null) {
  return useQuery({
    queryKey: ["applications", id],
    queryFn: async (): Promise<Application> => {
      const { data } = await api.get(`/headhunting/applications/${id}`);
      return data;
    },
    enabled: !!id,
    staleTime: 60 * 1000,
  });
}

export function useCreateApplication() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (payload: {
      role_id: string;
      candidate_id: string;
      source?: string;
    }) => {
      const { data } = await api.post("/headhunting/applications", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "metrics"] });
    },
  });
}

export function useUpdateApplicationStage() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({
      id,
      stage,
      notes,
    }: {
      id: string;
      stage: PipelineStage;
      notes?: string;
    }) => {
      const { data } = await api.patch(`/headhunting/applications/${id}/stage`, {
        stage,
        notes,
      });
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["applications", variables.id] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "metrics"] });
    },
  });
}

export function useMakeDecision() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({
      id,
      decision,
      notes,
      rejection_reason,
      start_date,
      salary_offered,
    }: {
      id: string;
      decision: "hired" | "rejected";
      notes?: string;
      rejection_reason?: string;
      start_date?: string;
      salary_offered?: number;
    }) => {
      const { data } = await api.post(`/headhunting/applications/${id}/decision`, {
        decision,
        notes,
        rejection_reason,
        start_date,
        salary_offered,
      });
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["applications", variables.id] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "metrics"] });
    },
  });
}

// ==================== APPLICATION DOCUMENTS ====================

export function useUploadDocument() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({
      applicationId,
      file,
      type,
    }: {
      applicationId: string;
      file: File;
      type: string;
    }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("type", type);
      
      const { data } = await api.post(
        `/headhunting/applications/${applicationId}/documents`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["applications", variables.applicationId],
      });
    },
  });
}

// ==================== APPLICATION FLAGS ====================

export function useCreateFlag() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({
      applicationId,
      severity,
      category,
      description,
      evidence,
    }: {
      applicationId: string;
      severity: string;
      category: string;
      description: string;
      evidence?: string;
    }) => {
      const { data } = await api.post(
        `/headhunting/applications/${applicationId}/flags`,
        {
          severity,
          category,
          description,
          evidence,
        }
      );
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["applications", variables.applicationId],
      });
    },
  });
}

export function useResolveFlag() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({
      applicationId,
      flagId,
      notes,
    }: {
      applicationId: string;
      flagId: string;
      notes?: string;
    }) => {
      const { data } = await api.patch(
        `/headhunting/applications/${applicationId}/flags/${flagId}/resolve`,
        { notes }
      );
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["applications", variables.applicationId],
      });
    },
  });
}

// ==================== CANDIDATES ====================

export function useCandidates(filters?: CandidateFilters) {
  return useQuery({
    queryKey: ["candidates", filters],
    queryFn: async (): Promise<CandidateSummary[]> => {
      const params = new URLSearchParams();
      if (filters?.search) params.append("search", filters.search);
      if (filters?.location) params.append("location", filters.location);
      if (filters?.skills) {
        filters.skills.forEach(skill => params.append("skills", skill));
      }
      if (filters?.min_years_experience) {
        params.append("min_years_experience", String(filters.min_years_experience));
      }
      
      const { data } = await api.get(`/headhunting/candidates?${params.toString()}`);
      return data;
    },
    staleTime: 60 * 1000,
  });
}

export function useCandidateApplications(candidateId: string | null) {
  return useQuery({
    queryKey: ["candidates", candidateId, "applications"],
    queryFn: async (): Promise<Application[]> => {
      const { data } = await api.get(`/headhunting/candidates/${candidateId}/applications`);
      return data;
    },
    enabled: !!candidateId,
    staleTime: 60 * 1000,
  });
}

// ==================== ROLES / VACANCIES ====================

export function useRoles(filters?: RoleFilters) {
  return useQuery({
    queryKey: ["roles", filters],
    queryFn: async (): Promise<Role[]> => {
      const params = new URLSearchParams();
      if (filters?.status) params.append("status", filters.status);
      if (filters?.client_id) params.append("client_id", filters.client_id);
      if (filters?.search) params.append("search", filters.search);
      if (filters?.assigned_consultant_id) {
        params.append("assigned_consultant_id", filters.assigned_consultant_id);
      }
      
      const { data } = await api.get(`/headhunting/roles?${params.toString()}`);
      return data;
    },
    staleTime: 60 * 1000,
  });
}

export function useRole(id: string | null) {
  return useQuery({
    queryKey: ["roles", id],
    queryFn: async (): Promise<Role> => {
      const { data } = await api.get(`/headhunting/roles/${id}`);
      return data;
    },
    enabled: !!id,
    staleTime: 60 * 1000,
  });
}

export function useCreateRole() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (payload: Partial<Role>) => {
      const { data } = await api.post("/headhunting/roles", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["roles"] });
    },
  });
}

// ==================== TERNA COMPARATOR ====================

export function useTernaComparison(roleId: string, candidateIds: string[]) {
  return useQuery({
    queryKey: ["terna", roleId, candidateIds],
    queryFn: async () => {
      const params = new URLSearchParams();
      candidateIds.forEach(id => params.append("candidate_ids", id));
      
      const { data } = await api.get(
        `/headhunting/roles/${roleId}/compare?${params.toString()}`
      );
      return data;
    },
    enabled: !!roleId && candidateIds.length >= 2,
    staleTime: 60 * 1000,
  });
}

// ==================== POST-HIRE ====================

export function usePostHirePlan(applicationId: string | null) {
  return useQuery({
    queryKey: ["post-hire", applicationId],
    queryFn: async (): Promise<PostHirePlan> => {
      const { data } = await api.get(`/headhunting/applications/${applicationId}/post-hire`);
      return data;
    },
    enabled: !!applicationId,
    staleTime: 60 * 1000,
  });
}

export function useUpdatePostHireMilestone() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({
      applicationId,
      milestoneId,
      updates,
    }: {
      applicationId: string;
      milestoneId: string;
      updates: Partial<PostHirePlan["milestones"][0]>;
    }) => {
      const { data } = await api.patch(
        `/headhunting/applications/${applicationId}/post-hire/milestones/${milestoneId}`,
        updates
      );
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["post-hire", variables.applicationId],
      });
    },
  });
}

// ==================== REPORTS ====================

export function useHiringReport(filters?: ReportFilters) {
  return useQuery({
    queryKey: ["reports", "hiring", filters],
    queryFn: async (): Promise<HiringReport> => {
      const params = new URLSearchParams();
      if (filters?.date_from) params.append("date_from", filters.date_from);
      if (filters?.date_to) params.append("date_to", filters.date_to);
      if (filters?.client_id) params.append("client_id", filters.client_id);
      if (filters?.role_id) params.append("role_id", filters.role_id);
      if (filters?.consultant_id) params.append("consultant_id", filters.consultant_id);
      
      const { data } = await api.get(`/headhunting/reports/hiring?${params.toString()}`);
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutos para reports
  });
}

export function useExportReport() {
  return useMutation({
    mutationFn: async ({
      format,
      filters,
    }: {
      format: "csv" | "pdf";
      filters?: ReportFilters;
    }) => {
      const params = new URLSearchParams();
      params.append("format", format);
      if (filters?.date_from) params.append("date_from", filters.date_from);
      if (filters?.date_to) params.append("date_to", filters.date_to);
      
      const response = await api.get(
        `/headhunting/reports/export?${params.toString()}`,
        { responseType: "blob" }
      );
      
      // Crear download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `reporte.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      return true;
    },
  });
}
