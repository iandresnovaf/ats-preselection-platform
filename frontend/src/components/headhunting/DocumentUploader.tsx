"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  FileText,
  Upload,
  X,
  File,
  FileImage,
  FileSpreadsheet,
  CheckCircle,
  AlertCircle,
  Loader2,
  Eye,
  Download,
} from "lucide-react";
import type { DocumentType, ApplicationDocument } from "@/types/headhunting";

interface DocumentUploaderProps {
  onUpload: (file: File, type: DocumentType) => Promise<void>;
  allowedTypes?: string[];
  maxSize?: number; // in MB
  className?: string;
}

const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  cv: "Currículum",
  cover_letter: "Carta de presentación",
  test_technical: "Prueba técnica",
  test_psychometric: "Prueba psicométrica",
  interview_notes: "Notas de entrevista",
  reference_check: "Verificación de referencias",
  offer_letter: "Carta de oferta",
  contract: "Contrato",
  other: "Otro",
};

/**
 * Componente DocumentUploader
 * Drag & drop con selector de tipo de documento
 */
export function DocumentUploader({
  onUpload,
  allowedTypes = [".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"],
  maxSize = 10, // 10MB default
  className,
}: DocumentUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedType, setSelectedType] = useState<DocumentType>("other");
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const validateFile = (file: File): string | null => {
    // Check file type
    const extension = `.${file.name.split(".").pop()?.toLowerCase()}`;
    if (!allowedTypes.includes(extension)) {
      return `Tipo de archivo no permitido. Use: ${allowedTypes.join(", ")}`;
    }

    // Check file size
    if (file.size > maxSize * 1024 * 1024) {
      return `Archivo demasiado grande. Máximo: ${maxSize}MB`;
    }

    return null;
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setError(null);

    const file = e.dataTransfer.files[0];
    if (file) {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }
      setSelectedFile(file);
    }
  }, [allowedTypes, maxSize]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setError(null);
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setProgress(0);

    // Simular progreso
    const progressInterval = setInterval(() => {
      setProgress(prev => Math.min(prev + 10, 90));
    }, 200);

    try {
      await onUpload(selectedFile, selectedType);
      setProgress(100);
      setTimeout(() => {
        setSelectedFile(null);
        setProgress(0);
      }, 500);
    } catch (err) {
      setError("Error al subir el archivo. Intente nuevamente.");
    } finally {
      clearInterval(progressInterval);
      setIsUploading(false);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setError(null);
    setProgress(0);
  };

  // Icono según tipo de archivo
  const getFileIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    if (["jpg", "jpeg", "png", "gif"].includes(ext || "")) {
      return <FileImage className="w-8 h-8 text-purple-500" />;
    }
    if (["xls", "xlsx", "csv"].includes(ext || "")) {
      return <FileSpreadsheet className="w-8 h-8 text-green-500" />;
    }
    if (["pdf"].includes(ext || "")) {
      return <FileText className="w-8 h-8 text-red-500" />;
    }
    return <File className="w-8 h-8 text-blue-500" />;
  };

  // Si hay archivo seleccionado, mostrar preview
  if (selectedFile) {
    return (
      <div className={cn("rounded-lg border bg-gray-50 p-4", className)}>
        <div className="flex items-start gap-3">
          {getFileIcon(selectedFile.name)}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{selectedFile.name}</p>
            <p className="text-xs text-gray-500">
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
            
            {isUploading && (
              <div className="mt-3">
                <Progress value={progress} className="h-2" />
                <p className="text-xs text-gray-500 mt-1">{progress}%</p>
              </div>
            )}
          </div>
          {!isUploading && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={clearFile}
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>

        {!isUploading && (
          <>
            <div className="mt-3">
              <label className="text-xs font-medium text-gray-700">
                Tipo de documento
              </label>
              <Select value={selectedType} onValueChange={(v) => setSelectedType(v as DocumentType)}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(DOCUMENT_TYPE_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              className="w-full mt-3"
              onClick={handleUpload}
              disabled={isUploading}
            >
              {isUploading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Upload className="w-4 h-4 mr-2" />
              )}
              Subir documento
            </Button>
          </>
        )}

        {error && (
          <div className="flex items-center gap-2 text-red-600 text-sm mt-3">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}
      </div>
    );
  }

  // Área de drag & drop
  return (
    <div
      className={cn(
        "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
        isDragging
          ? "border-blue-500 bg-blue-50"
          : "border-gray-300 hover:border-gray-400",
        className
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="flex flex-col items-center">
        <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
          <Upload className="w-6 h-6 text-gray-500" />
        </div>
        <p className="text-sm font-medium text-gray-700">
          Arrastra archivos aquí o{" "}
          <label className="text-blue-600 hover:text-blue-700 cursor-pointer">
            selecciona
            <input
              type="file"
              className="hidden"
              accept={allowedTypes.join(",")}
              onChange={handleFileSelect}
            />
          </label>
        </p>
        <p className="text-xs text-gray-500 mt-1">
          Máximo {maxSize}MB • {allowedTypes.join(", ")}
        </p>
      </div>

      {error && (
        <div className="flex items-center justify-center gap-2 text-red-600 text-sm mt-4">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}
    </div>
  );
}

/**
 * Lista de documentos subidos
 */
interface DocumentListProps {
  documents: ApplicationDocument[];
  onPreview?: (doc: ApplicationDocument) => void;
  onDownload?: (doc: ApplicationDocument) => void;
  onDelete?: (doc: ApplicationDocument) => void;
  className?: string;
}

export function DocumentList({
  documents,
  onPreview,
  onDownload,
  onDelete,
  className,
}: DocumentListProps) {
  const getStatusIcon = (status: ApplicationDocument["processing_status"]) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "processing":
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case "error":
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    if (["jpg", "jpeg", "png", "gif"].includes(ext || "")) {
      return <FileImage className="w-8 h-8 text-purple-500" />;
    }
    if (["xls", "xlsx", "csv"].includes(ext || "")) {
      return <FileSpreadsheet className="w-8 h-8 text-green-500" />;
    }
    if (["pdf"].includes(ext || "")) {
      return <FileText className="w-8 h-8 text-red-500" />;
    }
    return <File className="w-8 h-8 text-blue-500" />;
  };

  if (documents.length === 0) {
    return (
      <div className={cn("text-center py-8 text-gray-400", className)}>
        <FileText className="w-10 h-10 mx-auto mb-2 opacity-30" />
        <p className="text-sm">No hay documentos</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="flex items-center gap-3 p-3 rounded-lg border hover:bg-gray-50 transition-colors"
        >
          {getFileIcon(doc.name)}
          
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{doc.name}</p>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>{DOCUMENT_TYPE_LABELS[doc.type]}</span>
              <span>•</span>
              <span>{new Date(doc.created_at).toLocaleDateString("es-ES")}</span>
              <span>•</span>
              {getStatusIcon(doc.processing_status)}
            </div>
          </div>

          <div className="flex items-center gap-1">
            {onPreview && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => onPreview(doc)}
                title="Ver"
              >
                <Eye className="w-4 h-4" />
              </Button>
            )}
            {onDownload && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => onDownload(doc)}
                title="Descargar"
              >
                <Download className="w-4 h-4" />
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-red-500 hover:text-red-600"
                onClick={() => onDelete(doc)}
                title="Eliminar"
              >
                <X className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// Import Clock for DocumentList
import { Clock } from "lucide-react";
