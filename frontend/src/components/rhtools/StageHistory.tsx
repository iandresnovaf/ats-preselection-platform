"use client";

import { SubmissionHistory } from "@/types/rhtools";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { 
  Clock, 
  ArrowRight, 
  User, 
  MessageSquare,
  GitCommit
} from "lucide-react";
import { formatDistanceToNow } from "@/lib/utils";

interface StageHistoryProps {
  history: SubmissionHistory[];
  currentStageName?: string;
}

export function StageHistory({ history, currentStageName }: StageHistoryProps) {
  const sortedHistory = [...history].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Historial de Cambios
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-4 top-2 bottom-2 w-px bg-border" />

          <div className="space-y-6">
            {/* Current stage */}
            {currentStageName && (
              <div className="relative flex gap-4">
                <div className="relative z-10">
                  <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
                    <GitCommit className="h-4 w-4 text-primary-foreground" />
                  </div>
                </div>
                <div className="flex-1 pt-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">Etapa actual</span>
                    <Badge variant="default">{currentStageName}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    Estado actual del proceso
                  </p>
                </div>
              </div>
            )}

            {/* History items */}
            {sortedHistory.map((item, index) => (
              <div key={item.id} className="relative flex gap-4">
                <div className="relative z-10">
                  <Avatar className="h-8 w-8 border-2 border-background">
                    <AvatarFallback className="bg-muted text-xs">
                      {item.changed_by_user?.full_name
                        ?.split(" ")
                        .map(n => n[0])
                        .join("")
                        .toUpperCase() || <User className="h-3 w-3" />}
                    </AvatarFallback>
                  </Avatar>
                </div>
                <div className="flex-1 pt-0.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm">
                      {item.changed_by_user?.full_name || "Sistema"}
                    </span>
                    <span className="text-muted-foreground text-sm">
                      cambió la etapa
                    </span>
                    <div className="flex items-center gap-1 text-sm">
                      {item.from_stage_id && (
                        <>
                          <Badge variant="outline" className="text-xs">
                            {item.from_stage_id}
                          </Badge>
                          <ArrowRight className="h-3 w-3 text-muted-foreground" />
                        </>
                      )}
                      <Badge variant="default" className="text-xs">
                        {item.to_stage_id}
                      </Badge>
                    </div>
                  </div>

                  {/* Timestamp */}
                  <p className="text-xs text-muted-foreground mt-1">
                    {formatDistanceToNow(new Date(item.created_at))}
                  </p>

                  {/* Notes/Reason */}
                  {(item.notes || item.reason) && (
                    <div className="mt-2 p-2 bg-muted rounded-md">
                      {item.reason && (
                        <p className="text-xs font-medium text-muted-foreground mb-1">
                          Motivo: {item.reason}
                        </p>
                      )}
                      {item.notes && (
                        <p className="text-sm flex items-start gap-1.5">
                          <MessageSquare className="h-3.5 w-3.5 mt-0.5 text-muted-foreground" />
                          {item.notes}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {sortedHistory.length === 0 && (
              <div className="text-center py-4 text-muted-foreground">
                <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No hay cambios registrados</p>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
