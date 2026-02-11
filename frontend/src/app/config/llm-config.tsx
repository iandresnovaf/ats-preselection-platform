"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function LLMConfigForm() {
  const [config, setConfig] = useState({
    provider: "openai",
    apiKey: "",
    model: "gpt-4o-mini",
    temperature: "0.7",
    maxTokens: "1000",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Save to backend
    console.log("Saving LLM config:", config);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="provider">Proveedor</Label>
        <select
          id="provider"
          value={config.provider}
          onChange={(e) => setConfig({ ...config, provider: e.target.value })}
          className="w-full rounded-md border border-input bg-background px-3 py-2"
        >
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic (Claude)</option>
          <option value="google">Google (Gemini)</option>
          <option value="azure">Azure OpenAI</option>
        </select>
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="apiKey">API Key</Label>
        <Input
          id="apiKey"
          type="password"
          value={config.apiKey}
          onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
          placeholder="sk-..."
        />
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="model">Modelo</Label>
        <Input
          id="model"
          value={config.model}
          onChange={(e) => setConfig({ ...config, model: e.target.value })}
          placeholder="gpt-4o-mini"
        />
        <p className="text-sm text-muted-foreground">
          Recomendado: gpt-4o-mini para buen balance costo/rendimiento
        </p>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="temperature">Temperature</Label>
          <Input
            id="temperature"
            type="number"
            min="0"
            max="2"
            step="0.1"
            value={config.temperature}
            onChange={(e) => setConfig({ ...config, temperature: e.target.value })}
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="maxTokens">Max Tokens</Label>
          <Input
            id="maxTokens"
            type="number"
            value={config.maxTokens}
            onChange={(e) => setConfig({ ...config, maxTokens: e.target.value })}
          />
        </div>
      </div>
      
      <Button type="submit">Guardar Configuración</Button>
    </form>
  );
}
