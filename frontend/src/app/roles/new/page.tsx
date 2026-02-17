"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useClients, useCreateRole } from "@/hooks/use-headhunting";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function NewRolePage() {
  const router = useRouter();
  const { data: clients, isLoading: clientsLoading } = useClients();
  const createRole = useCreateRole();
  
  const [formData, setFormData] = useState({
    role_title: "",
    client_id: "",
    location: "",
    seniority: "",
    status: "open",
    date_opened: new Date().toISOString().split('T')[0],
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createRole.mutateAsync(formData);
      router.push("/roles");
    } catch (error) {
      console.error("Error creating role:", error);
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

      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle className="text-2xl">Nueva Vacante</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
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
                disabled={createRole.isPending || !formData.role_title || !formData.client_id}
              >
                {createRole.isPending ? "Creando..." : "Crear Vacante"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
