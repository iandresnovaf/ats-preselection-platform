"use client";

import { useEffect, useState } from "react";
import { configApi } from "@/services/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Loader2, RefreshCw, Database, Server, MessageSquare, Cloud, Brain, Mail } from "lucide-react";

interface SystemStatusData {
  database: boolean;
  redis: boolean;
  whatsapp: boolean | null;
  zoho: boolean | null;
  llm: boolean | null;
  email: boolean | null;
}

export function SystemStatus() {
  const [status, setStatus] = useState<SystemStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStatus = async () => {
    try {
      setRefreshing(true);
      const data = await configApi.getStatus();
      setStatus(data);
    } catch (error) {
      console.error("Error fetching status:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!status) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No se pudo obtener el estado del sistema.
      </div>
    );
  }

  const services = [
    { key: "database", label: "Base de Datos", icon: Database, status: status.database },
    { key: "redis", label: "Redis", icon: Server, status: status.redis },
    { key: "whatsapp", label: "WhatsApp API", icon: MessageSquare, status: status.whatsapp },
    { key: "zoho", label: "Zoho Recruit", icon: Cloud, status: status.zoho },
    { key: "llm", label: "Proveedor LLM", icon: Brain, status: status.llm },
    { key: "email", label: "Servidor Email", icon: Mail, status: status.email },
  ];

  const getStatusBadge = (status: boolean | null) => {
    if (status === null) {
      return <Badge variant="outline">No configurado</Badge>;
    }
    return status ? (
      <Badge className="bg-green-500 hover:bg-green-600">OK</Badge>
    ) : (
      <Badge variant="destructive">Error</Badge>
    );
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {services.map((service) => (
          <Card key={service.key}>
            <CardContent className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <service.icon className="h-5 w-5 text-muted-foreground" />
                <span className="font-medium">{service.label}</span>
              </div>
              {getStatusBadge(service.status)}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex justify-end">
        <Button 
          variant="outline" 
          onClick={fetchStatus}
          disabled={refreshing}
        >
          {refreshing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {!refreshing && <RefreshCw className="mr-2 h-4 w-4" />}
          Actualizar
        </Button>
      </div>
    </div>
  );
}
