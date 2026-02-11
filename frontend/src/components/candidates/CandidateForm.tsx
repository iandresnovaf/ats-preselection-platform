import { useState, useEffect } from "react";
import { CreateCandidateData, Candidate } from "@/types/candidates";
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

export function CandidateForm({ candidate, jobId, onSubmit, onCancel, isLoading }: CandidateFormProps) {
  const [jobs, setJobs] = useState<JobOpening[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [formData, setFormData] = useState<CreateCandidateData>({
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
      console.error("Error loading jobs:", error);
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleChange = (field: keyof CreateCandidateData, value: string | number | undefined) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{candidate ? "Editar Candidato" : "Nuevo Candidato"}</CardTitle>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="first_name">
                Nombre <span className="text-red-500">*</span>
              </Label>
              <Input
                id="first_name"
                value={formData.first_name}
                onChange={(e) => handleChange("first_name", e.target.value)}
                placeholder="Nombre"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="last_name">
                Apellido <span className="text-red-500">*</span>
              </Label>
              <Input
                id="last_name"
                value={formData.last_name}
                onChange={(e) => handleChange("last_name", e.target.value)}
                placeholder="Apellido"
                required
              />
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
                value={formData.email}
                onChange={(e) => handleChange("email", e.target.value)}
                placeholder="correo@ejemplo.com"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Teléfono</Label>
              <Input
                id="phone"
                value={formData.phone || ""}
                onChange={(e) => handleChange("phone", e.target.value)}
                placeholder="+34 123 456 789"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="job">
                Oferta <span className="text-red-500">*</span>
              </Label>
              <Select
                value={formData.job_opening_id}
                onValueChange={(value) => handleChange("job_opening_id", value)}
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
            </div>

            <div className="space-y-2">
              <Label htmlFor="source">Fuente</Label>
              <Select
                value={formData.source}
                onValueChange={(value) => handleChange("source", value)}
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
                value={formData.linkedin_url || ""}
                onChange={(e) => handleChange("linkedin_url", e.target.value)}
                placeholder="https://linkedin.com/in/..."
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="portfolio_url">Portfolio</Label>
              <Input
                id="portfolio_url"
                value={formData.portfolio_url || ""}
                onChange={(e) => handleChange("portfolio_url", e.target.value)}
                placeholder="https://..."
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="current_company">Empresa Actual</Label>
              <Input
                id="current_company"
                value={formData.current_company || ""}
                onChange={(e) => handleChange("current_company", e.target.value)}
                placeholder="Nombre de la empresa"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="current_position">Posición Actual</Label>
              <Input
                id="current_position"
                value={formData.current_position || ""}
                onChange={(e) => handleChange("current_position", e.target.value)}
                placeholder="Ej: Software Engineer"
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
              value={formData.years_experience || ""}
              onChange={(e) => handleChange("years_experience", e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="0"
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
