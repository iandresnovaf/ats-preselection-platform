"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuGroup,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import {
  LayoutDashboard,
  Settings,
  Users,
  LogOut,
  User,
  Briefcase,
  ChevronDown,
  Building2,
  Target,
  BarChart3,
  GitCompare,
  Plus,
  Building,
  UserPlus,
  Menu,
  FileText,
  PieChart,
  ChevronRight,
  Mail,
} from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, isAuthenticated } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  // Don't show navbar on login page
  if (pathname === "/login" || !isAuthenticated) {
    return null;
  }

  const isAdmin = user?.role === "super_admin";

  return (
    <nav className="border-b bg-background">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/dashboard" className="flex items-center gap-2">
            <BrandingLogo />
          </Link>

          {/* Navigation Menu */}
          <div className="flex items-center gap-2">
            {/* Menú Principal */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="flex items-center gap-2 px-4"
                >
                  <Menu className="h-5 w-5" />
                  <span className="hidden sm:inline">Menú</span>
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64">
                {/* PRINCIPAL */}
                <DropdownMenuLabel>Principal</DropdownMenuLabel>
                <DropdownMenuGroup>
                  <DropdownMenuItem asChild>
                    <Link
                      href="/dashboard"
                      className={`flex items-center gap-2 cursor-pointer ${
                        pathname === "/dashboard" ? "bg-primary/10 text-primary" : ""
                      }`}
                    >
                      <LayoutDashboard className="h-4 w-4" />
                      Dashboard
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link
                      href="/roles"
                      className={`flex items-center gap-2 cursor-pointer ${
                        pathname.startsWith("/roles") ? "bg-primary/10 text-primary" : ""
                      }`}
                    >
                      <Briefcase className="h-4 w-4" />
                      Vacantes
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link
                      href="/candidates"
                      className={`flex items-center gap-2 cursor-pointer ${
                        pathname.startsWith("/candidates") ? "bg-primary/10 text-primary" : ""
                      }`}
                    >
                      <Users className="h-4 w-4" />
                      Candidatos
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link
                      href="/terna-comparator"
                      className={`flex items-center gap-2 cursor-pointer ${
                        pathname === "/terna-comparator" ? "bg-primary/10 text-primary" : ""
                      }`}
                    >
                      <GitCompare className="h-4 w-4" />
                      Comparador de Terna
                    </Link>
                  </DropdownMenuItem>
                </DropdownMenuGroup>

                <DropdownMenuSeparator />

                {/* REPORTES Y ANÁLISIS */}
                <DropdownMenuLabel>Reportes y Análisis</DropdownMenuLabel>
                <DropdownMenuGroup>
                  <DropdownMenuItem asChild>
                    <Link
                      href="/reports"
                      className={`flex items-center gap-2 cursor-pointer ${
                        pathname === "/reports" ? "bg-primary/10 text-primary" : ""
                      }`}
                    >
                      <BarChart3 className="h-4 w-4" />
                      Reportes
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link
                      href="/dashboard/evaluations"
                      className={`flex items-center gap-2 cursor-pointer ${
                        pathname === "/dashboard/evaluations" ? "bg-primary/10 text-primary" : ""
                      }`}
                    >
                      <Target className="h-4 w-4" />
                      Evaluaciones
                    </Link>
                  </DropdownMenuItem>
                </DropdownMenuGroup>

                <DropdownMenuSeparator />

                {/* CREAR */}
                <DropdownMenuLabel>Crear Nuevo</DropdownMenuLabel>
                <DropdownMenuGroup>
                  <DropdownMenuItem asChild>
                    <Link
                      href="/clients/new"
                      className={`flex items-center gap-2 cursor-pointer ${
                        pathname === "/clients/new" ? "bg-primary/10 text-primary" : ""
                      }`}
                    >
                      <Building className="h-4 w-4" />
                      Nuevo Cliente
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link
                      href="/roles/new"
                      className={`flex items-center gap-2 cursor-pointer ${
                        pathname === "/roles/new" ? "bg-primary/10 text-primary" : ""
                      }`}
                    >
                      <Briefcase className="h-4 w-4" />
                      Nueva Vacante
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link
                      href="/candidates/new"
                      className={`flex items-center gap-2 cursor-pointer ${
                        pathname === "/candidates/new" ? "bg-primary/10 text-primary" : ""
                      }`}
                    >
                      <UserPlus className="h-4 w-4" />
                      Nuevo Candidato
                    </Link>
                  </DropdownMenuItem>
                </DropdownMenuGroup>

                <DropdownMenuSeparator />

                {/* ADMINISTRACIÓN */}
                <DropdownMenuLabel>Administración</DropdownMenuLabel>
                <DropdownMenuGroup>
                  {isAdmin && (
                    <>
                      <DropdownMenuItem asChild>
                        <Link
                          href="/dashboard/users"
                          className={`flex items-center gap-2 cursor-pointer ${
                            pathname === "/dashboard/users" ? "bg-primary/10 text-primary" : ""
                          }`}
                        >
                          <User className="h-4 w-4" />
                          Usuarios
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link
                          href="/message-templates"
                          className={`flex items-center gap-2 cursor-pointer ${
                            pathname.startsWith("/message-templates") ? "bg-primary/10 text-primary" : ""
                          }`}
                        >
                          <Mail className="h-4 w-4" />
                          Plantillas
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link
                          href="/config"
                          className={`flex items-center gap-2 cursor-pointer ${
                            pathname === "/config" ? "bg-primary/10 text-primary" : ""
                          }`}
                        >
                          <Settings className="h-4 w-4" />
                          Configuración
                        </Link>
                      </DropdownMenuItem>
                    </>
                  )}
                  <DropdownMenuItem asChild>
                    <Link
                      href="/dashboard/rhtools/clients"
                      className={`flex items-center gap-2 cursor-pointer ${
                        pathname.startsWith("/dashboard/rhtools") ? "bg-primary/10 text-primary" : ""
                      }`}
                    >
                      <Building2 className="h-4 w-4" />
                      RH Tools
                    </Link>
                  </DropdownMenuItem>
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* User Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="text-sm font-semibold text-primary">
                      {user?.firstName?.[0]}{user?.lastName?.[0]}
                    </span>
                  </div>
                  <div className="hidden sm:block text-left">
                    <p className="text-sm font-medium">{user?.fullName}</p>
                    <p className="text-xs text-muted-foreground">
                      {user?.role === "super_admin" 
                        ? "Super Admin" 
                        : user?.role === "consultant" 
                        ? "Consultor" 
                        : "Visualizador"}
                    </p>
                  </div>
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-2 py-1.5 sm:hidden">
                  <p className="text-sm font-medium">{user?.fullName}</p>
                  <p className="text-xs text-muted-foreground">
                    {user?.role === "super_admin" 
                      ? "Super Admin" 
                      : user?.role === "consultant" 
                      ? "Consultor" 
                      : "Visualizador"}
                  </p>
                </div>
                <DropdownMenuSeparator className="sm:hidden" />
                <DropdownMenuItem asChild>
                  <Link href="/dashboard" className="flex items-center gap-2 cursor-pointer">
                    <LayoutDashboard className="h-4 w-4" />
                    Dashboard
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="flex items-center gap-2 cursor-pointer text-red-600">
                  <LogOut className="h-4 w-4" />
                  Cerrar Sesión
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
    </nav>
  );
}

function BrandingLogo() {
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState("Top Management");

  useEffect(() => {
    const loadBranding = () => {
      const saved = localStorage.getItem("branding_config");
      if (saved) {
        const config = JSON.parse(saved);
        if (config.logoUrl) setLogoUrl(config.logoUrl);
        if (config.companyName) setCompanyName(config.companyName);
      }
    };
    
    loadBranding();
    
    // Listen for changes
    const handleStorage = () => loadBranding();
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  if (logoUrl) {
    return (
      <img 
        src={logoUrl} 
        alt={companyName}
        className="h-8 object-contain"
      />
    );
  }

  return (
    <>
      <div className="h-8 w-8 rounded bg-primary flex items-center justify-center">
        <span className="text-primary-foreground font-bold text-sm">TM</span>
      </div>
      <span className="font-semibold text-lg hidden sm:block">{companyName}</span>
    </>
  );
}
