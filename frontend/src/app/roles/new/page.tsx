"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useClients, useCreateRole } from "@/hooks/use-headhunting";
import { ArrowLeft, FileText, Edit3, Loader2 } from "lucide-react";
import Link from "next/link";
import { RoleDocumentUploader, RoleDataPreview, type ExtractedRoleData } from "@/components/roles";
import { toast } from "sonner";

export default function NewRolePage() {
  const router = useRouter();
  const { data: clients, isLoading: clientsLoading } = useClients();
  const createRole = useCreateRole();
  
  const [activeTab, setActiveTab] = useState("manual");
  const [extractedData, setExtractedData] = useState<ExtractedRoleData | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  
  // Form data for manual entry
  const [formData, setFormData] = useState({
    role_title: "",
    client_id: "",
    location: "",
    seniority: "",
    status: "open",
    date_opened: new Date().toISOString().split('T')[0],
    description: "",
    requirements: "",
  });

  const handleExtractedData = (data: ExtractedRoleData) => {
    setExtractedData(data);
    // Pre-fill form data with extracted information
    setFormData(prev => ({
      ...prev,
      role_title: data.role_title || prev.role_title,
      location: data.hierarchy?.location || data.conditions?.location || prev.location,
      description: data.description || prev.description,
      requirements: [
        data.requirements?.education,
        data.requirements?.experience_years,
        data.requirements?.experience_details,
      ].filter(Boolean).join("\n\n") || prev.requirements,
    }));
  };

  const handleConfirmExtractedData = async (data: Partial<ExtractedRoleData>) => {
    if (!formData.client_id) {
      toast.error("Por favor seleccione un cliente");
      setActiveTab("manual");
      return;
    }

    setIsCreating(true);
    
    try {
      // Build the description from extracted data
      const description = [
        data.objective,
        "\n## Responsabilidades",
        Object.entries(data.responsibilities || {})
          .map(([category, items]) => 
            `\n**${category}:**\n${items.map(item => `- ${item}`).join("\n")}`
          )
          .join("\n"),
        data.hierarchy?.reports_to ? `\n**Reporta a:** ${data.hierarchy.reports_to}` : "",
        data.hierarchy?.direct_reports ? `**Personas a cargo:** ${data.hierarchy.direct_reports}` : "",
        data.hierarchy?.work_mode ? `**Modalidad:** ${data.hierarchy.work_mode}` : "",
      ].filter(Boolean).join("\n");

      // Build requirements
      const requirements = [
        data.requirements?.education,
        data.requirements?.experience_years ? `Experiencia: ${data.requirements.experience_years}` : "",
        data.requirements?.experience_details,
        data.disc_profile ? `Perfil DISC: ${data.disc_profile}` : "",
        data.tools?.length ? `Herramientas: ${data.tools.join(", ")}` : "",
        data.skills?.technical?.length ? `Skills técnicos: ${data.skills.technical.join(", ")}` : "",
        data.skills?.soft?.length ? `Competencias: ${data.skills.soft.join(", ")}` : "",
      ].filter(Boolean).join("\n\n");

      const roleData = {
        role_title: data.role_title || extractedData?.role_title || "",
        client_id: formData.client_id,
        location: data.hierarchy?.location || data.conditions?.location || formData.location,
        seniority: inferSeniority(data.hierarchy?.level || ""),
        status: "open",
        date_opened: formData.date_opened,
        description: description || formData.description,
        requirements: requirements || formData.requirements,
      };

      await createRole.mutateAsync(roleData);
      toast.success("Vacante creada exitosamente");
      router.push("/roles");
    } catch (error) {
      console.error("Error creating role:", error);
      toast.error("Error al crear la vacante");
    } finally {
      setIsCreating(false);
    }
  };

  const inferSeniority = (level: string): string => {
    const levelLower = level.toLowerCase();
    if (levelLower.includes("director") || levelLower.includes("c-level") || levelLower.includes("ceo")) {
      return "director";
    } else if (levelLower.includes("manager") || levelLower.includes("gerente")) {
      return "manager";
    } else if (levelLower.includes("senior") || levelLower.includes("avanzado")) {
      return "senior";
    } else if (levelLower.includes("junior") || levelLower.includes("básico")) {
      return "junior";
    } else if (levelLower.includes("semi") || levelLower.includes("medio")) {
      return "semi_senior";
    }
    return "";
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);
    
    try {
      await createRole.mutateAsync(formData);
      toast.success("Vacante creada exitosamente");
      router.push("/roles");
    } catch (error) {
      console.error("Error creating role:", error);
      toast.error("Error al crear la vacante");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-6">
        <Link
          href="/roles"
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Volver a vacantes
        </Link>
      </div>

      <Card className="max-w-4xl mx-auto">
        <CardHeader>
          <CardTitle className="text-2xl">Nueva Vacante</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="manual" className="gap-2">
                <Edit3 className="w-4 h-4" />
                Crear Manualmente
              </TabsTrigger>
              <TabsTrigger value="document" className="gap-2">
                <FileText className="w-4 h-4" />
                Subir Documento
              </TabsTrigger>
            </TabsList>

            {/* Manual Entry Tab */}
            <TabsContent value="manual">
              <form onSubmit={handleManualSubmit} className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="role_title">Título del Cargo *</Label>
                  <Input
                    id="role_title"
                    placeholder="Ej: Director de Operaciones"
                    value={formData.role_title}
                    onChange={(e) =>
                      setFormData({ ...formData, role_title: e.target.value })
                    }
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="client_id">Cliente *</Label>
                  <Select
                    value={formData.client_id}
                    onValueChange={(value) =>
                      setFormData({ ...formData, client_id: value })
                    }
                    required
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Selecciona un cliente..." />
                    </SelectTrigger>
                    <SelectContent>
                      {clientsLoading ? (
                        <SelectItem value="loading" disabled>
                          Cargando...
                        </SelectItem>
                      ) : (
                        clients?.items?.map((client: any) => (
                          <SelectItem key={client.client_id} value={client.client_id}>
                            {client.client_name}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="location">Ubicación</Label>
                    <Input
                      id="location"
                      placeholder="Ej: Bogotá"
                      value={formData.location}
                      onChange={(e) =>
                        setFormData({ ...formData, location: e.target.value })
                      }
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="seniority">Nivel de Seniority</Label>
                    <Select
                      value={formData.seniority}
                      onValueChange={(value) =>
                        setFormData({ ...formData, seniority: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="junior">Junior</SelectItem>
                        <SelectItem value="semi_senior">Semi-Senior</SelectItem>
                        <SelectItem value="senior">Senior</SelectItem>
                        <SelectItem value="manager">Manager</SelectItem>
                        <SelectItem value="director">Director</SelectItem>
                        <SelectItem value="c_level">C-Level</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">Descripción del Cargo</Label>
                  <Textarea
                    id="description"
                    placeholder="Descripción detallada del cargo..."
                    value={formData.description}
                    onChange={(e) =>
                      setFormData({ ...formData, description: e.target.value })
                    }
                    className="min-h-[150px]"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="requirements">Requisitos</Label>
                  <Textarea
                    id="requirements"
                    placeholder="Requisitos del cargo..."
                    value={formData.requirements}
                    onChange={(e) =>
                      setFormData({ ...formData, requirements: e.target.value })
                    }
                    className="min-h-[150px]"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="status">Estado</Label>
                    <Select
                      value={formData.status}
                      onValueChange={(value) =>
                        setFormData({ ...formData, status: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="open">Abierta</SelectItem>
                        <SelectItem value="hold">En Pausa</SelectItem>
                        <SelectItem value="closed">Cerrada</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="date_opened">Fecha de Apertura</Label>
                    <Input
                      id="date_opened"
                      type="date"
                      value={formData.date_opened}
                      onChange={(e) =>
                        setFormData({ ...formData, date_opened: e.target.value })
                      }
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-4 pt-4">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => router.push("/roles")}
                  >
                    Cancelar
                  </Button>
                  <Button
                    type="submit"
                    disabled={isCreating || !formData.role_title || !formData.client_id}
                  >
                    {isCreating ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Creando...
                      </>
                    ) : (
                      "Crear Vacante"
                    )}
                  </Button>
                </div>
              </form>
            </TabsContent>

            {/* Document Upload Tab */}
            <TabsContent value="document" className="space-y-6">
              {!extractedData ? (
                <>
                  <RoleDocumentUploader onExtracted={handleExtractedData} />
                  
                  {/* Show client selection before upload for document mode */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Cliente para la Vacante *</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <Select
                        value={formData.client_id}
                        onValueChange={(value) =>
                          setFormData({ ...formData, client_id: value })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Selecciona un cliente..." />
                        </SelectTrigger>
                        <SelectContent>
                          {clientsLoading ? (
                            <SelectItem value="loading" disabled>
                              Cargando...
                            </SelectItem>
                          ) : (
                            clients?.items?.map((client: any) => (
                              <SelectItem key={client.client_id} value={client.client_id}>
                                {client.client_name}
                              </SelectItem>
                            ))
                          )}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-gray-500 mt-2">
                        Seleccione el cliente antes de subir el documento
                      </p>
                    </CardContent>
                  </Card>
                </>
              ) : (
                <RoleDataPreview
                  data={extractedData}
                  onConfirm={handleConfirmExtractedData}
                  onCancel={() => setExtractedData(null)}
                />
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}