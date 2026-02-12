"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { JobOpening } from "@/types/jobs";
import { Candidate } from "@/types/candidates";
import { MatchResult, MatchFilters } from "@/types/matching";
import { jobService } from "@/services/jobs";
import { candidateService } from "@/services/candidates";
import { matchingService } from "@/services/matching";
import { MatchingPanel } from "@/components/matching/MatchingPanel";
import { CandidateCard } from "@/components/candidates/CandidateCard";
import { InterviewQuestions } from "@/components/matching/InterviewQuestions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { 
  Loader2, 
  RefreshCw, 
  Filter, 
  Search,
  Briefcase,
  Users,
  Award,
  ArrowLeft,
  Sparkles
} from "lucide-react";
import { toast } from "@/components/ui/use-toast";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { sanitizeHtmlForDisplay } from "@/lib/validation";

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

export default function MatchingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("job");
  const candidateId = searchParams.get("candidate");

  // State
  const [jobs, setJobs] = useState<JobOpening[]>([]);
  const [selectedJob, setSelectedJob] = useState<JobOpening | null>(null);
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedMatch, setSelectedMatch] = useState<MatchResult | null>(null);
  
  // Loading states
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [runningBulkMatch, setRunningBulkMatch] = useState(false);
  
  // Filters
  const [minScore, setMinScore] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearch = useDebounce(searchQuery, 300);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);

  // Load jobs on mount
  useEffect(() => {
    loadJobs();
  }, []);

  // Load matches when job is selected
  useEffect(() => {
    if (selectedJob) {
      loadMatches(selectedJob.id);
    }
  }, [selectedJob]);

  // Set initial job from URL
  useEffect(() => {
    if (jobId && jobs.length > 0) {
      const job = jobs.find(j => j.id === jobId);
      if (job) {
        setSelectedJob(job);
      }
    }
  }, [jobId, jobs]);

  const loadJobs = async () => {
    setLoadingJobs(true);
    try {
      const jobsData = await jobService.getJobs({ status: "active" });
      setJobs(jobsData);
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudieron cargar las ofertas",
        variant: "destructive",
      });
    } finally {
      setLoadingJobs(false);
    }
  };

  const loadMatches = async (jobId: string) => {
    setLoadingMatches(true);
    try {
      const filters: MatchFilters = {
        job_opening_id: jobId,
        min_score: minScore > 0 ? minScore : undefined,
      };
      
      const matchesData = await matchingService.getMatches(filters);
      setMatches(matchesData);
      
      // Extract candidates from matches
      const candidatesFromMatches = matchesData
        .map(m => m.candidate)
        .filter((c): c is Candidate => c !== undefined);
      setCandidates(candidatesFromMatches);
      
      // Select initial match if provided in URL
      if (candidateId) {
        const match = matchesData.find(m => m.candidate_id === candidateId);
        if (match) {
          setSelectedMatch(match);
        }
      } else if (matchesData.length > 0) {
        setSelectedMatch(matchesData[0]);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudieron cargar los matches",
        variant: "destructive",
      });
    } finally {
      setLoadingMatches(false);
    }
  };

  const handleRunBulkMatch = async () => {
    if (!selectedJob) return;
    
    setRunningBulkMatch(true);
    try {
      const response = await matchingService.bulkMatch(selectedJob.id);
      toast({
        title: "Matching completado",
        description: `Se procesaron ${response.total_processed} candidatos`,
      });
      // Reload matches
      await loadMatches(selectedJob.id);
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudo completar el matching",
        variant: "destructive",
      });
    } finally {
      setRunningBulkMatch(false);
    }
  };

  // Filter matches based on search and skills
  const filteredMatches = useMemo(() => {
    return matches.filter(match => {
      const candidate = match.candidate;
      if (!candidate) return false;
      
      // Search filter
      if (debouncedSearch) {
        const searchLower = debouncedSearch.toLowerCase();
        const fullName = `${candidate.first_name} ${candidate.last_name}`.toLowerCase();
        const matchesSearch = 
          fullName.includes(searchLower) ||
          candidate.email.toLowerCase().includes(searchLower) ||
          candidate.current_position?.toLowerCase().includes(searchLower);
        if (!matchesSearch) return false;
      }
      
      // Skills filter (would require candidate skills data)
      if (selectedSkills.length > 0) {
        // This would filter based on candidate skills if available
        // For now, we accept all
      }
      
      return true;
    });
  }, [matches, debouncedSearch, selectedSkills]);

  // Sort by score descending
  const sortedMatches = useMemo(() => {
    return [...filteredMatches].sort((a, b) => b.score - a.score);
  }, [filteredMatches]);

  const handleJobChange = (jobId: string) => {
    const job = jobs.find(j => j.id === jobId);
    if (job) {
      setSelectedJob(job);
      setSelectedMatch(null);
      // Update URL
      router.push(`/dashboard/matching?job=${jobId}`);
    }
  };

  // Sanitize job description for XSS protection
  const sanitizedDescription = selectedJob?.description
    ? sanitizeHtmlForDisplay(selectedJob.description)
    : '';

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Matching de Candidatos</h1>
          <p className="text-muted-foreground">
            Compara candidatos contra los requisitos del puesto
          </p>
        </div>
        <Link href="/dashboard/jobs">
          <Button variant="outline">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver a Ofertas
          </Button>
        </Link>
      </div>

      {/* Job Selector */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Briefcase className="h-5 w-5" />
            Seleccionar Oferta
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Select
            value={selectedJob?.id || ""}
            onValueChange={handleJobChange}
            disabled={loadingJobs}
          >
            <SelectTrigger className="w-full md:w-[400px]">
              <SelectValue placeholder={loadingJobs ? "Cargando ofertas..." : "Selecciona una oferta"} />
            </SelectTrigger>
            <SelectContent>
              {jobs.map((job) => (
                <SelectItem key={job.id} value={job.id}>
                  {job.title} - {job.department}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {selectedJob ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Job Details */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Briefcase className="h-5 w-5" />
                  Detalles del Puesto
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h3 className="text-xl font-semibold">{selectedJob.title}</h3>
                  <div className="flex flex-wrap gap-2 mt-2">
                    <Badge variant="secondary">{selectedJob.department}</Badge>
                    <Badge variant="secondary">{selectedJob.seniority}</Badge>
                    <Badge variant="secondary">{selectedJob.location}</Badge>
                    {selectedJob.employment_type && (
                      <Badge variant="outline">{selectedJob.employment_type}</Badge>
                    )}
                  </div>
                </div>

                <Separator />

                {/* Job Description */}
                <div>
                  <h4 className="font-medium mb-2">Descripción</h4>
                  <div 
                    className="text-sm text-muted-foreground prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: sanitizedDescription }}
                  />
                </div>

                {/* Requirements */}
                {selectedJob.required_skills && selectedJob.required_skills.length > 0 && (
                  <>
                    <Separator />
                    <div>
                      <h4 className="font-medium mb-2">Skills Requeridas</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedJob.required_skills.map((skill, index) => (
                          <Badge key={index} variant="outline">
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </>
                )}

                {/* Experience & Education */}
                {(selectedJob.min_years_experience || selectedJob.education_level) && (
                  <>
                    <Separator />
                    <div className="grid grid-cols-2 gap-4">
                      {selectedJob.min_years_experience && (
                        <div>
                          <h4 className="font-medium mb-1">Experiencia Mínima</h4>
                          <p className="text-sm text-muted-foreground">
                            {selectedJob.min_years_experience} años
                          </p>
                        </div>
                      )}
                      {selectedJob.education_level && (
                        <div>
                          <h4 className="font-medium mb-1">Educación Requerida</h4>
                          <p className="text-sm text-muted-foreground capitalize">
                            {selectedJob.education_level.replace('-', ' ')}
                          </p>
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* Salary Range */}
                {(selectedJob.salary_min || selectedJob.salary_max) && (
                  <>
                    <Separator />
                    <div>
                      <h4 className="font-medium mb-1">Rango Salarial</h4>
                      <p className="text-sm text-muted-foreground">
                        ${selectedJob.salary_min?.toLocaleString() || '0'} - ${selectedJob.salary_max?.toLocaleString() || '0'} USD/año
                      </p>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Selected Candidate Matching Panel */}
            {selectedMatch && (
              <MatchingPanel 
                match={selectedMatch}
                onRefresh={() => selectedJob && loadMatches(selectedJob.id)}
              />
            )}

            {/* Interview Questions */}
            {selectedMatch && selectedMatch.candidate && (
              <InterviewQuestions
                matchId={selectedMatch.id}
                candidateName={`${selectedMatch.candidate.first_name} ${selectedMatch.candidate.last_name}`}
                jobTitle={selectedJob.title}
              />
            )}
          </div>

          {/* Right Column: Candidates List */}
          <div className="space-y-6">
            {/* Filters */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Filter className="h-5 w-5" />
                  Filtros
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="search">Buscar candidato</Label>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="search"
                        placeholder="Nombre, email, posición..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="min-score">Score mínimo</Label>
                    <Select
                      value={String(minScore)}
                      onValueChange={(value) => setMinScore(Number(value))}
                    >
                      <SelectTrigger id="min-score">
                        <SelectValue placeholder="Cualquier score" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="0">Cualquier score</SelectItem>
                        <SelectItem value="50">50+ (Review)</SelectItem>
                        <SelectItem value="75">75+ (Top)</SelectItem>
                        <SelectItem value="90">90+ (Excelente)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Button 
                  variant="outline" 
                  className="w-full"
                  onClick={() => {
                    setSearchQuery("");
                    setMinScore(0);
                    setSelectedSkills([]);
                  }}
                >
                  Limpiar filtros
                </Button>
              </CardContent>
            </Card>

            {/* Run Bulk Match Button */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-muted-foreground" />
                <span className="text-muted-foreground">
                  {sortedMatches.length} candidatos encontrados
                </span>
              </div>
              <Button 
                onClick={handleRunBulkMatch}
                disabled={runningBulkMatch}
              >
                {runningBulkMatch ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Procesando...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Re-ejecutar Matching
                  </>
                )}
              </Button>
            </div>

            {/* Candidates Grid */}
            {loadingMatches ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : sortedMatches.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Award className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <h3 className="text-lg font-medium mb-2">No hay matches</h3>
                  <p className="text-muted-foreground mb-4">
                    No se encontraron candidatos con el score mínimo especificado.
                  </p>
                  <Button onClick={handleRunBulkMatch} disabled={runningBulkMatch}>
                    {runningBulkMatch ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Procesando...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4 mr-2" />
                        Ejecutar Matching
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {sortedMatches.map((match) => {
                  if (!match.candidate) return null;
                  const isSelected = selectedMatch?.id === match.id;
                  
                  return (
                    <div 
                      key={match.id}
                      onClick={() => setSelectedMatch(match)}
                      className={cn(
                        "cursor-pointer transition-all",
                        isSelected && "ring-2 ring-primary ring-offset-2"
                      )}
                    >
                      <CandidateCard
                        candidate={match.candidate}
                        matchScore={match.score}
                        matchDecision={match.decision}
                        onMatch={() => setSelectedMatch(match)}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Briefcase className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-medium mb-2">Selecciona una oferta</h3>
            <p className="text-muted-foreground">
              Elige una oferta de trabajo para ver el matching con candidatos.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
