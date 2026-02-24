# Sistema de Scoring con IA - Resumen de Implementación

## 📋 Resumen

Se ha implementado un sistema completo de scoring con IA para evaluar compatibilidad entre CV de candidatos y vacantes en el ATS.

## 🗂️ Archivos Creados/Modificados

### Backend

#### 1. `app/services/scoring_service.py` (NUEVO)
Servicio principal de scoring con IA:
- Usa OpenAI GPT-4 para evaluar compatibilidad
- Extrae datos de CV de `hh_cv_extractions`
- Genera score 0-100 con justificación detallada
- Evalúa: skills, experiencia, seniority, industria
- Guarda resultados en `hh_applications.overall_score`
- Incluye fallback si IA no está disponible

#### 2. `app/api/v1/applications.py` (MODIFICADO)
Nuevos endpoints y funcionalidades:

**Nuevos Endpoints:**
- `POST /applications/{id}/score` - Evalúa candidato con IA
- `GET /applications/{id}/score` - Obtiene score existente
- `GET /applications/ranking/by-role/{role_id}` - Ranking de candidatos

**Modificaciones:**
- `GET /applications` - Ahora soporta:
  - `sort_by=score` / `sort_by=score_asc` - Ordenar por compatibilidad
  - `min_score=80` - Filtrar por score mínimo
  - `max_score=100` - Filtrar por score máximo
- `POST /applications` - Trigger automático de scoring en background

**Schemas Agregados:**
- `ScoringResponse` - Respuesta del scoring
- `ScoringRequest` - Request con opción de forzar recálculo
- `CandidateRankingResponse` - Respuesta del ranking
- `CandidateRankingItem` - Item individual del ranking

### Frontend

#### 3. `src/hooks/use-headhunting.ts` (MODIFICADO)
Nuevos hooks:

**Interfaces Agregadas:**
- `ScoringResponse` - Estructura de respuesta del scoring
- `RankingResponse` / `RankingItem` - Estructuras de ranking

**Nuevos Hooks:**
- `useScoreApplication()` - Ejecutar scoring con IA
- `useApplicationScore(id)` - Obtener score de aplicación
- `useScoreMultipleApplications()` - Score múltiple en batch
- `useCandidateRanking(roleId, options)` - Obtener ranking

**Modificaciones:**
- `useApplications()` - Ahora acepta `sort_by`, `min_score`, `max_score`

#### 4. `src/app/applications/[id]/compare/page.tsx` (NUEVO)
Vista de comparación lado a lado:
- Panel izquierdo: Requisitos de la vacante
- Panel derecho: CV del candidato con highlights
- Desglose del score por categorías
- Skills coincidentes (verde) vs faltantes (rojo)
- Justificación del score
- Botón para recalcular

#### 5. `src/app/roles/[id]/ranking/page.tsx` (NUEVO)
Vista de ranking de candidatos:
- Tabla ordenada por score (mayor a menor)
- Badges para Top 3: 🥇 🥈 🥉
- Filtros por rangos de score
- Exportación a CSV
- Estadísticas: total, con score, promedio, mejor score
- Candidatos sin evaluar listados separadamente

#### 6. `src/components/score-filters.tsx` (NUEVO)
Componente de filtros por score:
- Presets: Excelente, Muy bueno, Bueno, Regular, Bajo
- Slider para rango personalizado
- Hook `useScoreFilters()` para manejo de estado

#### 7. `src/app/roles/page.tsx` (MODIFICADO)
Mejoras en el diálogo de candidatos:
- Dropdown para ordenar por score
- Badges de score con colores según valor
- Enlaces a "Comparar" y "Ver Ranking"
- Indicador "Top" para scores >= 90

## 🔧 Funcionalidades Implementadas

### 1. Score Automático al Subir CV ✅
- Trigger automático en `POST /applications`
- Se ejecuta en background (async)
- No bloquea la creación de la aplicación
- Manejo de errores sin afectar el flujo

### 2. Comparación Lado a Lado ✅
- URL: `/applications/{id}/compare`
- Vista dividida: Vacante | Candidato
- Highlights visuales de coincidencias
- Desglose por categorías
- Botón de recálculo

### 3. Ranking de Candidatos ✅
- URL: `/roles/{id}/ranking`
- Tabla ordenada por score
- Badges para Top 3
- Exportación CSV
- Filtros por rangos

### 4. Filtros por Score ✅
- Endpoint soporta `min_score` y `max_score`
- Componente visual con presets
- Slider para rangos personalizados
- Ordenamiento ascendente/descendente

## 📊 Prompt de IA Detallado

El sistema utiliza un prompt completo que evalúa:

```
1. MATCH DE SKILLS TÉCNICAS (30% del score)
   - Compara habilidades del CV vs requisitos del rol
   - Identifica skills faltantes críticas vs deseables
   
2. AÑOS DE EXPERIENCIA (25% del score)
   - Compara experiencia del candidato vs requisitos
   - Evalúa relevancia de experiencia previa
   
3. NIVEL DE SENIORITY (25% del score)
   - Evalúa coincidencia de nivel
   - Considera responsabilidades previas
   
4. INDUSTRIA/SECTOR (20% del score)
   - Evalúa experiencia en industria similar
   - Considera transferibilidad de skills
```

**Rangos de Score:**
- 90-100: Candidato ideal
- 70-89: Candidato fuerte
- 50-69: Candidato aceptable
- 30-49: Candidato débil
- 0-29: No compatible

## 🔌 Integración con OpenAI

Requiere variables de entorno:
```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini  # o gpt-4, gpt-3.5-turbo
```

## 📈 API Endpoints

### Scoring
```
POST   /api/v1/applications/{id}/score
GET    /api/v1/applications/{id}/score
```

### Ranking
```
GET    /api/v1/applications/ranking/by-role/{role_id}?min_score=80&max_results=50
```

### Listado con Filtros
```
GET    /api/v1/applications?role_id=xxx&sort_by=score&min_score=70&max_score=100
```

## 🎨 Frontend URLs

### Comparación
```
/applications/{id}/compare
```

### Ranking
```
/roles/{id}/ranking
```

## 🧪 Pruebas Sugeridas

1. Crear una aplicación nueva y verificar scoring automático
2. Probar el endpoint de scoring manual
3. Verificar ordenamiento por score
4. Probar filtros por rangos de score
5. Exportar ranking a CSV
6. Verificar vista de comparación lado a lado

## 📦 Dependencias

### Backend
- `openai` - Cliente de OpenAI

### Frontend
- Componentes UI existentes (@/components/ui/*)
- TanStack Query para estado y caching
- Lucide React para iconos

## 🔒 Seguridad

- Todos los endpoints requieren autenticación
- Scoring automático ejecutado como "system_auto_scoring"
- Registro de auditoría de todos los scores calculados
- Validación de rangos de score (0-100)

## 🚀 Próximos Pasos Sugeridos

1. Agregar caché de resultados de OpenAI para reducir costos
2. Implementar batch scoring para múltiples aplicaciones
3. Agregar métricas de uso del scoring
4. Integrar con sistema de notificaciones cuando el score esté listo
5. Agregar comparación de múltiples candidatos (terna mejorada)
