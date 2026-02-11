"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { configApi } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { Loader2, Save, TestTube } from "lucide-react";

const llmSchema = z.object({
  provider: z.string().default("openai"),
  api_key: z.string().min(1, "API Key requerida"),
  model: z.string().default("gpt-4o-mini"),
  max_tokens: z.number().min(100).max(8000).default(2000),
  temperature: z.number().min(0).max(2).default(0),
  prompt_version: z.string().default("v1.0"),
});

type LLMFormData = z.infer<typeof llmSchema>;

const PROVIDERS = [
  { value: "openai", label: "OpenAI", models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"] },
  { value: "anthropic", label: "Anthropic", models: ["claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku"] },
];

export function LLMConfigForm() {
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [existingConfig, setExistingConfig] = useState<LLMFormData | null>(null);
  const [availableModels, setAvailableModels] = useState<string[]>(PROVIDERS[0].models);
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isDirty },
    reset,
  } = useForm<LLMFormData>({
    resolver: zodResolver(llmSchema),
    defaultValues: {
      provider: "openai",
      model: "gpt-4o-mini",
      max_tokens: 2000,
      temperature: 0,
      prompt_version: "v1.0",
    },
  });

  const selectedProvider = watch("provider");

  useEffect(() => {
    const provider = PROVIDERS.find(p => p.value === selectedProvider);
    if (provider) {
      setAvailableModels(provider.models);
      setValue("model", provider.models[0]);
    }
  }, [selectedProvider, setValue]);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const config = await configApi.getLLMConfig();
      if (config) {
        setExistingConfig(config);
        reset(config);
      }
    } catch (error) {
      console.error("Error loading config:", error);
    }
  };

  const onSubmit = async (data: LLMFormData) => {
    try {
      setLoading(true);
      await configApi.saveLLMConfig(data);
      toast({
        title: "Éxito",
        description: "Configuración de LLM guardada correctamente.",
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
      const result = await configApi.testLLMConnection();
      toast({
        title: "Conexión exitosa",
        description: result.message,
      });
    } catch (error: any) {
      toast({
        title: "Error de conexión",
        description: error.response?.data?.detail || "No se pudo conectar con el proveedor LLM",
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
            onValueChange={(value) => setValue("provider", value)}
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
          <Label htmlFor="api_key">API Key *</Label>
          <Input
            id="api_key"
            type="password"
            placeholder="sk-..."
            {...register("api_key")}
          />
          {errors.api_key && (
            <p className="text-sm text-red-500">{errors.api_key.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="model">Modelo</Label>
          <Select
            value={watch("model")}
            onValueChange={(value) => setValue("model", value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Selecciona modelo" />
            </SelectTrigger>
            <SelectContent>
              {availableModels.map((m) => (
                <SelectItem key={m} value={m}>
                  {m}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="max_tokens">Max Tokens</Label>
          <Input
            id="max_tokens"
            type="number"
            min={100}
            max={8000}
            {...register("max_tokens", { valueAsNumber: true })}
          />
          {errors.max_tokens && (
            <p className="text-sm text-red-500">{errors.max_tokens.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="temperature">Temperature (0-2)</Label>
          <Input
            id="temperature"
            type="number"
            step="0.1"
            min={0}
            max={2}
            {...register("temperature", { valueAsNumber: true })}
          />
          {errors.temperature && (
            <p className="text-sm text-red-500">{errors.temperature.message}</p>
          )}
          <p className="text-xs text-muted-foreground">
            0 = determinista, 2 = muy creativo (recomendado: 0 para scoring)
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="prompt_version">Versión de Prompt</Label>
          <Input
            id="prompt_version"
            placeholder="v1.0"
            {...register("prompt_version")}
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
