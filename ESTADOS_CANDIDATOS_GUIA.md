# Estados Detallados de Candidatos - Guía de Implementación

## Resumen de Cambios

Esta implementación expande el sistema de estados de candidatos de 7 estados básicos a 15 estados detallados que cubren todo el flujo de contacto y selección.

## Nuevos Estados

### Etapas Iniciales (1-3)
1. `sourcing` - Recién ingresado
2. `shortlist` - Pre-seleccionado
3. `terna` - En terna de 3 candidatos

### Etapas de Contacto (4-8)
4. `contact_pending` - Pendiente de contactar (necesita datos)
5. `contacted` - Contactado, esperando respuesta
6. `interested` - Respondió positivamente
7. `not_interested` - Respondió negativamente
8. `no_response` - No respondió (48-72h)

### Etapas de Entrevista (9-10)
9. `interview_scheduled` - Entrevista agendada
10. `interview_done` - Entrevista realizada

### Etapas de Oferta (11-13)
11. `offer_sent` - Oferta enviada
12. `offer_accepted` - Oferta aceptada
13. `offer_rejected` - Oferta rechazada

### Estados Finales (14-15)
14. `hired` - Contratado
15. `discarded` - Descartado por consultor

## Componentes Nuevos

### 1. MissingContactModal
Modal para solicitar datos de contacto faltantes cuando el consultor marca "CONTINUAR".

```tsx
import { MissingContactModal } from "@/components/modals";

<MissingContactModal
  isOpen={isModalOpen}
  candidate={{
    candidate_id: "uuid",
    full_name: "Juan Pérez",
    email: undefined,
    phone: undefined,
  }}
  onSubmit={(data) => console.log(data)} // { email?: string; phone?: string }
  onSkip={() => console.log("Skipped")}
  isLoading={false}
/>
```

### 2. useApplicationDecision Hook
Hook para manejar decisiones del consultor con lógica de negocio integrada.

```tsx
import { useApplicationDecision } from "@/hooks";

const {
  isContactModalOpen,
  pendingCandidate,
  makeConsultantDecision,
  updateContactStatus,
  sendMessage,
  closeContactModal,
  submitContactData,
  skipContactModal,
} = useApplicationDecision();

// Cuando el consultor marca "CONTINUAR"
await makeConsultantDecision(applicationId, { decision: "continue" }, candidateInfo);
// Si faltan datos, se abre automáticamente el modal

// Actualizar estado de contacto
await updateContactStatus(applicationId, { status: "interested" });

// Enviar mensaje
await sendMessage(applicationId, { template_id: "welcome", channel: "email" });
```

### 3. StageBadge Actualizado
Badge con colores específicos para cada estado.

```tsx
import { StageBadge } from "@/components/headhunting";

<StageBadge stage="contact_pending" size="md" />
<StageBadge stage="interested" />
<StageBadge stage="offer_accepted" size="lg" />
```

## API Endpoints Nuevos

### 1. PATCH /api/v1/applications/{id}/consultant-decision
Toma de decisión por parte del consultor.

```json
{
  "decision": "continue" | "discard",
  "reason": "string"  // requerido si decision == "discard"
}
```

**Lógica:**
- Si `continue` y faltan datos → `contact_pending`
- Si `continue` y datos completos → `contacted`
- Si `discard` → `discarded`

### 2. PATCH /api/v1/applications/{id}/contact-status
Actualizar estado de contacto.

```json
{
  "status": "contacted" | "interested" | "not_interested" | "no_response"
}
```

### 3. POST /api/v1/applications/{id}/send-message
Enviar mensaje al candidato.

```json
{
  "template_id": "string",
  "channel": "email" | "whatsapp"
}
```

## Flujo de Uso

### Ejemplo Completo

```tsx
import { useState } from "react";
import { useApplicationDecision } from "@/hooks";
import { MissingContactModal } from "@/components/modals";
import { Button } from "@/components/ui/button";

function ApplicationActions({ application, candidate }) {
  const {
    isContactModalOpen,
    pendingCandidate,
    makeConsultantDecision,
    closeContactModal,
    submitContactData,
    skipContactModal,
    isDecisionLoading,
  } = useApplicationDecision();

  const handleContinue = async () => {
    await makeConsultantDecision(
      application.id,
      { decision: "continue" },
      {
        candidate_id: candidate.id,
        full_name: candidate.full_name,
        email: candidate.email,
        phone: candidate.phone,
      }
    );
  };

  const handleDiscard = async () => {
    await makeConsultantDecision(
      application.id,
      { decision: "discard", reason: "No cumple requisitos" }
    );
  };

  return (
    <>
      <div className="flex gap-2">
        <Button onClick={handleContinue} disabled={isDecisionLoading}>
          Continuar
        </Button>
        <Button variant="destructive" onClick={handleDiscard} disabled={isDecisionLoading}>
          Descartar
        </Button>
      </div>

      <MissingContactModal
        isOpen={isContactModalOpen}
        candidate={pendingCandidate || candidate}
        onSubmit={submitContactData}
        onSkip={skipContactModal}
        isLoading={isDecisionLoading}
      />
    </>
  );
}
```

## Migración de Datos

La migración `20260216_2055_detailed_application_stages.py` convierte:
- `interview` → `interview_scheduled`
- `offer` → `offer_sent`
- `rejected` → `discarded`

## Compatibilidad

Los componentes mantienen compatibilidad hacia atrás:
- `StageBadge` soporta estados legacy (`interview`, `offer`, `rejected`)
- El API acepta y normaliza estados antiguos
- La base de datos usa el nuevo enum con todos los estados

## Tests

Los tests están ubicados en:
- `frontend/src/hooks/__tests__/use-application-decision.test.tsx`
- `frontend/src/components/modals/__tests__/MissingContactModal.test.tsx`
