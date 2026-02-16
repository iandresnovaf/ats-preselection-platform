"use client";

import { useState } from "react";
import { useRoles, useApplications } from "@/hooks/use-headhunting";
import { StageBadge } from "@/components/headhunting";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Search,
  Building2,
  MapPin,
  Users,
  Briefcase,
  Loader2,
  Plus,
  Filter,
  ChevronRight,
  FileText,
  Upload,
} from "lucide-react";
import Link from "next/link";
import type { Role, RoleStatus, Application } from "@/types/headhunting";

interface RoleCardProps {
  role: Role;
  onViewCandidates: (role: Role) => void;
}

const statusColors: Record<RoleStatus, string> = {
  draft: "bg-gray-100 text-gray-800",
  active: "bg-green-100 text-green-800",
  paused: "bg-yellow-100 text-yellow-800",
  closed: "bg-red-100 text-red-800",
};

const statusLabels: Record<RoleStatus, string> = {
  draft: "Borrador",
  active: "Activa",
  paused: "Pausada",
  closed: "Cerrada",
};

function RoleCard({ role, onViewCandidates }: RoleCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-5">
        <div className="flex flex-col lg:flex-row lg:items-start gap-4">
          {/* Main Info */}
          <div className="flex-1">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold text-lg">{role.title}</h3>
                <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                  <Building2 className="w-4 h-4" />
                  <span>{role.client?.name || "Cliente no especificado"}</span>
                </div>
              </div>
              <Badge className={statusColors[role.status]}>
                {statusLabels[role.status]}
              </Badge>
            </div>

            <div className="flex flex-wrap items-center gap-3 mt-3 text-sm text-gray-600">
              {role.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {role.location}
                </span>
              )}
              {role.department && (
                <Badge variant="outline" className="text-xs">
                  {role.department}
                </Badge>
              )}
              {role.seniority && (
                <Badge variant="outline" className="text-xs">
                  {role.seniority}
                </Badge>
              )}
              {role.employment_type && (
                <Badge variant="outline" className="text-xs">
                  {role.employment_type}
                </Badge>
              )}
            </div>

            {role.required_skills && role.required_skills.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-3">
                {role.required_skills.slice(0, 4).map((skill) => (
                  <Badge key={skill} variant="secondary" className="text-xs">
                    {skill}
                  </Badge>
                ))}
                {role.required_skills.length > 4 && (
                  <Badge variant="secondary" className="text-xs">
                    +{role.required_skills.length - 4}
                  </Badge>
                )}
              </div>
            )}

            {/* Progress Stats */}
            {role.status === "active" && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Progreso</span>
                  <span className="font-medium">
                    {role.hired_count || 0} / {role.applications_count || 0} contratados
                  </span>
                </div>
                <Progress 
                  value={role.applications_count ? ((role.hired_count || 0) / role.applications_count) * 100 : 0} 
                  className="h-2"
                />
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-row lg:flex-col gap-2">
            <Button
              variant="outline"
              onClick={() => onViewCandidates(role)}
              className="flex-1 lg:flex-none"
            >
              <Users className="w-4 h-4 mr-2" />
              Ver candidatos
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
            <Link href={`/roles/${role.id}`} className="flex-1 lg:flex-none">
              <Button variant="ghost" className="w-full">
                Editar
              </Button>
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface RoleCandidatesDialogProps {
  role: Role | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function RoleCandidatesDialog({
  role,
  open,
  onOpenChange,
}: RoleCandidatesDialogProps) {
  const { data: applications, isLoading } = useApplications(
    role ? { role_id: role.id } : undefined
  );

  if (!role) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            <div className="flex items-center gap-2">
              <Briefcase className="w-5 h-5" />
              Candidatos para: {role.title}
            </div>
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
          </div>
        ) : applications && applications.length > 0 ? (
          <div className="space-y-3 mt-4">
            {applications.map((app) => (
              <Card key={app.id}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium">
                        {app.candidate?.first_name} {app.candidate?.last_name}
                      </h4>
                      <p className="text-sm text-gray-500">
                        {app.candidate?.current_position} @ {app.candidate?.current_company}
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        <StageBadge stage={app.stage} />
                        <span className="text-xs text-gray-400">
                          Score: {app.overall_score}/100
                        </span>
                      </div>
                    </div>
                    <Link href={`/applications/${app.id}`}>
                      <Button variant="outline" size="sm">
                        Ver detalle
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Users className="w-12 h-12 mx-auto mb-2 opacity-30" />
            <p>No hay candidatos para esta vacante</p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function RolesPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<RoleStatus | "all">("all");
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [candidatesOpen, setCandidatesOpen] = useState(false);

  const { data: roles, isLoading } = useRoles({
    search: search || undefined,
    status: status === "all" ? undefined : status,
  });

  const handleViewCandidates = (role: Role) => {
    setSelectedRole(role);
    setCandidatesOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Vacantes</h1>
          <p className="text-gray-600 mt-1">Gestiona las posiciones abiertas</p>
        </div>
        <Link href="/roles/new">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Nueva Vacante
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Buscar por título o cliente..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={status} onValueChange={(v) => setStatus(v as RoleStatus | "all")}>
              <SelectTrigger>
                <SelectValue placeholder="Filtrar por estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los estados</SelectItem>
                <SelectItem value="active">Activas</SelectItem>
                <SelectItem value="draft">Borradores</SelectItem>
                <SelectItem value="paused">Pausadas</SelectItem>
                <SelectItem value="closed">Cerradas</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" className="md:w-auto">
              <Filter className="w-4 h-4 mr-2" />
              Más filtros
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Activas</p>
            <p className="text-2xl font-bold">
              {roles?.filter(r => r.status === "active").length || 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Total Candidatos</p>
            <p className="text-2xl font-bold">
              {roles?.reduce((acc, r) => acc + (r.applications_count || 0), 0) || 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">En Terna</p>
            <p className="text-2xl font-bold">
              {roles?.reduce((acc, r) => acc + (r.candidates_in_terna || 0), 0) || 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Contratados</p>
            <p className="text-2xl font-bold">
              {roles?.reduce((acc, r) => acc + (r.hired_count || 0), 0) || 0}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Roles List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : roles && roles.length > 0 ? (
        <div className="grid grid-cols-1 gap-4">
          {roles.map((role) => (
            <RoleCard
              key={role.id}
              role={role}
              onViewCandidates={handleViewCandidates}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <Briefcase className="w-12 h-12 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-900">
            No se encontraron vacantes
          </h3>
          <p className="text-gray-500 mt-2">
            {search || status !== "all"
              ? "Intenta ajustar los filtros de búsqueda"
              : "Crea tu primera vacante para comenzar"}
          </p>
          {!search && status === "all" && (
            <Link href="/roles/new">
              <Button className="mt-4">
                <Plus className="w-4 h-4 mr-2" />
                Crear Vacante
              </Button>
            </Link>
          )}
        </div>
      )}

      {/* Candidates Dialog */}
      <RoleCandidatesDialog
        role={selectedRole}
        open={candidatesOpen}
        onOpenChange={setCandidatesOpen}
      />
    </div>
  );
}
