"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Mail,
  RotateCcw,
  BarChart3,
  Send,
  AlertCircle,
  CheckCircle,
  Loader2,
} from "lucide-react";
import type { TrackedCandidate, ApplicationStatus } from "@/types/tracking";

interface QuickActionsPanelProps {
  pendingCandidates: TrackedCandidate[];
  noResponseCandidates: TrackedCandidate[];
  onContactPending: (candidateIds: string[], channel: "email" | "whatsapp", message?: string) => void;
  onResendNoResponse: (candidateIds: string[], message?: string) => void;
  onViewReport: () => void;
  isLoading?: boolean;
}

export function QuickActionsPanel({
  pendingCandidates,
  noResponseCandidates,
  onContactPending,
  onResendNoResponse,
  onViewReport,
  isLoading = false,
}: QuickActionsPanelProps) {
  const [contactDialogOpen, setContactDialogOpen] = useState(false);
  const [resendDialogOpen, setResendDialogOpen] = useState(false);
  const [selectedChannel, setSelectedChannel] = useState<"email" | "whatsapp">("email");
  const [customMessage, setCustomMessage] = useState("");
  const [selectedCandidates, setSelectedCandidates] = useState<string[]>([]);

  const pendingCount = pendingCandidates.length;
  const noResponseCount = noResponseCandidates.length;

  const handleContactSubmit = () => {
    const candidateIds = selectedCandidates.length > 0 
      ? selectedCandidates 
      : pendingCandidates.map(c => c.id);
    
    onContactPending(candidateIds, selectedChannel, customMessage || undefined);
    setContactDialogOpen(false);
    setCustomMessage("");
    setSelectedCandidates([]);
  };

  const handleResendSubmit = () => {
    const candidateIds = selectedCandidates.length > 0 
      ? selectedCandidates 
      : noResponseCandidates.map(c => c.id);
    
    onResendNoResponse(candidateIds, customMessage || undefined);
    setResendDialogOpen(false);
    setCustomMessage("");
    setSelectedCandidates([]);
  };

  const toggleCandidate = (id: string) => {
    setSelectedCandidates(prev => 
      prev.includes(id) 
        ? prev.filter(c => c !== id)
        : [...prev, id]
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Send className="h-5 w-5" />
          Acciones Rápidas
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Contact Pending Button */}
        <Dialog open={contactDialogOpen} onOpenChange={setContactDialogOpen}>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              className="w-full justify-between"
              disabled={pendingCount === 0 || isLoading}
            >
              <span className="flex items-center gap-2">
                <Mail className="h-4 w-4" />
                Contactar pendientes
              </span>
              <Badge variant={pendingCount > 5 ? "destructive" : "secondary"}>
                {pendingCount}
              </Badge>
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Contactar candidatos pendientes</DialogTitle>
              <DialogDescription>
                Se enviará un mensaje a {pendingCount} candidatos que aún no han sido contactados.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Canal de contacto</Label>
                <Select
                  value={selectedChannel}
                  onValueChange={(v) => setSelectedChannel(v as "email" | "whatsapp")}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="email">Email</SelectItem>
                    <SelectItem value="whatsapp">WhatsApp</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Mensaje personalizado (opcional)</Label>
                <Textarea
                  placeholder="Deja en blanco para usar la plantilla por defecto..."
                  value={customMessage}
                  onChange={(e) => setCustomMessage(e.target.value)}
                  rows={4}
                />
              </div>

              {pendingCount > 10 && (
                <div className="space-y-2 max-h-40 overflow-y-auto border rounded p-2">
                  <Label className="text-xs text-muted-foreground">
                    Seleccionar candidatos específicos (opcional):
                  </Label>
                  {pendingCandidates.map((c) => (
                    <div key={c.id} className="flex items-center gap-2">
                      <Checkbox
                        checked={selectedCandidates.includes(c.id)}
                        onCheckedChange={() => toggleCandidate(c.id)}
                      />
                      <span className="text-sm">{c.first_name} {c.last_name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setContactDialogOpen(false)}>
                Cancelar
              </Button>
              <Button 
                onClick={handleContactSubmit}
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Enviando...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Enviar a {selectedCandidates.length || pendingCount} candidatos
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Resend No Response Button */}
        <Dialog open={resendDialogOpen} onOpenChange={setResendDialogOpen}>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              className="w-full justify-between"
              disabled={noResponseCount === 0 || isLoading}
            >
              <span className="flex items-center gap-2">
                <RotateCcw className="h-4 w-4" />
                Reenviar a sin respuesta
              </span>
              <Badge variant={noResponseCount > 5 ? "destructive" : "secondary"}>
                {noResponseCount}
              </Badge>
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Reenviar recordatorio</DialogTitle>
              <DialogDescription>
                Se reenviará un recordatorio a {noResponseCount} candidatos que no han respondido.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Mensaje personalizado (opcional)</Label>
                <Textarea
                  placeholder="Deja en blanco para usar la plantilla por defecto..."
                  value={customMessage}
                  onChange={(e) => setCustomMessage(e.target.value)}
                  rows={4}
                />
              </div>

              {noResponseCount > 10 && (
                <div className="space-y-2 max-h-40 overflow-y-auto border rounded p-2">
                  <Label className="text-xs text-muted-foreground">
                    Seleccionar candidatos específicos (opcional):
                  </Label>
                  {noResponseCandidates.map((c) => (
                    <div key={c.id} className="flex items-center gap-2">
                      <Checkbox
                        checked={selectedCandidates.includes(c.id)}
                        onCheckedChange={() => toggleCandidate(c.id)}
                      />
                      <span className="text-sm">{c.first_name} {c.last_name}</span>
                      <span className="text-xs text-muted-foreground">
                        ({c.days_without_response} días)
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setResendDialogOpen(false)}>
                Cancelar
              </Button>
              <Button 
                onClick={handleResendSubmit}
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Enviando...
                  </>
                ) : (
                  <>
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Reenviar a {selectedCandidates.length || noResponseCount} candidatos
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* View Report Button */}
        <Button
          variant="outline"
          className="w-full justify-between"
          onClick={onViewReport}
        >
          <span className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Ver reporte
          </span>
        </Button>

        {/* Summary */}
        <div className="pt-3 border-t space-y-2">
          <div className="flex items-center gap-2 text-sm">
            {pendingCount > 5 ? (
              <AlertCircle className="h-4 w-4 text-amber-500" />
            ) : (
              <CheckCircle className="h-4 w-4 text-green-500" />
            )}
            <span className={pendingCount > 5 ? "text-amber-600" : ""}>
              {pendingCount === 0 
                ? "Todos los candidatos han sido contactados"
                : `${pendingCount} candidatos pendientes de contacto`}
            </span>
          </div>
          {noResponseCount > 0 && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <RotateCcw className="h-4 w-4" />
              <span>{noResponseCount} candidatos sin respuesta (&gt;48h)</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
