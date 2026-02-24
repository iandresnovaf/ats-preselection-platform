# Recomendaciones de Optimización - Base de Datos ATS

## Resumen

Este documento contiene recomendaciones adicionales para optimizar el rendimiento de la base de datos del sistema ATS, específicamente para las nuevas tablas de procesamiento de CVs.

---

## 1. Configuración de PostgreSQL

### Parámetros recomendados en `postgresql.conf`:

```ini
# Memoria compartida (ajustar según RAM disponible)
shared_buffers = 4GB                    # 25% de la RAM total
effective_cache_size = 12GB             # 75% de la RAM total
work_mem = 256MB                        # Para operaciones de ordenamiento
maintenance_work_mem = 1GB              # Para VACUUM, CREATE INDEX

# WAL y checkpointing
wal_buffers = 16MB
max_wal_size = 4GB
min_wal_size = 1GB
checkpoint_completion_target = 0.9

# Concurrencia
max_connections = 200
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
max_worker_processes = 8

# Query planning
effective_io_concurrency = 200
random_page_cost = 1.1                  # Para SSD
```

---

## 2. Mantenimiento Automatizado

### Script de mantenimiento diario:

```sql
-- Archivo: maintenance/daily_maintenance.sql

-- 1. Actualizar estadísticas
ANALYZE hh_cv_processing;
ANALYZE hh_cv_versions;
ANALYZE hh_cv_processing_logs;

-- 2. VACUUM para recuperar espacio
VACUUM ANALYZE hh_cv_processing_logs;

-- 3. Reindexar si es necesario (verificar fragmentación)
REINDEX INDEX CONCURRENTLY idx_hh_cv_processing_extracted_json_gin;
```

### Configuración de autovacuum específica:

```sql
-- Para tablas con alta rotación de datos
ALTER TABLE hh_cv_processing_logs 
SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05,
    autovacuum_vacuum_cost_limit = 1000
);
```

---

## 3. Particionamiento de Tablas Grandes

### Particionamiento de hh_cv_processing_logs por rango de fechas:

```sql
-- Crear tabla particionada
CREATE TABLE hh_cv_processing_logs_partitioned (
    LIKE hh_cv_processing_logs INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Crear particiones iniciales
CREATE TABLE hh_cv_processing_logs_y2026m02 
    PARTITION OF hh_cv_processing_logs_partitioned
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE hh_cv_processing_logs_y2026m03 
    PARTITION OF hh_cv_processing_logs_partitioned
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Función para crear particiones automáticamente
CREATE OR REPLACE FUNCTION create_monthly_partition()
RETURNS void AS $$
DECLARE
    next_month DATE := DATE_TRUNC('month', NOW() + INTERVAL '1 month');
    partition_name TEXT := 'hh_cv_processing_logs_y' || 
                           TO_CHAR(next_month, 'YYYY') || 'm' || 
                           TO_CHAR(next_month, 'MM');
    start_date DATE := next_month;
    end_date DATE := next_month + INTERVAL '1 month';
BEGIN
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF hh_cv_processing_logs_partitioned
         FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
END;
$$ LANGUAGE plpgsql;
```

---

## 4. Búsqueda de Texto Completo (Full-Text Search)

### Implementación de búsqueda en CVs:

```sql
-- 1. Agregar columna de búsqueda
ALTER TABLE hh_cv_processing 
ADD COLUMN IF NOT EXISTS search_vector tsvector 
GENERATED ALWAYS AS (
    setweight(to_tsvector('spanish', COALESCE(raw_text, '')), 'A') ||
    setweight(to_tsvector('spanish', COALESCE(extracted_name, '')), 'B') ||
    setweight(to_tsvector('spanish', COALESCE(extracted_title, '')), 'B')
) STORED;

-- 2. Crear índice GIN
CREATE INDEX idx_hh_cv_processing_fts 
ON hh_cv_processing USING GIN (search_vector);

-- 3. Función de búsqueda conveniente
CREATE OR REPLACE FUNCTION search_cvs(query TEXT)
RETURNS TABLE (
    processing_id UUID,
    candidate_id UUID,
    extracted_name TEXT,
    extracted_title TEXT,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cvp.processing_id,
        cvp.candidate_id,
        cvp.extracted_name,
        cvp.extracted_title,
        ts_rank(cvp.search_vector, plainto_tsquery('spanish', query)) as rank
    FROM hh_cv_processing cvp
    WHERE cvp.search_vector @@ plainto_tsquery('spanish', query)
    AND cvp.processing_status = 'completed'
    ORDER BY rank DESC
    LIMIT 50;
END;
$$ LANGUAGE plpgsql;

-- Uso: SELECT * FROM search_cvs('ingeniero python');
```

---

## 5. Caché y Materialización

### Vista materializada para dashboards:

```sql
-- Vista materializada de métricas diarias
CREATE MATERIALIZED VIEW mv_daily_cv_metrics AS
SELECT 
    DATE(created_at) as date,
    extraction_method,
    processing_status,
    COUNT(*) as total,
    AVG(confidence_score) as avg_confidence,
    AVG(extraction_duration_ms) as avg_duration_ms,
    SUM(file_size_bytes) / 1024.0 / 1024.0 as total_size_mb
FROM hh_cv_processing
GROUP BY DATE(created_at), extraction_method, processing_status
WITH DATA;

-- Índice en la vista materializada
CREATE UNIQUE INDEX idx_mv_daily_cv_metrics 
ON mv_daily_cv_metrics(date, extraction_method, processing_status);

-- Función para refrescar concurrentemente
CREATE OR REPLACE FUNCTION refresh_cv_metrics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_cv_metrics;
END;
$$ LANGUAGE plpgsql;
```

---

## 6. Optimización de Consultas Comunes

### Consulta optimizada para obtener último CV de candidatos:

```sql
-- En lugar de subconsulta correlacionada, usar DISTINCT ON
SELECT DISTINCT ON (c.candidate_id)
    c.candidate_id,
    c.full_name,
    cvp.processing_id,
    cvp.processed_at,
    cvp.confidence_score
FROM hh_candidates c
LEFT JOIN hh_cv_processing cvp ON c.candidate_id = cvp.candidate_id
    AND cvp.processing_status = 'completed'
ORDER BY c.candidate_id, cvp.processed_at DESC;

-- Índice necesario:
CREATE INDEX idx_hh_cv_processing_candidate_processed 
ON hh_cv_processing(candidate_id, processed_at DESC) 
WHERE processing_status = 'completed';
```

### Consulta para candidatos sin CV procesado:

```sql
-- Usar NOT EXISTS en lugar de LEFT JOIN + IS NULL
SELECT c.candidate_id, c.full_name, c.email
FROM hh_candidates c
WHERE NOT EXISTS (
    SELECT 1 FROM hh_cv_processing cvp 
    WHERE cvp.candidate_id = c.candidate_id
    AND cvp.processing_status = 'completed'
);
```

---

## 7. Monitoreo de Performance

### Vistas para monitoreo:

```sql
-- Tamaño de tablas
CREATE OR REPLACE VIEW v_table_sizes AS
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = schemaname AND table_name = tablename) as column_count
FROM pg_tables
WHERE schemaname = 'public'
AND tablename LIKE 'hh_%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Uso de índices
CREATE OR REPLACE VIEW v_index_usage AS
SELECT 
    schemaname,
    tablename,
    indexrelname as index_name,
    idx_scan as times_used,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
AND tablename LIKE 'hh_%'
ORDER BY idx_scan DESC;
```

---

## 8. Estrategia de Backup

### Backup selectivo para tablas grandes:

```bash
#!/bin/bash
# backup_script.sh

# Backup completo semanal
pg_dump -Fc -Z9 ats_db > backup/full_$(date +%Y%m%d).dump

# Backup diario solo de datos críticos (excluir logs antiguos)
pg_dump -Fc --exclude-table='hh_cv_processing_logs' \
    --exclude-table='hh_audit_log' ats_db > backup/critical_$(date +%Y%m%d).dump

# Backup de logs recientes (últimos 7 días)
pg_dump -Fc --table='hh_cv_processing_logs' \
    --where="created_at > NOW() - INTERVAL '7 days'" \
    ats_db > backup/logs_recent_$(date +%Y%m%d).dump
```

---

## 9. Seguridad Adicional

### Encriptación de datos sensibles:

```sql
-- Extensión pgcrypto para encriptación
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Función para almacenar datos encriptados
CREATE OR REPLACE FUNCTION encrypt_sensitive_data(data TEXT, key TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN pgp_sym_encrypt(data, key);
END;
$$ LANGUAGE plpgsql;

-- Ejemplo de uso en aplicación (no recomendado hacerlo en BD)
-- Los datos sensibles deben encriptarse en la aplicación antes de insertar
```

### Row Level Security (RLS) avanzado:

```sql
-- Política para consultores
CREATE POLICY cv_processing_consultant_isolation ON hh_cv_processing
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM hh_applications a
        WHERE a.candidate_id = hh_cv_processing.candidate_id
        AND a.assigned_consultant_id = current_setting('app.current_user_id')::UUID
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM hh_applications a
        WHERE a.candidate_id = hh_cv_processing.candidate_id
        AND a.assigned_consultant_id = current_setting('app.current_user_id')::UUID
    )
);

-- Habilitar RLS
ALTER TABLE hh_cv_processing ENABLE ROW LEVEL SECURITY;
ALTER TABLE hh_cv_processing FORCE ROW LEVEL SECURITY;
```

---

## 10. Métricas y Alertas

### Función para monitoreo de salud:

```sql
CREATE OR REPLACE FUNCTION check_db_health()
RETURNS TABLE (
    check_name TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    -- Verificar conexiones activas
    RETURN QUERY
    SELECT 
        'active_connections'::TEXT,
        CASE WHEN count > 150 THEN 'WARNING' ELSE 'OK' END,
        count::TEXT || ' connections'
    FROM pg_stat_activity
    WHERE datname = current_database();
    
    -- Verificar tablas sin vacuum reciente
    RETURN QUERY
    SELECT 
        'stale_tables'::TEXT,
        'WARNING',
        relname || ' last vacuum: ' || COALESCE(last_vacuum::TEXT, 'never')
    FROM pg_stat_user_tables
    WHERE last_vacuum < NOW() - INTERVAL '7 days'
    OR last_vacuum IS NULL;
    
    -- Verificar índices sin uso
    RETURN QUERY
    SELECT 
        'unused_indexes'::TEXT,
        'INFO',
        indexrelname || ' on ' || relname || ' (0 scans)'
    FROM pg_stat_user_indexes
    WHERE idx_scan = 0
    AND indexrelname NOT LIKE '%_pkey'
    AND indexrelname NOT LIKE '%_unique%';
END;
$$ LANGUAGE plpgsql;

-- Uso: SELECT * FROM check_db_health();
```

---

## Checklist de Implementación

- [ ] Aplicar configuración de PostgreSQL
- [ ] Crear índices adicionales según patrones de uso
- [ ] Configurar autovacuum específico para tablas grandes
- [ ] Implementar particionamiento si se esperan >10M registros/año
- [ ] Configurar backups automatizados
- [ ] Crear vistas materializadas para dashboards
- [ ] Implementar monitoreo con métricas clave
- [ ] Configurar alertas para conexiones y espacio en disco
- [ ] Documentar procedimientos de recuperación
- [ ] Probar plan de disaster recovery

---

## Referencias

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PGTune](https://pgtune.leopard.in.ua/) - Configuración automática
- [PostgreSQL Wiki - Performance Optimization](https://wiki.postgresql.org/wiki/Performance_Optimization)
