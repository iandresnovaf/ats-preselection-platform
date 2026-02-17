"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { CalendarIcon, Filter, X, Search } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import type { TrackingFilters as TrackingFiltersType, ApplicationStatus } from "@/types/tracking";

interface TrackingFiltersProps {
  filters: TrackingFiltersType;
  onFiltersChange: (filters: TrackingFiltersType) => void;
  availableRoles?: { id: string; title: string }[];
}

const statusOptions: { value: ApplicationStatus; label: string }[] = [
  { value: "pending_contact", label: "Pendiente de contacto" },
  { value: "contacted", label: "Contactado" },
  { value: "interested", label: "Interesado" },
  { value: "not_interested", label: "No interesado" },
  { value: "no_response", label: "Sin respuesta" },
  { value: "scheduled", label: "Entrevista agendada" },
  { value: "completed", label: "Proceso completado" },
  { value: "hired", label: "Contratado" },
];

export function TrackingFilters({
  filters,
  onFiltersChange,
  availableRoles,
}: TrackingFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [localFilters, setLocalFilters] = useState<TrackingFiltersType>(filters);

  const activeFiltersCount = [
    filters.role_id,
    filters.status && filters.status.length > 0,
    filters.date_from,
    filters.date_to,
    filters.has_response !== undefined && filters.has_response !== null,
    filters.search,
  ].filter(Boolean).length;

  const handleApplyFilters = () => {
    onFiltersChange(localFilters);
  };

  const handleClearFilters = () => {
    const cleared: TrackingFiltersType = {
      role_id: undefined,
      status: undefined,
      date_from: undefined,
      date_to: undefined,
      has_response: null,
      search: undefined,
    };
    setLocalFilters(cleared);
    onFiltersChange(cleared);
  };

  const toggleStatus = (status: ApplicationStatus) => {
    const current = localFilters.status || [];
    const updated = current.includes(status)
      ? current.filter((s) => s !== status)
      : [...current, status];
    setLocalFilters({ ...localFilters, status: updated });
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex flex-col gap-4">
          {/* Search and quick filters row */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar candidato..."
                className="pl-9"
                value={localFilters.search || ""}
                onChange={(e) =>
                  setLocalFilters({ ...localFilters, search: e.target.value || undefined })
                }
                onKeyDown={(e) => e.key === "Enter" && handleApplyFilters()}
              />
            </div>

            <Popover open={isExpanded} onOpenChange={setIsExpanded}>
              <PopoverTrigger asChild>
                <Button variant="outline" className="gap-2">
                  <Filter className="h-4 w-4" />
                  Filtros
                  {activeFiltersCount > 0 && (
                    <Badge variant="secondary" className="ml-1">
                      {activeFiltersCount}
                    </Badge>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-96" align="end">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium">Filtros avanzados</h4>
                    {activeFiltersCount > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleClearFilters}
                        className="h-auto p-1"
                      >
                        <X className="h-4 w-4 mr-1" />
                        Limpiar
                      </Button>
                    )}
                  </div>

                  {/* Role filter */}
                  {availableRoles && availableRoles.length > 0 && (
                    <div className="space-y-2">
                      <Label>Vacante</Label>
                      <Select
                        value={localFilters.role_id || "all"}
                        onValueChange={(v) =>
                          setLocalFilters({
                            ...localFilters,
                            role_id: v === "all" ? undefined : v,
                          })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Todas las vacantes" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Todas las vacantes</SelectItem>
                          {availableRoles.map((role) => (
                            <SelectItem key={role.id} value={role.id}>
                              {role.title}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  {/* Status filter */}
                  <div className="space-y-2">
                    <Label>Estado</Label>
                    <div className="flex flex-wrap gap-1">
                      {statusOptions.map((option) => {
                        const isSelected = localFilters.status?.includes(option.value);
                        return (
                          <Badge
                            key={option.value}
                            variant={isSelected ? "default" : "outline"}
                            className="cursor-pointer"
                            onClick={() => toggleStatus(option.value)}
                          >
                            {option.label}
                          </Badge>
                        );
                      })}
                    </div>
                  </div>

                  {/* Date range filter */}
                  <div className="space-y-2">
                    <Label>Rango de fechas</Label>
                    <div className="flex gap-2">
                      <Popover>
                        <PopoverTrigger asChild>
                          <Button
                            variant="outline"
                            className="flex-1 justify-start text-left font-normal"
                          >
                            <CalendarIcon className="mr-2 h-4 w-4" />
                            {localFilters.date_from ? (
                              format(localFilters.date_from, "dd/MM/yyyy", { locale: es })
                            ) : (
                              <span className="text-muted-foreground">Desde</span>
                            )}
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0" align="start">
                          <Calendar
                            mode="single"
                            selected={localFilters.date_from}
                            onSelect={(date) =>
                              setLocalFilters({ ...localFilters, date_from: date })
                            }
                            initialFocus
                          />
                        </PopoverContent>
                      </Popover>
                      <Popover>
                        <PopoverTrigger asChild>
                          <Button
                            variant="outline"
                            className="flex-1 justify-start text-left font-normal"
                          >
                            <CalendarIcon className="mr-2 h-4 w-4" />
                            {localFilters.date_to ? (
                              format(localFilters.date_to, "dd/MM/yyyy", { locale: es })
                            ) : (
                              <span className="text-muted-foreground">Hasta</span>
                            )}
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0" align="start">
                          <Calendar
                            mode="single"
                            selected={localFilters.date_to}
                            onSelect={(date) =>
                              setLocalFilters({ ...localFilters, date_to: date })
                            }
                            initialFocus
                          />
                        </PopoverContent>
                      </Popover>
                    </div>
                  </div>

                  {/* Response filter */}
                  <div className="space-y-2">
                    <Label>Tiene respuesta</Label>
                    <Select
                      value={
                        localFilters.has_response === null || localFilters.has_response === undefined
                          ? "all"
                          : localFilters.has_response.toString()
                      }
                      onValueChange={(v) =>
                        setLocalFilters({
                          ...localFilters,
                          has_response:
                            v === "all" ? null : v === "true",
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos</SelectItem>
                        <SelectItem value="true">Con respuesta</SelectItem>
                        <SelectItem value="false">Sin respuesta</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <Button onClick={handleApplyFilters} className="w-full">
                    Aplicar filtros
                  </Button>
                </div>
              </PopoverContent>
            </Popover>
          </div>

          {/* Active filters display */}
          {activeFiltersCount > 0 && (
            <div className="flex flex-wrap gap-2">
              {filters.search && (
                <Badge variant="secondary" className="gap-1">
                  Búsqueda: {filters.search}
                  <X
                    className="h-3 w-3 cursor-pointer"
                    onClick={() => {
                      const updated = { ...localFilters, search: undefined };
                      setLocalFilters(updated);
                      onFiltersChange(updated);
                    }}
                  />
                </Badge>
              )}
              {filters.status?.map((status) => (
                <Badge key={status} variant="secondary" className="gap-1">
                  {statusOptions.find((o) => o.value === status)?.label}
                  <X
                    className="h-3 w-3 cursor-pointer"
                    onClick={() => toggleStatus(status)}
                  />
                </Badge>
              ))}
              {(filters.date_from || filters.date_to) && (
                <Badge variant="secondary" className="gap-1">
                  {filters.date_from && format(filters.date_from, "dd/MM/yyyy")} -
                  {filters.date_to && format(filters.date_to, "dd/MM/yyyy")}
                  <X
                    className="h-3 w-3 cursor-pointer"
                    onClick={() => {
                      const updated = {
                        ...localFilters,
                        date_from: undefined,
                        date_to: undefined,
                      };
                      setLocalFilters(updated);
                      onFiltersChange(updated);
                    }}
                  />
                </Badge>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
