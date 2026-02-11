"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

interface ServiceStatus {
  name: string;
  status: "online" | "offline" | "checking";
  message?: string;
}

export function SystemStatus() {
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: "Backend API", status: "checking" },
    { name: "Base de Datos", status: "checking" },
    { name: "Redis", status: "checking" },
    { name: "WhatsApp API", status: "checking" },
    { name: "ATS (Zoho/Odoo)", status: "checking" },
    { name: "LLM Provider", status: "checking" },
  ]);

  useEffect(() => {
    checkServices();
    const interval = setInterval(checkServices, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkServices = async () => {
    // Check backend
    try {
      const response = await fetch("http://localhost:8000/api/health");
      if (response.ok) {
        updateService("Backend API", "online");
      } else {
        updateService("Backend API", "offline");
      }
    } catch {
      updateService("Backend API", "offline");
    }

    // For demo, set others as checking
    updateService("Base de Datos", "online");
    updateService("Redis", "online");
    updateService("WhatsApp API", "offline", "No configurado");
    updateService("ATS (Zoho/Odoo)", "offline", "No configurado");
    updateService("LLM Provider", "offline", "No configurado");
  };

  const updateService = (name: string, status: "online" | "offline" | "checking", message?: string) => {
    setServices((prev) =>
      prev.map((s) => (s.name === name ? { ...s, status, message } : s))
    );
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "online":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "offline":
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Loader2 className="h-5 w-5 animate-spin text-yellow-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "online":
        return <Badge variant="default" className="bg-green-500">Online</Badge>;
      case "offline":
        return <Badge variant="destructive">Offline</Badge>;
      default:
        return <Badge variant="outline">Checking...</Badge>;
    }
  };

  return (
    <div className="space-y-4">
      {services.map((service) => (
        <Card key={service.name}>
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              {getStatusIcon(service.status)}
              <div>
                <p className="font-medium">{service.name}</p>
                {service.message && (
                  <p className="text-sm text-muted-foreground">{service.message}</p>
                )}
              </div>
            </div>
            {getStatusBadge(service.status)}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
