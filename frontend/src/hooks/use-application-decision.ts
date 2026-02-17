/**
 * Hook para manejar decisiones de aplicaciones por parte del consultor
 * Incluye lógica para manejo de datos de contacto faltantes
 */

import { useState, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { toast } from "@/hooks/use-toast";
import type { PipelineStage } from "@/types/headhunting";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

export interface ApplicationDecisionInput {
  decision: "continue" | "discard";
  reason?: string;
}

export interface ContactStatusInput {
  status: "contacted" | "interested" | "not_interested" | "no_response";
}

export interface SendMessageInput {
  template_id: string;
  channel: "email" | "whatsapp";
}

export interface CandidateContactInfo {
  candidate_id: string;
  full_name: string;
  email?: string;
  phone?: string;
}

interface UseApplicationDecisionReturn {
  // Estado del modal
  isContactModalOpen: boolean;
  pendingCandidate: CandidateContactInfo | null;
  
  // Acciones
  makeConsultantDecision: (applicationId: string, input: ApplicationDecisionInput) => Promise<void>;
  updateContactStatus: (applicationId: string, input: ContactStatusInput) => Promise<void>;
  sendMessage: (applicationId: string, input: SendMessageInput) => Promise<void>;
  updateCandidateContact: (applicationId: string, candidateId: string, data: { email?: string; phone?: string }) => Promise<void>;
  
  // Manejo del modal
  closeContactModal: () => void;
  submitContactData: (data: { email?: string; phone?: string }) => void;
  skipContactModal: () => void;
  
  // Estados
  isDecisionLoading: boolean;
  isContactUpdateLoading: boolean;
  isMessageSending: boolean;
}

/**
 * Hook para manejar decisiones del consultor sobre candidatos
 * 
 * Lógica de negocio:
 * - Cuando el consultor marca "CONTINUAR":
 *   1. Verificar si faltan datos de contacto
 *   2. Si faltan: mostrar modal para completar datos
 *   3. Si están completos: actualizar estado a CONTACTED y enviar mensaje
 * 
 * - Cuando el consultor marca "DESCARTAR":
 *   1. Actualizar estado a DISCARDED
 *   2. Guardar razón de descarte
 */
export function useApplicationDecision(): UseApplicationDecisionReturn {
  const queryClient = useQueryClient();
  const [isContactModalOpen, setIsContactModalOpen] = useState(false);
  const [pendingCandidate, setPendingCandidate] = useState<CandidateContactInfo | null>(null);
  const [pendingDecision, setPendingDecision] = useState<{ applicationId: string; input: ApplicationDecisionInput } | null>(null);

  // Mutación para decisión del consultor
  const decisionMutation = useMutation({
    mutationFn: async ({
      applicationId,
      input,
    }: {
      applicationId: string;
      input: ApplicationDecisionInput;
    }) => {
      const { data } = await api.patch(
        `/applications/${applicationId}/consultant-decision`,
        input
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      toast({
        title: "Decisión registrada",
        description: "La decisión del consultor ha sido guardada",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "No se pudo registrar la decisión",
        variant: "destructive",
      });
    },
  });

  // Mutación para actualizar estado de contacto
  const contactStatusMutation = useMutation({
    mutationFn: async ({
      applicationId,
      input,
    }: {
      applicationId: string;
      input: ContactStatusInput;
    }) => {
      const { data } = await api.patch(
        `/applications/${applicationId}/contact-status`,
        input
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "No se pudo actualizar el estado",
        variant: "destructive",
      });
    },
  });

  // Mutación para enviar mensaje
  const sendMessageMutation = useMutation({
    mutationFn: async ({
      applicationId,
      input,
    }: {
      applicationId: string;
      input: SendMessageInput;
    }) => {
      const { data } = await api.post(
        `/applications/${applicationId}/send-message`,
        input
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      toast({
        title: "Mensaje enviado",
        description: "El mensaje ha sido enviado al candidato",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "No se pudo enviar el mensaje",
        variant: "destructive",
      });
    },
  });

  // Mutación para actualizar datos del candidato
  const updateCandidateMutation = useMutation({
    mutationFn: async ({
      candidateId,
      data,
    }: {
      candidateId: string;
      data: { email?: string; phone?: string };
    }) => {
      const { data: response } = await api.patch(`/candidates/${candidateId}`, data);
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["candidates"] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "No se pudo actualizar el candidato",
        variant: "destructive",
      });
    },
  });

  /**
   * Realizar decisión del consultor
   * Si es "continue" y faltan datos, muestra el modal
   */
  const makeConsultantDecision = useCallback(
    async (applicationId: string, input: ApplicationDecisionInput, candidateInfo?: CandidateContactInfo) => {
      if (input.decision === "discard") {
        // Descartar directamente
        await decisionMutation.mutateAsync({ applicationId, input });
        return;
      }

      // Si es continue, verificar datos de contacto
      if (candidateInfo && (!candidateInfo.email || !candidateInfo.phone)) {
        // Faltan datos - mostrar modal
        setPendingCandidate(candidateInfo);
        setPendingDecision({ applicationId, input });
        setIsContactModalOpen(true);
        return;
      }

      // Datos completos - proceder directamente
      await decisionMutation.mutateAsync({ applicationId, input });
    },
    [decisionMutation]
  );

  /**
   * Cerrar modal de contacto
   */
  const closeContactModal = useCallback(() => {
    setIsContactModalOpen(false);
    setPendingCandidate(null);
    setPendingDecision(null);
  }, []);

  /**
   * Enviar datos de contacto desde el modal
   */
  const submitContactData = useCallback(
    async (data: { email?: string; phone?: string }) => {
      if (!pendingDecision || !pendingCandidate) return;

      try {
        // Actualizar datos del candidato
        await updateCandidateMutation.mutateAsync({
          candidateId: pendingCandidate.candidate_id,
          data,
        });

        // Cerrar modal
        setIsContactModalOpen(false);

        // Continuar con la decisión
        await decisionMutation.mutateAsync({
          applicationId: pendingDecision.applicationId,
          input: pendingDecision.input,
        });

        toast({
          title: "Datos guardados",
          description: "Los datos de contacto han sido actualizados",
        });
      } catch (error) {
        // Error ya manejado por la mutación
      } finally {
        setPendingCandidate(null);
        setPendingDecision(null);
      }
    },
    [pendingDecision, pendingCandidate, updateCandidateMutation, decisionMutation]
  );

  /**
   * Omitir modal y continuar sin datos
   */
  const skipContactModal = useCallback(async () => {
    if (!pendingDecision) return;

    setIsContactModalOpen(false);

    try {
      await decisionMutation.mutateAsync({
        applicationId: pendingDecision.applicationId,
        input: pendingDecision.input,
      });
    } finally {
      setPendingCandidate(null);
      setPendingDecision(null);
    }
  }, [pendingDecision, decisionMutation]);

  /**
   * Actualizar estado de contacto
   */
  const updateContactStatus = useCallback(
    async (applicationId: string, input: ContactStatusInput) => {
      await contactStatusMutation.mutateAsync({ applicationId, input });
    },
    [contactStatusMutation]
  );

  /**
   * Enviar mensaje al candidato
   */
  const sendMessage = useCallback(
    async (applicationId: string, input: SendMessageInput) => {
      await sendMessageMutation.mutateAsync({ applicationId, input });
    },
    [sendMessageMutation]
  );

  /**
   * Actualizar datos de contacto del candidato
   */
  const updateCandidateContact = useCallback(
    async (applicationId: string, candidateId: string, data: { email?: string; phone?: string }) => {
      await updateCandidateMutation.mutateAsync({ candidateId, data });
    },
    [updateCandidateMutation]
  );

  return {
    isContactModalOpen,
    pendingCandidate,
    makeConsultantDecision,
    updateContactStatus,
    sendMessage,
    updateCandidateContact,
    closeContactModal,
    submitContactData,
    skipContactModal,
    isDecisionLoading: decisionMutation.isPending,
    isContactUpdateLoading: contactStatusMutation.isPending,
    isMessageSending: sendMessageMutation.isPending,
  };
}

export default useApplicationDecision;
