"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { configApi } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Save, TestTube } from "lucide-react";

const emailSchema = z.object({
  provider: z.string().default("smtp"),
  smtp_host: z.string().min(1, "Host SMTP requerido"),
  smtp_port: z.number().min(1).max(65535).default(587),
  smtp_user: z.string().min(1, "Usuario SMTP requerido"),
  smtp_password: z.string().min(1, "Contraseña requerida"),
  use_tls: z.boolean().default(true),
  default_from: z.string().email("Email válido requerido"),
  default_from_name: z.string().min(1, "Nombre requerido").default("Top Management"),
});

type EmailFormData = z.infer<typeof emailSchema>;

const PROVIDERS = [
  { value: "smtp", label: "SMTP Genérico" },
  { value: "sendgrid", label: "SendGrid" },
  { value: "mailgun", label: "Mailgun" },
];

const SMTP_PRESETS: Record<string, { host: string; port: number }> = {
  gmail: { host: "smtp.gmail.com", port: 587 },
  outlook: { host: "smtp.office365.com", port: 587 },
  sendgrid: { host: "smtp.sendgrid.net", port: 587 },
  mailgun: { host: "smtp.mailgun.org", port: 587 },
};

export function EmailConfigForm() {
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [existingConfig, setExistingConfig] = useState<EmailFormData | null>(null);
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isDirty },
    reset,
  } = useForm<EmailFormData>({
    resolver: zodResolver(emailSchema),
    defaultValues: {
      provider: "smtp",
      smtp_port: 587,
      use_tls: true,
      default_from_name: "Top Management",
    },
  });

  const selectedProvider = watch("provider");

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const config = await configApi.getEmailConfig();
      if (config) {
        setExistingConfig(config);
        reset(config);
      }
    } catch (error) {
      console.error("Error loading config:", error);
    }
  };

  const applyPreset = (preset: string) => {
    if (SMTP_PRESETS[preset]) {
      setValue("smtp_host", SMTP_PRESETS[preset].host);
      setValue("smtp_port", SMTP_PRESETS[preset].port);
    }
  };

  const onSubmit = async (data: EmailFormData) => {
    try {
      setLoading(true);
      await configApi.saveEmailConfig(data);
      toast({
        title: "Éxito",
        description: "Configuración de Email guardada correctamente.",
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
      const result = await configApi.testEmailConnection();
      toast({
        title: "Conexión exitosa",
        description: result.message,
      });
    } catch (error: any) {
      toast({
        title: "Error de conexión",
        description: error.response?.data?.detail || "No se pudo conectar con el servidor SMTP",
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
          <Label htmlFor="provider">Proveedor</Label>
          <Select
            value={selectedProvider}
            onValueChange={(value) => {
              setValue("provider", value);
              applyPreset(value);
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="Selecciona proveedor" />
            </SelectTrigger>
            <SelectContent>
              {PROVIDERS.map((p) => (
                <SelectItem key={p.value} value={p.value}>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="smtp_host">Host SMTP *</Label>
          <Input
            id="smtp_host"
            placeholder="smtp.gmail.com"
            {...register("smtp_host")}
          />
          {errors.smtp_host && (
            <p className="text-sm text-red-500">{errors.smtp_host.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="smtp_port">Puerto SMTP</Label>
          <Input
            id="smtp_port"
            type="number"
            {...register("smtp_port", { valueAsNumber: true })}
          />
          {errors.smtp_port && (
            <p className="text-sm text-red-500">{errors.smtp_port.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="smtp_user">Usuario SMTP *</Label>
          <Input
            id="smtp_user"
            placeholder="usuario@ejemplo.com"
            {...register("smtp_user")}
          />
          {errors.smtp_user && (
            <p className="text-sm text-red-500">{errors.smtp_user.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="smtp_password">Contraseña *</Label>
          <Input
            id="smtp_password"
            type="password"
            placeholder="Contraseña o API Key"
            {...register("smtp_password")}
          />
          {errors.smtp_password && (
            <p className="text-sm text-red-500">{errors.smtp_password.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="default_from">Email Remitente *</Label>
          <Input
            id="default_from"
            type="email"
            placeholder="noreply@tudominio.com"
            {...register("default_from")}
          />
          {errors.default_from && (
            <p className="text-sm text-red-500">{errors.default_from.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="default_from_name">Nombre Remitente *</Label>
          <Input
            id="default_from_name"
            placeholder="Top Management"
            {...register("default_from_name")}
          />
          {errors.default_from_name && (
            <p className="text-sm text-red-500">{errors.default_from_name.message}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="use_tls"
          checked={watch("use_tls")}
          onCheckedChange={(checked) => setValue("use_tls", checked)}
        />
        <Label htmlFor="use_tls">Usar TLS/SSL</Label>
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
