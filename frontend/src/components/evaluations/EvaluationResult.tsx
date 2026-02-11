import { Evaluation, EvaluationDecision } from "@/types/evaluations";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  Star, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  HelpCircle,
  TrendingUp,
  User,
  Calendar,
  FileText,
  Lightbulb,
  AlertOctagon
} from "lucide-react";

interface EvaluationResultProps {
  evaluation: Evaluation;
  showCandidate?: boolean;
}

const decisionConfig: Record<EvaluationDecision, { 
  label: string; 
  color: string; 
  icon: React.ReactNode;
  bgColor: string;
}> = {
  strong_yes: {
    label: "¡Fuerte Sí!",
    color: "text-green-700",
    icon: <CheckCircle2 className="h-6 w-6" />,
    bgColor: "bg-green-100",
  },
  yes: {
    label: "Sí",
    color: "text-green-600",
    icon: <CheckCircle2 className="h-6 w-6" />,
    bgColor: "bg-green-50",
  },
  maybe: {
    label: "Quizás",
    color: "text-yellow-600",
    icon: <HelpCircle className="h-6 w-6" />,
    bgColor: "bg-yellow-50",
  },
  no: {
    label: "No",
    color: "text-red-600",
    icon: <XCircle className="h-6 w-6" />,
    bgColor: "bg-red-50",
  },
  strong_no: {
    label: "¡Fuerte No!",
    color: "text-red-700",
    icon: <XCircle className="h-6 w-6" />,
    bgColor: "bg-red-100",
  },
};

function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  if (score >= 40) return "text-orange-600";
  return "text-red-600";
}

function getProgressColor(score: number): string {
  if (score >= 80) return "bg-green-600";
  if (score >= 60) return "bg-yellow-600";
  if (score >= 40) return "bg-orange-600";
  return "bg-red-600";
}

export function EvaluationResult({ evaluation, showCandidate = false }: EvaluationResultProps) {
  const decision = decisionConfig[evaluation.decision];
  const scoreColor = getScoreColor(evaluation.score);
  const progressColor = getProgressColor(evaluation.score);

  return (
    <div className="space-y-6">
      {/* Header con score y decisión */}
      <div className="flex flex-col md:flex-row gap-6 items-start md:items-center">
        <Card className="flex-1 w-full">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Puntuación General</p>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className={`text-4xl font-bold ${scoreColor}`}>
                    {evaluation.score}
                  </span>
                  <span className="text-muted-foreground">/100</span>
                </div>
              </div>
              <div className={`p-3 rounded-full ${decision.bgColor} ${decision.color}`}>
                {decision.icon}
              </div>
            </div>
            <Progress value={evaluation.score} className={`mt-4 h-2 ${progressColor}`} />
          </CardContent>
        </Card>

        <Card className="flex-1 w-full">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-full ${decision.bgColor} ${decision.color}`}>
                {decision.icon}
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Decisión</p>
                <p className={`text-2xl font-bold ${decision.color}`}>
                  {decision.label}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Info del candidato si es necesario */}
      {showCandidate && evaluation.candidate && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <User className="h-5 w-5" />
              Candidato
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">
                  {evaluation.candidate.first_name} {evaluation.candidate.last_name}
                </p>
                <p className="text-sm text-muted-foreground">{evaluation.candidate.email}</p>
              </div>
              {evaluation.candidate.job_opening && (
                <Badge variant="secondary">{evaluation.candidate.job_opening.title}</Badge>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Resumen */}
      {evaluation.summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Resumen
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground leading-relaxed">{evaluation.summary}</p>
          </CardContent>
        </Card>
      )}

      {/* Métricas detalladas */}
      {(evaluation.technical_skills || evaluation.soft_skills || 
        evaluation.experience_match || evaluation.education_match || evaluation.cultural_fit) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Métricas Detalladas
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {evaluation.experience_match !== undefined && (
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">Experiencia</span>
                  <span className="text-sm font-medium">{evaluation.experience_match}%</span>
                </div>
                <Progress value={evaluation.experience_match} className="h-2" />
              </div>
            )}
            {evaluation.education_match !== undefined && (
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">Educación</span>
                  <span className="text-sm font-medium">{evaluation.education_match}%</span>
                </div>
                <Progress value={evaluation.education_match} className="h-2" />
              </div>
            )}
            {evaluation.cultural_fit !== undefined && (
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">Cultura</span>
                  <span className="text-sm font-medium">{evaluation.cultural_fit}%</span>
                </div>
                <Progress value={evaluation.cultural_fit} className="h-2" />
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Fortalezas */}
      {evaluation.strengths && evaluation.strengths.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2 text-green-700">
              <CheckCircle2 className="h-5 w-5" />
              Fortalezas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {evaluation.strengths.map((strength, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-green-600 mt-1">•</span>
                  <span className="text-muted-foreground">{strength}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Gaps */}
      {evaluation.gaps && evaluation.gaps.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2 text-yellow-700">
              <Lightbulb className="h-5 w-5" />
              Áreas de Mejora
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {evaluation.gaps.map((gap, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-yellow-600 mt-1">•</span>
                  <span className="text-muted-foreground">{gap}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Red Flags */}
      {evaluation.red_flags && evaluation.red_flags.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2 text-red-700">
              <AlertOctagon className="h-5 w-5" />
              Alertas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {evaluation.red_flags.map((flag, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-red-600 mt-1">•</span>
                  <span className="text-muted-foreground">{flag}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Recomendación final */}
      {evaluation.overall_recommendation && (
        <Card className="bg-muted/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Recomendación
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground leading-relaxed">
              {evaluation.overall_recommendation}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Footer con metadata */}
      <div className="flex items-center justify-between text-sm text-muted-foreground pt-4 border-t">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4" />
          <span>Evaluado el {new Date(evaluation.created_at).toLocaleDateString('es-ES')}</span>
        </div>
        {evaluation.evaluated_by_user && (
          <div className="flex items-center gap-2">
            <User className="h-4 w-4" />
            <span>Por {evaluation.evaluated_by_user.full_name}</span>
          </div>
        )}
      </div>
    </div>
  );
}
