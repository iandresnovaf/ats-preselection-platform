"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Mail,
  Phone,
  Send,
  RotateCcw,
  MoreHorizontal,
  Clock,
  CheckCircle,
  XCircle,
  HelpCircle,
  AlertCircle,
  Calendar,
  UserCheck,
} from "lucide-react";
import type { TrackedCandidate, ApplicationStatus } from "@/types/tracking";

interface KanbanBoardProps {
  candidates: Record<ApplicationStatus, TrackedCandidate[]>;
  onCandidateClick?: (candidate: TrackedCandidate) => void;
  onContactClick?: (candidate: TrackedCandidate) => void;
  onResendClick?: (candidate: TrackedCandidate) => void;
  onStatusChange?: (candidate: TrackedCandidate, status: ApplicationStatus) => void;
}

interface ColumnConfig {
  id: ApplicationStatus;
  title: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  borderColor: string;
}

const columns: ColumnConfig[] = [
  {
    id: "pending_contact",
    title: "Pendiente",
    icon: <AlertCircle className="h-4 w-4" />,
    color: "text-amber-600",
    bgColor: "bg-amber-50",
    borderColor: "border-amber-200",
  },
  {
    id: "contacted",
    title: "Contactado",
    icon: <Send className="h-4 w-4" />,
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
  },
  {
    id: "interested",
    title: "Interesado",
    icon: <CheckCircle className="h-4 w-4" />,
    color: "text-green-600",
    bgColor: "bg-green-50",
    borderColor: "border-green-200",
  },
  {
    id: "not_interested",
    title: "No Interesado",
    icon: <XCircle className="h-4 w-4" />,
    color: "text-red-600",
    bgColor: "bg-red-50",
    borderColor: "border-red-200",
  },
  {
    id: "no_response",
    title: "Sin Respuesta",
    icon: <HelpCircle className="h-4 w-4" />,
    color: "text-gray-600",
    bgColor: "bg-gray-50",
    borderColor: "border-gray-200",
  },
  {
    id: "scheduled",
    title: "Agendado",
    icon: <Calendar className="h-4 w-4" />,
    color: "text-purple-600",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-200",
  },
  {
    id: "hired",
    title: "Contratado",
    icon: <UserCheck className="h-4 w-4" />,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
    borderColor: "border-emerald-200",
  },
];

export function KanbanBoard({
  candidates,
  onCandidateClick,
  onContactClick,
  onResendClick,
}: KanbanBoardProps) {
  const [selectedColumn, setSelectedColumn] = useState<ApplicationStatus | null>(null);

  // Filter columns to show only those with candidates or all if none selected
  const visibleColumns = selectedColumn
    ? columns.filter((c) => c.id === selectedColumn)
    : columns;

  return (
    <div className="space-y-4">
      {/* Column filter */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={selectedColumn === null ? "default" : "outline"}
          size="sm"
          onClick={() => setSelectedColumn(null)}
        >
          Todas
        </Button>
        {columns.map((col) => (
          <Button
            key={col.id}
            variant={selectedColumn === col.id ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedColumn(col.id)}
            className={`${selectedColumn === col.id ? "" : col.color}`}
          >
            {col.icon}
            <span className="ml-1">{col.title}</span>
            <Badge variant="secondary" className="ml-1 text-xs">
              {(candidates[col.id] || []).length}
            </Badge>
          </Button>
        ))}
      </div>

      {/* Kanban columns */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {visibleColumns.map((column) => (
          <KanbanColumn
            key={column.id}
            column={column}
            candidates={candidates[column.id] || []}
            onCandidateClick={onCandidateClick}
            onContactClick={onContactClick}
            onResendClick={onResendClick}
          />
        ))}
      </div>
    </div>
  );
}

interface KanbanColumnProps {
  column: ColumnConfig;
  candidates: TrackedCandidate[];
  onCandidateClick?: (candidate: TrackedCandidate) => void;
  onContactClick?: (candidate: TrackedCandidate) => void;
  onResendClick?: (candidate: TrackedCandidate) => void;
}

function KanbanColumn({
  column,
  candidates,
  onCandidateClick,
  onContactClick,
  onResendClick,
}: KanbanColumnProps) {
  return (
    <Card className={`${column.bgColor} border-${column.borderColor}`}>
      <CardHeader className="pb-2">
        <CardTitle className={`text-sm font-semibold flex items-center gap-2 ${column.color}`}>
          {column.icon}
          {column.title}
          <Badge variant="secondary" className="ml-auto">
            {candidates.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ScrollArea className="h-[500px] pr-2">
          <div className="space-y-2">
            {candidates.map((candidate) => (
              <CandidateCard
                key={candidate.id}
                candidate={candidate}
                columnId={column.id}
                onClick={() => onCandidateClick?.(candidate)}
                onContact={() => onContactClick?.(candidate)}
                onResend={() => onResendClick?.(candidate)}
              />
            ))}
            {candidates.length === 0 && (
              <div className="text-center py-8 text-muted-foreground text-sm">
                Sin candidatos
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

interface CandidateCardProps {
  candidate: TrackedCandidate;
  columnId: ApplicationStatus;
  onClick?: () => void;
  onContact?: () => void;
  onResend?: () => void;
}

function CandidateCard({
  candidate,
  columnId,
  onClick,
  onContact,
  onResend,
}: CandidateCardProps) {
  const initials = `${candidate.first_name[0]}${candidate.last_name[0]}`.toUpperCase();

  const isMissingContact = columnId === "pending_contact" && (!candidate.email && !candidate.phone);
  const needsResend = columnId === "no_response" && (candidate.days_without_response || 0) >= 2;

  return (
    <Card
      className="cursor-pointer hover:shadow-md transition-shadow bg-white"
      onClick={onClick}
    >
      <CardContent className="p-3 space-y-2">
        <div className="flex items-start gap-2">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="text-xs bg-primary/10">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">
              {candidate.first_name} {candidate.last_name}
            </p>
            <p className="text-xs text-muted-foreground truncate">
              {candidate.role_title}
            </p>
          </div>
        </div>

        {/* Contact info status */}
        {isMissingContact && (
          <div className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 p-1.5 rounded">
            <AlertCircle className="h-3 w-3" />
            <span>Falta email/teléfono</span>
          </div>
        )}

        {/* Response time indicator */}
        {candidate.days_without_response && candidate.days_without_response > 0 && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>
              {candidate.days_without_response === 1
                ? "1 día sin resp."
                : `${candidate.days_without_response} días sin resp.`}
            </span>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-1 pt-1">
          {columnId === "pending_contact" && (
            <Button
              size="sm"
              variant="outline"
              className="flex-1 h-7 text-xs"
              onClick={(e) => {
                e.stopPropagation();
                onContact?.();
              }}
              disabled={isMissingContact}
            >
              <Mail className="h-3 w-3 mr-1" />
              Contactar
            </Button>
          )}
          {needsResend && (
            <Button
              size="sm"
              variant="outline"
              className="flex-1 h-7 text-xs"
              onClick={(e) => {
                e.stopPropagation();
                onResend?.();
              }}
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Reenviar
            </Button>
          )}
          {(candidate.email || candidate.phone) && (
            <div className="flex gap-1">
              {candidate.email && (
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7"
                  title={candidate.email}
                >
                  <Mail className="h-3 w-3" />
                </Button>
              )}
              {candidate.phone && (
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7"
                  title={candidate.phone}
                >
                  <Phone className="h-3 w-3" />
                </Button>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
