import { useState, useCallback } from "react";
import { MatchResult, MatchDecision, InterviewQuestion } from "@/types/matching";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { 
  CheckCircle2, 
  AlertCircle, 
  XCircle, 
  ChevronDown, 
  ChevronUp, 
  Lightbulb,
  FileText,
  Sparkles,
  Loader2
} from "lucide-react";
import { cn } from "@/lib/utils";
import { matchingService } from "@/services/matching";
import { toast } from "@/components/ui/use-toast";
import { sanitizeHtmlForDisplay } from "@/lib/validation";

interface MatchingPanelProps {
  match: MatchResult;
  onRefresh?: () => void;
  className?: string;
}

const decisionConfig: Record<MatchDecision, { 
  label: string; 
  color: string; 
  bgColor: string;
  icon: typeof CheckCircle2;
}> = {
  PROCEED: {
    label: "PROCEED",
    color: "text-green-700",
    bgColor: "bg-green-100",
    icon: CheckCircle2,
  },
  REVIEW: {
    label: "REVIEW",
    color: "text-yellow-700",
    bgColor: "bg-yellow-100",
    icon: AlertCircle,
  },
  REJECT: {
    label: "REJECT",
    color: "text-red-700",
    bgColor: "bg-red-100",
    icon: XCircle,
  },
};

function getScoreColor(score: number): string {
  if (score >= 75) return "text-green-600";
  if (score >= 50) return "text-yellow-600";
  return "text-red-600";
}

function getScoreBgColor(score: number): string {
  if (score >= 75) return "bg-green-500";
  if (score >= 50) return "bg-yellow-500";
  return "bg-red-500";
}

export function MatchingPanel({ match, onRefresh, className }: MatchingPanelProps) {
  const [showDetails, setShowDetails] = useState(false);
  const [showQuestions, setShowQuestions] = useState(false);
  const [questions, setQuestions] = useState<InterviewQuestion[]>([]);
  const [generatingQuestions, setGeneratingQuestions] = useState(false);
  const [questionsGenerated, setQuestionsGenerated] = useState(false);

  const decision = decisionConfig[match.decision];
  const DecisionIcon = decision.icon;

  const handleGenerateQuestions = useCallback(async () => {
    setGeneratingQuestions(true);
    try {
      const response = await matchingService.generateInterviewQuestions({
        match_id: match.id,
        count: 8,
        focus_areas: ['gaps', 'strengths', 'technical', 'behavioral'],
      });
      setQuestions(response.questions);
      setQuestionsGenerated(true);
      setShowQuestions(true);
      toast({
        title: "Preguntas generadas",
        description: `Se generaron ${response.questions.length} preguntas de entrevista`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudieron generar las preguntas. Intenta de nuevo.",
        variant: "destructive",
      });
    } finally {
      setGeneratingQuestions(false);
    }
  }, [match.id]);

  // Sanitize reasoning for XSS protection
  const sanitizedReasoning = match.reasoning 
    ? sanitizeHtmlForDisplay(match.reasoning)
    : null;

  return (
    <Card className={cn("overflow-hidden", className)}>
      {/* Score Header */}
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Análisis de Matching</CardTitle>
          <Badge 
            className={cn("font-semibold", decision.bgColor, decision.color)}
            aria-label={`Decisión: ${decision.label}`}
          >
            <DecisionIcon className="h-3 w-3 mr-1" />
            {decision.label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Big Score */}
        <div className="text-center">
          <div className={cn("text-6xl font-bold", getScoreColor(match.score))} aria-label={`Score de matching: ${match.score} de 100`}>
            {Math.round(match.score)}
          </div>
          <p className="text-sm text-muted-foreground mt-1">Score de compatibilidad</p>
          <div className="mt-3">
            <Progress 
              value={match.score} 
              className="h-3"
              aria-label="Barra de progreso del score"
            />
          </div>
        </div>

        {/* Breakdown */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            Desglose
          </h4>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>Skills</span>
              <span className={getScoreColor(match.breakdown.skills_match)}>
                {Math.round(match.breakdown.skills_match)}%
              </span>
            </div>
            <Progress 
              value={match.breakdown.skills_match} 
              className="h-2"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>Experiencia</span>
              <span className={getScoreColor(match.breakdown.experience_match)}>
                {Math.round(match.breakdown.experience_match)}%
              </span>
            </div>
            <Progress 
              value={match.breakdown.experience_match} 
              className="h-2"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>Educación</span>
              <span className={getScoreColor(match.breakdown.education_match)}>
                {Math.round(match.breakdown.education_match)}%
              </span>
            </div>
            <Progress 
              value={match.breakdown.education_match} 
              className="h-2"
            />
          </div>
        </div>

        {/* Strengths */}
        {match.strengths && match.strengths.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-green-700 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Fortalezas
            </h4>
            <ul className="space-y-1">
              {match.strengths.slice(0, 4).map((strength, index) => (
                <li 
                  key={index} 
                  className="text-sm text-muted-foreground flex items-start gap-2"
                >
                  <CheckCircle2 className="h-3 w-3 text-green-500 mt-0.5 shrink-0" />
                  <span>{strength}</span>
                </li>
              ))}
              {match.strengths.length > 4 && (
                <li className="text-xs text-muted-foreground italic">
                  +{match.strengths.length - 4} más...
                </li>
              )}
            </ul>
          </div>
        )}

        {/* Gaps */}
        {match.gaps && match.gaps.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-yellow-700 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              Gaps Identificados
            </h4>
            <ul className="space-y-1">
              {match.gaps.slice(0, 4).map((gap, index) => (
                <li 
                  key={index} 
                  className="text-sm text-muted-foreground flex items-start gap-2"
                >
                  <AlertCircle className="h-3 w-3 text-yellow-500 mt-0.5 shrink-0" />
                  <span>{gap}</span>
                </li>
              ))}
              {match.gaps.length > 4 && (
                <li className="text-xs text-muted-foreground italic">
                  +{match.gaps.length - 4} más...
                </li>
              )}
            </ul>
          </div>
        )}

        {/* Red Flags */}
        {match.red_flags && match.red_flags.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-red-700 flex items-center gap-2">
              <XCircle className="h-4 w-4" />
              Red Flags
            </h4>
            <ul className="space-y-1">
              {match.red_flags.map((flag, index) => (
                <li 
                  key={index} 
                  className="text-sm text-muted-foreground flex items-start gap-2"
                >
                  <XCircle className="h-3 w-3 text-red-500 mt-0.5 shrink-0" />
                  <span>{flag}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>

      <CardFooter className="flex flex-col gap-3">
        {/* View Details Button with Dialog */}
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" className="w-full">
              <FileText className="h-4 w-4 mr-2" />
              Ver detalles completos
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Análisis Detallado del Matching</DialogTitle>
            </DialogHeader>
            <div className="space-y-6 py-4">
              {/* Full Score Breakdown */}
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="p-4 bg-muted rounded-lg">
                  <div className={cn("text-2xl font-bold", getScoreColor(match.breakdown.skills_match))}>
                    {Math.round(match.breakdown.skills_match)}%
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Skills</p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <div className={cn("text-2xl font-bold", getScoreColor(match.breakdown.experience_match))}>
                    {Math.round(match.breakdown.experience_match)}%
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Experiencia</p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <div className={cn("text-2xl font-bold", getScoreColor(match.breakdown.education_match))}>
                    {Math.round(match.breakdown.education_match)}%
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Educación</p>
                </div>
              </div>

              {/* Full Strengths */}
              {match.strengths && match.strengths.length > 0 && (
                <div>
                  <h4 className="font-medium text-green-700 flex items-center gap-2 mb-3">
                    <CheckCircle2 className="h-4 w-4" />
                    Fortalezas ({match.strengths.length})
                  </h4>
                  <ul className="space-y-2">
                    {match.strengths.map((strength, index) => (
                      <li 
                        key={index} 
                        className="text-sm flex items-start gap-2 p-2 bg-green-50 rounded"
                      >
                        <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                        <span>{strength}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Full Gaps */}
              {match.gaps && match.gaps.length > 0 && (
                <div>
                  <h4 className="font-medium text-yellow-700 flex items-center gap-2 mb-3">
                    <AlertCircle className="h-4 w-4" />
                    Gaps Identificados ({match.gaps.length})
                  </h4>
                  <ul className="space-y-2">
                    {match.gaps.map((gap, index) => (
                      <li 
                        key={index} 
                        className="text-sm flex items-start gap-2 p-2 bg-yellow-50 rounded"
                      >
                        <AlertCircle className="h-4 w-4 text-yellow-500 mt-0.5 shrink-0" />
                        <span>{gap}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Full Red Flags */}
              {match.red_flags && match.red_flags.length > 0 && (
                <div>
                  <h4 className="font-medium text-red-700 flex items-center gap-2 mb-3">
                    <XCircle className="h-4 w-4" />
                    Red Flags ({match.red_flags.length})
                  </h4>
                  <ul className="space-y-2">
                    {match.red_flags.map((flag, index) => (
                      <li 
                        key={index} 
                        className="text-sm flex items-start gap-2 p-2 bg-red-50 rounded"
                      >
                        <XCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                        <span>{flag}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* AI Reasoning */}
              {sanitizedReasoning && (
                <div>
                  <h4 className="font-medium flex items-center gap-2 mb-3">
                    <Lightbulb className="h-4 w-4" />
                    Razonamiento de la IA
                  </h4>
                  <div 
                    className="text-sm text-muted-foreground p-4 bg-muted rounded-lg prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: sanitizedReasoning }}
                  />
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>

        {/* Generate Questions Button */}
        <Button 
          variant="secondary" 
          className="w-full"
          onClick={handleGenerateQuestions}
          disabled={generatingQuestions}
        >
          {generatingQuestions ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Generando preguntas...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4 mr-2" />
              Generar preguntas de entrevista
            </>
          )}
        </Button>

        {/* Generated Questions Dialog */}
        <Dialog open={showQuestions} onOpenChange={setShowQuestions}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                Preguntas de Entrevista Generadas
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {questions.length === 0 ? (
                <p className="text-center text-muted-foreground">
                  No se generaron preguntas. Intenta de nuevo.
                </p>
              ) : (
                <div className="space-y-4">
                  {questions.map((q, index) => (
                    <div key={q.id} className="p-4 bg-muted rounded-lg">
                      <div className="flex items-start gap-3">
                        <span className="flex-shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-xs font-medium">
                          {index + 1}
                        </span>
                        <div className="flex-1">
                          <p className="font-medium">{q.question}</p>
                          {q.context && (
                            <p className="text-sm text-muted-foreground mt-1">
                              {q.context}
                            </p>
                          )}
                          <Badge variant="outline" className="mt-2 text-xs">
                            {q.category === 'gap' && 'Gap'}
                            {q.category === 'strength' && 'Fortaleza'}
                            {q.category === 'technical' && 'Técnica'}
                            {q.category === 'behavioral' && 'Comportamental'}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </CardFooter>
    </Card>
  );
}

export default MatchingPanel;
