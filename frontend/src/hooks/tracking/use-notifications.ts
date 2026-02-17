"use client";

import { useEffect, useCallback } from "react";
import { useToast } from "@/hooks/use-toast";
import type { ApplicationStatus, TrackedCandidate } from "@/types/tracking";

interface NotificationPayload {
  type: "candidate_response" | "pending_contact" | "no_response_reminder";
  candidate?: TrackedCandidate;
  count?: number;
  message?: string;
}

/**
 * Hook for real-time notifications in the tracking dashboard
 */
export function useTrackingNotifications() {
  const { toast } = useToast();

  const showCandidateResponse = useCallback((
    candidate: TrackedCandidate,
    response: ApplicationStatus
  ) => {
    const statusLabels: Record<ApplicationStatus, string> = {
      pending_contact: "Pendiente de contacto",
      contacted: "Contactado",
      interested: "INTERESADO",
      not_interested: "NO INTERESADO",
      no_response: "Sin respuesta",
      scheduled: "Entrevista agendada",
      completed: "Proceso completado",
      hired: "Contratado",
    };

    const isPositive = response === "interested" || response === "scheduled" || response === "hired";

    toast({
      title: isPositive ? "🎉 ¡Nueva respuesta!" : "Respuesta recibida",
      description: `${candidate.first_name} ${candidate.last_name} ha respondido: ${statusLabels[response]}`,
      variant: isPositive ? "default" : "destructive",
    });
  }, [toast]);

  const showPendingContactWarning = useCallback((count: number) => {
    toast({
      title: "⚠️ Candidatos pendientes",
      description: `Tienes ${count} candidatos pendientes de contacto.`,
      variant: "destructive",
    });
  }, [toast]);

  const showNoResponseReminder = useCallback((count: number) => {
    toast({
      title: "⏰ Recordatorio",
      description: `${count} candidatos sin respuesta en más de 48h. Considera reenviar el mensaje.`,
      variant: "default",
    });
  }, [toast]);

  const showBulkActionComplete = useCallback((
    action: string,
    processed: number,
    failed: number
  ) => {
    if (failed === 0) {
      toast({
        title: "✅ Acción completada",
        description: `${action}: ${processed} candidatos procesados exitosamente.`,
      });
    } else {
      toast({
        title: "⚠️ Acción parcialmente completada",
        description: `${action}: ${processed} exitosos, ${failed} fallidos.`,
        variant: "destructive",
      });
    }
  }, [toast]);

  const showError = useCallback((message: string) => {
    toast({
      title: "❌ Error",
      description: message,
      variant: "destructive",
    });
  }, [toast]);

  const showSuccess = useCallback((message: string) => {
    toast({
      title: "✅ Éxito",
      description: message,
    });
  }, [toast]);

  // Simulated WebSocket connection for real-time updates
  useEffect(() => {
    // In a real implementation, this would connect to a WebSocket
    // For now, we'll use polling via React Query
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        // Trigger refetch when user returns to the page
        window.dispatchEvent(new CustomEvent("tracking:refresh"));
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  return {
    showCandidateResponse,
    showPendingContactWarning,
    showNoResponseReminder,
    showBulkActionComplete,
    showError,
    showSuccess,
  };
}

/**
 * Hook to check for candidates needing attention
 */
export function useAttentionChecker(candidates: TrackedCandidate[] | undefined) {
  const { toast } = useToast();

  useEffect(() => {
    if (!candidates) return;

    const pendingContact = candidates.filter(
      (c) => c.status === "pending_contact"
    );

    const noResponse = candidates.filter(
      (c) => c.status === "no_response" && (c.days_without_response || 0) > 2
    );

    // Show warnings only if significant
    if (pendingContact.length > 5) {
      toast({
        title: "⚠️ Atención requerida",
        description: `Tienes ${pendingContact.length} candidatos pendientes de contacto.`,
        variant: "destructive",
      });
    }

    if (noResponse.length > 3) {
      toast({
        title: "⏰ Reenvío recomendado",
        description: `${noResponse.length} candidatos sin respuesta en más de 48h.`,
      });
    }
  }, [candidates, toast]);
}
