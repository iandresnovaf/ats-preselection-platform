"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useApplications } from "@/hooks/use-headhunting";
import { useState } from "react";
import Link from "next/link";
import { FileText, CheckCircle, Clock, AlertCircle, Loader2 } from "lucide-react";

export default function EvaluationsDashboardPage() {
  const { data: applications, isLoading } = useApplications();
  const [selectedFilter, setSelectedFilter] = useState<string>("all");

  // Filter applications that have assessments
  const applicationsWithAssessments = applications?.items?.filter(
    (app: any) => app.assessments_count > 0 || app.stage === "terna" || app.stage === "interview"
  ) || [];

  const filteredApplications = selectedFilter === "all" 
    ? applicationsWithAssessments
    : applicationsWithAssessments.filter((app: any) => app.stage === selectedFilter);

  const stats = {
    total: applicationsWithAssessments.length,
    pending: applicationsWithAssessments.filter((app: any) => !app.overall_score).length,
    completed: applicationsWithAssessments.filter((app: any) => app.overall_score).length,
    inReview: applicationsWithAssessments.filter((app: any) => app.stage === "terna").length,
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Evaluaciones</h1>
        <p className="text-gray-600">
          Gestiona las evaluaciones psicométricas y técnicas de los candidatos
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Total Evaluaciones</p>
            <p className="text-2xl font-bold">{stats.total}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Pendientes</p>
            <p className="text-2xl font-bold text-yellow-600">{stats.pending}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Completadas</p>
            <p className="text-2xl font-bold text-green-600">{stats.completed}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">En Revisión</p>
            <p className="text-2xl font-bold text-blue-600">{stats.inReview}</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-6">
        {[
          { value: "all", label: "Todas" },
          { value: "sourcing", label: "Sourcing" },
          { value: "shortlist", label: "Shortlist" },
          { value: "terna", label: "En Terna" },
          { value: "interview", label: "Entrevista" },
        ].map((filter) => (
          <Button
            key={filter.value}
            variant={selectedFilter === filter.value ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedFilter(filter.value)}
          >
            {filter.label}
          </Button>
        ))}
      </div>

      {/* Evaluations List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : filteredApplications.length > 0 ? (
        <div className="space-y-4">
          {filteredApplications.map((app: any) => (
            <Card key={app.application_id}>
              <CardContent className="p-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-lg">
                        {app.candidate?.full_name}
                      </h3>
                      <Badge 
                        variant={app.overall_score ? "default" : "secondary"}
                        className={app.overall_score ? "bg-green-100 text-green-800" : ""}
                      >
                        {app.overall_score ? "Completado" : "Pendiente"}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-500 mb-1">
                      {app.role?.role_title} - {app.role?.client?.client_name}
                    </p>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="flex items-center gap-1">
                        <FileText className="w-4 h-4" />
                        {app.assessments_count || 0} evaluaciones
                      </span>
                      <span className="flex items-center gap-1">
                        <AlertCircle className="w-4 h-4" />
                        {app.flags_count || 0} flags
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    {app.overall_score ? (
                      <div className="text-center">
                        <p className="text-sm text-gray-500">Score</p>
                        <p className={`text-2xl font-bold ${
                          app.overall_score >= 80 ? "text-green-600" :
                          app.overall_score >= 60 ? "text-yellow-600" :
                          "text-red-600"
                        }`}>
                          {app.overall_score}
                        </p>
                      </div>
                    ) : (
                      <div className="text-center">
                        <Clock className="w-8 h-8 text-yellow-500 mx-auto" />
                        <p className="text-xs text-gray-500 mt-1">Pendiente</p>
                      </div>
                    )}
                    <Link href={`/applications/${app.application_id}`}>
                      <Button variant="outline">
                        Ver Detalle
                      </Button>
                    </Link>
                  </div>
                </div>

                {app.overall_score && (
                  <div className="mt-4 pt-4 border-t">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-gray-500">Progreso de Evaluación</span>
                      <span className="font-medium">{app.assessments_count || 0} completadas</span>
                    </div>
                    <Progress 
                      value={Math.min((app.assessments_count || 0) * 33, 100)} 
                      className="h-2"
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <FileText className="w-12 h-12 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-900">
            No hay evaluaciones
          </h3>
          <p className="text-gray-500 mt-2">
            Las evaluaciones aparecerán aquí cuando los candidatos tengan aplicaciones activas
          </p>
        </div>
      )}
    </div>
  );
}
