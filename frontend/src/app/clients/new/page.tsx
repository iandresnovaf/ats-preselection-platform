"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateClient } from "@/hooks/use-headhunting";
import { ArrowLeft, Building2 } from "lucide-react";
import Link from "next/link";

export default function NewClientPage() {
  const router = useRouter();
  const createClient = useCreateClient();
  
  const [formData, setFormData] = useState({
    client_name: "",
    industry: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Submitting form...", formData);
    try {
      const result = await createClient.mutateAsync(formData);
      console.log("Client created:", result);
      router.push("/roles");
    } catch (error: any) {
      console.error("Error creating client:", error);
      alert("Error al crear cliente: " + (error.response?.data?.detail || error.message));
    }
  };

  const industries = [
    "Tecnología",
    "Banca",
    "Retail",
    "Salud",
    "Manufactura",
    "Energía",
    "Telecomunicaciones",
    "Construcción",
    "Servicios",
    "Otros",
  ];

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
          <div className="flex items-center gap-3">
            <Building2 className="w-6 h-6 text-blue-600" />
            <CardTitle className="text-2xl">Nuevo Cliente</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="client_name">Nombre del Cliente *</Label>
              <Input
                id="client_name"
                placeholder="Ej: TechCorp Colombia"
                value={formData.client_name}
                onChange={(e) =>
                  setFormData({ ...formData, client_name: e.target.value })
                }
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="industry">Industria</Label>
              <select
                id="industry"
                value={formData.industry}
                onChange={(e) =>
                  setFormData({ ...formData, industry: e.target.value })
                }
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option value="">Selecciona una industria...</option>
                {industries.map((industry) => (
                  <option key={industry} value={industry}>
                    {industry}
                  </option>
                ))}
              </select>
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
                disabled={createClient.isPending || !formData.client_name}
              >
                {createClient.isPending ? "Creando..." : "Crear Cliente"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
