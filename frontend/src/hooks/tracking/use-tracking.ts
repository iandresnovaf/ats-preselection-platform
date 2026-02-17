"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import type {
  TrackedCandidate,
  VacanteSummary,
  ActivityItem,
  TrackingStats,
  TrackingFilters,
  BulkActionResult,
  ContactCandidateData,
  ResendReminderData,
  ApplicationStatus,
} from "@/types/tracking";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Hook to fetch tracking data grouped by status
 */
export function useTrackingData(roleId?: string) {
  return useQuery({
    queryKey: ["tracking", "candidates", roleId],
    queryFn: async () => {
      const params = roleId ? { role_id: roleId } : {};
      const response = await api.get("/api/v1/tracking/candidates", { params });
      return response.data as {
        by_status: Record<ApplicationStatus, TrackedCandidate[]>;
        total: number;
      };
    },
  });
}

/**
 * Hook to fetch all roles with tracking summary
 */
export function useVacanteSummaries() {
  return useQuery({
    queryKey: ["tracking", "vacantes"],
    queryFn: async () => {
      const response = await api.get("/api/v1/tracking/vacantes");
      return response.data as VacanteSummary[];
    },
  });
}

/**
 * Hook to fetch candidates for a specific role
 */
export function useRoleCandidates(roleId: string) {
  return useQuery({
    queryKey: ["tracking", "candidates", roleId],
    queryFn: async () => {
      const response = await api.get(`/api/v1/tracking/roles/${roleId}/candidates`);
      return response.data as TrackedCandidate[];
    },
    enabled: !!roleId,
  });
}

/**
 * Hook for bulk actions on candidates
 */
export function useBulkActions() {
  const queryClient = useQueryClient();

  const contactMultiple = useMutation({
    mutationFn: async (data: ContactCandidateData): Promise<BulkActionResult> => {
      const response = await api.post("/api/v1/tracking/bulk/contact", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tracking"] });
    },
  });

  const resendToNoResponse = useMutation({
    mutationFn: async (data: ResendReminderData): Promise<BulkActionResult> => {
      const response = await api.post("/api/v1/tracking/bulk/resend", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tracking"] });
    },
  });

  const updateStatus = useMutation({
    mutationFn: async ({
      candidateIds,
      status,
    }: {
      candidateIds: string[];
      status: ApplicationStatus;
    }): Promise<BulkActionResult> => {
      const response = await api.post("/api/v1/tracking/bulk/status", {
        candidate_ids: candidateIds,
        status,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tracking"] });
    },
  });

  return {
    contactMultiple,
    resendToNoResponse,
    updateStatus,
  };
}

/**
 * Hook to fetch recent activity
 */
export function useRecentActivity(limit: number = 20) {
  return useQuery({
    queryKey: ["tracking", "activity", limit],
    queryFn: async () => {
      const response = await api.get("/api/v1/tracking/activity", {
        params: { limit },
      });
      return response.data as ActivityItem[];
    },
  });
}

/**
 * Hook to fetch tracking statistics
 */
export function useTrackingStats(roleId?: string) {
  return useQuery({
    queryKey: ["tracking", "stats", roleId],
    queryFn: async () => {
      const params = roleId ? { role_id: roleId } : {};
      const response = await api.get("/api/v1/tracking/stats", { params });
      return response.data as TrackingStats;
    },
  });
}

/**
 * Hook for individual candidate actions
 */
export function useCandidateActions() {
  const queryClient = useQueryClient();

  const updateCandidateStatus = useMutation({
    mutationFn: async ({
      candidateId,
      status,
      notes,
    }: {
      candidateId: string;
      status: ApplicationStatus;
      notes?: string;
    }) => {
      const response = await api.patch(`/api/v1/tracking/candidates/${candidateId}/status`, {
        status,
        notes,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tracking"] });
    },
  });

  const contactCandidate = useMutation({
    mutationFn: async ({
      candidateId,
      channel,
      message,
    }: {
      candidateId: string;
      channel: "email" | "whatsapp";
      message?: string;
    }) => {
      const response = await api.post(`/api/v1/tracking/candidates/${candidateId}/contact`, {
        channel,
        message,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tracking"] });
    },
  });

  const addNote = useMutation({
    mutationFn: async ({
      candidateId,
      note,
    }: {
      candidateId: string;
      note: string;
    }) => {
      const response = await api.post(`/api/v1/tracking/candidates/${candidateId}/notes`, {
        note,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tracking"] });
    },
  });

  return {
    updateCandidateStatus,
    contactCandidate,
    addNote,
  };
}

/**
 * Hook to fetch filtered candidates
 */
export function useFilteredCandidates(filters: TrackingFilters) {
  return useQuery({
    queryKey: ["tracking", "candidates", "filtered", filters],
    queryFn: async () => {
      const response = await api.get("/api/v1/tracking/candidates/filtered", {
        params: {
          ...filters,
          date_from: filters.date_from?.toISOString(),
          date_to: filters.date_to?.toISOString(),
        },
      });
      return response.data as TrackedCandidate[];
    },
  });
}
