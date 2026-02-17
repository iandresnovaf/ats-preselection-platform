"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Mail, Phone, AlertTriangle, Loader2 } from "lucide-react";

export interface MissingContactData {
  email?: string;
  phone?: string;
}

export interface MissingContactModalProps {
  isOpen: boolean;
  candidate: {
    candidate_id: string;
    full_name: string;
    email?: string;
    phone?: string;
  };
  onSubmit: (data: MissingContactData) => void;
  onSkip: () => void;
  isLoading?: boolean;
}

/**
 * Modal para solicitar datos de contacto faltantes del candidato
 * Detecta automáticamente qué datos faltan y muestra solo esos campos
 */
export function MissingContactModal({
  isOpen,
  candidate,
  onSubmit,
  onSkip,
  isLoading = false,
}: MissingContactModalProps) {
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [phoneError, setPhoneError] = useState<string | null>(null);

  // Determinar qué datos faltan
  const needsEmail = !candidate.email;
  const needsPhone = !candidate.phone;

  // Resetear estado cuando se abre el modal
  useEffect(() => {
    if (isOpen) {
      setEmail("");
      setPhone("");
      setEmailError(null);
      setPhoneError(null);
    }
  }, [isOpen]);

  // Validar formato de email
  const validateEmail = (value: string): boolean => {
    if (!value) return true; // Opcional si ya tiene email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(value);
  };

  // Validar formato de teléfono (básico)
  const validatePhone = (value: string): boolean => {
    if (!value) return true; // Opcional si ya tiene teléfono
    // Aceptar formatos: +1234567890, 123-456-7890, (123) 456-7890, etc.
    const phoneRegex = /^[\d\s\-\+\(\)]{8,20}$/;
    return phoneRegex.test(value);
  };

  const handleSubmit = () => {
    let hasError = false;

    // Validar email si se requiere y se ingresó
    if (needsEmail && email) {
      if (!validateEmail(email)) {
        setEmailError("Formato de email inválido");
        hasError = true;
      } else {
        setEmailError(null);
      }
    }

    // Validar teléfono si se requiere y se ingresó
    if (needsPhone && phone) {
      if (!validatePhone(phone)) {
        setPhoneError("Formato de teléfono inválido");
        hasError = true;
      } else {
        setPhoneError(null);
      }
    }

    if (hasError) return;

    // Construir objeto de datos
    const data: MissingContactData = {};
    if (needsEmail && email) data.email = email;
    if (needsPhone && phone) data.phone = phone;

    onSubmit(data);
  };

  const handleSkip = () => {
    onSkip();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && !isLoading && handleSkip()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            Datos de contacto incompletos
          </DialogTitle>
          <DialogDescription>
            El candidato <strong>{candidate.full_name}</strong> necesita datos de contacto
            para continuar con el proceso.
          </DialogDescription>
        </DialogHeader>

        <Alert className="bg-amber-50 border-amber-200">
          <AlertDescription className="text-amber-800">
            {!needsEmail && !needsPhone ? (
              "El candidato ya tiene todos los datos de contacto."
            ) : (
              <>
                Faltan los siguientes datos:
                <ul className="mt-2 ml-4 list-disc">
                  {needsEmail && <li>Correo electrónico</li>}
                  {needsPhone && <li>Teléfono</li>}
                </ul>
              </>
            )}
          </AlertDescription>
        </Alert>

        <div className="space-y-4 py-4">
          {/* Campo Email - solo si falta */}
          {needsEmail && (
            <div className="space-y-2">
              <Label htmlFor="email" className="flex items-center gap-2">
                <Mail className="w-4 h-4" />
                Correo electrónico
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="ejemplo@correo.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (emailError) setEmailError(null);
                }}
                disabled={isLoading}
                className={emailError ? "border-red-500" : ""}
              />
              {emailError && (
                <p className="text-sm text-red-500">{emailError}</p>
              )}
            </div>
          )}

          {/* Campo Teléfono - solo si falta */}
          {needsPhone && (
            <div className="space-y-2">
              <Label htmlFor="phone" className="flex items-center gap-2">
                <Phone className="w-4 h-4" />
                Teléfono
              </Label>
              <Input
                id="phone"
                type="tel"
                placeholder="+1 234 567 8900"
                value={phone}
                onChange={(e) => {
                  setPhone(e.target.value);
                  if (phoneError) setPhoneError(null);
                }}
                disabled={isLoading}
                className={phoneError ? "border-red-500" : ""}
              />
              {phoneError && (
                <p className="text-sm text-red-500">{phoneError}</p>
              )}
              <p className="text-xs text-gray-500">
                Formato: +código país y número (ej: +57 312 345 6789)
              </p>
            </div>
          )}

          {/* Mostrar datos existentes */}
          {!needsEmail && (
            <div className="p-3 bg-gray-50 rounded-md">
              <p className="text-sm text-gray-600">
                <Mail className="w-4 h-4 inline mr-2" />
                <strong>Email existente:</strong> {candidate.email}
              </p>
            </div>
          )}
          {!needsPhone && (
            <div className="p-3 bg-gray-50 rounded-md">
              <p className="text-sm text-gray-600">
                <Phone className="w-4 h-4 inline mr-2" />
                <strong>Teléfono existente:</strong> {candidate.phone}
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={handleSkip}
            disabled={isLoading}
          >
            Omitir por ahora
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isLoading || (needsEmail && !email && needsPhone && !phone)}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Guardando...
              </>
            ) : (
              "Guardar y continuar"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default MissingContactModal;
