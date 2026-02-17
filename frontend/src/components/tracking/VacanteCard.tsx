"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Users, Clock, CheckCircle, XCircle, HelpCircle } from "lucide-react";
import type { VacanteSummary } from "@/types/tracking";

interface VacanteCardProps {
  role: VacanteSummary;
  onClick?: () => void;
}

export function VacanteCard({ role, onClick }: VacanteCardProps) {
  const {
    role_title,
    client_name,
    stats,
    progress_percentage,
    last_activity_at,
  } = role;

  const formatLastActivity = (date: string | undefined) => {
    if (!date) return "Sin actividad";
    const diff = Date.now() - new Date(date).getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);

    if (hours < 1) return "Hace minutos";
    if (hours < 24) return `Hace ${hours}h`;
    if (days === 1) return "Ayer";
    return `Hace ${days} días`;
  };

  return (
    <Card 
      className="cursor-pointer hover:shadow-lg transition-shadow duration-200"
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-lg font-semibold line-clamp-1">
              {role_title}
            </CardTitle>
            <p className="text-sm text-muted-foreground">{client_name}</p>
          </div>
          <Badge variant="outline" className="text-xs">
            {formatLastActivity(last_activity_at)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Progreso</span>
            <span>{progress_percentage}%</span>
          </div>
          <Progress value={progress_percentage} className="h-2" />
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-4 gap-2">
          <StatItem
            icon={<Users className="h-3 w-3" />}
            label="Total"
            value={stats.total_candidates}
            color="text-blue-600"
          />
          <StatItem
            icon={<Clock className="h-3 w-3" />}
            label="Pendientes"
            value={stats.pending_contact}
            color="text-amber-600"
            highlight={stats.pending_contact > 0}
          />
          <StatItem
            icon={<CheckCircle className="h-3 w-3" />}
            label="Interesados"
            value={stats.interested}
            color="text-green-600"
          />
          <StatItem
            icon={<HelpCircle className="h-3 w-3" />}
            label="Sin resp."
            value={stats.no_response}
            color="text-gray-600"
            highlight={stats.no_response > 3}
          />
        </div>

        {/* Detailed stats */}
        <div className="pt-2 border-t border-border">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Contactados:</span>
              <span className="font-medium">{stats.contacted}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">No interesados:</span>
              <span className="font-medium text-red-600">{stats.not_interested}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Agendados:</span>
              <span className="font-medium">{stats.scheduled}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Contratados:</span>
              <span className="font-medium text-green-600">{stats.hired}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface StatItemProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
  highlight?: boolean;
}

function StatItem({ icon, label, value, color, highlight }: StatItemProps) {
  return (
    <div
      className={`flex flex-col items-center p-2 rounded-lg bg-muted/50 ${
        highlight ? "ring-1 ring-amber-400 bg-amber-50" : ""
      }`}
    >
      <div className={`flex items-center gap-1 ${color}`}>
        {icon}
        <span className="font-bold text-sm">{value}</span>
      </div>
      <span className="text-[10px] text-muted-foreground">{label}</span>
    </div>
  );
}
