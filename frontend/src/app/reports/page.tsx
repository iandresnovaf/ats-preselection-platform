"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useRoles } from "@/hooks/use-headhunting";

export default function ReportsPage() {
  const { data: roles, isLoading } = useRoles();

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Reportería</h1>
        <p className="text-gray-600">
          Dashboard de métricas y análisis de procesos de selección
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Procesos Activos
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{isLoading ? "-" : roles?.total || 0}</div>
            <p className="text-xs text-green-600 mt-1">↑ 20% este mes</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Candidatos en Terna
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">3</div>
            <p className="text-xs text-green-600 mt-1">↑ 2 vs mes anterior</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Contratados
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">1</div>
            <p className="text-xs text-gray-500 mt-1">Este mes</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Alertas Pendientes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">2</div>
            <p className="text-xs text-red-600 mt-1">Requieren atención</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Funnel de Conversión</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { stage: "Sourcing", count: 5, color: "bg-blue-500" },
                { stage: "Shortlist", count: 5, color: "bg-blue-400" },
                { stage: "Terna", count: 3, color: "bg-blue-300" },
                { stage: "Interview", count: 1, color: "bg-blue-200" },
                { stage: "Offer", count: 1, color: "bg-yellow-400" },
                { stage: "Hired", count: 1, color: "bg-green-500" },
              ].map((item) => (
                <div key={item.stage} className="flex items-center gap-4">
                  <div className="w-24 text-sm font-medium">{item.stage}</div>
                  <div className="flex-1 h-8 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${item.color} transition-all duration-500`}
                      style={{ width: `${(item.count / 5) * 100}%` }}
                    />
                  </div>
                  <div className="w-8 text-right font-bold">{item.count}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Vacantes por Cliente</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p>Cargando...</p>
            ) : (
              <div className="space-y-4">
                {roles?.items?.map((role: any) => (
                  <div
                    key={role.role_id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div>
                      <p className="font-medium">{role.role_title}</p>
                      <p className="text-sm text-gray-500">
                        {role.client?.client_name}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          role.status === "open"
                            ? "bg-green-100 text-green-800"
                            : role.status === "hold"
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {role.status}
                      </span>
                      <Button variant="ghost" size="sm">
                        Ver
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-8 flex justify-end gap-4">
        <Button variant="outline">📊 Exportar CSV</Button>
        <Button variant="outline">📄 Exportar PDF</Button>
      </div>
    </div>
  );
}
