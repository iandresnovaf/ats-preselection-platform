"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { LoginForm } from "@/components/auth/LoginForm";
import { ImageIcon } from "lucide-react";

interface BrandingConfig {
  companyName: string;
  logoUrl: string;
}

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [branding, setBranding] = useState<BrandingConfig>({
    companyName: "Top Management",
    logoUrl: "",
  });

  useEffect(() => {
    if (isAuthenticated) {
      router.push("/dashboard");
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    const saved = localStorage.getItem("branding_config");
    if (saved) {
      setBranding(JSON.parse(saved));
    }
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-lg">
        <div className="text-center">
          {branding.logoUrl ? (
            <div className="flex justify-center mb-4">
              <img 
                src={branding.logoUrl} 
                alt={branding.companyName}
                className="h-16 object-contain"
              />
            </div>
          ) : (
            <div className="mx-auto h-16 w-16 rounded bg-primary flex items-center justify-center mb-4">
              <span className="text-primary-foreground font-bold text-2xl">
                {branding.companyName.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase()}
              </span>
            </div>
          )}
          <h2 className="text-3xl font-bold text-gray-900">
            {branding.companyName}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Plataforma de Preselección de Candidatos
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Inicia sesión para continuar
          </p>
        </div>
        <LoginForm />
      </div>
    </div>
  );
}
