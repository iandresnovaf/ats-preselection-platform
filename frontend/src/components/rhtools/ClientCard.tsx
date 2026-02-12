"use client";

import { Client, ClientStatus } from "@/types/rhtools";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Building2, 
  Mail, 
  Phone, 
  MapPin, 
  Users, 
  Briefcase, 
  MoreHorizontal, 
  Eye, 
  Edit,
  ExternalLink 
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Link from "next/link";

interface ClientCardProps {
  client: Client;
  onEdit?: (client: Client) => void;
  variant?: "default" | "compact";
}

const statusConfig: Record<ClientStatus, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  active: { label: "Activo", variant: "default" },
  inactive: { label: "Inactivo", variant: "destructive" },
  prospect: { label: "Prospecto", variant: "secondary" },
};

const sizeLabels: Record<string, string> = {
  startup: "Startup",
  sme: "PYME",
  enterprise: "Empresa",
  large_enterprise: "Gran Empresa",
};

export function ClientCard({ client, onEdit, variant = "default" }: ClientCardProps) {
  const status = statusConfig[client.status];
  const primaryContact = client.contacts?.find(c => c.is_primary) || client.contacts?.[0];

  if (variant === "compact") {
    return (
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
              {client.logo_url ? (
                <img 
                  src={client.logo_url} 
                  alt={client.name}
                  className="h-8 w-8 object-contain"
                />
              ) : (
                <Building2 className="h-5 w-5 text-primary" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-medium truncate">{client.name}</h4>
              <p className="text-xs text-muted-foreground">
                {client.industry || "Sin industria"} • {sizeLabels[client.size || ""] || "N/A"}
              </p>
            </div>
            <Badge variant={status.variant} className="text-xs">
              {status.label}
            </Badge>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
              {client.logo_url ? (
                <img 
                  src={client.logo_url} 
                  alt={client.name}
                  className="h-10 w-10 object-contain"
                />
              ) : (
                <Building2 className="h-6 w-6 text-primary" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-lg truncate">{client.name}</h3>
                <Badge variant={status.variant}>{status.label}</Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                {client.industry || "Sin industria especificada"}
              </p>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link href={`/dashboard/rhtools/clients/${client.id}`} className="flex items-center gap-2">
                  <Eye className="h-4 w-4" />
                  Ver detalles
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onEdit?.(client)}>
                <Edit className="h-4 w-4 mr-2" />
                Editar
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="pb-3 space-y-4">
        {/* Contacto principal */}
        {primaryContact && (
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Contacto principal
            </p>
            <div className="flex items-center gap-2 text-sm">
              <span className="font-medium">{primaryContact.name}</span>
              {primaryContact.position && (
                <span className="text-muted-foreground">({primaryContact.position})</span>
              )}
            </div>
            <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
              <a 
                href={`mailto:${primaryContact.email}`} 
                className="flex items-center gap-1 hover:text-primary"
              >
                <Mail className="h-3.5 w-3.5" />
                {primaryContact.email}
              </a>
              {primaryContact.phone && (
                <a 
                  href={`tel:${primaryContact.phone}`}
                  className="flex items-center gap-1 hover:text-primary"
                >
                  <Phone className="h-3.5 w-3.5" />
                  {primaryContact.phone}
                </a>
              )}
            </div>
          </div>
        )}

        {/* Información de ubicación */}
        {(client.city || client.country) && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <MapPin className="h-4 w-4" />
            <span>
              {[client.city, client.country].filter(Boolean).join(", ")}
            </span>
          </div>
        )}

        {/* Estadísticas */}
        <div className="grid grid-cols-2 gap-3 pt-3 border-t">
          <div className="flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-lg font-semibold">{client.active_jobs_count || 0}</p>
              <p className="text-xs text-muted-foreground">Jobs activos</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-lg font-semibold">{client.total_placements || 0}</p>
              <p className="text-xs text-muted-foreground">Placements</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
