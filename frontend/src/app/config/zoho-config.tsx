"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function ZohoConfigForm() {
  const [config, setConfig] = useState({
    clientId: "",
    clientSecret: "",
    refreshToken: "",
    dataCenter: "com",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Save to backend
    console.log("Saving Zoho config:", config);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="clientId">Client ID</Label>
        <Input
          id="clientId"
          value={config.clientId}
          onChange={(e) => setConfig({ ...config, clientId: e.target.value })}
          placeholder="1000.XXXXXXXX"
        />
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="clientSecret">Client Secret</Label>
        <Input
          id="clientSecret"
          type="password"
          value={config.clientSecret}
          onChange={(e) => setConfig({ ...config, clientSecret: e.target.value })}
          placeholder="Tu client secret"
        />
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="refreshToken">Refresh Token</Label>
        <Textarea
          id="refreshToken"
          value={config.refreshToken}
          onChange={(e) => setConfig({ ...config, refreshToken: e.target.value })}
          placeholder="1000.XXXXXX..."
          rows={3}
        />
        <p className="text-sm text-muted-foreground">
          Generado via OAuth2 flow con Zoho.
        </p>
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="dataCenter">Data Center</Label>
        <select
          id="dataCenter"
          value={config.dataCenter}
          onChange={(e) => setConfig({ ...config, dataCenter: e.target.value })}
          className="w-full rounded-md border border-input bg-background px-3 py-2"
        >
          <option value="com">.com (US/Global)</option>
          <option value="eu">.eu (Europe)</option>
          <option value="in">.in (India)</option>
          <option value="com.cn">.com.cn (China)</option>
          <option value="com.au">.com.au (Australia)</option>
        </select>
      </div>
      
      <Button type="submit">Guardar Configuración</Button>
    </form>
  );
}
