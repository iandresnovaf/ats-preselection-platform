#!/bin/bash
# ============================================================
# SCRIPT: Backup Automático de Base de Datos PostgreSQL
# ATS Platform
# ============================================================

set -euo pipefail

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Valores por defecto (sobrescribir con variables de entorno)
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ats_platform}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.sql"

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

# ============================================================
# FUNCIONES
# ============================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error_exit() {
    log "ERROR: $*"
    exit 1
}

# ============================================================
# VALIDACIONES
# ============================================================

# Verificar que pg_dump esté disponible
if ! command -v pg_dump &> /dev/null; then
    error_exit "pg_dump no está instalado. Instalar postgresql-client."
fi

# Verificar conexión a la base de datos
export PGPASSWORD="$DB_PASSWORD"
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
    error_exit "No se puede conectar a PostgreSQL en $DB_HOST:$DB_PORT"
fi

log "Conexión a PostgreSQL verificada"

# ============================================================
# EJECUTAR BACKUP
# ============================================================

log "Iniciando backup de $DB_NAME..."

# Backup con formato custom (comprimido y permitiendo restore selectivo)
# -Fc: Formato custom
# -Z9: Máxima compresión
# --verbose: Información detallada
# --lock-wait-timeout: No bloquear indefinidamente
# --no-password: Usar PGPASSWORD del environment

pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -Fc \
    -Z9 \
    --verbose \
    --lock-wait-timeout=5000 \
    --file="${BACKUP_FILE}.dump" \
    2>&1 || error_exit "Falló el backup"

# También crear backup en formato SQL plano (más legible)
pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --verbose \
    --lock-wait-timeout=5000 \
    --file="${BACKUP_FILE}" \
    2>&1 || log "Advertencia: Backup SQL plano falló (el dump comprimido se creó correctamente)"

# Calcular tamaño del backup
BACKUP_SIZE=$(du -h "${BACKUP_FILE}.dump" | cut -f1)
log "Backup completado: ${BACKUP_FILE}.dump (Tamaño: $BACKUP_SIZE)"

# ============================================================
# CREAR METADATA DEL BACKUP
# ============================================================

cat > "${BACKUP_FILE}.meta" <<EOF
{
    "database": "$DB_NAME",
    "timestamp": "$TIMESTAMP",
    "host": "$DB_HOST",
    "port": "$DB_PORT",
    "user": "$DB_USER",
    "backup_file": "${BACKUP_FILE}.dump",
    "sql_file": "${BACKUP_FILE}",
    "size": "$BACKUP_SIZE",
    "retention_days": $RETENTION_DAYS
}
EOF

log "Metadata guardada: ${BACKUP_FILE}.meta"

# ============================================================
# LIMPIEZA DE BACKUPS ANTIGUOS
# ============================================================

log "Limpiando backups antiguos (más de $RETENTION_DAYS días)..."

# Contar backups eliminados
DELETED_COUNT=$(find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.dump" -type f -mtime +$RETENTION_DAYS | wc -l)

# Eliminar backups antiguos
find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.dump" -type f -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.sql" -type f -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.meta" -type f -mtime +$RETENTION_DAYS -delete

log "Backups eliminados: $DELETED_COUNT"

# ============================================================
# VERIFICACIÓN DEL BACKUP
# ============================================================

log "Verificando integridad del backup..."

# Verificar que el archivo existe y no está vacío
if [ ! -s "${BACKUP_FILE}.dump" ]; then
    error_exit "El archivo de backup está vacío o no existe"
fi

# Listar contenido del backup (sin extraer)
pg_restore -l "${BACKUP_FILE}.dump" > "${BACKUP_FILE}.toc" 2>&1 || log "Advertencia: No se pudo generar TOC"

log "Backup verificado exitosamente"

# ============================================================
# RESUMEN
# ============================================================

REMAINING_BACKUPS=$(find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.dump" -type f | wc -l)

cat <<EOF

============================================================
BACKUP COMPLETADO EXITOSAMENTE
============================================================
Database:        $DB_NAME
Timestamp:       $TIMESTAMP
Archivo:         ${BACKUP_FILE}.dump
Tamaño:          $BACKUP_SIZE
Retención:       $RETENTION_DAYS días
Backups totales: $REMAINING_BACKUPS
============================================================

EOF

log "Backup finalizado exitosamente"
exit 0
