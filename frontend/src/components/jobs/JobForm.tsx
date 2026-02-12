import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { CreateJobData, UpdateJobData, JobOpening } from "@/types/jobs";
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
import { Loader2 } from "lucide-react";
import { userService } from "@/services/users";
import { sanitizeInput, MAX_LENGTHS } from "@/lib/validation";

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

// Schema de validación con Zod
const jobSchema = z.object({
  title: z.string().min(1, "El título es requerido").max(MAX_LENGTHS.TITLE, "Título demasiado largo"),
  description: z.string().min(1, "La descripción es requerida").max(MAX_LENGTHS.DESCRIPTION, "Descripción demasiado larga"),
  department: z.string().min(1, "El departamento es requerido"),
  location: z.string().min(1, "La ubicación es requerida").max(MAX_LENGTHS.NAME, "Ubicación demasiado larga"),
  seniority: z.string().min(1, "El nivel de seniority es requerido"),
  sector: z.string().min(1, "El sector es requerido"),
  assigned_consultant_id: z.string().optional(),
});

type JobFormData = z.infer<typeof jobSchema>;

function JobForm({ job, onSubmit, onCancel, isLoading }: JobFormProps) {
  const [consultants, setConsultants] = useState<User[]>([]);
  const [loadingConsultants, setLoadingConsultants] = useState(false);
  
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

  const handleFormSubmit = (data: JobFormData) => {
    // Sanitizar datos antes de enviar
    const sanitizedData = {
      title: sanitizeInput(data.title),
      description: data.description, // Textarea, validado por React
      department: data.department,
      location: sanitizeInput(data.location),
      seniority: data.seniority,
      sector: data.sector,
      assigned_consultant_id: data.assigned_consultant_id || undefined,
    };
    
    onSubmit(sanitizedData);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{job ? "Editar Oferta" : "Nueva Oferta"}</CardTitle>
      </CardHeader>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">
              Título <span className="text-red-500">*</span>
            </Label>
            <Input
              id="title"
              placeholder="Ej: Senior Software Engineer"
              maxLength={MAX_LENGTHS.TITLE}
              {...register("title")}
            />
            {errors.title && (
              <p className="text-sm text-red-500">{errors.title.message}</p>
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
              {...register("description")}
            />
            {errors.description && (
              <p className="text-sm text-red-500">{errors.description.message}</p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="department">
                Departamento <span className="text-red-500">*</span>
              </Label>
              <Select
                value={watch("department")}
                onValueChange={(value) => setValue("department", value)}
              >
                <SelectTrigger>
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

            <div className="space-y-2">
              <Label htmlFor="location">
                Ubicación <span className="text-red-500">*</span>
              </Label>
              <Input
                id="location"
                placeholder="Ej: Madrid, España o Remoto"
                maxLength={MAX_LENGTHS.NAME}
                {...register("location")}
              />
              {errors.location && (
                <p className="text-sm text-red-500">{errors.location.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="seniority">
                Nivel de Seniority <span className="text-red-500">*</span>
              </Label>
              <Select
                value={watch("seniority")}
                onValueChange={(value) => setValue("seniority", value)}
              >
                <SelectTrigger>
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

            <div className="space-y-2">
              <Label htmlFor="sector">
                Sector <span className="text-red-500">*</span>
              </Label>
              <Select
                value={watch("sector")}
                onValueChange={(value) => setValue("sector", value)}
              >
                <SelectTrigger>
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

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="consultant">Consultor Asignado</Label>
              <Select
                value={watch("assigned_consultant_id") || "none"}
                onValueChange={(value) => setValue("assigned_consultant_id", value === "none" ? "" : value)}
                disabled={loadingConsultants}
              >
                <SelectTrigger>
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
          <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>
            Cancelar
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Guardando...
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
