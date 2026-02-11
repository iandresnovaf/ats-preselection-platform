"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { Loader2, TestTube, Database } from "lucide-react";

interface ATSConfig {
  provider: "zoho" | "odoo";
  // Zoho fields
  clientId?: string;
  clientSecret?: string;
  refreshToken?: string;
  redirectUri?: string;
  // Odoo fields
  url?: string;
  database?: string;
  username?: string;
  apiKey?: string;
}

export function ATSConfigForm() {
  const [config, setConfig] = useState<ATSConfig>({
    provider: "zoho",
    redirectUri: "http://localhost:8000/api/v1/zoho/callback",
    jobModel: "hr.job",
    applicantModel: "hr.applicant",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      // TODO: Save to backend
      localStorage.setItem("ats_config", JSON.stringify(config));
      toast({
        title: "Éxito",
        description: `Configuración de ${config.provider === "zoho" ? "Zoho Recruit" : "Odoo"} guardada`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudo guardar la configuración",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    try {
      // TODO: Test connection with backend
      await new Promise((resolve) => setTimeout(resolve, 1500));
      toast({
        title: "Éxito",
        description: `Conexión con ${config.provider === "zoho" ? "Zoho Recruit" : "Odoo"} exitosa`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudo conectar con el ATS",
        variant: "destructive",
      });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>Proveedor de ATS</Label>
        <div className="grid grid-cols-2 gap-4">
          <Card
            className={`cursor-pointer transition-all ${
              config.provider === "zoho"
                ? "border-primary ring-2 ring-primary/20"
                : "hover:border-muted-foreground/50"
            }`}
            onClick={() => setConfig({ ...config, provider: "zoho" })}
          >
            <CardContent className="p-4 flex items-center gap-3">
              <div className="h-10 w-10 rounded bg-green-100 flex items-center justify-center">
                <span className="text-green-700 font-bold text-lg">Z</span>
              </div>
              <div>
                <p className="font-medium">Zoho Recruit</p>
                <p className="text-xs text-muted-foreground">ATS basado en la nube</p>
              </div>
            </CardContent>
          </Card>

          <Card
            className={`cursor-pointer transition-all ${
              config.provider === "odoo"
                ? "border-primary ring-2 ring-primary/20"
                : "hover:border-muted-foreground/50"
            }`}
            onClick={() => setConfig({ ...config, provider: "odoo" })}
          >
            <CardContent className="p-4 flex items-center gap-3">
              <div className="h-10 w-10 rounded bg-purple-100 flex items-center justify-center">
                <span className="text-purple-700 font-bold text-lg">O</span>
              </div>
              <div>
                <p className="font-medium">Odoo</p>
                <p className="text-xs text-muted-foreground">ERP con módulo de reclutamiento</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {config.provider === "zoho" ? (
          <>
            <div className="space-y-2">
              <Label htmlFor="clientId">Client ID</Label>
              <Input
                id="clientId"
                value={config.clientId || ""}
                onChange={(e) => setConfig({ ...config, clientId: e.target.value })}
                placeholder="1000.XXXXXXXX"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="clientSecret">Client Secret</Label>
              <Input
                id="clientSecret"
                type="password"
                value={config.clientSecret || ""}
                onChange={(e) => setConfig({ ...config, clientSecret: e.target.value })}
                placeholder="Tu client secret"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="refreshToken">Refresh Token</Label>
              <Input
                id="refreshToken"
                type="password"
                value={config.refreshToken || ""}
                onChange={(e) => setConfig({ ...config, refreshToken: e.target.value })}
                placeholder="1000.XXXXXX..."
              />
              <p className="text-sm text-muted-foreground">
                Generado via OAuth2 flow con Zoho.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="redirectUri">Redirect URI</Label>
              <Input
                id="redirectUri"
                value={config.redirectUri || ""}
                onChange={(e) => setConfig({ ...config, redirectUri: e.target.value })}
                placeholder="http://localhost:8000/api/v1/zoho/callback"
              />
            </div>

            <div className="p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-700">
                <strong>¿Cómo obtener las credenciales?</strong>
              </p>
              <ol className="text-sm text-blue-600 mt-2 list-decimal list-inside space-y-1">
                <li>Ve a <a href="https://api-console.zoho.com" target="_blank" rel="noopener" className="underline">Zoho API Console</a></li>
                <li>Crea un nuevo workspace "Self Client"</li>
                <li>Genera un Grant Token con scope: <code>ZohoRecruit.modules.ALL</code></li>
                <li>Intercambia el Grant Token por Refresh Token</li>
              </ol>
            </div>
          </>
        ) : (
          <>
            <div className="space-y-2">
              <Label htmlFor="url">URL de Odoo</Label>
              <Input
                id="url"
                value={config.url || ""}
                onChange={(e) => setConfig({ ...config, url: e.target.value })}
                placeholder="https://miempresa.odoo.com"
              />
              <p className="text-sm text-muted-foreground">
                URL de tu instancia Odoo (incluye https://)
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="database">Base de Datos</Label>
              <Input
                id="database"
                value={config.database || ""}
                onChange={(e) => setConfig({ ...config, database: e.target.value })}
                placeholder="miempresa_prod"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="username">Usuario / Email</Label>
              <Input
                id="username"
                value={config.username || ""}
                onChange={(e) => setConfig({ ...config, username: e.target.value })}
                placeholder="admin@miempresa.com"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="apiKey">API Key o Contraseña</Label>
              <Input
                id="apiKey"
                type="password"
                value={config.apiKey || ""}
                onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
                placeholder="••••••••"
              />
              <p className="text-sm text-muted-foreground">
                Recomendado: Crea una API Key en tu perfil de Odoo
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="jobModel">Modelo de Puestos</Label>
                <Input
                  id="jobModel"
                  value={config.jobModel || "hr.job"}
                  onChange={(e) => setConfig({ ...config, jobModel: e.target.value })}
                  placeholder="hr.job"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="applicantModel">Modelo de Candidatos</Label>
                <Input
                  id="applicantModel"
                  value={config.applicantModel || "hr.applicant"}
                  onChange={(e) => setConfig({ ...config, applicantModel: e.target.value })}
                  placeholder="hr.applicant"
                />
              </div>
            </div>

            <div className="p-4 bg-purple-50 rounded-lg">
              <p className="text-sm text-purple-700">
                <strong>¿Cómo configurar Odoo?</strong>
              </p>
              <ol className="text-sm text-purple-600 mt-2 list-decimal list-inside space-y-1">
                <li>Activa el módulo "Recruitment" en Odoo</li>
                <li>Ve a tu perfil de usuario → Preferences → API Keys</li>
                <li>Crea una nueva API Key para esta integración</li>
                <li>Asegúrate de tener permisos de lectura/escritura en hr.job y hr.applicant</li>
              </ol>
            </div>
          </>
        )}

        <div className="flex gap-2">
          <Button type="submit" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Guardar Configuración
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={handleTestConnection}
            disabled={isTesting}
          >
            {isTesting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <TestTube className="mr-2 h-4 w-4" />
            Probar Conexión
          </Button>
        </div>
      </form>
    </div>
  );
}
