-- Script SQL para crear tablas de procesamiento de CVs
-- Ejecutar manualmente si las migraciones de Alembic fallan

-- Verificar y crear tabla hh_cv_extractions
CREATE TABLE IF NOT EXISTS hh_cv_extractions (
    extraction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES hh_candidates(candidate_id) ON DELETE CASCADE,
    raw_text TEXT,
    extracted_json JSONB,
    extraction_method VARCHAR(50) CHECK (extraction_method IN ('pdf_text', 'ocr', 'ai_extraction', 'hybrid', 'manual')),
    confidence_score NUMERIC(5,2),
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    file_size_bytes INTEGER,
    mime_type VARCHAR(100),
    processing_status VARCHAR(50) DEFAULT 'completed' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para hh_cv_extractions
CREATE INDEX IF NOT EXISTS idx_cv_extractions_candidate_id ON hh_cv_extractions(candidate_id);
CREATE INDEX IF NOT EXISTS idx_cv_extractions_processing_status ON hh_cv_extractions(processing_status);
CREATE INDEX IF NOT EXISTS idx_cv_extractions_created_at ON hh_cv_extractions(created_at DESC);

-- Comentarios
COMMENT ON TABLE hh_cv_extractions IS 'Almacena datos extraídos de CVs procesados por IA/OCR';
COMMENT ON COLUMN hh_cv_extractions.extracted_json IS 'JSON estructurado con todos los datos extraídos del CV';
COMMENT ON COLUMN hh_cv_extractions.confidence_score IS 'Score 0-100 de confianza en la extracción';
COMMENT ON COLUMN hh_cv_extractions.extraction_method IS 'Método usado: pdf_text, ocr, ai_extraction, hybrid, manual';

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_cv_extractions_updated_at ON hh_cv_extractions;
CREATE TRIGGER update_cv_extractions_updated_at
    BEFORE UPDATE ON hh_cv_extractions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Verificar creación
SELECT 'Tabla hh_cv_extractions creada exitosamente' as status;
