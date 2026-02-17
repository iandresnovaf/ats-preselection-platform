"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CheckCircle,
  XCircle,
  Send,
  RefreshCw,
  UserPlus,
  MessageSquare,
  Calendar,
  MoreHorizontal,
} from "lucide-react";
import type { ActivityItem, ActivityType } from "@/types/tracking";

interface RecentActivityFeedProps {
  activities: ActivityItem[] | undefined;
  isLoading?: boolean;
  limit?: number;
  onViewAll?: () => void;
}

export function RecentActivityFeed({
  activities,
  isLoading = false,
  limit = 20,
  onViewAll,
}: RecentActivityFeedProps) {
  const displayActivities = activities?.slice(0, limit) || [];

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <RefreshCw className="h-5 w-5" />
            Actividad Reciente
          </CardTitle>
          {onViewAll && activities && activities.length > limit && (
            <Badge
              variant="outline"
              className="cursor-pointer hover:bg-secondary"
              onClick={onViewAll}
            >
              Ver todo
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-2">
          <div className="space-y-3">
            {isLoading ? (
              // Loading skeletons
              Array.from({ length: 5 }).map((_, i) => (
                <ActivitySkeleton key={i} />
              ))
            ) : displayActivities.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <MessageSquare className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No hay actividad reciente</p>
              </div>
            ) : (
              displayActivities.map((activity) => (
                <ActivityItem key={activity.id} activity={activity} />
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

interface ActivityItemProps {
  activity: ActivityItem;
}

function ActivityItem({ activity }: ActivityItemProps) {
  const { icon, color, bgColor } = getActivityConfig(activity.type);
  const timeAgo = formatTimeAgo(activity.created_at);

  return (
    <div className="flex gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors">
      <div className={`flex-shrink-0 w-8 h-8 rounded-full ${bgColor} flex items-center justify-center`}>
        <span className={color}>{icon}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm">
          <span className="font-medium">{activity.candidate_name}</span>{" "}
          <span className="text-muted-foreground">
            {getActivityMessage(activity)}
          </span>
        </p>
        <div className="flex items-center gap-2 mt-1">
          <Badge variant="secondary" className="text-xs">
            {activity.role_title}
          </Badge>
          <span className="text-xs text-muted-foreground">{timeAgo}</span>
        </div>
        {activity.message && (
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
            &ldquo;{activity.message}&rdquo;
          </p>
        )}
      </div>
    </div>
  );
}

function ActivitySkeleton() {
  return (
    <div className="flex gap-3 p-3">
      <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
      </div>
    </div>
  );
}

function getActivityConfig(type: ActivityType): {
  icon: React.ReactNode;
  color: string;
  bgColor: string;
} {
  switch (type) {
    case "candidate_responded":
      return {
        icon: <CheckCircle className="h-4 w-4" />,
        color: "text-green-600",
        bgColor: "bg-green-100",
      };
    case "message_sent":
      return {
        icon: <Send className="h-4 w-4" />,
        color: "text-blue-600",
        bgColor: "bg-blue-100",
      };
    case "status_changed":
      return {
        icon: <RefreshCw className="h-4 w-4" />,
        color: "text-purple-600",
        bgColor: "bg-purple-100",
      };
    case "contact_attempt":
      return {
        icon: <UserPlus className="h-4 w-4" />,
        color: "text-amber-600",
        bgColor: "bg-amber-100",
      };
    case "reminder_sent":
      return {
        icon: <Send className="h-4 w-4" />,
        color: "text-orange-600",
        bgColor: "bg-orange-100",
      };
    case "interview_scheduled":
      return {
        icon: <Calendar className="h-4 w-4" />,
        color: "text-indigo-600",
        bgColor: "bg-indigo-100",
      };
    default:
      return {
        icon: <MoreHorizontal className="h-4 w-4" />,
        color: "text-gray-600",
        bgColor: "bg-gray-100",
      };
  }
}

function getActivityMessage(activity: ActivityItem): string {
  switch (activity.type) {
    case "candidate_responded":
      const statusLabel = activity.new_status 
        ? getStatusLabel(activity.new_status)
        : "";
      return `respondió: ${statusLabel}`;
    case "message_sent":
      return "recibió un mensaje";
    case "status_changed":
      const from = activity.previous_status 
        ? getStatusLabel(activity.previous_status)
        : "";
      const to = activity.new_status 
        ? getStatusLabel(activity.new_status)
        : "";
      return from 
        ? `cambió de ${from} a ${to}`
        : `marcado como ${to}`;
    case "contact_attempt":
      return "fue contactado por primera vez";
    case "reminder_sent":
      return "recibió un recordatorio";
    case "interview_scheduled":
      return "tiene una entrevista agendada";
    default:
      return "tuvo actividad";
  }
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending_contact: "Pendiente",
    contacted: "Contactado",
    interested: "Interesado",
    not_interested: "No Interesado",
    no_response: "Sin Respuesta",
    scheduled: "Agendado",
    completed: "Completado",
    hired: "Contratado",
  };
  return labels[status] || status;
}

function formatTimeAgo(date: string): string {
  const diff = Date.now() - new Date(date).getTime();
  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (minutes < 1) return "Hace un momento";
  if (minutes === 1) return "Hace 1 minuto";
  if (minutes < 60) return `Hace ${minutes} minutos`;
  if (hours === 1) return "Hace 1 hora";
  if (hours < 24) return `Hace ${hours} horas`;
  if (days === 1) return "Ayer";
  if (days < 7) return `Hace ${days} días`;
  return new Date(date).toLocaleDateString("es-ES", {
    day: "numeric",
    month: "short",
  });
}
