"use client";

import { useState } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  useRoleCandidates,
  useTrackingStats,
  useBulkActions,
  useCandidateActions,
} from "@/hooks/tracking/use-tracking";
import { useTrackingNotifications } from "@/hooks/tracking/use-notifications";
import { QuickActionsPanel } from "@/components/tracking/QuickActionsPanel";
import { StatsPanel } from "@/components/tracking/StatsPanel";
import { TrackingFilters } from "@/components/tracking/TrackingFilters";
import {
  ArrowLeft,
  Mail,
  Phone,
  Linkedin,
  Calendar,
  Clock,
  MessageSquare,
  CheckCircle,
  XCircle,
  MoreHorizontal,
  Send,
  RotateCcw,
  User,
  FileText,
} from "lucide-react";
import type {
  TrackedCandidate,
  ApplicationStatus,
  TrackingFilters as TrackingFiltersType,
} from "@/types/tracking";

const statusLabels: Record<ApplicationStatus, string> = {
  pending_contact: "Pendiente de contacto",
  contacted: "Contactado",
  interested: "Interesado",
  not_interested: "No interesado",
  no_response: "Sin respuesta",
  scheduled: "Entrevista agendada",
  completed: "Proceso completado",
  hired: "Contratado",
};

const statusColors: Record<ApplicationStatus, string> = {
  pending_contact: "bg-amber-100 text-amber-800",
  contacted: "bg-blue-100 text-blue-800",
  interested: "bg-green-100 text-green-800",
  not_interested: "bg-red-100 text-red-800",
  no_response: "bg-gray-100 text-gray-800",
  scheduled: "bg-purple-100 text-purple-800",
  completed: "bg-indigo-100 text-indigo-800",
  hired: "bg-emerald-100 text-emerald-800",
};

export default function RoleTrackingPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const roleId = params.role_id as string;
  const candidateId = searchParams.get("candidate");

  const [selectedCandidate, setSelectedCandidate] = useState<TrackedCandidate | null>(null);
  const [noteDialogOpen, setNoteDialogOpen] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [filters, setFilters] = useState<TrackingFiltersType>({
    status: undefined,
    search: undefined,
  });

  // Data fetching
  const { data: candidates, isLoading: candidatesLoading } = useRoleCandidates(roleId);
  const { data: stats, isLoading: statsLoading } = useTrackingStats(roleId);

  // Mutations
  const { contactMultiple, resendToNoResponse, updateStatus } = useBulkActions();
  const { updateCandidateStatus, addNote } = useCandidateActions();
  const notifications = useTrackingNotifications();

  // Filter candidates
  const filteredCandidates = candidates?.filter((c) => {
    if (filters.status && filters.status.length > 0 && !filters.status.includes(c.status)) {
      return false;
    }
    if (filters.search) {
      const search = filters.search.toLowerCase();
      const name = `${c.first_name} ${c.last_name}`.toLowerCase();
      const email = c.email?.toLowerCase() || "";
      if (!name.includes(search) && !email.includes(search)) {
        return false;
      }
    }
    return true;
  });

  // Group by status
  const byStatus = filteredCandidates?.reduce((acc, candidate) => {
    if (!acc[candidate.status]) {
      acc[candidate.status] = [];
    }
    acc[candidate.status].push(candidate);
    return acc;
  }, {} as Record<ApplicationStatus, TrackedCandidate[]>);

  // Handlers
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

  const handleStatusChange = (candidateId: string, status: ApplicationStatus) => {
    updateCandidateStatus.mutate(
      { candidateId, status },
      {
        onSuccess: () => {
          notifications.showSuccess(`Estado actualizado a: ${statusLabels[status]}`);
        },
        onError: (error) => {
          notifications.showError(error.message || "Error al actualizar estado");
        },
      }
    );
  };

  const handleAddNote = () => {
    if (!selectedCandidate || !noteText.trim()) return;

    addNote.mutate(
      { candidateId: selectedCandidate.id, note: noteText },
      {
        onSuccess: () => {
          notifications.showSuccess("Nota agregada correctamente");
          setNoteDialogOpen(false);
          setNoteText("");
        },
        onError: (error) => {
          notifications.showError(error.message || "Error al agregar nota");
        },
      }
    );
  };

  const pendingCandidates = candidates?.filter((c) => c.status === "pending_contact") || [];
  const noResponseCandidates = candidates?.filter((c) => c.status === "no_response") || [];

  // Pre-select candidate from URL
  if (candidateId && candidates && !selectedCandidate) {
    const candidate = candidates.find((c) => c.id === candidateId);
    if (candidate) {
      setSelectedCandidate(candidate);
    }
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" onClick={() => router.push("/dashboard/tracking")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Detalle de Vacante</h1>
            <p className="text-muted-foreground">
              {stats?.by_role?.[0]?.client_name} • {stats?.total_candidates || 0} candidatos
            </p>
          </div>
        </div>
        <QuickActionsPanel
          pendingCandidates={pendingCandidates}
          noResponseCandidates={noResponseCandidates}
          onContactPending={handleContactPending}
          onResendNoResponse={handleResendNoResponse}
          onViewReport={() => {}}
          isLoading={contactMultiple.isPending || resendToNoResponse.isPending}
        />
      </div>

      {/* Stats */}
      <StatsPanel stats={stats} isLoading={statsLoading} />

      {/* Filters */}
      <TrackingFilters
        filters={filters}
        onFiltersChange={setFilters}
        availableRoles={[]}
      />

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Candidate list */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Candidatos</span>
                <Badge variant="secondary">{filteredCandidates?.length || 0}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {candidatesLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-16" />
                  ))}
                </div>
              ) : filteredCandidates && filteredCandidates.length > 0 ? (
                <ScrollArea className="h-[600px]">
                  <div className="space-y-2">
                    {filteredCandidates.map((candidate) => (
                      <CandidateListItem
                        key={candidate.id}
                        candidate={candidate}
                        isSelected={selectedCandidate?.id === candidate.id}
                        onClick={() => setSelectedCandidate(candidate)}
                        onStatusChange={(status) => handleStatusChange(candidate.id, status)}
                      />
                    ))}
                  </div>
                </ScrollArea>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  No hay candidatos que coincidan con los filtros
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Candidate detail */}
        <div className="lg:col-span-1">
          {selectedCandidate ? (
            <CandidateDetailCard
              candidate={selectedCandidate}
              onAddNote={() => setNoteDialogOpen(true)}
              onContact={() => handleContactPending([selectedCandidate.id], "email")}
              onStatusChange={(status) => handleStatusChange(selectedCandidate.id, status)}
            />
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <User className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Selecciona un candidato para ver los detalles</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Add note dialog */}
      <Dialog open={noteDialogOpen} onOpenChange={setNoteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Agregar nota</DialogTitle>
            <DialogDescription>
              {selectedCandidate && (
                <>
                  Para: {selectedCandidate.first_name} {selectedCandidate.last_name}
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <Textarea
              placeholder="Escribe tu nota aquí..."
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              rows={4}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNoteDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleAddNote} disabled={!noteText.trim() || addNote.isPending}>
              {addNote.isPending ? "Guardando..." : "Guardar nota"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface CandidateListItemProps {
  candidate: TrackedCandidate;
  isSelected: boolean;
  onClick: () => void;
  onStatusChange: (status: ApplicationStatus) => void;
}

function CandidateListItem({ candidate, isSelected, onClick, onStatusChange }: CandidateListItemProps) {
  const initials = `${candidate.first_name[0]}${candidate.last_name[0]}`.toUpperCase();

  return (
    <div
      className={`p-3 rounded-lg cursor-pointer transition-colors ${
        isSelected ? "bg-primary/10 border border-primary/20" : "hover:bg-muted"
      }`}
      onClick={onClick}
    >
      <div className="flex items-center gap-3">
        <Avatar className="h-10 w-10">
          <AvatarFallback className="bg-primary/10">{initials}</AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-medium truncate">
              {candidate.first_name} {candidate.last_name}
            </p>
            <Badge className={`text-xs ${statusColors[candidate.status]}`}>
              {statusLabels[candidate.status]}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground truncate">
            {candidate.email || candidate.phone || "Sin información de contacto"}
          </p>
        </div>
      </div>
    </div>
  );
}

interface CandidateDetailCardProps {
  candidate: TrackedCandidate;
  onAddNote: () => void;
  onContact: () => void;
  onStatusChange: (status: ApplicationStatus) => void;
}

function CandidateDetailCard({
  candidate,
  onAddNote,
  onContact,
  onStatusChange,
}: CandidateDetailCardProps) {
  const initials = `${candidate.first_name[0]}${candidate.last_name[0]}`.toUpperCase();

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-4">
          <Avatar className="h-16 w-16">
            <AvatarFallback className="text-lg bg-primary/10">{initials}</AvatarFallback>
          </Avatar>
          <div>
            <CardTitle className="text-xl">
              {candidate.first_name} {candidate.last_name}
            </CardTitle>
            <Badge className={`mt-1 ${statusColors[candidate.status]}`}>
              {statusLabels[candidate.status]}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Contact info */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Información de contacto</h4>
          <div className="space-y-2">
            {candidate.email ? (
              <div className="flex items-center gap-2 text-sm">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <a href={`mailto:${candidate.email}`} className="text-blue-600 hover:underline">
                  {candidate.email}
                </a>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-sm text-amber-600">
                <Mail className="h-4 w-4" />
                <span>Falta email</span>
              </div>
            )}
            {candidate.phone ? (
              <div className="flex items-center gap-2 text-sm">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <span>{candidate.phone}</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-sm text-amber-600">
                <Phone className="h-4 w-4" />
                <span>Falta teléfono</span>
              </div>
            )}
            {candidate.linkedin_url && (
              <div className="flex items-center gap-2 text-sm">
                <Linkedin className="h-4 w-4 text-muted-foreground" />
                <a
                  href={candidate.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline truncate"
                >
                  LinkedIn
                </a>
              </div>
            )}
          </div>
        </div>

        <Separator />

        {/* Timeline info */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Timeline</h4>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span>Registrado: {new Date(candidate.created_at).toLocaleDateString("es-ES")}</span>
            </div>
            {candidate.last_contact_at && (
              <div className="flex items-center gap-2">
                <Send className="h-4 w-4 text-muted-foreground" />
                <span>
                  Último contacto: {new Date(candidate.last_contact_at).toLocaleDateString("es-ES")}
                </span>
              </div>
            )}
            {candidate.response_at && (
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                <span>
                  Respondió: {new Date(candidate.response_at).toLocaleDateString("es-ES")}
                </span>
              </div>
            )}
            {candidate.days_without_response !== undefined && candidate.days_without_response > 0 && (
              <div className="flex items-center gap-2 text-amber-600">
                <Clock className="h-4 w-4" />
                <span>{candidate.days_without_response} días sin respuesta</span>
              </div>
            )}
          </div>
        </div>

        <Separator />

        {/* Notes */}
        {candidate.notes && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground">Notas</h4>
            <p className="text-sm bg-muted p-3 rounded-lg">{candidate.notes}</p>
          </div>
        )}

        {/* Response message */}
        {candidate.response_message && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground">Mensaje de respuesta</h4>
            <p className="text-sm bg-green-50 p-3 rounded-lg">{candidate.response_message}</p>
          </div>
        )}

        {/* Actions */}
        <div className="space-y-2 pt-2">
          <h4 className="text-sm font-medium text-muted-foreground">Acciones</h4>
          <div className="grid grid-cols-2 gap-2">
            <Button variant="outline" size="sm" onClick={onContact}>
              <Send className="h-4 w-4 mr-2" />
              Contactar
            </Button>
            <Button variant="outline" size="sm" onClick={onAddNote}>
              <FileText className="h-4 w-4 mr-2" />
              Agregar nota
            </Button>
          </div>
          <Select onValueChange={(v) => onStatusChange(v as ApplicationStatus)}>
            <SelectTrigger>
              <SelectValue placeholder="Cambiar estado..." />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(statusLabels).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}
