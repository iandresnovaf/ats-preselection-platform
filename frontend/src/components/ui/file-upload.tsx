import React, { useState, useRef, useCallback, DragEvent } from "react";
import { Upload, File, X, AlertCircle, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface FileUploadProps {
  accept?: string;
  maxSize?: number; // in bytes
  onFileSelect: (file: File) => void;
  onFileRemove?: () => void;
  selectedFile?: File | null;
  uploadedUrl?: string | null;
  uploading?: boolean;
  uploadProgress?: number;
  disabled?: boolean;
  className?: string;
  id?: string;
}

export function FileUpload({
  accept = ".pdf",
  maxSize = 10 * 1024 * 1024, // 10MB default
  onFileSelect,
  onFileRemove,
  selectedFile,
  uploadedUrl,
  uploading = false,
  uploadProgress = 0,
  disabled = false,
  className = "",
  id,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): boolean => {
    setError(null);

    // Check file type
    if (accept === ".pdf" && file.type !== "application/pdf") {
      setError("Solo se permiten archivos PDF");
      return false;
    }

    // Check file size
    if (file.size > maxSize) {
      const maxSizeMB = maxSize / (1024 * 1024);
      setError(`El archivo es demasiado grande. Máximo ${maxSizeMB}MB`);
      return false;
    }

    return true;
  };

  const handleFileSelect = (file: File) => {
    if (validateFile(file)) {
      onFileSelect(file);
    }
  };

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled && !uploading) {
      setIsDragging(true);
    }
  }, [disabled, uploading]);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled || uploading) return;

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [disabled, uploading]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleRemove = () => {
    setError(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
    onFileRemove?.();
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const hasFile = selectedFile || uploadedUrl;

  if (hasFile) {
    return (
      <div
        className={cn(
          "border rounded-lg p-4 bg-muted/50",
          className
        )}
        id={id}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <File className="h-6 w-6 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">
              {selectedFile?.name || "Archivo PDF subido"}
            </p>
            {selectedFile && (
              <p className="text-xs text-muted-foreground">
                {formatFileSize(selectedFile.size)}
              </p>
            )}
            {uploading && (
              <div className="mt-2">
                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                    role="progressbar"
                    aria-valuenow={uploadProgress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Subiendo... {uploadProgress}%
                </p>
              </div>
            )}
            {uploadedUrl && !uploading && (
              <div className="flex items-center gap-1 text-xs text-green-600">
                <Check className="h-3 w-3" />
                <span>Subido correctamente</span>
              </div>
            )}
          </div>
          {!uploading && onFileRemove && (
            <button
              type="button"
              onClick={handleRemove}
              className="p-1 hover:bg-destructive/10 rounded-full transition-colors"
              aria-label="Remove file"
            >
              <X className="h-4 w-4 text-destructive" />
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={className} id={id}>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={cn(
          "border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-muted-foreground/50",
          disabled && "opacity-50 cursor-not-allowed",
          error && "border-destructive bg-destructive/5"
        )}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Upload PDF file"
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleInputChange}
          disabled={disabled}
          className="hidden"
          aria-label="File input"
        />
        <Upload className="h-8 w-8 mx-auto mb-3 text-muted-foreground" />
        <p className="text-sm font-medium mb-1">
          Arrastra y suelta tu PDF aquí
        </p>
        <p className="text-xs text-muted-foreground">
          o haz clic para seleccionar archivo
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          Máximo {formatFileSize(maxSize)}
        </p>
      </div>
      {error && (
        <div className="flex items-center gap-2 mt-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
