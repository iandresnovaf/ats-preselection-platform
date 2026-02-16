# Pipeline de Procesamiento de Documentos

## Visión General

El sistema implementa un pipeline completo de procesamiento de documentos con estados, diseñado para extraer datos estructurados de CVs, pruebas psicométricas y notas de entrevistas.

## Arquitectura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   UPLOADED  │────▶│   PARSING   │────▶│ EXTRACTING  │────▶│ VALIDATING  │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                     │
                               ┌────────────────────────────────────┘
                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  CONFIRMED  │◀────│MANUAL_REVIEW│◀────│  COMPLETED  │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                       │    ERROR    │
                                        └─────────────┘
```

## Estados del Pipeline

| Estado | Descripción |
|--------|-------------|
| `uploaded` | Documento subido, pendiente de procesar |
| `parsing` | Extrayendo texto del documento (PDF/DOCX/TXT) |
| `extracting` | Extrayendo datos estructurados según tipo |
| `validating` | Validando datos extraídos (rangos, formatos) |
| `completed` | Procesamiento exitoso |
| `manual_review` | Esperando revisión/confirmación manual |
| `confirmed` | Datos confirmados manualmente |
| `error` | Error en el procesamiento |

## Flujo de Datos

### 1. Ingesta
```python
POST /api/v1/documents/{id}/process
```
Inicia el pipeline de procesamiento para un documento.

### 2. Parsing
El `DocumentParser` extrae texto puro del archivo:
- **PDF**: Usa `pdfplumber` para extracción de texto
- **DOCX**: Usa `python-docx` para párrafos y tablas
- **TXT**: Lectura directa con detección de encoding

### 3. Detección de Tipo
Basado en patrones de texto, detecta automáticamente:
- **CV/Resume**: Palabras clave como "experiencia laboral", "educación", "skills"
- **Assessment**: Palabras como "factor oscuro", "dimensión", "score", "percentil"
- **Interview**: Palabras como "entrevista", "pregunta", "respuesta", "recomendación"

### 4. Extracción Específica

#### AssessmentExtractor
Extrae de pruebas psicométricas:
```python
{
    "test_name": "Dark Factor Inventory",
    "test_type": "personality_dark",
    "candidate_name": "Juan Pérez",
    "test_date": "2024-01-15",
    "scores": [
        {"name": "Egocentrism", "value": 72.5, "category": "dark_factor"},
        {"name": "Psychopathy", "value": 45.0, "category": "dark_factor"},
        # ... más dimensiones
    ],
    "sincerity_score": 88.0,
    "interpretation": "Perfil dentro de rangos normales"
}
```

**IMPORTANTE**: Los scores se almacenan como **FILAS** en `assessment_scores`, no como columnas:
```sql
-- Correcto (filas)
INSERT INTO assessment_scores (document_id, test_name, dimension_name, score_value)
VALUES ('doc-123', 'Dark Factor', 'Egocentrism', 72.5);

-- Incorrecto (columnas)
-- No hacer: CREATE TABLE scores (egocentrism FLOAT, psychopathy FLOAT, ...)
```

#### CVExtractor
Extrae de CVs:
- Datos personales (nombre, email, teléfono)
- Experiencia laboral (empresa, título, fechas)
- Educación (institución, grado, campo de estudio)
- Skills (lista de tecnologías y habilidades)
- Idiomas y certificaciones

#### InterviewExtractor
Extrae de notas de entrevistas:
- Tipo de entrevista (técnica, conductual, etc.)
- Citas clave del candidato
- Flags de riesgo detectados
- Fortalezas y preocupaciones
- Sentimiento general
- Recomendación final

### 5. Validación
El `DataValidator` verifica:
- Scores en rango 0-100
- Emails con formato válido
- Teléfonos en formato E.164
- Fechas parseables
- Campos requeridos presentes

### 6. Limpieza
El `DataCleaner` normaliza:
- Nombres: Title Case inteligente ("de la Cruz")
- Empresas: Remover sufijos legales (S.A., Ltd., etc.)
- Skills: Normalización de tecnologías ("js" → "JavaScript")
- Teléfonos: Solo dígitos y +
- Texto: Unicode normalizado, espacios extra removidos

### 7. Almacenamiento
Los datos se guardan en:
- `document_text_extractions`: Texto extraído y datos parseados
- `assessment_scores`: Scores como filas (una por dimensión)
- Tablas específicas según el tipo

## Endpoints API

### Procesar Documento
```http
POST /api/v1/documents/{id}/process
```
Inicia el pipeline completo.

**Respuesta:**
```json
{
  "job_id": "job-abc-123",
  "document_id": "doc-xyz-456",
  "status": "parsing",
  "message": "Procesamiento iniciado. Estado actual: parsing",
  "started_at": "2024-01-15T10:30:00Z"
}
```

### Consultar Estado
```http
GET /api/v1/documents/{id}/status
```

**Respuesta:**
```json
{
  "document_id": "doc-xyz-456",
  "status": "completed",
  "document_type": "cv",
  "extraction": {
    "status": "completed",
    "text_length": 2500,
    "parsed_data": {
      "document_type": "cv",
      "confidence": 0.85,
      "validation_valid": true
    }
  }
}
```

### Vista Previa (Dry-Run)
```http
GET /api/v1/documents/{id}/extract/preview
```
Genera una vista previa sin guardar cambios.

### Obtener Datos Extraídos
```http
GET /api/v1/documents/{id}/extract
```
Retorna los datos extraídos para revisión.

### Confirmar Extracción Manual
```http
POST /api/v1/documents/{id}/extract/confirm
Content-Type: application/json

{
  "document_type": "cv",
  "full_name": "Juan Pérez (corregido)",
  "email": "juan.correcto@email.com",
  ...
}
```
Guarda datos confirmados manualmente (modo asistido).

## Modo Asistido (Manual Review)

El sistema soporta un flujo de trabajo híbrido:

1. **Extracción automática**: El sistema extrae datos automáticamente
2. **Revisión humana**: Usuario revisa y corrige los datos
3. **Confirmación**: Usuario confirma los datos
4. **Almacenamiento**: Solo se guardan los datos confirmados

```python
# Flujo típico
POST /api/v1/documents/{id}/process           # Extraer automáticamente
GET /api/v1/documents/{id}/extract            # Ver datos para revisar
POST /api/v1/documents/{id}/extract/confirm   # Confirmar/Corregir
```

## Deduplicación

El sistema detecta duplicados por hash SHA-256 del contenido:

```python
# Antes de procesar
existing_id = await parser.dedupe_by_hash(sha256_hash, db_session)
if existing_id:
    # Documento ya existe, podemos copiar datos o retornar referencia
    return existing_id
```

## Testing

Ejecutar tests:
```bash
cd ats-platform/backend
pytest tests/services/test_document_parser.py -v
pytest tests/services/test_assessment_extractor.py -v
pytest tests/services/test_cv_extractor.py -v
pytest tests/services/test_data_validator.py -v
```

## Dependencias

```
pdfplumber>=0.10.0      # Extracción de PDFs
python-docx>=1.1.0      # Extracción de DOCX
pytesseract>=0.3.10     # OCR (opcional)
textblob>=0.17.1        # Análisis de sentimiento
```

## Configuración

Variables de entorno relevantes:
```bash
UPLOAD_DIR=./uploads          # Directorio de uploads
MAX_FILE_SIZE=10485760        # 10MB máximo
```

## Extensiones Futuras

- Soporte para OCR en PDFs escaneados
- Extracción de imágenes incrustadas
- Más tipos de assessments (DISC, 16PF, etc.)
- Integración con APIs de parsing de CVs (como Affinda)
- Extracción de tablas complejas con ML
