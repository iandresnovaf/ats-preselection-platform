"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { HeatmapTable } from "@/components/headhunting/HeatmapTable";
import { ScoreBadge } from "@/components/headhunting/ScoreBadge";
import { FlagCard } from "@/components/headhunting/FlagCard";
import { useRoles, useApplications } from "@/hooks/use-headhunting";

export default function TernaComparatorPage() {
  const [selectedRole, setSelectedRole] = useState<string>("");
  const [selectedCandidates, setSelectedCandidates] = useState<string[]>([]);
  
  const { data: roles, isLoading: rolesLoading } = useRoles();
  const { data: applications, isLoading: appsLoading } = useApplications({
    role_id: selectedRole,
  });

  const toggleCandidate = (candidateId: string) => {
    setSelectedCandidates((prev) =>
      prev.includes(candidateId)
        ? prev.filter((id) => id !== candidateId)
        : [...prev, candidateId]
    );
  };

  const selectedApplications = applications?.items?.filter((app: any) =>
    selectedCandidates.includes(app.candidate_id)
  ) || [];

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Comparador de Terna</h1>
        <p className="text-gray-600">
          Compara candidatos lado a lado para tomar la mejor decisión
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Seleccionar Vacante</CardTitle>
        </CardHeader>
        <CardContent>
          <Select value={selectedRole} onValueChange={setSelectedRole}>
            <SelectTrigger className="w-full md:w-96">
              <SelectValue placeholder="Selecciona una vacante..." />
            </SelectTrigger>
            <SelectContent>
              {rolesLoading ? (
                <SelectItem value="loading" disabled>
                  Cargando...
                </SelectItem>
              ) : (
                roles?.items?.map((role: any) => (
                  <SelectItem key={role.role_id} value={role.role_id}>
                    {role.role_title} - {role.client?.client_name}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {selectedRole && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Seleccionar Candidatos para Comparar</CardTitle>
          </CardHeader>
          <CardContent>
            {appsLoading ? (
              <p>Cargando candidatos...</p>
            ) : (
              <div className="space-y-3">
                {applications?.items?.map((app: any) => (
                  <div
                    key={app.application_id}
                    className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-gray-50"
                  >
                    <Checkbox
                      checked={selectedCandidates.includes(app.candidate_id)}
                      onCheckedChange={() => toggleCandidate(app.candidate_id)}
                    />
                    <div className="flex-1">
                      <p className="font-medium">{app.candidate?.full_name}</p>
                      <p className="text-sm text-gray-500">
                        Score: {app.overall_score || "N/A"} | Etapa: {app.stage}
                      </p>
                    </div>
                    <ScoreBadge score={app.overall_score} />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {selectedApplications.length > 0 && (
        <>
          <Card className="mb-6">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Comparación de Candidatos</CardTitle>
              <Button variant="outline">
                📄 Generar Reporte PDF
              </Button>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr>
                      <th className="text-left p-3 border-b">Dimensión</th>
                      {selectedApplications.map((app: any) => (
                        <th key={app.application_id} className="p-3 border-b text-center">
                          {app.candidate?.full_name}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="p-3 border-b font-medium">Score General</td>
                      {selectedApplications.map((app: any) => (
                        <td key={app.application_id} className="p-3 border-b text-center">
                          <ScoreBadge score={app.overall_score} />
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 border-b font-medium">Etapa</td>
                      {selectedApplications.map((app: any) => (
                        <td key={app.application_id} className="p-3 border-b text-center">
                          <span className="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">
                            {app.stage}
                          </span>
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 border-b font-medium">Entrevistas</td>
                      {selectedApplications.map((app: any) => (
                        <td key={app.application_id} className="p-3 border-b text-center">
                          {app.interviews_count || 0}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 border-b font-medium">Evaluaciones</td>
                      {selectedApplications.map((app: any) => (
                        <td key={app.application_id} className="p-3 border-b text-center">
                          {app.assessments_count || 0}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 border-b font-medium">Flags</td>
                      {selectedApplications.map((app: any) => (
                        <td key={app.application_id} className="p-3 border-b text-center">
                          {app.flags_count || 0 > 0 ? (
                            <span className="text-red-600 font-bold">
                              {app.flags_count} 🚩
                            </span>
                          ) : (
                            <span className="text-green-600">✓</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Resumen Ejecutivo</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {selectedApplications
                  .sort((a: any, b: any) => (b.overall_score || 0) - (a.overall_score || 0))
                  .map((app: any, index: number) => (
                    <div
                      key={app.application_id}
                      className={`p-4 rounded-lg border ${
                        index === 0 ? "border-green-500 bg-green-50" : "border-gray-200"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-bold text-lg">
                          {index === 0 ? "🥇" : index === 1 ? "🥈" : "🥉"} {" "}
                          {app.candidate?.full_name}
                        </h3>
                        <ScoreBadge score={app.overall_score} />
                      </div>
                      <p className="text-sm text-gray-600">
                        <strong>Fortalezas:</strong> {app.notes || "En evaluación"}
                      </p>
                      <p className="text-sm text-gray-600 mt-1">
                        <strong>Riesgos:</strong> {app.flags_count || 0} flags detectados
                      </p>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
