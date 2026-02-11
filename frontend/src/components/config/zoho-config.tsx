"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { configApi } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { Loader2, Save, TestTube } from "lucide-react";

const zohoSchema = z.object({
  client_id: z.string().min(1, "Client ID requerido"),
  client_secret: z.string().min(1, "Client Secret requerido"),
  refresh_token: z.string().min(1, "Refresh Token requerido"),
  redirect_uri: z.string().url("URL válida requerida").default("http://localhost:8000/api/v1/zoho/callback"),
  job_id_field: z.string().default("Job_Opening_ID"),
  candidate_id_field: z.string().default("Candidate_ID"),
  stage_field: z.string().default("Stage"),
});

type ZohoFormData = z.infer<typeof zohoSchema>;

export function ZohoConfigForm() {
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [existingConfig, setExistingConfig] = useState<ZohoFormData | null>(null);
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    reset,
  } = useForm<ZohoFormData>({
    resolver: zodResolver(zohoSchema),
    defaultValues: {
      redirect_uri: "http://localhost:8000/api/v1/zoho/callback",
      job_id_field: "Job_Opening_ID",
      candidate_id_field: "Candidate_ID",
      stage_field: "Stage",
    },
  });

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const config = await configApi.getZohoConfig();
      if (config) {
        setExistingConfig(config);
        reset(config);
      }
    } catch (error) {
      console.error("Error loading config:", error);
    }
  };

  const onSubmit = async (data: ZohoFormData) => {
    try {
      setLoading(true);
      await configApi.saveZohoConfig(data);
      toast({
        title: "Éxito",
        description: "Configuración de Zoho guardada correctamente.",
      });
      setExistingConfig(data);
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudo guardar la configuración.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    try {
      setTesting(true);
      const result = await configApi.testZohoConnection();
      toast({
        title: "Conexión exitosa",
        description: result.message,
      });
    } catch (error: any) {
      toast({
        title: "Error de conexión",
        description: error.response?.data?.detail || "No se pudo conectar con Zoho",
        variant: "destructive",
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <Label htmlFor="client_id">Client ID *</Label>
          <Input
            id="client_id"
            placeholder="1000.xxxxx"
            {...register("client_id")}
          />
          {errors.client_id && (
            <p className="text-sm text-red-500">{errors.client_id.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="client_secret">Client Secret *</Label>
          <Input
            id="client_secret"
            type="password"
            placeholder="Client Secret de Zoho"
            {...register("client_secret")}
          />
          {errors.client_secret && (
            <p className="text-sm text-red-500">{errors.client_secret.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="refresh_token">Refresh Token *</Label>
          <Input
            id="refresh_token"
            type="password"
            placeholder="Refresh Token de OAuth"
            {...register("refresh_token")}
          />
          {errors.refresh_token && (
            <p className="text-sm text-red-500">{errors.refresh_token.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="redirect_uri">Redirect URI</Label>
          <Input
            id="redirect_uri"
            {...register("redirect_uri")}
          />
          {errors.redirect_uri && (
            <p className="text-sm text-red-500">{errors.redirect_uri.message}</p>
          )}
        </div>
      </div>

      <div className="border-t pt-6">
        <h4 className="text-sm font-medium mb-4">Mapeo de Campos</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="job_id_field">Campo Job ID</Label>
            <Input
              id="job_id_field"
              {...register("job_id_field")}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="candidate_id_field">Campo Candidate ID</Label>
            <Input
              id="candidate_id_field"
              {...register("candidate_id_field")}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="stage_field">Campo Stage</Label>
            <Input
              id="stage_field"
              {...register("stage_field")}
            />
          </div>
        </div>
      </div>

      <div className="flex gap-4">
        <Button type="submit" disabled={loading || !isDirty}>
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {!loading && <Save className="mr-2 h-4 w-4" />}
          Guardar Configuración
        </Button>

        <Button 
          type="button" 
          variant="outline" 
          onClick={handleTest}
          disabled={testing || !existingConfig}
        >
          {testing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {!testing && <TestTube className="mr-2 h-4 w-4" />}
          Probar Conexión
        </Button>
      </div>

      {existingConfig && (
        <Card className="bg-muted">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">
              ✅ Configuración guardada. Usa "Probar Conexión" para validar.
            </p>
          </CardContent>
        </Card>
      )}
    </form>
  );
}
