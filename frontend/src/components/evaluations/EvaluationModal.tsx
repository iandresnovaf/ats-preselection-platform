import { useState } from "react";
import { Evaluation, AIEvaluationResponse } from "@/types/evaluations";
import { Candidate } from "@/types/candidates";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { EvaluationResult } from "./EvaluationResult";
import { Sparkles, Loader2, RefreshCw, X } from "lucide-react";
import { evaluationService } from "@/services/evaluations";
import { useToast } from "@/hooks/use-toast";

interface EvaluationModalProps {
  candidate: Candidate;
  isOpen: boolean;
  onClose: () => void;
  onEvaluationComplete?: (evaluation: Evaluation) => void;
}

export function EvaluationModal({ 
  candidate, 
  isOpen, 
  onClose, 
  onEvaluationComplete 
}: EvaluationModalProps) {
  const { toast } = useToast();
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAIEvaluation, setIsAIEvaluation] = useState(false);

  const handleAIEvaluation = async () => {
    setIsLoading(true);
    setIsAIEvaluation(true);
    try {
      const response: AIEvaluationResponse = await evaluationService.evaluateWithAI({
        candidate_id: candidate.id,
        use_llm: true,
      });
      
      setEvaluation(response.evaluation);
      onEvaluationComplete?.(response.evaluation);
      
      toast({
        title: "Evaluación completada",
        description: `El candidato fue evaluado con una puntuación de ${response.evaluation.score}/100`,
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Error al evaluar el candidato con IA",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setEvaluation(null);
    setIsAIEvaluation(false);
  };

  const handleClose = () => {
    setEvaluation(null);
    setIsAIEvaluation(false);
    setIsLoading(false);
    onClose();
  };

  const fullName = `${candidate.first_name} ${candidate.last_name}`;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span>Evaluar Candidato: {fullName}</span>
            {evaluation && (
              <Button variant="ghost" size="icon" onClick={handleReset}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            )}
          </DialogTitle>
        </DialogHeader>

        {!evaluation ? (
          <div className="py-12">
            <div className="text-center space-y-6">
              <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
                <Sparkles className="h-8 w-8 text-primary" />
              </div>
              
              <div className="space-y-2">
                <h3 className="text-xl font-semibold">Evaluación con IA</h3>
                <p className="text-muted-foreground max-w-md mx-auto">
                  Utiliza nuestro sistema de inteligencia artificial para analizar el CV y 
                  perfil del candidato. Obtendrás una evaluación completa con puntuación, 
                  fortalezas, áreas de mejora y recomendaciones.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button 
                  onClick={handleAIEvaluation} 
                  disabled={isLoading}
                  size="lg"
                  className="gap-2"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Evaluando con IA...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-5 w-5" />
                      Evaluar con IA
                    </>
                  )}
                </Button>
                <Button 
                  variant="outline" 
                  onClick={handleClose}
                  disabled={isLoading}
                  size="lg"
                >
                  Cancelar
                </Button>
              </div>

              {isLoading && (
                <div className="mt-8 space-y-3">
                  <div className="flex items-center justify-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Analizando CV...</span>
                  </div>
                  <div className="w-64 h-2 bg-gray-200 rounded-full mx-auto overflow-hidden">
                    <div className="h-full bg-primary animate-pulse rounded-full" 
                         style={{ width: '60%', animation: 'pulse 1.5s ease-in-out infinite' }} />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Esto puede tomar unos segundos...
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="py-4">
            <EvaluationResult evaluation={evaluation} />
            
            <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
              <Button variant="outline" onClick={handleClose}>
                Cerrar
              </Button>
              <Button onClick={handleReset} variant="secondary">
                <RefreshCw className="h-4 w-4 mr-2" />
                Nueva Evaluación
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
