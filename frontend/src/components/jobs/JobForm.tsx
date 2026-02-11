import { useState, useEffect } from "react";
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

export function JobForm({ job, onSubmit, onCancel, isLoading }: JobFormProps) {
  const [consultants, setConsultants] = useState<User[]>([]);
  const [loadingConsultants, setLoadingConsultants] = useState(false);
  const [formData, setFormData] = useState<CreateJobData>({
    title: job?.title || "",
    description: job?.description || "",
    department: job?.department || "",
    location: job?.location || "",
    seniority: job?.seniority || "",
    sector: job?.sector || "",
    assigned_consultant_id: job?.assigned_consultant_id || "",
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
      console.error("Error loading consultants:", error);
    } finally {
      setLoadingConsultants(false);
    }
  };

  const handleChange = (field: keyof CreateJobData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{job ? "Editar Oferta" : "Nueva Oferta"}</CardTitle>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">
              Título <span className="text-red-500">*</span>
            </Label>
            <Input
              id="title"
              value={formData.title}
              onChange={(e) => handleChange("title", e.target.value)}
              placeholder="Ej: Senior Software Engineer"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">
              Descripción <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => handleChange("description", e.target.value)}
              placeholder="Describe las responsabilidades, requisitos y beneficios del puesto..."
              rows={5}
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="department">
                Departamento <span className="text-red-500">*</span>
              </Label>
              <Select
                value={formData.department}
                onValueChange={(value) => handleChange("department", value)}
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
            </div>

            <div className="space-y-2">
              <Label htmlFor="location">
                Ubicación <span className="text-red-500">*</span>
              </Label>
              <Input
                id="location"
                value={formData.location}
                onChange={(e) => handleChange("location", e.target.value)}
                placeholder="Ej: Madrid, España o Remoto"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="seniority">
                Nivel de Seniority <span className="text-red-500">*</span>
              </Label>
              <Select
                value={formData.seniority}
                onValueChange={(value) => handleChange("seniority", value)}
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
            </div>

            <div className="space-y-2">
              <Label htmlFor="sector">
                Sector <span className="text-red-500">*</span>
              </Label>
              <Select
                value={formData.sector}
                onValueChange={(value) => handleChange("sector", value)}
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
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="consultant">Consultor Asignado</Label>
              <Select
                value={formData.assigned_consultant_id || "none"}
                onValueChange={(value) => handleChange("assigned_consultant_id", value === "none" ? "" : value)}
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
