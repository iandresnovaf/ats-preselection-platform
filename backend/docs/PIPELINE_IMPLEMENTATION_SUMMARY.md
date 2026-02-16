# Pipeline de Procesamiento de Documentos - Data Engineer

## Resumen de Implementación

Se ha implementado un pipeline completo de procesamiento de documentos para la plataforma ATS con las siguientes características:

### Servicios Implementados

1. **DocumentParser** (`app/services/extraction/document_parser.py`)
   - Extrae texto de PDFs (pdfplumber), DOCX (python-docx) y TXT
   - Detecta automáticamente el tipo de documento (CV, Assessment, Interview)
   - Soporta deduplicación por hash SHA-256
   - Extrae metadatos del documento

2. **AssessmentExtractor** (`app/services/extraction/assessment_extractor.py`)
   - Extrae datos de pruebas psicométricas (Dark Factor, DISC, Big Five, etc.)
   - Detecta dimensiones y scores (0-100)
   - Extrae sincerity_score
   - Normaliza nombres de dimensiones conocidas
   - **IMPORTANTE**: Los scores van como FILAS, nunca como columnas

3. **CVExtractor** (`app/services/extraction/cv_extractor.py`)
   - Extrae datos personales (nombre, email, teléfono)
   - Experiencia laboral con fechas
   - Educación
   - Skills (con normalización de tecnologías)
   - Idiomas y certificaciones

4. **InterviewExtractor** (`app/services/extraction/interview_extractor.py`)
   - Extrae citas clave
   - Detecta flags de riesgo
   - Analiza sentimiento (positive/negative/neutral/mixed)
   - Genera recomendación (PROCEED/REVIEW/REJECT)

### Pipeline con Estados

**DocumentPipeline** (`app/pipeline/document_pipeline.py`)

Estados del documento:
```
uploaded → parsing → extracting → validating → completed/error
                    ↓
              manual_review → confirmed
```

### Validación y Limpieza

1. **DataValidator** (`app/validators/data_validator.py`)
   - Valida scores en rango 0-100
   - Valida emails (formato correcto)
   - Valida teléfonos (formato E.164)
   - Valida fechas (múltiples formatos)
   - Validación específica por tipo de documento

2. **DataCleaner** (`app/validators/data_cleaner.py`)
   - Limpia y normaliza nombres (Title Case inteligente)
   - Limpia nombres de empresas (remueve sufijos legales)
   - Normaliza skills ("js" → "JavaScript")
   - Limpia teléfonos (solo dígitos y +)
   - Remueve HTML y espacios extras

### Endpoints API

**document_pipeline.py** (`app/api/document_pipeline.py`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/documents/{id}/process` | POST | Inicia pipeline de procesamiento |
| `/api/v1/documents/{id}/status` | GET | Consulta estado actual |
| `/api/v1/documents/{id}/extract` | GET | Obtiene datos extraídos |
| `/api/v1/documents/{id}/extract/preview` | GET | Vista previa (dry-run) |
| `/api/v1/documents/{id}/extract/confirm` | POST | Confirma datos manualmente |

### Modelos de Datos

**DocumentType** - Tipos soportados:
- `cv` - Curriculum Vitae
- `assessment` - Pruebas psicométricas
- `interview` - Notas de entrevistas
- `other` - Otros documentos

**ProcessingStatus** - Estados del pipeline:
- `uploaded`, `parsing`, `extracting`, `validating`
- `completed`, `error`, `manual_review`, `confirmed`

### Tests Unitarios

Ubicados en `tests/services/`:
- `test_document_parser.py` - Tests del parser
- `test_assessment_extractor.py` - Tests de extracción de assessments
- `test_cv_extractor.py` - Tests de extracción de CVs
- `test_data_validator.py` - Tests de validación

### Modo Asistido (Manual Review)

El sistema permite:
1. Extraer datos automáticamente
2. Mostrar al usuario para revisión
3. Usuario confirma/edita datos
4. Guarda solo después de confirmación

### Integración con Core ATS

El pipeline está diseñado para trabajar con el sistema existente:
- Usa los modelos de RHTools (`Document`, `DocumentTextExtraction`)
- Compatible con el modelo core_ats (`AssessmentScore` como filas)
- Se integra con el router existente en FastAPI

### Dependencias Agregadas

```
pdfplumber==0.10.4      # Extracción de PDFs
python-docx==1.1.0      # Extracción de DOCX
textblob==0.17.1        # Análisis de sentimiento
chardet==5.2.0          # Detección de encoding
```

### Documentación

- `docs/DOCUMENT_PIPELINE.md` - Documentación completa del flujo

### Uso Básico

```python
# Iniciar pipeline
pipeline = DocumentPipeline(db_session=db)
job = await pipeline.process(document_id)

# Procesamiento manual
job = await pipeline.process_manual_review(document_id, confirmed_data)

# Consultar estado
status = await pipeline.get_status(document_id)
```

### Notas Importantes

1. **Scores como FILAS**: Los scores de assessment siempre se almacenan como filas en `assessment_scores`, nunca como columnas. Esto permite agregar nuevas dimensiones sin modificar el schema.

2. **Deduplicación**: El sistema detecta documentos duplicados por hash SHA-256 del contenido.

3. **Modo Asistido**: El sistema permite revisión manual antes de confirmar los datos extraídos.

4. **Validación**: Todos los datos pasan por validación antes de ser guardados.

5. **Limpieza**: Los datos se normalizan automáticamente (nombres, teléfonos, emails, etc.).
