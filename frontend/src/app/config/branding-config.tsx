"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { Upload, Loader2, ImageIcon } from "lucide-react";

interface BrandingConfig {
  companyName: string;
  logoUrl: string;
  primaryColor: string;
}

export function BrandingConfigForm() {
  const [config, setConfig] = useState<BrandingConfig>({
    companyName: "Top Management",
    logoUrl: "",
    primaryColor: "#000000",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [previewLogo, setPreviewLogo] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setIsLoading(true);
    try {
      // TODO: Load from backend
      const saved = localStorage.getItem("branding_config");
      if (saved) {
        const parsed = JSON.parse(saved);
        setConfig(parsed);
        if (parsed.logoUrl) {
          setPreviewLogo(parsed.logoUrl);
        }
      }
    } catch (error) {
      console.error("Error loading config:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      toast({
        title: "Error",
        description: "El logo no puede superar los 2MB",
        variant: "destructive",
      });
      return;
    }

    if (!file.type.startsWith("image/")) {
      toast({
        title: "Error",
        description: "El archivo debe ser una imagen",
        variant: "destructive",
      });
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const result = event.target?.result as string;
      setPreviewLogo(result);
      setConfig({ ...config, logoUrl: result });
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      // TODO: Save to backend API
      localStorage.setItem("branding_config", JSON.stringify(config));
      
      // Dispatch event to update other components
      window.dispatchEvent(new StorageEvent("storage", {
        key: "branding_config",
        newValue: JSON.stringify(config),
      }));
      
      toast({
        title: "Éxito",
        description: "Configuración de marca guardada correctamente",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudo guardar la configuración",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="companyName">Nombre de la Empresa</Label>
        <Input
          id="companyName"
          value={config.companyName}
          onChange={(e) => setConfig({ ...config, companyName: e.target.value })}
          placeholder="Top Management"
        />
        <p className="text-sm text-muted-foreground">
          Este nombre aparecerá en los correos y comunicaciones enviadas a los candidatos.
        </p>
      </div>

      <div className="space-y-2">
        <Label>Logo de la Empresa</Label>
        <Card>
          <CardContent className="p-6">
            <div className="flex flex-col items-center gap-4">
              {previewLogo ? (
                <div className="relative">
                  <img
                    src={previewLogo}
                    alt="Logo preview"
                    className="max-h-32 max-w-full object-contain rounded-lg"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="mt-2"
                    onClick={() => {
                      setPreviewLogo(null);
                      setConfig({ ...config, logoUrl: "" });
                    }}
                  >
                    Eliminar
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2 text-muted-foreground">
                  <ImageIcon className="h-16 w-16" />
                  <p className="text-sm">No hay logo configurado</p>
                </div>
              )}
              
              <div className="flex items-center gap-2">
                <Input
                  type="file"
                  accept="image/*"
                  onChange={handleLogoUpload}
                  className="hidden"
                  id="logo-upload"
                />
                <Label htmlFor="logo-upload" className="cursor-pointer">
                  <div className="flex items-center gap-2 px-4 py-2 border rounded-md hover:bg-muted transition-colors">
                    <Upload className="h-4 w-4" />
                    <span>{previewLogo ? "Cambiar logo" : "Subir logo"}</span>
                  </div>
                </Label>
              </div>
              
              <p className="text-xs text-muted-foreground">
                Formatos: PNG, JPG, SVG. Máximo 2MB. Recomendado: 200x50px
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-2">
        <Label htmlFor="primaryColor">Color Principal</Label>
        <div className="flex items-center gap-4">
          <Input
            id="primaryColor"
            type="color"
            value={config.primaryColor}
            onChange={(e) => setConfig({ ...config, primaryColor: e.target.value })}
            className="w-16 h-10 p-1"
          />
          <Input
            type="text"
            value={config.primaryColor}
            onChange={(e) => setConfig({ ...config, primaryColor: e.target.value })}
            placeholder="#000000"
            className="flex-1"
          />
        </div>
        <p className="text-sm text-muted-foreground">
          Este color se usará en los botones y elementos principales de la interfaz.
        </p>
      </div>

      <Button type="submit" disabled={isSaving}>
        {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Guardar Configuración de Marca
      </Button>

      {/* Preview */}
      <Card className="mt-6">
        <CardContent className="p-6">
          <h3 className="font-medium mb-4">Vista Previa</h3>
          <div 
            className="border rounded-lg p-6 flex items-center justify-center"
            style={{ backgroundColor: "#f8f9fa" }}
          >
            {previewLogo ? (
              <img 
                src={previewLogo} 
                alt="Company logo" 
                className="max-h-16 object-contain"
              />
            ) : (
              <div className="text-center">
                <p className="text-2xl font-bold" style={{ color: config.primaryColor }}>
                  {config.companyName}
                </p>
              </div>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-4 text-center">
            Así se verá el logo en las landing pages para candidatos
          </p>
        </CardContent>
      </Card>
    </form>
  );
}
