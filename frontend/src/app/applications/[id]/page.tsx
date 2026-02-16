"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  useApplication,
  useUpdateApplicationStage,
  useMakeDecision,
  useUploadDocument,
  useResolveFlag,
  useCreateFlag,
} from "@/hooks/use-headhunting";
import {
  ScoreBadge,
  ScoreValue,
  StageBadge,
  PipelineTimeline,
  FlagList,
  DocumentList,
  DocumentUploader,
  ScoreBar,
} from "@/components/headhunting";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  ArrowLeft,
  User,
  Building2,
  Briefcase,
  Calendar,
  Flag,
  FileText,
  CheckCircle,
  XCircle,
  Loader2,
  History,
  AlertTriangle,
} from "lucide-react";
import { toast } from "@/hooks/use-toast";
import type { PipelineStage } from "@/types/headhunting";
import { PIPELINE_STAGES } from "@/types/headhunting";

export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const applicationId = params.id as string;

  const [activeTab, setActiveTab] = useState("timeline");
  const [isDecisionDialogOpen, setIsDecisionDialogOpen] = useState(false);
  const [decisionType, setDecisionType] = useState<"hired" | "rejected" | null>(null);
  const [decisionNotes, setDecisionNotes] = useState("");
  const [decisionDate, setDecisionDate] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");

  const { data: application, isLoading, error } = useApplication(applicationId);
  const updateStage = useUpdateApplicationStage();
  const makeDecision = useMakeDecision();
  const uploadDocument = useUploadDocument();
  const resolveFlag = useResolveFlag();

  const handleStageChange = async (newStage: PipelineStage) => {
    try {
      await updateStage.mutateAsync({
        id: applicationId,
        stage: newStage,
        notes: `Cambio de etapa a ${newStage}`,
      });
      toast({
        title: "Etapa actualizada",
        description: `La aplicación ha pasado a ${newStage}`,
      });
    } catch (err) {
      toast({
        title: "Error",
        description: "No se pudo actualizar la etapa",
        variant: "destructive",
      });
    }
  };

  const handleDecision = async () => {
    if (!decisionType) return;

    try {
      await makeDecision.mutateAsync({
        id: applicationId,
        decision: decisionType,
        notes: decisionNotes,
        rejection_reason: decisionType === "rejected" ? rejectionReason : undefined,
      });
      
      toast({
        title: decisionType === "hired" ? "¡Candidato contratado!" : "Candidato rechazado",
        description: decisionType === "hired" 
          ? "La decisión ha sido registrada exitosamente" 
          : "La decisión ha sido registrada",
      });
      
      setIsDecisionDialogOpen(false);
    } catch (err) {
      toast({
        title: "Error",
        description: "No se pudo registrar la decisión",
        variant: "destructive",
      });
    }
  };

  const handleUpload = async (file: File, type: string) => {
    await uploadDocument.mutateAsync({
      applicationId,
      file,
      type,
    });
    toast({
      title: "Documento subido",
      description: "El documento se ha subido exitosamente",
    });
  };

  const handleResolveFlag = async (flagId: string, notes?: string) => {
    await resolveFlag.mutateAsync({
      applicationId,
      flagId,
      notes,
    });
    toast({
      title: "Alerta resuelta",
      description: "La alerta ha sido marcada como resuelta",
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error || !application) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-12 h-12 mx-auto text-red-500 mb-4" />
        <h2 className="text-xl font-semibold">Error al cargar la aplicación</h2>
        <p className="text-gray-500 mt-2">No se pudo encontrar la aplicación solicitada</p>
        <Button className="mt-4" onClick={() => router.back()}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Volver
        </Button>
      </div>
    );
  }

  const activeFlags = application.flags?.filter(f => !f.resolved) || [];
  const pendingFlagsCount = activeFlags.length;

  return (
    <div className="space-y-6">
      {/* Header Navigation */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Volver
        </Button>
      </div>

      {/* Main Header Card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Candidate Info */}
            <div className="flex items-start gap-4 flex-1">
              {application.candidate?.photo_url ? (
                <img
                  src={application.candidate.photo_url}
                  alt={application.candidate.first_name}
                  className="w-20 h-20 rounded-full object-cover"
                />
              ) : (
                <div className="w-20 h-20 rounded-full bg-gray-200 flex items-center justify-center">
                  <User className="w-10 h-10 text-gray-400" />
                </div>
              )}
              <div>
                <h1 className="text-2xl font-bold">
                  {application.candidate?.first_name} {application.candidate?.last_name}
                </h1>
                <div className="flex items-center gap-2 text-gray-500 mt-1">
                  <Building2 className="w-4 h-4" />
                  <span>{application.role?.client?.name || "Cliente no especificado"}</span>
                </div>
                <div className="flex items-center gap-2 text-gray-500">
                  <Briefcase className="w-4 h-4" />
                  <span>{application.role?.title || "Vacante no especificada"}</span>
                </div>
                {pendingFlagsCount > 0 && (
                  <Badge variant="destructive" className="mt-2">
                    <AlertTriangle className="w-3 h-3 mr-1" />
                    {pendingFlagsCount} alerta{pendingFlagsCount !== 1 ? "s" : ""} pendiente{pendingFlagsCount !== 1 ? "s" : ""}
                  </Badge>
                )}
              </div>
            </div>

            {/* Stage & Score */}
            <div className="flex flex-col sm:flex-row gap-6 items-start lg:items-center">
              <div>
                <Label className="text-xs text-gray-500 uppercase">Etapa Actual</Label>
                <Select
                  value={application.stage}
                  onValueChange={(v) => handleStageChange(v as PipelineStage)}
                  disabled={application.stage === "hired" || application.stage === "rejected"}
                >
                  <SelectTrigger className="w-[200px] mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PIPELINE_STAGES.map((stage) => (
                      <SelectItem key={stage.value} value={stage.value}>
                        {stage.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col items-center">
                <Label className="text-xs text-gray-500 uppercase">Score General</Label>
                <ScoreBadge score={application.overall_score} size="xl" showLabel className="mt-1" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4 lg:w-[600px]">
          <TabsTrigger value="timeline">
            <History className="w-4 h-4 mr-2 hidden sm:inline" />
            Timeline
          </TabsTrigger>
          <TabsTrigger value="documents">
            <FileText className="w-4 h-4 mr-2 hidden sm:inline" />
            Documentos
          </TabsTrigger>
          <TabsTrigger value="scores">
            <CheckCircle className="w-4 h-4 mr-2 hidden sm:inline" />
            Scores
          </TabsTrigger>
          <TabsTrigger value="decision">
            <Flag className="w-4 h-4 mr-2 hidden sm:inline" />
            Decisión
          </TabsTrigger>
        </TabsList>

        {/* Tab: Timeline */}
        <TabsContent value="timeline">
          <Card>
            <CardHeader>
              <CardTitle>Historial del Proceso</CardTitle>
            </CardHeader>
            <CardContent>
              <PipelineTimeline
                currentStage={application.stage}
                transitions={application.stage_transitions || []}
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Documents */}
        <TabsContent value="documents">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Subir Documento</CardTitle>
              </CardHeader>
              <CardContent>
                <DocumentUploader onUpload={handleUpload} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Documentos ({application.documents?.length || 0})</CardTitle>
              </CardHeader>
              <CardContent>
                <DocumentList
                  documents={application.documents || []}
                  onDownload={(doc) => window.open(doc.file_url, "_blank")}
                />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab: Scores & Flags */}
        <TabsContent value="scores">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Scores por Dimensión</CardTitle>
              </CardHeader>
              <CardContent>
                {application.assessment_scores && application.assessment_scores.length > 0 ? (
                  <div className="space-y-4">
                    {application.assessment_scores.map((score) => (
                      <div key={score.id}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium">{score.dimension}</span>
                          <ScoreValue score={score.score} />
                        </div>
                        <ScoreBar score={score.score} height="h-2" showValue={false} />
                        {score.notes && (
                          <p className="text-xs text-gray-500 mt-1">{score.notes}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">
                    No hay scores registrados
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Alertas y Flags</CardTitle>
              </CardHeader>
              <CardContent>
                <FlagList
                  flags={application.flags || []}
                  onResolve={handleResolveFlag}
                  showResolved={true}
                />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab: Decision */}
        <TabsContent value="decision">
          <Card>
            <CardHeader>
              <CardTitle>Decisión Final</CardTitle>
            </CardHeader>
            <CardContent>
              {application.decision ? (
                <div className="text-center py-8">
                  <div
                    className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-4 ${
                      application.decision.decision === "hired"
                        ? "bg-green-100 text-green-600"
                        : "bg-red-100 text-red-600"
                    }`}
                  >
                    {application.decision.decision === "hired" ? (
                      <CheckCircle className="w-8 h-8" />
                    ) : (
                      <XCircle className="w-8 h-8" />
                    )}
                  </div>
                  <h3 className="text-xl font-semibold">
                    {application.decision.decision === "hired"
                      ? "Candidato Contratado"
                      : "Candidato Rechazado"}
                  </h3>
                  <p className="text-gray-500 mt-2">
                    Decisión tomada el{" "}
                    {new Date(application.decision.decision_date).toLocaleDateString("es-ES")}
                  </p>
                  {application.decision.notes && (
                    <div className="mt-4 p-4 bg-gray-50 rounded-lg text-left max-w-md mx-auto">
                      <p className="text-sm text-gray-600">{application.decision.notes}</p>
                    </div>
                  )}
                  {application.decision.decision === "hired" && (
                    <Button
                      className="mt-6"
                      onClick={() =>
                        router.push(`/post-hire/${applicationId}`)
                      }
                    >
                      Ver Plan Post-Contratación
                    </Button>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-500 mb-6">
                    Esta aplicación está en etapa: <StageBadge stage={application.stage} />
                  </p>
                  
                  {application.stage === "offer" ? (
                    <div className="flex justify-center gap-4">
                      <Button
                        variant="default"
                        size="lg"
                        className="bg-green-600 hover:bg-green-700"
                        onClick={() => {
                          setDecisionType("hired");
                          setIsDecisionDialogOpen(true);
                        }}
                      >
                        <CheckCircle className="w-5 h-5 mr-2" />
                        Contratar
                      </Button>
                      <Button
                        variant="destructive"
                        size="lg"
                        onClick={() => {
                          setDecisionType("rejected");
                          setIsDecisionDialogOpen(true);
                        }}
                      >
                        <XCircle className="w-5 h-5 mr-2" />
                        Rechazar
                      </Button>
                    </div>
                  ) : (
                    <div className="text-gray-400">
                      <p>La decisión final está disponible en la etapa de Oferta</p>
                      <Button
                        className="mt-4"
                        onClick={() => handleStageChange("offer")}
                        disabled={updateStage.isPending}
                      >
                        {updateStage.isPending ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : null}
                        Mover a Oferta
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Decision Dialog */}
      <Dialog open={isDecisionDialogOpen} onOpenChange={setIsDecisionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {decisionType === "hired" ? "Confirmar Contratación" : "Confirmar Rechazo"}
            </DialogTitle>
            <DialogDescription>
              {decisionType === "hired"
                ? "Esta acción marcará al candidato como contratado."
                : "Esta acción rechazará al candidato del proceso."}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div>
              <Label>Fecha de decisión</Label>
              <Input
                type="date"
                value={decisionDate}
                onChange={(e) => setDecisionDate(e.target.value)}
                className="mt-1"
              />
            </div>

            {decisionType === "rejected" && (
              <div>
                <Label>Motivo del rechazo</Label>
                <Select value={rejectionReason} onValueChange={setRejectionReason}>
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="Selecciona un motivo" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="skills_mismatch">No cumple con skills requeridos</SelectItem>
                    <SelectItem value="experience">Experiencia insuficiente</SelectItem>
                    <SelectItem value="salary">Expectativa salarial</SelectItem>
                    <SelectItem value="availability">No disponible</SelectItem>
                    <SelectItem value="culture">No encaja en cultura</SelectItem>
                    <SelectItem value="other">Otro</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div>
              <Label>Notas / Justificación</Label>
              <Textarea
                value={decisionNotes}
                onChange={(e) => setDecisionNotes(e.target.value)}
                placeholder="Agrega notas sobre la decisión..."
                className="mt-1"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDecisionDialogOpen(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleDecision}
              disabled={
                makeDecision.isPending ||
                (decisionType === "rejected" && !rejectionReason)
              }
              variant={decisionType === "hired" ? "default" : "destructive"}
              className={decisionType === "hired" ? "bg-green-600 hover:bg-green-700" : ""}
            >
              {makeDecision.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : decisionType === "hired" ? (
                <CheckCircle className="w-4 h-4 mr-2" />
              ) : (
                <XCircle className="w-4 h-4 mr-2" />
              )}
              {decisionType === "hired" ? "Confirmar Contratación" : "Confirmar Rechazo"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
