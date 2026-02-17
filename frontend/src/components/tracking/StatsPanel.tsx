"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Users,
  MessageCircle,
  ThumbsUp,
  Clock,
  TrendingUp,
  Target,
} from "lucide-react";
import type { TrackingStats } from "@/types/tracking";

interface StatsPanelProps {
  stats: TrackingStats | undefined;
  isLoading?: boolean;
}

export function StatsPanel({ stats, isLoading = false }: StatsPanelProps) {
  if (isLoading || !stats) {
    return <StatsPanelSkeleton />;
  }

  const metrics = [
    {
      label: "Total Candidatos",
      value: stats.total_candidates,
      icon: <Users className="h-5 w-5" />,
      color: "text-blue-600",
      bgColor: "bg-blue-50",
      description: "En todas las vacantes",
    },
    {
      label: "Tasa de Respuesta",
      value: stats.response_rate,
      icon: <MessageCircle className="h-5 w-5" />,
      color: "text-purple-600",
      bgColor: "bg-purple-50",
      description: "% que respondieron",
    },
    {
      label: "Tasa de Interés",
      value: stats.interest_rate,
      icon: <ThumbsUp className="h-5 w-5" />,
      color: "text-green-600",
      bgColor: "bg-green-50",
      description: "% interesados",
    },
    {
      label: "Tiempo Promedio",
      value: stats.avg_response_time,
      icon: <Clock className="h-5 w-5" />,
      color: "text-amber-600",
      bgColor: "bg-amber-50",
      description: "Tiempo de respuesta",
    },
    {
      label: "Tasa de Conversión",
      value: stats.conversion_rate,
      icon: <TrendingUp className="h-5 w-5" />,
      color: "text-emerald-600",
      bgColor: "bg-emerald-50",
      description: "% contratados",
    },
  ];

  return (
    <div className="space-y-4">
      {/* Main metrics grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {metrics.map((metric) => (
          <MetricCard key={metric.label} metric={metric} />
        ))}
      </div>

      {/* Role breakdown */}
      {stats.by_role && stats.by_role.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Target className="h-5 w-5" />
              Progreso por Vacante
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats.by_role.map((role) => (
                <div key={role.role_id} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">{role.role_title}</span>
                    <span className="text-muted-foreground">
                      {role.stats.total_candidates} candidatos
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Progress value={role.progress_percentage} className="flex-1 h-2" />
                    <span className="text-sm font-medium w-10 text-right">
                      {role.progress_percentage}%
                    </span>
                  </div>
                  <div className="flex gap-2 text-xs text-muted-foreground">
                    <span className="text-green-600">
                      {role.stats.interested} interesados
                    </span>
                    <span>•</span>
                    <span className="text-amber-600">
                      {role.stats.pending_contact} pendientes
                    </span>
                    <span>•</span>
                    <span className="text-blue-600">
                      {role.stats.scheduled + role.stats.hired} en proceso
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

interface MetricCardProps {
  metric: {
    label: string;
    value: string | number;
    icon: React.ReactNode;
    color: string;
    bgColor: string;
    description: string;
  };
}

function MetricCard({ metric }: MetricCardProps) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className={`p-2 rounded-lg ${metric.bgColor} ${metric.color}`}>
            {metric.icon}
          </div>
        </div>
        <div className="mt-3">
          <p className="text-2xl font-bold">{metric.value}</p>
          <p className="text-sm font-medium text-foreground">{metric.label}</p>
          <p className="text-xs text-muted-foreground">{metric.description}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function StatsPanelSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4 space-y-3">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <Skeleton className="h-8 w-16" />
              <Skeleton className="h-4 w-24" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
