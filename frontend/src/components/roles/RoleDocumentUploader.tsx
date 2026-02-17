"use client";

import { useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, FileText, AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ExtractedRoleData {
  role_title: string;
  objective: string;
  hierarchy: {
    reports_to: string;
    level: string;
    direct_reports: string;
    work_mode: string;
    location: string;
  };
  responsibilities: Record<string, string[]>;
  requirements: {
    education: string;
    experience_years: string;
    experience_details: string;
  };
  skills: {
    technical: string[];
    soft: string[];
  };
  disc_profile?: string;
  tools: string[];
  conditions: {
    salary_range: string;
    benefits: string;
    location: string;
    work_schedule: string;
  };
  description: string;
  metadata: {
    extraction_errors: string[];
    extraction_warnings: string[];
    sections_found: string[];
  };
}

interface RoleDocumentUploaderProps {
  onExtracted: (data: ExtractedRoleData) => void;
  apiBaseUrl?: string;
}

type UploadState = "idle" | "uploading" | "processing" | "success" | "error";

export function RoleDocumentUploader({
  onExtracted,
  apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
}: RoleDocumentUploaderProps) {
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [progress, setProgress] = useState<number>(0);

  const allowedTypes = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
  ];

  const allowedExtensions = [".pdf", ".docx", ".doc", ".txt"];

  const validateFile = (file: File): string | null => {
    // Validar tipo MIME
    if (!allowedTypes.includes(file.type)) {
      // Verificar extensión como fallback
      const ext = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
      if (!allowedExtensions.includes(ext)) {
        return "Formato no soportado. Use PDF, Word (DOCX/DOC) o TXT.";
      }
    }

    // Validar tamaño (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      return "El archivo es muy grande. Máximo 10MB.";
    }

    return null;
  };

  const handleFileSelect = useCallback((file: File) => {
    const error = validateFile(file);
    if (error) {
      setErrorMessage(error);
      setUploadState("error");
      return;
    }

    setSelectedFile(file);
    setErrorMessage("");
    setUploadState("idle");
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) {
        handleFileSelect(file);
      }
    },
    [handleFileSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFileSelect(file);
      }
    },
    [handleFileSelect]
  );

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploadState("uploading");
    setProgress(0);
    setErrorMessage("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      setUploadState("processing");

      const response = await fetch(`${apiBaseUrl}/roles/extract-from-document`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Error ${response.status}: ${response.statusText}`
        );
      }

      const result = await response.json();

      if (result.success && result.data) {
        setUploadState("success");
        onExtracted(result.data);
      } else {
        throw new Error("No se pudo extraer información del documento");
      }
    } catch (error) {
      setUploadState("error");
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Error procesando el documento. Inténtelo de nuevo."
      );
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <FileText className="w-5 h-5" />
          Subir Perfil de Cargo
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Drop Zone */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          className={cn(
            "border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer",
            uploadState === "uploading" || uploadState === "processing"
              ? "border-blue-400 bg-blue-50"
              : uploadState === "success"
              ? "border-green-400 bg-green-50"
              : uploadState === "error"
              ? "border-red-400 bg-red-50"
              : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
          )}
        >
          <input
            type="file"
            accept=".pdf,.docx,.doc,.txt"
            onChange={handleInputChange}
            className="hidden"
            id="role-document-upload"
            disabled={uploadState === "uploading" || uploadState === "processing"}
          />
          <label
            htmlFor="role-document-upload"
            className="cursor-pointer block"
          >
            {uploadState === "uploading" || uploadState === "processing" ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
                <p className="text-sm text-gray-600">
                  {uploadState === "uploading"
                    ? "Subiendo archivo..."
                    : "Extrayendo información..."}
                </p>
              </div>
            ) : uploadState === "success" ? (
              <div className="flex flex-col items-center gap-3">
                <CheckCircle className="w-10 h-10 text-green-500" />
                <p className="text-sm text-green-600 font-medium">
                  ¡Documento procesado exitosamente!
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <Upload className="w-10 h-10 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-700">
                    Arrastre su archivo aquí o haga clic para seleccionar
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    PDF, Word (DOCX/DOC) o TXT. Máximo 10MB.
                  </p>
                </div>
              </div>
            )}
          </label>
        </div>

        {/* File Preview */}
        {selectedFile && uploadState !== "success" && (
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
            <FileText className="w-8 h-8 text-gray-400" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-700 truncate">
                {selectedFile.name}
              </p>
              <p className="text-xs text-gray-500">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
            {uploadState === "idle" && (
              <Button
                size="sm"
                onClick={handleUpload}
                disabled={!selectedFile}
              >
                Procesar
              </Button>
            )}
          </div>
        )}

        {/* Error Message */}
        {uploadState === "error" && errorMessage && (
          <div className="flex items-start gap-2 p-3 bg-red-50 text-red-700 rounded-lg">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium">Error al procesar el documento</p>
              <p className="text-red-600">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Tips */}
        <div className="text-xs text-gray-500 bg-gray-50 p-3 rounded-lg">
          <p className="font-medium mb-1">💡 Consejos para mejores resultados:</p>
          <ul className="list-disc list-inside space-y-0.5">
            <li>Use documentos con texto seleccionable (no imágenes escaneadas)</li>
            <li>Asegúrese de que el documento tenga secciones claramente identificadas</li>
            <li>Los formatos PDF y DOCX funcionan mejor que los documentos antiguos DOC</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}