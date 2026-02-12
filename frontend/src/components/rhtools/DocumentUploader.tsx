"use client";

import { useState, useCallback } from "react";
import { Document, DocumentType, DocumentStatus } from "@/types/rhtools";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  Upload, 
  File, 
  X, 
  CheckCircle, 
  AlertCircle, 
  Loader2,
  FileText,
  FileImage,
  File as FileIcon
} from "lucide-react";
import { cn } from "@/lib/utils";
import { documentsService } from "@/services/rhtools/documents";

interface DocumentUploaderProps {
  type: DocumentType;
  submissionId?: string;
  candidateId?: string;
  jobId?: string;
  onUploadComplete?: (document: Document) => void;
  onUploadError?: (error: Error) => void;
  maxSize?: number;
  allowedTypes?: string[];
  className?: string;
}

const typeLabels: Record<DocumentType, string> = {
  cv: "Currículum",
  cover_letter: "Carta de presentación",
  evaluation: "Evaluación",
  contract: "Contrato",
  reference: "Referencia",
  id_document: "Documento de identidad",
  other: "Otro",
};

const statusConfig: Record<DocumentStatus, { icon: React.ReactNode; color: string; label: string }> = {
  uploaded: { 
    icon: <Loader2 className="h-4 w-4 animate-spin" />, 
    color: "text-blue-500", 
    label: "Subiendo..." 
  },
  processing: { 
    icon: <Loader2 className="h-4 w-4 animate-spin" />, 
    color: "text-yellow-500", 
    label: "Procesando..." 
  },
  extracted: { 
    icon: <CheckCircle className="h-4 w-4" />, 
    color: "text-green-500", 
    label: "Procesado" 
  },
  error: { 
    icon: <AlertCircle className="h-4 w-4" />, 
    color: "text-red-500", 
    label: "Error" 
  },
};

function getFileIcon(mimeType: string) {
  if (mimeType.startsWith("image/")) {
    return <FileImage className="h-8 w-8 text-purple-500" />;
  }
  if (mimeType.includes("pdf")) {
    return <FileText className="h-8 w-8 text-red-500" />;
  }
  return <FileIcon className="h-8 w-8 text-blue-500" />;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

export function DocumentUploader({
  type,
  submissionId,
  candidateId,
  jobId,
  onUploadComplete,
  onUploadError,
  maxSize = 10 * 1024 * 1024, // 10MB default
  allowedTypes,
  className,
}: DocumentUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedDoc, setUploadedDoc] = useState<Document | null>(null);

  const getAllowedExtensions = useCallback(() => {
    if (allowedTypes) return allowedTypes;
    const allowed = documentsService.getAllowedTypes().find(t => t.type === type);
    return allowed?.extensions || [".pdf", ".doc", ".docx"];
  }, [type, allowedTypes]);

  const validateFile = (file: File): string | null => {
    if (file.size > maxSize) {
      return `El archivo excede el tamaño máximo de ${formatFileSize(maxSize)}`;
    }

    const extensions = getAllowedExtensions();
    const fileExt = "." + file.name.split(".").pop()?.toLowerCase();
    if (!extensions.includes(fileExt)) {
      return `Tipo de archivo no permitido. Permitidos: ${extensions.join(", ")}`;
    }

    return null;
  };

  const handleUpload = async (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setIsUploading(true);
    setUploadProgress(0);

    try {
      const document = await documentsService.uploadDocument({
        file,
        type,
        submission_id: submissionId,
        candidate_id: candidateId,
        job_id: jobId,
      });

      setUploadedDoc(document);
      setUploadProgress(100);
      onUploadComplete?.(document);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Error al subir el archivo");
      setError(error.message);
      onUploadError?.(error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleUpload(files[0]);
    }
  }, [type, submissionId, candidateId, jobId]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleUpload(files[0]);
    }
  };

  const clearUpload = () => {
    setUploadedDoc(null);
    setUploadProgress(0);
    setError(null);
  };

  // Mostrar documento subido
  if (uploadedDoc) {
    const status = statusConfig[uploadedDoc.status];
    return (
      <div className={cn("border rounded-lg p-4", className)}>
        <div className="flex items-start gap-3">
          {getFileIcon(uploadedDoc.mime_type)}
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate">{uploadedDoc.original_name}</p>
            <p className="text-sm text-muted-foreground">
              {formatFileSize(uploadedDoc.file_size)} • {typeLabels[type]}
            </p>
            <div className="flex items-center gap-2 mt-2">
              <span className={cn("flex items-center gap-1 text-sm", status.color)}>
                {status.icon}
                {status.label}
              </span>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={clearUpload}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={cn(
          "border-2 border-dashed rounded-lg p-6 text-center transition-colors",
          isDragging 
            ? "border-primary bg-primary/5" 
            : "border-muted-foreground/25 hover:border-muted-foreground/50",
          isUploading && "opacity-50 pointer-events-none"
        )}
      >
        <input
          type="file"
          id={`file-upload-${type}`}
          className="hidden"
          onChange={handleFileInput}
          accept={getAllowedExtensions().join(",")}
          disabled={isUploading}
        />
        
        <div className="flex flex-col items-center gap-2">
          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
            {isUploading ? (
              <Loader2 className="h-6 w-6 text-primary animate-spin" />
            ) : (
              <Upload className="h-6 w-6 text-primary" />
            )}
          </div>
          
          <div className="space-y-1">
            <p className="font-medium">
              {isUploading ? "Subiendo..." : `Subir ${typeLabels[type]}`}
            </p>
            <p className="text-sm text-muted-foreground">
              Arrastra y suelta o{" "}
              <label 
                htmlFor={`file-upload-${type}`}
                className="text-primary hover:underline cursor-pointer"
              >
                selecciona un archivo
              </label>
            </p>
            <p className="text-xs text-muted-foreground">
              Máximo {formatFileSize(maxSize)} • {getAllowedExtensions().join(", ")}
            </p>
          </div>
        </div>

        {isUploading && (
          <div className="mt-4">
            <Progress value={uploadProgress} className="h-2" />
            <p className="text-sm text-muted-foreground mt-1">
              {uploadProgress}%
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
