# Esquema de Extracción de CVs por IA

Documentación técnica del modelo de datos para almacenar extracciones de CVs procesados por inteligencia artificial.

## Tabla Principal: `hh_cv_extractions`

Esta tabla almacena los resultados de la extracción de información de CVs utilizando diferentes métodos (PDF text, OCR, IA).

### Estructura de la Tabla

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| `extraction_id` | UUID | NO | Clave primaria única de la extracción |
| `candidate_id` | UUID | NO | FK a `hh_candidates.candidate_id` - Candidato asociado |
| `raw_text` | TEXT | SÍ | Texto completo extraído del CV (sin estructurar) |
| `extracted_json` | JSONB | SÍ | Datos estructurados extraídos por la IA |
| `extraction_method` | ENUM | SÍ | Método usado: `pdf_text`, `ocr`, `ai_extraction`, `hybrid`, `manual` |
| `confidence_score` | NUMERIC(5,2) | SÍ | Score de confianza 0-100 del proceso de extracción |
| `filename` | TEXT | NO | Nombre original del archivo procesado |
| `file_hash` | TEXT | NO | Hash SHA256 del archivo (para detección de duplicados) |
| `document_id` | UUID | SÍ | FK opcional a `hh_documents.document_id` |
| `created_at` | TIMESTAMP | NO | Fecha de creación del registro |
| `updated_at` | TIMESTAMP | NO | Fecha de última actualización |

### Constraints

- **Primary Key**: `extraction_id`
- **Foreign Keys**:
  - `candidate_id` → `hh_candidates.candidate_id` (ON DELETE CASCADE)
  - `document_id` → `hh_documents.document_id` (ON DELETE SET NULL)
- **Check**: `confidence_score >= 0 AND confidence_score <= 100`
- **Unique**: `file_hash` (para evitar procesar el mismo archivo múltiples veces)

### Índices

| Índice | Columnas | Tipo | Propósito |
|--------|----------|------|-----------|
| `idx_hh_cv_extractions_candidate` | `candidate_id` | B-tree | Búsquedas por candidato |
| `idx_hh_cv_extractions_method` | `extraction_method` | B-tree | Filtrar por método de extracción |
| `idx_hh_cv_extractions_score` | `confidence_score` | B-tree | Filtrar por nivel de confianza |
| `idx_hh_cv_extractions_file_hash` | `file_hash` | B-tree | Buscar por hash de archivo |
| `idx_hh_cv_extractions_created` | `created_at` | B-tree | Ordenar por fecha |
| `idx_hh_cv_extractions_filename` | `filename` | B-tree | Buscar por nombre de archivo |
| `idx_hh_cv_extractions_json_gin` | `extracted_json` | GIN | Búsquedas dentro del JSON |
| `idx_hh_cv_extractions_candidate_method` | `candidate_id`, `extraction_method` | B-tree | Búsquedas compuestas frecuentes |

### ENUMs Utilizados

#### `extractionmethod`
- `pdf_text`: Extracción directa de texto PDF
- `ocr`: Reconocimiento óptico de caracteres
- `ai_extraction`: Extracción usando modelos de IA/LLM
- `hybrid`: Combinación de múltiples métodos
- `manual`: Ingreso manual de datos

## Modelo SQLAlchemy

```python
class HHCVExtraction(Base):
    """Extracción de datos de CV procesados por IA."""
    __tablename__ = "hh_cv_extractions"

    extraction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("hh_candidates.candidate_id"), nullable=False)
    
    raw_text = Column(Text, nullable=True)
    extracted_json = Column(JSONB, nullable=True)
    
    extraction_method = Column(SQLEnum(ExtractionMethod), nullable=True)
    confidence_score = Column(Numeric(5, 2), nullable=True)
    
    filename = Column(Text, nullable=False)
    file_hash = Column(Text, nullable=False)
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("hh_documents.document_id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    candidate = relationship("HHCandidate", back_populates="cv_extractions")
    document = relationship("HHDocument", back_populates="cv_extraction", uselist=False)
```

## Vistas Disponibles

### `v_candidate_cv_extractions`
Muestra todas las extracciones por candidato incluyendo el nivel de confianza calculado.

**Columnas**:
- `candidate_id`, `candidate_name`, `candidate_email`
- `extraction_id`, `filename`, `file_hash`
- `extraction_method`, `confidence_score`
- `extraction_date`, `extracted_json`
- `confidence_level` (high/medium/low calculado)

### `v_cv_extraction_stats_simple`
Estadísticas agregadas de extracciones por método.

**Columnas**:
- `extraction_method`
- `total_extractions`
- `avg_confidence`, `min_confidence`, `max_confidence`
- `high_confidence_count`, `low_confidence_count`
- `first_extraction`, `last_extraction`

### `v_candidates_with_cv_extraction`
Candidatos que tienen CVs extraídos con campos específicos del JSON.

**Columnas**:
- Datos del candidato (`candidate_id`, `full_name`, `email`, `phone`)
- Datos de extracción (`extraction_id`, `confidence_score`, `extraction_method`, `filename`, `extracted_at`)
- Campos extraídos del JSON (`extracted_name`, `extracted_email`, `extracted_phone`, `extracted_title`, `extracted_location`)

## Ejemplos de Uso

### Insertar una nueva extracción

```python
from app.models.core_ats import HHCVExtraction, ExtractionMethod

extraction = HHCVExtraction(
    candidate_id=candidate_uuid,
    raw_text="Texto completo del CV...",
    extracted_json={
        "nombre": "Juan Pérez",
        "email": "juan@ejemplo.com",
        "telefono": "+56912345678",
        "experiencia": [...],
        "educacion": [...]
    },
    extraction_method=ExtractionMethod.AI_EXTRACTION,
    confidence_score=85.50,
    filename="cv_juan_perez.pdf",
    file_hash="sha256_hash_del_archivo"
)
```

### Buscar extracciones por candidato

```sql
SELECT * FROM hh_cv_extractions
WHERE candidate_id = 'uuid-del-candidato'
ORDER BY created_at DESC;
```

### Buscar en el JSON extraído

```sql
-- Buscar candidatos con experiencia en Python
SELECT * FROM hh_cv_extractions
WHERE extracted_json @> '{"habilidades": ["Python"]}';

-- Buscar por email extraído
SELECT * FROM hh_cv_extractions
WHERE extracted_json->>'email' = 'juan@ejemplo.com';
```

### Filtrar por score de confianza

```sql
-- Solo extracciones de alta confianza
SELECT * FROM hh_cv_extractions
WHERE confidence_score >= 80;

-- Extracciones que necesitan revisión
SELECT * FROM hh_cv_extractions
WHERE confidence_score < 50;
```

## Relaciones con Otras Tablas

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  hh_candidates  │◄────┤  hh_cv_extractions   ├────►│  hh_documents   │
│   (1)           │     │       (N)            │     │    (0..1)       │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
        │
        │
        ▼
┌─────────────────┐
│  cv_extractions │
│  (relationship) │
└─────────────────┘
```

- **Un candidato puede tener múltiples extracciones** (histórico de CVs)
- **Cada extracción pertenece a un solo candidato**
- **Una extracción puede estar asociada a un documento** (opcional)

## Migración

**Archivo**: `backend/migrations/versions/20260217_1520_cv_extractions_table.py`

**Revisión anterior**: `20260217_1511_cv_processing_tables`

**Comandos**:
```bash
# Aplicar migración
alembic upgrade 20260217_1520_cv_extractions_table

# Revertir migración
alembic downgrade 20260217_1511_cv_processing_tables
```

## Buenas Prácticas

1. **Siempre verificar `file_hash`** antes de procesar un CV para evitar duplicados
2. **Usar índice GIN** para búsquedas eficientes en `extracted_json`
3. **Almacenar el `raw_text`** como respaldo en caso de necesitar re-procesar
4. **Mantener el `confidence_score`** para identificar extracciones que necesitan revisión manual
5. **Versionar extracciones** usando el campo `created_at` y relaciones con el candidato

## Comparación con hh_cv_processing

Esta tabla (`hh_cv_extractions`) es una versión simplificada de `hh_cv_processing`:

| Característica | hh_cv_extractions | hh_cv_processing |
|----------------|-------------------|------------------|
| Propósito | Almacenar resultado final de extracción | Pipeline completo de procesamiento |
| Complejidad | Simple, enfocada en datos | Compleja, incluye logs y versiones |
| Estados | No tiene estados explícitos | Estados: pending, processing, completed, failed |
| Logs | No incluye | Incluye logs detallados |
| Versiones | Implícita (múltiples filas) | Tabla separada hh_cv_versions |

Usar `hh_cv_extractions` cuando solo se necesite el resultado final.
Usar `hh_cv_processing` cuando se necesite trazabilidad completa del proceso.
