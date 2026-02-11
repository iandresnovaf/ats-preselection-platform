"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { Loader2, Lock, Mail, User } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { authService } from "@/services/auth";

const changePasswordSchema = z.object({
  currentPassword: z.string().min(1, "Contraseña actual requerida"),
  newPassword: z.string().min(8, "La nueva contraseña debe tener al menos 8 caracteres"),
  confirmPassword: z.string(),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Las contraseñas no coinciden",
  path: ["confirmPassword"],
});

const changeEmailSchema = z.object({
  newEmail: z.string().email("Email inválido"),
  password: z.string().min(1, "Contraseña requerida"),
});

type ChangePasswordFormData = z.infer<typeof changePasswordSchema>;
type ChangeEmailFormData = z.infer<typeof changeEmailSchema>;

export function AccountConfigForm() {
  const { user, setUser } = useAuthStore();
  const { toast } = useToast();
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isChangingEmail, setIsChangingEmail] = useState(false);

  const passwordForm = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
  });

  const emailForm = useForm<ChangeEmailFormData>({
    resolver: zodResolver(changeEmailSchema),
  });

  const handleChangePassword = async (data: ChangePasswordFormData) => {
    setIsChangingPassword(true);
    try {
      await authService.changePassword(data.currentPassword, data.newPassword);
      toast({
        title: "Éxito",
        description: "Contraseña cambiada correctamente",
      });
      passwordForm.reset();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Error al cambiar contraseña",
        variant: "destructive",
      });
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleChangeEmail = async (data: ChangeEmailFormData) => {
    setIsChangingEmail(true);
    try {
      await authService.changeEmail(data.newEmail, data.password);
      
      // Actualizar el usuario en el store
      if (user) {
        setUser({ ...user, email: data.newEmail });
      }
      
      toast({
        title: "Éxito",
        description: "Email cambiado correctamente",
      });
      emailForm.reset();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Error al cambiar email",
        variant: "destructive",
      });
    } finally {
      setIsChangingEmail(false);
    }
  };

  return (
    <Tabs defaultValue="password" className="space-y-4">
      <TabsList className="grid w-full grid-cols-2">
        <TabsTrigger value="password">
          <Lock className="mr-2 h-4 w-4" />
          Cambiar Contraseña
        </TabsTrigger>
        <TabsTrigger value="email">
          <Mail className="mr-2 h-4 w-4" />
          Cambiar Email
        </TabsTrigger>
      </TabsList>

      <TabsContent value="password">
        <Card>
          <CardHeader>
            <CardTitle>Cambiar Contraseña</CardTitle>
            <CardDescription>
              Actualiza tu contraseña de acceso a la plataforma.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={passwordForm.handleSubmit(handleChangePassword)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="currentPassword">Contraseña Actual</Label>
                <Input
                  id="currentPassword"
                  type="password"
                  placeholder="••••••••"
                  {...passwordForm.register("currentPassword")}
                />
                {passwordForm.formState.errors.currentPassword && (
                  <p className="text-sm text-red-500">
                    {passwordForm.formState.errors.currentPassword.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="newPassword">Nueva Contraseña</Label>
                <Input
                  id="newPassword"
                  type="password"
                  placeholder="••••••••"
                  {...passwordForm.register("newPassword")}
                />
                {passwordForm.formState.errors.newPassword && (
                  <p className="text-sm text-red-500">
                    {passwordForm.formState.errors.newPassword.message}
                  </p>
                )}
                <p className="text-xs text-muted-foreground">
                  Mínimo 8 caracteres
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirmar Nueva Contraseña</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  {...passwordForm.register("confirmPassword")}
                />
                {passwordForm.formState.errors.confirmPassword && (
                  <p className="text-sm text-red-500">
                    {passwordForm.formState.errors.confirmPassword.message}
                  </p>
                )}
              </div>

              <Button type="submit" disabled={isChangingPassword}>
                {isChangingPassword && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Cambiar Contraseña
              </Button>
            </form>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="email">
        <Card>
          <CardHeader>
            <CardTitle>Cambiar Email</CardTitle>
            <CardDescription>
              Cambia el email asociado a tu cuenta. Necesitarás verificar tu contraseña actual.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-4 p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">Email actual:</p>
              <p className="font-medium">{user?.email}</p>
            </div>

            <form onSubmit={emailForm.handleSubmit(handleChangeEmail)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="newEmail">Nuevo Email</Label>
                <Input
                  id="newEmail"
                  type="email"
                  placeholder="nuevo@email.com"
                  {...emailForm.register("newEmail")}
                />
                {emailForm.formState.errors.newEmail && (
                  <p className="text-sm text-red-500">
                    {emailForm.formState.errors.newEmail.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Contraseña Actual (para verificar)</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  {...emailForm.register("password")}
                />
                {emailForm.formState.errors.password && (
                  <p className="text-sm text-red-500">
                    {emailForm.formState.errors.password.message}
                  </p>
                )}
              </div>

              <Button type="submit" disabled={isChangingEmail}>
                {isChangingEmail && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Cambiar Email
              </Button>
            </form>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}
