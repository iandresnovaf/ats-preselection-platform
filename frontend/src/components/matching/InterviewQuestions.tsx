import { useState, useCallback } from "react";
import { InterviewQuestion, GenerateQuestionsRequest } from "@/types/matching";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { 
  Sparkles, 
  Loader2, 
  Copy, 
  Check,
  HelpCircle,
  Target,
  Brain,
  Users,
  RefreshCw
} from "lucide-react";
import { matchingService } from "@/services/matching";
import { toast } from "@/components/ui/use-toast";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";

interface InterviewQuestionsProps {
  matchId: string;
  candidateName?: string;
  jobTitle?: string;
  className?: string;
}

type QuestionCategory = 'gaps' | 'strengths' | 'technical' | 'behavioral';

interface CategoryOption {
  id: QuestionCategory;
  label: string;
  description: string;
  icon: typeof Target;
}

const categoryOptions: CategoryOption[] = [
  {
    id: 'gaps',
    label: 'Gaps',
    description: 'Preguntas para profundizar en áreas de mejora',
    icon: Target,
  },
  {
    id: 'strengths',
    label: 'Fortalezas',
    description: 'Preguntas para validar fortalezas identificadas',
    icon: Check,
  },
  {
    id: 'technical',
    label: 'Técnicas',
    description: 'Preguntas técnicas específicas del puesto',
    icon: Brain,
  },
  {
    id: 'behavioral',
    label: 'Comportamentales',
    description: 'Preguntas sobre comportamiento y soft skills',
    icon: Users,
  },
];

export function InterviewQuestions({ 
  matchId, 
  candidateName, 
  jobTitle,
  className 
}: InterviewQuestionsProps) {
  const [questions, setQuestions] = useState<InterviewQuestion[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<QuestionCategory[]>([
    'gaps', 'strengths', 'technical', 'behavioral'
  ]);
  const [generating, setGenerating] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [questionCount, setQuestionCount] = useState(8);
  const [generated, setGenerated] = useState(false);

  const handleCategoryToggle = useCallback((category: QuestionCategory) => {
    setSelectedCategories(prev => 
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  }, []);

  const handleGenerate = useCallback(async () => {
    if (selectedCategories.length === 0) {
      toast({
        title: "Selecciona categorías",
        description: "Elige al menos una categoría de preguntas",
        variant: "destructive",
      });
      return;
    }

    setGenerating(true);
    try {
      const response = await matchingService.generateInterviewQuestions({
        match_id: matchId,
        count: questionCount,
        focus_areas: selectedCategories,
      });
      setQuestions(response.questions);
      setGenerated(true);
      toast({
        title: "Preguntas generadas",
        description: `Se generaron ${response.questions.length} preguntas personalizadas`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudieron generar las preguntas. Intenta de nuevo.",
        variant: "destructive",
      });
    } finally {
      setGenerating(false);
    }
  }, [matchId, selectedCategories, questionCount]);

  const handleCopyQuestion = useCallback((question: string, index: number) => {
    navigator.clipboard.writeText(question);
    setCopiedIndex(index);
    toast({
      title: "Copiado",
      description: "Pregunta copiada al portapapeles",
    });
    setTimeout(() => setCopiedIndex(null), 2000);
  }, []);

  const handleCopyAll = useCallback(() => {
    const allQuestions = questions.map((q, i) => `${i + 1}. ${q.question}`).join('\n\n');
    navigator.clipboard.writeText(allQuestions);
    toast({
      title: "Todas copiadas",
      description: `${questions.length} preguntas copiadas al portapapeles`,
    });
  }, [questions]);

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'gap': return Target;
      case 'strength': return Check;
      case 'technical': return Brain;
      case 'behavioral': return Users;
      default: return HelpCircle;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'gap': return 'bg-yellow-100 text-yellow-800';
      case 'strength': return 'bg-green-100 text-green-800';
      case 'technical': return 'bg-blue-100 text-blue-800';
      case 'behavioral': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'gap': return 'Gap';
      case 'strength': return 'Fortaleza';
      case 'technical': return 'Técnica';
      case 'behavioral': return 'Comportamental';
      default: return category;
    }
  };

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Sparkles className="h-5 w-5 text-primary" />
          Generador de Preguntas de Entrevista
        </CardTitle>
        {candidateName && jobTitle && (
          <p className="text-sm text-muted-foreground">
            Para: <span className="font-medium">{candidateName}</span> | {jobTitle}
          </p>
        )}
      </CardHeader>

      <CardContent className="flex-1 space-y-6">
        {/* Category Selection */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Categorías de preguntas</Label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {categoryOptions.map((category) => {
              const Icon = category.icon;
              const isSelected = selectedCategories.includes(category.id);
              return (
                <div
                  key={category.id}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                    isSelected 
                      ? "border-primary bg-primary/5" 
                      : "border-muted hover:border-muted-foreground/50"
                  )}
                  onClick={() => handleCategoryToggle(category.id)}
                  role="checkbox"
                  aria-checked={isSelected}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleCategoryToggle(category.id);
                    }
                  }}
                >
                  <Checkbox 
                    checked={isSelected}
                    onChange={() => {}}
                    aria-hidden="true"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium text-sm">{category.label}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {category.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Question Count */}
        <div className="space-y-2">
          <Label htmlFor="question-count" className="text-sm font-medium">
            Cantidad de preguntas: {questionCount}
          </Label>
          <div className="flex items-center gap-4">
            <input
              id="question-count"
              type="range"
              min={3}
              max={15}
              value={questionCount}
              onChange={(e) => setQuestionCount(Number(e.target.value))}
              className="flex-1 h-2 bg-secondary rounded-lg appearance-none cursor-pointer"
              aria-label="Número de preguntas a generar"
            />
            <span className="text-sm font-medium w-8 text-center">{questionCount}</span>
          </div>
        </div>

        {/* Generate Button */}
        <Button 
          onClick={handleGenerate}
          disabled={generating || selectedCategories.length === 0}
          className="w-full"
        >
          {generating ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Generando con IA...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4 mr-2" />
              Generar Preguntas
            </>
          )}
        </Button>

        {/* Generated Questions */}
        {generated && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-medium">
                Preguntas Generadas ({questions.length})
              </h4>
              {questions.length > 0 && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={handleCopyAll}
                >
                  <Copy className="h-3 w-3 mr-1" />
                  Copiar todas
                </Button>
              )}
            </div>

            {questions.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <HelpCircle className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No se pudieron generar preguntas</p>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="mt-3"
                  onClick={handleGenerate}
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Intentar de nuevo
                </Button>
              </div>
            ) : (
              <ScrollArea className="h-[400px] pr-4">
                <div className="space-y-3">
                  {questions.map((question, index) => {
                    const CategoryIcon = getCategoryIcon(question.category);
                    return (
                      <div 
                        key={question.id}
                        className="p-4 bg-muted rounded-lg group hover:bg-muted/80 transition-colors"
                      >
                        <div className="flex items-start gap-3">
                          <span className="flex-shrink-0 w-6 h-6 bg-primary/10 text-primary rounded-full flex items-center justify-center text-xs font-medium">
                            {index + 1}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm">{question.question}</p>
                            {question.context && (
                              <p className="text-xs text-muted-foreground mt-1">
                                {question.context}
                              </p>
                            )}
                            <div className="flex items-center gap-2 mt-2">
                              <Badge 
                                variant="secondary" 
                                className={cn("text-xs", getCategoryColor(question.category))}
                              >
                                <CategoryIcon className="h-3 w-3 mr-1" />
                                {getCategoryLabel(question.category)}
                              </Badge>
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={() => handleCopyQuestion(question.question, index)}
                            aria-label="Copiar pregunta"
                          >
                            {copiedIndex === index ? (
                              <Check className="h-4 w-4 text-green-500" />
                            ) : (
                              <Copy className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </ScrollArea>
            )}
          </div>
        )}
      </CardContent>

      {generated && questions.length > 0 && (
        <CardFooter className="border-t pt-4">
          <p className="text-xs text-muted-foreground">
            Estas preguntas fueron generadas por IA basándose en el análisis de matching 
            entre el candidato y el puesto.
          </p>
        </CardFooter>
      )}
    </Card>
  );
}

export default InterviewQuestions;
