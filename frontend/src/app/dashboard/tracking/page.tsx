"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useVacanteSummaries,
  useTrackingData,
  useBulkActions,
  useRecentActivity,
  useTrackingStats,
} from "@/hooks/tracking/use-tracking";
import { useTrackingNotifications, useAttentionChecker } from "@/hooks/tracking/use-notifications";
import { VacanteCard } from "@/components/tracking/VacanteCard";
import { KanbanBoard } from "@/components/tracking/KanbanBoard";
import { QuickActionsPanel } from "@/components/tracking/QuickActionsPanel";
import { RecentActivityFeed } from "@/components/tracking/RecentActivityFeed";
import { TrackingFilters } from "@/components/tracking/TrackingFilters";
import { StatsPanel } from "@/components/tracking/StatsPanel";
import { LayoutGrid, List, BarChart3, Activity } from "lucide-react";
import type { TrackedCandidate, TrackingFilters as TrackingFiltersType } from "@/types/tracking";

export default function TrackingDashboardPage() {
  const router = useRouter();
  const [selectedRoleId, setSelectedRoleId] = useState<string | undefined>(undefined);
  const [viewMode, setViewMode] = useState<"cards" | "kanban" | "stats">("cards");
  const [filters, setFilters] = useState<TrackingFiltersType>({
    role_id: undefined,
    status: undefined,
    date_from: undefined,
    date_to: undefined,
    has_response: null,
    search: undefined,
  });

  // Data fetching
  const { data: vacantes, isLoading: vacantesLoading } = useVacanteSummaries();
  const { data: trackingData, isLoading: trackingLoading } = useTrackingData(selectedRoleId);
  const { data: activities, isLoading: activitiesLoading } = useRecentActivity(20);
  const { data: stats, isLoading: statsLoading } = useTrackingStats(selectedRoleId);

  // Mutations
  const { contactMultiple, resendToNoResponse } = useBulkActions();
  const notifications = useTrackingNotifications();

  // Check for candidates needing attention
  const allCandidates = trackingData
    ? Object.values(trackingData.by_status).flat()
    : undefined;
  useAttentionChecker(allCandidates);

  // Handlers
  const handleRoleSelect = (roleId: string) => {
    setSelectedRoleId(roleId === "all" ? undefined : roleId);
    setFilters({ ...filters, role_id: roleId === "all" ? undefined : roleId });
  };

  const handleVacanteClick = (roleId: string) => {
    router.push(`/dashboard/tracking/${roleId}`);
  };

  const handleContactPending = (candidateIds: string[], channel: "email" | "whatsapp", message?: string) => {
    contactMultiple.mutate(
      { candidate_ids: candidateIds, channel, message_template: message },
      {
        onSuccess: (result) => {
          notifications.showBulkActionComplete("Contactar", result.processed, result.failed);
        },
        onError: (error) => {
          notifications.showError(error.message || "Error al contactar candidatos");
        },
      }
    );
  };

  const handleResendNoResponse = (candidateIds: string[], message?: string) => {
    resendToNoResponse.mutate(
      { candidate_ids: candidateIds, custom_message: message },
      {
        onSuccess: (result) => {
          notifications.showBulkActionComplete("Reenviar", result.processed, result.failed);
        },
        onError: (error) => {
          notifications.showError(error.message || "Error al reenviar mensajes");
        },
      }
    );
  };

  const handleCandidateClick = (candidate: TrackedCandidate) => {
    router.push(`/dashboard/tracking/${candidate.role_id}?candidate=${candidate.id}`);
  };

  // Get candidates for quick actions
  const pendingCandidates = trackingData?.by_status?.pending_contact || [];
  const noResponseCandidates = trackingData?.by_status?.no_response || [];

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Seguimiento de Candidatos</h1>
          <p className="text-muted-foreground">
            Gestiona y da seguimiento a tus candidatos por vacante
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedRoleId || "all"} onValueChange={handleRoleSelect}>
            <SelectTrigger className="w-[250px]">
              <SelectValue placeholder="Todas las vacantes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas las vacantes</SelectItem>
              {vacantes?.map((v) => (
                <SelectItem key={v.role_id} value={v.role_id}>
                  {v.role_title} ({v.client_name})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Filters */}
      <TrackingFilters
        filters={filters}
        onFiltersChange={setFilters}
        availableRoles={vacantes?.map((v) => ({ id: v.role_id, title: v.role_title }))}
      />

      {/* Quick Actions & Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <QuickActionsPanel
            pendingCandidates={pendingCandidates}
            noResponseCandidates={noResponseCandidates}
            onContactPending={handleContactPending}
            onResendNoResponse={handleResendNoResponse}
            onViewReport={() => setViewMode("stats")}
            isLoading={contactMultiple.isPending || resendToNoResponse.isPending}
          />
          <RecentActivityFeed
            activities={activities}
            isLoading={activitiesLoading}
            onViewAll={() => setViewMode("stats")}
          />
        </div>

        {/* Main content */}
        <div className="lg:col-span-2">
          <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as typeof viewMode)}>
            <TabsList className="mb-4">
              <TabsTrigger value="cards" className="gap-2">
                <LayoutGrid className="h-4 w-4" />
                Tarjetas
              </TabsTrigger>
              <TabsTrigger value="kanban" className="gap-2">
                <List className="h-4 w-4" />
                Pipeline
              </TabsTrigger>
              <TabsTrigger value="stats" className="gap-2">
                <BarChart3 className="h-4 w-4" />
                Estadísticas
              </TabsTrigger>
            </TabsList>

            <TabsContent value="cards" className="space-y-4">
              {vacantesLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-48" />
                  ))}
                </div>
              ) : vacantes && vacantes.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {vacantes.map((vacante) => (
                    <VacanteCard
                      key={vacante.role_id}
                      role={vacante}
                      onClick={() => handleVacanteClick(vacante.role_id)}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No hay vacantes activas con candidatos</p>
                  <Button
                    variant="outline"
                    className="mt-4"
                    onClick={() => router.push("/roles/new")}
                  >
                    Crear nueva vacante
                  </Button>
                </div>
              )}
            </TabsContent>

            <TabsContent value="kanban">
              {trackingLoading ? (
                <Skeleton className="h-[600px]" />
              ) : trackingData ? (
                <KanbanBoard
                  candidates={trackingData.by_status}
                  onCandidateClick={handleCandidateClick}
                  onContactClick={(c) => handleContactPending([c.id], "email")}
                  onResendClick={(c) => handleResendNoResponse([c.id])}
                />
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  Selecciona una vacante para ver el pipeline
                </div>
              )}
            </TabsContent>

            <TabsContent value="stats">
              <StatsPanel stats={stats} isLoading={statsLoading} />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
