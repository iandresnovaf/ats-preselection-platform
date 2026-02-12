import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { CreateCandidateData, Candidate, CandidateSource } from "@/types/candidates";
import { JobOpening } from "@/types/jobs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import { jobService } from "@/services/jobs";
import { 
  isValidEmail, 
  isValidPhone, 
  isValidUrl, 
  sanitizeName, 
  sanitizePhone,
  MAX_LENGTHS 
} from "@/lib/validation";

interface CandidateFormProps {
  candidate?: Candidate;
  jobId?: string;
  onSubmit: (data: CreateCandidateData) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const sources = [
  { value: "manual", label: "Manual" },
  { value: "email", label: "Email" },
  { value: "zoho", label: "Zoho" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "referral", label: "Referido" },
  { value: "other", label: "Otro" },
];

// Schema de validación con Zod
const candidateSchema = z.object({
  first_name: z.string().min(1, "El nombre es requerido").max(MAX_LENGTHS.NAME, "Nombre demasiado largo"),
  last_name: z.string().min(1, "El apellido es requerido").max(MAX_LENGTHS.NAME, "Apellido demasiado largo"),
  email: z.string().min(1, "El email es requerido").refine((val) => isValidEmail(val), {
    message: "Email inválido",
  }),
  phone: z.string().optional().refine((val) => !val || isValidPhone(val), {
    message: "Teléfono inválido",
  }),
  job_opening_id: z.string().min(1, "Debes seleccionar una oferta"),
  source: z.string(),
  linkedin_url: z.string().optional().refine((val) => !val || isValidUrl(val), {
    message: "URL de LinkedIn inválida",
  }),
  portfolio_url: z.string().optional().refine((val) => !val || isValidUrl(val), {
    message: "URL de portfolio inválida",
  }),
  years_experience: z.number().min(0).max(50).optional(),
  current_company: z.string().max(MAX_LENGTHS.NAME, "Nombre de empresa demasiado largo").optional(),
  current_position: z.string().max(MAX_LENGTHS.NAME, "Posición demasiado larga").optional(),
  notes: z.string().max(MAX_LENGTHS.NOTES, "Notas demasiado largas").optional(),
});

type CandidateFormData = z.infer<typeof candidateSchema>;

export function CandidateForm({ candidate, jobId, onSubmit, onCancel, isLoading }: CandidateFormProps) {
  const [jobs, setJobs] = useState<JobOpening[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<CandidateFormData>({
    resolver: zodResolver(candidateSchema),
    defaultValues: {
      first_name: candidate?.first_name || "",
      last_name: candidate?.last_name || "",
      email: candidate?.email || "",
      phone: candidate?.phone || "",
      job_opening_id: candidate?.job_opening_id || jobId || "",
      source: candidate?.source || "manual",
      linkedin_url: candidate?.linkedin_url || "",
      portfolio_url: candidate?.portfolio_url || "",
      years_experience: candidate?.years_experience || undefined,
      current_company: candidate?.current_company || "",
      current_position: candidate?.current_position || "",
      notes: candidate?.notes || "",
    },
  });

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    setLoadingJobs(true);
    try {
      const activeJobs = await jobService.getJobs({ status: "active" });
      setJobs(activeJobs);
    } catch (error) {
      console.error("Error loading jobs");
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleFormSubmit = (data: CandidateFormData) => {
    // Sanitizar datos antes de enviar
    const sanitizedData: CreateCandidateData = {
      first_name: sanitizeName(data.first_name),
      last_name: sanitizeName(data.last_name),
      email: data.email.toLowerCase().trim(),
      phone: data.phone ? sanitizePhone(data.phone) : undefined,
      job_opening_id: data.job_opening_id,
      source: (data.source as CandidateSource) || 'manual',
      linkedin_url: data.linkedin_url || undefined,
      portfolio_url: data.portfolio_url || undefined,
      years_experience: data.years_experience,
      current_company: data.current_company || undefined,
      current_position: data.current_position || undefined,
      notes: data.notes || undefined,
    };
    
    onSubmit(sanitizedData);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{candidate ? "Editar Candidato" : "Nuevo Candidato"}</CardTitle>
      </CardHeader>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="first_name">
                Nombre <span className="text-red-500">*</span>
              </Label>
              <Input
                id="first_name"
                placeholder="Nombre"
                maxLength={MAX_LENGTHS.NAME}
                {...register("first_name")}
              />
              {errors.first_name && (
                <p className="text-sm text-red-500">{errors.first_name.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="last_name">
                Apellido <span className="text-red-500">*</span>
              </Label>
              <Input
                id="last_name"
                placeholder="Apellido"
                maxLength={MAX_LENGTHS.NAME}
                {...register("last_name")}
              />
              {errors.last_name && (
                <p className="text-sm text-red-500">{errors.last_name.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="email">
                Email <span className="text-red-500">*</span>
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="correo@ejemplo.com"
                maxLength={MAX_LENGTHS.EMAIL}
                {...register("email")}
              />
              {errors.email && (
                <p className="text-sm text-red-500">{errors.email.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Teléfono</Label>
              <Input
                id="phone"
                placeholder="+34 123 456 789"
                maxLength={MAX_LENGTHS.PHONE}
                {...register("phone")}
              />
              {errors.phone && (
                <p className="text-sm text-red-500">{errors.phone.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="job">
                Oferta <span className="text-red-500">*</span>
              </Label>
              <Select
                value={watch("job_opening_id")}
                onValueChange={(value) => setValue("job_opening_id", value)}
                disabled={loadingJobs || !!jobId}
              >
                <SelectTrigger>
                  <SelectValue placeholder={loadingJobs ? "Cargando..." : "Selecciona una oferta"} />
                </SelectTrigger>
                <SelectContent>
                  {jobs.map((job) => (
                    <SelectItem key={job.id} value={job.id}>
                      {job.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.job_opening_id && (
                <p className="text-sm text-red-500">{errors.job_opening_id.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="source">Fuente</Label>
              <Select
                value={watch("source")}
                onValueChange={(value) => setValue("source", value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona la fuente" />
                </SelectTrigger>
                <SelectContent>
                  {sources.map((source) => (
                    <SelectItem key={source.value} value={source.value}>
                      {source.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="linkedin_url">LinkedIn</Label>
              <Input
                id="linkedin_url"
                placeholder="https://linkedin.com/in/..."
                maxLength={MAX_LENGTHS.URL}
                {...register("linkedin_url")}
              />
              {errors.linkedin_url && (
                <p className="text-sm text-red-500">{errors.linkedin_url.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="portfolio_url">Portfolio</Label>
              <Input
                id="portfolio_url"
                placeholder="https://..."
                maxLength={MAX_LENGTHS.URL}
                {...register("portfolio_url")}
              />
              {errors.portfolio_url && (
                <p className="text-sm text-red-500">{errors.portfolio_url.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="current_company">Empresa Actual</Label>
              <Input
                id="current_company"
                placeholder="Nombre de la empresa"
                maxLength={MAX_LENGTHS.NAME}
                {...register("current_company")}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="current_position">Posición Actual</Label>
              <Input
                id="current_position"
                placeholder="Ej: Software Engineer"
                maxLength={MAX_LENGTHS.NAME}
                {...register("current_position")}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="years_experience">Años de Experiencia</Label>
            <Input
              id="years_experience"
              type="number"
              min={0}
              max={50}
              placeholder="0"
              {...register("years_experience", { valueAsNumber: true })}
            />
          </div>
        </CardContent>
        <CardFooter className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>
            Cancelar
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Guardando...
              </>
            ) : candidate ? (
              "Actualizar"
            ) : (
              "Crear Candidato"
            )}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}

export default CandidateForm;
