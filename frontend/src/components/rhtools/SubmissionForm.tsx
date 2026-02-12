"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, AlertCircle } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { CreateSubmissionData, Submission, Client, PipelineTemplate } from "@/types/rhtools";
import { Candidate } from "@/types/candidates";
import { JobOpening } from "@/types/jobs";
import { User } from "@/types/auth";
import { submissionsService } from "@/services/rhtools/submissions";
import { clientsService } from "@/services/rhtools/clients";
import { pipelineService } from "@/services/rhtools/pipeline";
import { candidateService } from "@/services/candidates";
import { jobsService } from "@/services/jobs";
import { usersService } from "@/services/users";

interface SubmissionFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (submission: Submission) => void;
  initialData?: Partial<CreateSubmissionData>;
}

const priorityOptions = [
  { value: "low", label: "Baja" },
  { value: "medium", label: "Media" },
  { value: "high", label: "Alta" },
  { value: "urgent", label: "Urgente" },
];

export function SubmissionForm({ isOpen, onClose, onSuccess, initialData }: SubmissionFormProps) {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data lists
  const [clients, setClients] = useState<Client[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [jobs, setJobs] = useState<JobOpening[]>([]);
  const [consultants, setConsultants] = useState<User[]>([]);
  const [templates, setTemplates] = useState<PipelineTemplate[]>([]);

  // Form state
  const [formData, setFormData] = useState<CreateSubmissionData>({
    client_id: initialData?.client_id || "",
    job_id: initialData?.job_id || "",
    candidate_id: initialData?.candidate_id || "",
    consultant_id: initialData?.consultant_id || "",
    template_id: initialData?.template_id || "",
    priority: initialData?.priority || "medium",
    salary_expectation: initialData?.salary_expectation,
    proposed_salary: initialData?.proposed_salary,
    currency: initialData?.currency || "EUR",
    notes: initialData?.notes || "",
    internal_notes: initialData?.internal_notes || "",
  });

  // Fetch data on mount
  useEffect(() => {
    if (isOpen) {
      fetchData();
    }
  }, [isOpen]);

  const fetchData = async () => {
    setIsFetching(true);
    setError(null);

    try {
      const [clientsRes, candidatesRes, jobsRes, consultantsRes, templatesRes] = await Promise.all([
        clientsService.getClients({ status: "active" }),
        candidateService.getCandidates(),
        jobsService.getJobs({ status: "active" }),
        usersService.getUsers(),
        pipelineService.getTemplates(),
      ]);

      setClients(clientsRes);
      setCandidates(candidatesRes);
      setJobs(jobsRes);
      setConsultants(consultantsRes.filter(u => u.role === "consultant" || u.role === "super_admin"));
      setTemplates(templatesRes.filter(t => t.is_active));
    } catch (err) {
      setError("Error al cargar los datos. Por favor, intenta de nuevo.");
    } finally {
      setIsFetching(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // Validación
      if (!formData.client_id || !formData.candidate_id || !formData.consultant_id || !formData.template_id) {
        throw new Error("Por favor completa todos los campos obligatorios");
      }

      const submission = await submissionsService.createSubmission(formData);
      
      toast({
        title: "Éxito",
        description: "Submission creada correctamente",
      });

      onSuccess?.(submission);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Error al crear la submission";
      setError(message);
      toast({
        title: "Error",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const updateFormData = (field: keyof CreateSubmissionData, value: string | number | undefined) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nueva Submission</DialogTitle>
          <DialogDescription>
            Crea una nueva submission para un candidato en un proceso de selección.
          </DialogDescription>
        </DialogHeader>

        {isFetching ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="grid grid-cols-2 gap-4">
              {/* Cliente */}
              <div className="space-y-2">
                <Label htmlFor="client">Cliente *</Label>
                <Select
                  value={formData.client_id}
                  onValueChange={(value) => updateFormData("client_id", value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar cliente" />
                  </SelectTrigger>
                  <SelectContent>
                    {clients.map((client) => (
                      <SelectItem key={client.id} value={client.id}>
                        {client.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Job */}
              <div className="space-y-2">
                <Label htmlFor="job">Job/Posición</Label>
                <Select
                  value={formData.job_id || "none"}
                  onValueChange={(value) => updateFormData("job_id", value === "none" ? undefined : value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar job (opcional)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Sin job específico</SelectItem>
                    {jobs.map((job) => (
                      <SelectItem key={job.id} value={job.id}>
                        {job.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Candidato */}
              <div className="space-y-2">
                <Label htmlFor="candidate">Candidato *</Label>
                <Select
                  value={formData.candidate_id}
                  onValueChange={(value) => updateFormData("candidate_id", value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar candidato" />
                  </SelectTrigger>
                  <SelectContent>
                    {candidates.map((candidate) => (
                      <SelectItem key={candidate.id} value={candidate.id}>
                        {candidate.first_name} {candidate.last_name} ({candidate.email})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Consultor */}
              <div className="space-y-2">
                <Label htmlFor="consultant">Consultor *</Label>
                <Select
                  value={formData.consultant_id}
                  onValueChange={(value) => updateFormData("consultant_id", value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Asignar consultor" />
                  </SelectTrigger>
                  <SelectContent>
                    {consultants.map((consultant) => (
                      <SelectItem key={consultant.id} value={consultant.id}>
                        {consultant.full_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Pipeline Template */}
              <div className="space-y-2 col-span-2">
                <Label htmlFor="template">Pipeline Template *</Label>
                <Select
                  value={formData.template_id}
                  onValueChange={(value) => updateFormData("template_id", value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar pipeline" />
                  </SelectTrigger>
                  <SelectContent>
                    {templates.map((template) => (
                      <SelectItem key={template.id} value={template.id}>
                        {template.name} {template.is_default && "(Default)"}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Prioridad */}
              <div className="space-y-2">
                <Label htmlFor="priority">Prioridad</Label>
                <Select
                  value={formData.priority}
                  onValueChange={(value: any) => updateFormData("priority", value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {priorityOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Moneda */}
              <div className="space-y-2">
                <Label htmlFor="currency">Moneda</Label>
                <Select
                  value={formData.currency}
                  onValueChange={(value) => updateFormData("currency", value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EUR">EUR (€)</SelectItem>
                    <SelectItem value="USD">USD ($)</SelectItem>
                    <SelectItem value="GBP">GBP (£)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Salario esperado */}
              <div className="space-y-2">
                <Label htmlFor="salary_expectation">Expectativa salarial</Label>
                <Input
                  id="salary_expectation"
                  type="number"
                  placeholder="Ej: 50000"
                  value={formData.salary_expectation || ""}
                  onChange={(e) => updateFormData("salary_expectation", e.target.value ? parseInt(e.target.value) : undefined)}
                />
              </div>

              {/* Salario propuesto */}
              <div className="space-y-2">
                <Label htmlFor="proposed_salary">Salario propuesto</Label>
                <Input
                  id="proposed_salary"
                  type="number"
                  placeholder="Ej: 55000"
                  value={formData.proposed_salary || ""}
                  onChange={(e) => updateFormData("proposed_salary", e.target.value ? parseInt(e.target.value) : undefined)}
                />
              </div>
            </div>

            {/* Notas */}
            <div className="space-y-2">
              <Label htmlFor="notes">Notas (visibles para el cliente)</Label>
              <Textarea
                id="notes"
                placeholder="Información adicional sobre el candidato..."
                value={formData.notes}
                onChange={(e) => updateFormData("notes", e.target.value)}
                rows={3}
              />
            </div>

            {/* Notas internas */}
            <div className="space-y-2">
              <Label htmlFor="internal_notes">Notas internas</Label>
              <Textarea
                id="internal_notes"
                placeholder="Notas solo para el equipo interno..."
                value={formData.internal_notes}
                onChange={(e) => updateFormData("internal_notes", e.target.value)}
                rows={3}
              />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creando...
                  </>
                ) : (
                  "Crear Submission"
                )}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
