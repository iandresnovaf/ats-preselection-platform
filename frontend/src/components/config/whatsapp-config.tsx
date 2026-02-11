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

const whatsappSchema = z.object({
  access_token: z.string().min(1, "Token de acceso requerido"),
  phone_number_id: z.string().min(1, "ID de número de teléfono requerido"),
  verify_token: z.string().min(1, "Token de verificación requerido"),
  app_secret: z.string().optional(),
  business_account_id: z.string().optional(),
});

type WhatsAppFormData = z.infer<typeof whatsappSchema>;

export function WhatsAppConfigForm() {
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [existingConfig, setExistingConfig] = useState<WhatsAppFormData | null>(null);
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    reset,
  } = useForm<WhatsAppFormData>({
    resolver: zodResolver(whatsappSchema),
  });

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const config = await configApi.getWhatsAppConfig();
      if (config) {
        setExistingConfig(config);
        reset(config);
      }
    } catch (error) {
      console.error("Error loading config:", error);
    }
  };

  const onSubmit = async (data: WhatsAppFormData) => {
    try {
      setLoading(true);
      await configApi.saveWhatsAppConfig(data);
      toast({
        title: "Éxito",
        description: "Configuración de WhatsApp guardada correctamente.",
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
      const result = await configApi.testWhatsAppConnection();
      toast({
        title: "Conexión exitosa",
        description: result.message,
      });
    } catch (error: any) {
      toast({
        title: "Error de conexión",
        description: error.response?.data?.detail || "No se pudo conectar con WhatsApp",
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
          <Label htmlFor="access_token">Access Token *</Label>
          <Input
            id="access_token"
            type="password"
            placeholder="EAAB..."
            {...register("access_token")}
          />
          {errors.access_token && (
            <p className="text-sm text-red-500">{errors.access_token.message}</p>
          )}
          <p className="text-xs text-muted-foreground">
            Token de acceso permanente de Meta Business
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="phone_number_id">Phone Number ID *</Label>
          <Input
            id="phone_number_id"
            placeholder="123456789"
            {...register("phone_number_id")}
          />
          {errors.phone_number_id && (
            <p className="text-sm text-red-500">{errors.phone_number_id.message}</p>
          )}
          <p className="text-xs text-muted-foreground">
            ID del número de teléfono de WhatsApp Business
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="verify_token">Verify Token (Webhook) *</Label>
          <Input
            id="verify_token"
            placeholder="token_seguro_para_webhook"
            {...register("verify_token")}
          />
          {errors.verify_token && (
            <p className="text-sm text-red-500">{errors.verify_token.message}</p>
          )}
          <p className="text-xs text-muted-foreground">
            Token para verificar webhooks entrantes
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="app_secret">App Secret (opcional)</Label>
          <Input
            id="app_secret"
            type="password"
            placeholder="Opcional para verificación de firmas"
            {...register("app_secret")}
          />
          <p className="text-xs text-muted-foreground">
            Para verificación de firmas de webhook (X-Hub-Signature)
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="business_account_id">Business Account ID (opcional)</Label>
          <Input
            id="business_account_id"
            placeholder="ID de cuenta de negocio"
            {...register("business_account_id")}
          />
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
