"use client";

import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, Briefcase, FileText, Settings } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const { user } = useAuthStore();

  const stats = [
    { name: "Usuarios", value: "12", icon: Users, href: "/dashboard/users" },
    { name: "Ofertas", value: "8", icon: Briefcase, href: "/dashboard/jobs" },
    { name: "Candidatos", value: "156", icon: FileText, href: "/dashboard/candidates" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Bienvenido, {user?.fullName || user?.email}
        </h1>
        <p className="text-gray-600 mt-2">
          Panel de control del ATS Preselection Platform
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat) => (
          <Link key={stat.name} href={stat.href}>
            <Card className="hover:shadow-lg transition-shadow cursor-pointer">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">
                  {stat.name}
                </CardTitle>
                <stat.icon className="h-4 w-4 text-gray-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Acceso Rápido</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link href="/config">
              <Button variant="outline" className="w-full justify-start">
                <Settings className="mr-2 h-4 w-4" />
                Configuración del Sistema
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Estado del Sistema</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">Backend API</span>
                <span className="text-sm text-green-600 font-medium">Operativo</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Base de Datos</span>
                <span className="text-sm text-green-600 font-medium">Conectada</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
