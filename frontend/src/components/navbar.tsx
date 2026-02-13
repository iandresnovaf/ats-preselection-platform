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
  GitBranch,
  FileText,
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

  const navItems = [
    {
      href: "/dashboard",
      label: "Dashboard",
      icon: LayoutDashboard,
      show: true,
    },
    {
      href: "/dashboard/jobs",
      label: "Ofertas",
      icon: Briefcase,
      show: true,
    },
    {
      href: "/dashboard/candidates",
      label: "Candidatos",
      icon: Users,
      show: true,
    },
    {
      href: "/dashboard/evaluations",
      label: "Evaluaciones",
      icon: Users,
      show: true,
    },
    {
      href: "/dashboard/users",
      label: "Usuarios",
      icon: User,
      show: isAdmin,
    },
    {
      href: "/config",
      label: "Configuración",
      icon: Settings,
      show: isAdmin,
    },
    {
      href: "/dashboard/rhtools/clients",
      label: "RH Tools",
      icon: Building2,
      show: true,
    },
  ];

  return (
    <nav className="border-b bg-background">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/dashboard" className="flex items-center gap-2">
            <BrandingLogo />
          </Link>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center gap-1">
            {navItems
              .filter((item) => item.show)
              .map((item) => {
                const Icon = item.icon;
                const isActive = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
          </div>

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
              {isAdmin && (
                <>
                  <DropdownMenuItem asChild>
                    <Link href="/users" className="flex items-center gap-2 cursor-pointer">
                      <User className="h-4 w-4" />
                      Gestión de Usuarios
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/config" className="flex items-center gap-2 cursor-pointer">
                      <Settings className="h-4 w-4" />
                      Configuración
                    </Link>
                  </DropdownMenuItem>
                </>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="flex items-center gap-2 cursor-pointer text-red-600">
                <LogOut className="h-4 w-4" />
                Cerrar Sesión
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
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
