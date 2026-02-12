import { useState, useEffect, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { CreateJobData, UpdateJobData, JobOpening, EmploymentType, EducationLevel } from "@/types/jobs";
import { User } from "@/types/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, FileText } from "lucide-react";
import { userService } from "@/services/users";
import { jobService } from "@/services/jobs";
import { sanitizeInput, MAX_LENGTHS } from "@/lib/validation";
import { TagsInput } from "@/components/ui/tags-input";
import { FileUpload } from "@/components/ui/file-upload";
import { toast } from "@/components/ui/use-toast";

interface JobFormProps {
  job?: JobOpening;
  onSubmit: (data: CreateJobData | UpdateJobData) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const departments = [
  "Engineering",
  "Product",
  "Design",
  "Marketing",
  "Sales",
  "Operations",
  "HR",
  "Finance",
  "Legal",
  "Customer Success",
  "Other",
];

const seniorities = [
  "Entry Level",
  "Junior",
  "Mid-Level",
  "Senior",
  "Lead",
  "Manager",
  "Director",
  "VP",
  "C-Level",
];

const sectors = [
  "Technology",
  "Healthcare",
  "Finance",
  "Education",
  "Manufacturing",
  "Retail",
  "Consulting",
  "Media",
  "Energy",
  "Real Estate",
  "Other",
];

const employmentTypes: { value: EmploymentType; label: string }[] = [
  { value: "full-time", label: "Tiempo completo" },
  { value: "part-time", label: "Medio tiempo" },
  { value: "contract", label: "Contrato" },
  { value: "internship", label: "Prácticas" },
];

const educationLevels: { value: EducationLevel; label: string }[] = [
  { value: "high-school", label: "Bachillerato" },
  { value: "associate", label: "Técnico/Tecnólogo" },
  { value: "bachelor", label: "Pregrado" },
  { value: "master", label: "Maestría" },
  { value: "phd", label: "Doctorado" },
  { value: "other", label: "Otro" },
];

// Schema de validación con Zod
const jobSchema = z.object({
  title: z.string().min(1, "El título es requerido").max(MAX_LENGTHS.TITLE, "Título demasiado largo"),
  description: z.string().min(1, "La descripción es requerida").max(MAX_LENGTHS.DESCRIPTION, "Descripción demasiado larga"),
  department: z.string().min(1, "El departamento es requerido"),
  location: z.string().min(1, "La ubicación es requerida").max(MAX_LENGTHS.NAME, "Ubicación demasiado larga"),
  seniority: z.string().min(1, "El nivel de seniority es requerido"),
  sector: z.string().min(1, "El sector es requerido"),
  assigned_consultant_id: z.string().optional(),
  // Nuevos campos
  required_skills: z.array(z.string()).default([]),
  min_years_experience: z.number().min(0, "Los años de experiencia deben ser positivos").max(50, "Valor máximo 50 años").optional(),
  education_level: z.string().optional(),
  employment_type: z.string().optional(),
  salary_min: z.number().min(0, "El salario mínimo debe ser positivo").optional(),
  salary_max: z.number().min(0, "El salario máximo debe ser positivo").optional(),
}).refine((data) => {
  if (data.salary_min && data.salary_max) {
    return data.salary_min <= data.salary_max;
  }
  return true;
}, {
  message: "El salario máximo debe ser mayor o igual al mínimo",
  path: ["salary_max"],
});

type JobFormData = z.infer<typeof jobSchema>;

function JobForm({ job, onSubmit, onCancel, isLoading }: JobFormProps) {
  const [consultants, setConsultants] = useState<User[]>([]);
  const [loadingConsultants, setLoadingConsultants] = useState(false);
  
  // PDF upload state
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfUploading, setPdfUploading] = useState(false);
  const [pdfUploadProgress, setPdfUploadProgress] = useState(0);
  const [pdfUrl, setPdfUrl] = useState<string | null>(job?.pdf_url || null);
  const [pdfName, setPdfName] = useState<string | null>(job?.pdf_name || null);
  
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<JobFormData>({
    resolver: zodResolver(jobSchema),
    defaultValues: {
      title: job?.title || "",
      description: job?.description || "",
      department: job?.department || "",
      location: job?.location || "",
      seniority: job?.seniority || "",
      sector: job?.sector || "",
      assigned_consultant_id: job?.assigned_consultant_id || "",
      required_skills: job?.required_skills || [],
      min_years_experience: job?.min_years_experience,
      education_level: job?.education_level || "",
      employment_type: job?.employment_type || "",
      salary_min: job?.salary_min,
      salary_max: job?.salary_max,
    },
  });

  useEffect(() => {
    loadConsultants();
  }, []);

  const loadConsultants = async () => {
    setLoadingConsultants(true);
    try {
      const users = await userService.getUsers({ role: "consultant" });
      setConsultants(users.filter(u => u.status === "active"));
    } catch (error) {
      console.error("Error loading consultants");
    } finally {
      setLoadingConsultants(false);
    }
  };

  const handlePdfSelect = useCallback((file: File) => {
    setPdfFile(file);
    setPdfUrl(null); // Reset URL when new file selected
  }, []);

  const handlePdfRemove = useCallback(() => {
    setPdfFile(null);
    setPdfUrl(null);
    setPdfName(null);
  }, []);

  const uploadPdf = async (jobId: string): Promise<boolean> => {
    if (!pdfFile) return true;
    
    setPdfUploading(true);
    try {
      const response = await jobService.uploadJobPdf(jobId, pdfFile, (progress) => {
        setPdfUploadProgress(progress);
      });
      setPdfUrl(response.url);
      setPdfName(response.filename);
      return true;
    } catch (error) {
      toast({
        title: "Error al subir PDF",
        description: "No se pudo subir el archivo. Intenta de nuevo.",
        variant: "destructive",
      });
      return false;
    } finally {
      setPdfUploading(false);
    }
  };

  const handleFormSubmit = async (data: JobFormData) => {
    // Sanitizar datos antes de enviar
    const sanitizedData: CreateJobData | UpdateJobData = {
      title: sanitizeInput(data.title),
      description: data.description, // Textarea, validado por React
      department: data.department,
      location: sanitizeInput(data.location),
      seniority: data.seniority,
      sector: data.sector,
      assigned_consultant_id: data.assigned_consultant_id || undefined,
      // Nuevos campos
      required_skills: data.required_skills,
      min_years_experience: data.min_years_experience,
      education_level: data.education_level as EducationLevel || undefined,
      employment_type: data.employment_type as EmploymentType || undefined,
      salary_min: data.salary_min,
      salary_max: data.salary_max,
    };
    
    // If editing and has PDF changes
    if (job) {
      if (pdfFile) {
        const uploaded = await uploadPdf(job.id);
        if (!uploaded) return; // Stop if upload failed
      } else if (!pdfUrl && job.pdf_url) {
        // PDF was removed
        await jobService.removeJobPdf(job.id);
      }
    }
    
    onSubmit(sanitizedData);
  };

  const requiredSkills = watch("required_skills") || [];
  const salaryMin = watch("salary_min");
  const salaryMax = watch("salary_max");

  return (
    <Card>
      <CardHeader>
        <CardTitle>{job ? "Editar Oferta" : "Nueva Oferta"}</CardTitle>
      </CardHeader>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <CardContent className="space-y-6">
          {/* PDF Upload Section */}
          <div className="space-y-2">
            <Label htmlFor="pdf-upload">
              Job Description (PDF)
            </Label>
            <FileUpload
              id="pdf-upload"
              accept=".pdf"
              maxSize={10 * 1024 * 1024} // 10MB
              onFileSelect={handlePdfSelect}
              onFileRemove={handlePdfRemove}
              selectedFile={pdfFile}
              uploadedUrl={pdfUrl}
              uploading={pdfUploading}
              uploadProgress={pdfUploadProgress}
              disabled={isLoading}
            />
            <p className="text-xs text-muted-foreground">
              Sube el Job Description en formato PDF para un análisis más preciso del matching
            </p>
            {pdfUrl && !pdfFile && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <FileText className="h-4 w-4" />
                <a 
                  href={pdfUrl} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  {pdfName || "Ver PDF actual"}
                </a>
              </div>
            )}
          </div>

          {/* Basic Info */}
          <div className="space-y-2">
            <Label htmlFor="title">
              Título <span className="text-red-500">*</span>
            </Label>
            <Input
              id="title"
              placeholder="Ej: Senior Software Engineer"
              maxLength={MAX_LENGTHS.TITLE}
              disabled={isLoading}
              aria-invalid={errors.title ? "true" : "false"}
              aria-describedby={errors.title ? "title-error" : undefined}
              {...register("title")}
            />
            {errors.title && (
              <p id="title-error" className="text-sm text-red-500">{errors.title.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">
              Descripción <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="description"
              placeholder="Describe las responsabilidades, requisitos y beneficios del puesto..."
              rows={5}
              maxLength={MAX_LENGTHS.DESCRIPTION}
              disabled={isLoading}
              aria-invalid={errors.description ? "true" : "false"}
              aria-describedby={errors.description ? "description-error" : undefined}
              {...register("description")}
            />
            {errors.description && (
              <p id="description-error" className="text-sm text-red-500">{errors.description.message}</p>
            )}
          </div>

          {/* Required Skills */}
          <div className="space-y-2">
            <Label htmlFor="skills">
              Skills Requeridas
            </Label>
            <TagsInput
              id="skills"
              tags={requiredSkills}
              onTagsChange={(tags) => setValue("required_skills", tags)}
              placeholder="Ej: React, Python, AWS..."
              maxTags={20}
              disabled={isLoading}
            />
            <p className="text-xs text-muted-foreground">
              {requiredSkills.length}/20 skills añadidas. Presiona Enter para agregar.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Department */}
            <div className="space-y-2">
              <Label htmlFor="department">
                Departamento <span className="text-red-500">*</span>
              </Label>
              <Select
                value={watch("department")}
                onValueChange={(value) => setValue("department", value)}
                disabled={isLoading}
              >
                <SelectTrigger id="department" aria-invalid={errors.department ? "true" : "false"}>
                  <SelectValue placeholder="Selecciona un departamento" />
                </SelectTrigger>
                <SelectContent>
                  {departments.map((dept) => (
                    <SelectItem key={dept} value={dept}>
                      {dept}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.department && (
                <p className="text-sm text-red-500">{errors.department.message}</p>
              )}
            </div>

            {/* Location */}
            <div className="space-y-2">
              <Label htmlFor="location">
                Ubicación <span className="text-red-500">*</span>
              </Label>
              <Input
                id="location"
                placeholder="Ej: Madrid, España o Remoto"
                maxLength={MAX_LENGTHS.NAME}
                disabled={isLoading}
                aria-invalid={errors.location ? "true" : "false"}
                {...register("location")}
              />
              {errors.location && (
                <p className="text-sm text-red-500">{errors.location.message}</p>
              )}
            </div>

            {/* Seniority */}
            <div className="space-y-2">
              <Label htmlFor="seniority">
                Nivel de Seniority <span className="text-red-500">*</span>
              </Label>
              <Select
                value={watch("seniority")}
                onValueChange={(value) => setValue("seniority", value)}
                disabled={isLoading}
              >
                <SelectTrigger id="seniority" aria-invalid={errors.seniority ? "true" : "false"}>
                  <SelectValue placeholder="Selecciona el nivel" />
                </SelectTrigger>
                <SelectContent>
                  {seniorities.map((level) => (
                    <SelectItem key={level} value={level}>
                      {level}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.seniority && (
                <p className="text-sm text-red-500">{errors.seniority.message}</p>
              )}
            </div>

            {/* Sector */}
            <div className="space-y-2">
              <Label htmlFor="sector">
                Sector <span className="text-red-500">*</span>
              </Label>
              <Select
                value={watch("sector")}
                onValueChange={(value) => setValue("sector", value)}
                disabled={isLoading}
              >
                <SelectTrigger id="sector" aria-invalid={errors.sector ? "true" : "false"}>
                  <SelectValue placeholder="Selecciona el sector" />
                </SelectTrigger>
                <SelectContent>
                  {sectors.map((sector) => (
                    <SelectItem key={sector} value={sector}>
                      {sector}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.sector && (
                <p className="text-sm text-red-500">{errors.sector.message}</p>
              )}
            </div>

            {/* Employment Type */}
            <div className="space-y-2">
              <Label htmlFor="employment_type">
                Tipo de Empleo
              </Label>
              <Select
                value={watch("employment_type") || ""}
                onValueChange={(value) => setValue("employment_type", value)}
                disabled={isLoading}
              >
                <SelectTrigger id="employment_type">
                  <SelectValue placeholder="Selecciona el tipo" />
                </SelectTrigger>
                <SelectContent>
                  {employmentTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Years of Experience */}
            <div className="space-y-2">
              <Label htmlFor="min_years_experience">
                Años de Experiencia Mínima
              </Label>
              <Input
                id="min_years_experience"
                type="number"
                min={0}
                max={50}
                placeholder="Ej: 3"
                disabled={isLoading}
                aria-invalid={errors.min_years_experience ? "true" : "false"}
                {...register("min_years_experience", { valueAsNumber: true })}
              />
              {errors.min_years_experience && (
                <p className="text-sm text-red-500">{errors.min_years_experience.message}</p>
              )}
            </div>

            {/* Education Level */}
            <div className="space-y-2">
              <Label htmlFor="education_level">
                Nivel Educativo Requerido
              </Label>
              <Select
                value={watch("education_level") || ""}
                onValueChange={(value) => setValue("education_level", value)}
                disabled={isLoading}
              >
                <SelectTrigger id="education_level">
                  <SelectValue placeholder="Selecciona el nivel" />
                </SelectTrigger>
                <SelectContent>
                  {educationLevels.map((level) => (
                    <SelectItem key={level.value} value={level.value}>
                      {level.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Salary Range */}
            <div className="space-y-2 md:col-span-2">
              <Label>Rango Salarial Anual (USD)</Label>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Input
                    type="number"
                    min={0}
                    placeholder="Mínimo"
                    disabled={isLoading}
                    aria-invalid={errors.salary_min ? "true" : "false"}
                    {...register("salary_min", { valueAsNumber: true })}
                  />
                  {errors.salary_min && (
                    <p className="text-sm text-red-500">{errors.salary_min.message}</p>
                  )}
                </div>
                <div>
                  <Input
                    type="number"
                    min={0}
                    placeholder="Máximo"
                    disabled={isLoading}
                    aria-invalid={errors.salary_max ? "true" : "false"}
                    {...register("salary_max", { valueAsNumber: true })}
                  />
                  {errors.salary_max && (
                    <p className="text-sm text-red-500">{errors.salary_max.message}</p>
                  )}
                </div>
              </div>
              {salaryMin && salaryMax && salaryMin > salaryMax && (
                <p className="text-sm text-red-500">El salario máximo debe ser mayor o igual al mínimo</p>
              )}
            </div>

            {/* Assigned Consultant */}
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="consultant">Consultor Asignado</Label>
              <Select
                value={watch("assigned_consultant_id") || "none"}
                onValueChange={(value) => setValue("assigned_consultant_id", value === "none" ? "" : value)}
                disabled={loadingConsultants || isLoading}
              >
                <SelectTrigger id="consultant">
                  <SelectValue placeholder={loadingConsultants ? "Cargando..." : "Selecciona un consultor"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Sin asignar</SelectItem>
                  {consultants.map((consultant) => (
                    <SelectItem key={consultant.id} value={consultant.id}>
                      {consultant.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
        <CardFooter className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading || pdfUploading}>
            Cancelar
          </Button>
          <Button type="submit" disabled={isLoading || pdfUploading}>
            {isLoading || pdfUploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {pdfUploading ? "Subiendo PDF..." : "Guardando..."}
              </>
            ) : job ? (
              "Actualizar"
            ) : (
              "Crear Oferta"
            )}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}

export default JobForm;
