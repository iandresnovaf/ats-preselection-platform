"use client";

import { useState } from "react";
import { useCandidates, useCandidateApplications } from "@/hooks/use-headhunting";
import { StageBadge, MiniPipeline } from "@/components/headhunting";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
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
import {
  Search,
  MapPin,
  Building2,
  History,
  User,
  Loader2,
  Briefcase,
  Filter,
} from "lucide-react";
import Link from "next/link";
import type { CandidateSummary } from "@/types/headhunting";

interface CandidateCardProps {
  candidate: CandidateSummary;
  onViewHistory: (candidate: CandidateSummary) => void;
}

function CandidateCard({ candidate, onViewHistory }: CandidateCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          {/* Photo */}
          {candidate.photo_url ? (
            <img
              src={candidate.photo_url}
              alt={`${candidate.first_name} ${candidate.last_name}`}
              className="w-16 h-16 rounded-full object-cover"
            />
          ) : (
            <div className="w-16 h-16 rounded-full bg-gray-200 flex items-center justify-center">
              <User className="w-8 h-8 text-gray-400" />
            </div>
          )}

          {/* Info */}
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-lg truncate">
              {candidate.first_name} {candidate.last_name}
            </h3>
            
            {candidate.headline && (
              <p className="text-sm text-gray-600 truncate">{candidate.headline}</p>
            )}
            
            <div className="flex flex-wrap items-center gap-2 mt-2 text-sm text-gray-500">
              {candidate.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {candidate.location}
                </span>
              )}
              {candidate.current_company && (
                <span className="flex items-center gap-1">
                  <Building2 className="w-3 h-3" />
                  {candidate.current_company}
                </span>
              )}
              {candidate.years_experience !== undefined && (
                <Badge variant="secondary" className="text-xs">
                  {candidate.years_experience} años exp.
                </Badge>
              )}
            </div>

            {candidate.skills && candidate.skills.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {candidate.skills.slice(0, 5).map((skill) => (
                  <Badge key={skill} variant="outline" className="text-xs">
                    {skill}
                  </Badge>
                ))}
                {candidate.skills.length > 5 && (
                  <Badge variant="outline" className="text-xs">
                    +{candidate.skills.length - 5}
                  </Badge>
                )}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onViewHistory(candidate)}
            >
              <History className="w-4 h-4 mr-2" />
              Ver histórico
            </Button>
            <Link href={`/candidates/${candidate.id}`}>
              <Button variant="ghost" size="sm" className="w-full">
                Ver perfil
              </Button>
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface CandidateHistoryDialogProps {
  candidate: CandidateSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function CandidateHistoryDialog({
  candidate,
  open,
  onOpenChange,
}: CandidateHistoryDialogProps) {
  const { data: applications, isLoading } = useCandidateApplications(
    candidate?.id || null
  );

  if (!candidate) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            {candidate.photo_url ? (
              <img
                src={candidate.photo_url}
                alt={candidate.first_name}
                className="w-10 h-10 rounded-full object-cover"
              />
            ) : (
              <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                <User className="w-5 h-5 text-gray-400" />
              </div>
            )}
            <span>
              Histórico de {candidate.first_name} {candidate.last_name}
            </span>
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
          </div>
        ) : applications && applications.length > 0 ? (
          <div className="space-y-4 mt-4">
            {applications.map((app) => (
              <Card key={app.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-medium">{app.role?.title}</h4>
                      <p className="text-sm text-gray-500">
                        {app.role?.client?.name}
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        <StageBadge stage={app.stage} />
                        <span className="text-xs text-gray-400">
                          {new Date(app.created_at).toLocaleDateString("es-ES")}
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <MiniPipeline currentStage={app.stage} />
                      <Link href={`/applications/${app.id}`}>
                        <Button variant="outline" size="sm">
                          Ver aplicación
                        </Button>
                      </Link>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Briefcase className="w-12 h-12 mx-auto mb-2 opacity-30" />
            <p>Este candidato no tiene aplicaciones registradas</p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function CandidatesPage() {
  const [search, setSearch] = useState("");
  const [location, setLocation] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateSummary | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  const { data: candidates, isLoading } = useCandidates({
    search: search || undefined,
    location: location || undefined,
  });

  const handleViewHistory = (candidate: CandidateSummary) => {
    setSelectedCandidate(candidate);
    setHistoryOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Candidatos</h1>
          <p className="text-gray-600 mt-1">Base de talentos y aplicaciones</p>
        </div>
        <Link href="/candidates/new">
          <Button>
            <User className="w-4 h-4 mr-2" />
            Nuevo Candidato
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Buscar por nombre..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Ubicación..."
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button variant="outline" className="md:w-auto">
              <Filter className="w-4 h-4 mr-2" />
              Más filtros
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Candidates List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : candidates && candidates.length > 0 ? (
        <div className="grid grid-cols-1 gap-4">
          {candidates.map((candidate) => (
            <CandidateCard
              key={candidate.id}
              candidate={candidate}
              onViewHistory={handleViewHistory}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <User className="w-12 h-12 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-900">
            No se encontraron candidatos
          </h3>
          <p className="text-gray-500 mt-2">
            Intenta ajustar los filtros de búsqueda
          </p>
        </div>
      )}

      {/* History Dialog */}
      <CandidateHistoryDialog
        candidate={selectedCandidate}
        open={historyOpen}
        onOpenChange={setHistoryOpen}
      />
    </div>
  );
}
