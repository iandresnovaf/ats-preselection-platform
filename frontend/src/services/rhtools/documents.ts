import api from "@/services/api";
import {
  Document,
  DocumentFilters,
  UploadDocumentData,
  DocumentType,
} from "@/types/rhtools";

export const documentsService = {
  async getDocuments(filters?: DocumentFilters): Promise<Document[]> {
    const params = new URLSearchParams();
    if (filters?.submission_id) params.append("submission_id", filters.submission_id);
    if (filters?.candidate_id) params.append("candidate_id", filters.candidate_id);
    if (filters?.job_id) params.append("job_id", filters.job_id);
    if (filters?.type) params.append("type", filters.type);
    if (filters?.status) params.append("status", filters.status);

    const response = await api.get(`/rhtools/documents?${params.toString()}`);
    return response.data.items || response.data || [];
  },

  async getDocument(id: string): Promise<Document> {
    const response = await api.get(`/rhtools/documents/${id}`);
    return response.data;
  },

  async uploadDocument(data: UploadDocumentData): Promise<Document> {
    const formData = new FormData();
    formData.append("file", data.file);
    formData.append("type", data.type);
    if (data.submission_id) formData.append("submission_id", data.submission_id);
    if (data.candidate_id) formData.append("candidate_id", data.candidate_id);
    if (data.job_id) formData.append("job_id", data.job_id);

    const response = await api.post("/rhtools/documents", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        // El progreso se maneja en el componente
        const percentCompleted = progressEvent.total
          ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
          : 0;
        return percentCompleted;
      },
    });
    return response.data;
  },

  async deleteDocument(id: string): Promise<void> {
    await api.delete(`/rhtools/documents/${id}`);
  },

  async reprocessDocument(id: string): Promise<Document> {
    const response = await api.post(`/rhtools/documents/${id}/reprocess`);
    return response.data;
  },

  async getDocumentUrl(id: string): Promise<string> {
    const response = await api.get(`/rhtools/documents/${id}/url`);
    return response.data.url;
  },

  async getDocumentsBySubmission(submissionId: string): Promise<Document[]> {
    const response = await api.get(`/rhtools/submissions/${submissionId}/documents`);
    return response.data;
  },

  async getDocumentsByCandidate(candidateId: string): Promise<Document[]> {
    const response = await api.get(`/rhtools/candidates/${candidateId}/documents`);
    return response.data;
  },

  // Tipos de documentos permitidos
  getAllowedTypes(): { type: DocumentType; label: string; extensions: string[] }[] {
    return [
      { type: "cv", label: "Currículum", extensions: [".pdf", ".doc", ".docx"] },
      { type: "cover_letter", label: "Carta de presentación", extensions: [".pdf", ".doc", ".docx"] },
      { type: "evaluation", label: "Evaluación", extensions: [".pdf"] },
      { type: "contract", label: "Contrato", extensions: [".pdf"] },
      { type: "reference", label: "Referencia", extensions: [".pdf"] },
      { type: "id_document", label: "Documento de identidad", extensions: [".pdf", ".jpg", ".png"] },
      { type: "other", label: "Otro", extensions: [".pdf", ".doc", ".docx", ".jpg", ".png"] },
    ];
  },

  getMaxFileSize(): number {
    return 10 * 1024 * 1024; // 10MB
  },
};
