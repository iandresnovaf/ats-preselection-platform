#!/bin/bash
# ============================================================
# SCRIPT: Restaurar Base de Datos PostgreSQL desde Backup
# ATS Platform
# ============================================================

set -euo pipefail

# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ats_platform}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"

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

usage() {
    cat <<EOF
Uso: $0 [OPCIONES] <archivo_backup>

Opciones:
    -h, --help              Mostrar esta ayuda
    -l, --list              Listar backups disponibles
    -c, --create-db         Crear la base de datos antes de restaurar
    -d, --drop              Eliminar y recrear la base de datos
    -t, --test              Modo de prueba (verificar sin restaurar)
    -v, --verbose           Modo verbose

Ejemplos:
    $0 -l                                           # Listar backups
    $0 backup_ats_platform_20240115_120000.dump     # Restaurar backup específico
    $0 -d backup_ats_platform_20240115_120000.dump  # Drop y restaurar
    $0 -c backup_ats_platform_20240115_120000.dump  # Crear DB y restaurar
    $0 -t backup_ats_platform_20240115_120000.dump  # Verificar backup

EOF
    exit 1
}

list_backups() {
    log "Backups disponibles en $BACKUP_DIR:"
    echo ""
    printf "%-30s %-15s %-20s\n" "FECHA" "TAMAÑO" "ARCHIVO"
    echo "─────────────────────────────────────────────────────────────────────────"
    
    find "$BACKUP_DIR" -name "backup_*.dump" -type f -printf '%T@ %p\n' 2>/dev/null | \
        sort -rn | \
        while read -r timestamp filepath; do
            filename=$(basename "$filepath")
            filedate=$(date -d "@$timestamp" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || stat -c %y "$filepath" 2>/dev/null | cut -d' ' -f1,2)
            filesize=$(du -h "$filepath" 2>/dev/null | cut -f1)
            printf "%-30s %-15s %-20s\n" "$filedate" "$filesize" "$filename"
        done
    echo ""
}

verify_backup() {
    local backup_file="$1"
    log "Verificando backup: $backup_file"
    
    if [ ! -f "$backup_file" ]; then
        error_exit "Archivo no encontrado: $backup_file"
    fi
    
    # Verificar que es un archivo de pg_dump válido
    if ! pg_restore -l "$backup_file" > /dev/null 2>&1; then
        error_exit "El archivo no es un backup válido de PostgreSQL"
    fi
    
    # Mostrar información del backup
    log "Información del backup:"
    pg_restore --list "$backup_file" | head -20
    
    # Contar objetos
    local object_count
    object_count=$(pg_restore -l "$backup_file" 2>/dev/null | wc -l)
    log "Total de objetos en backup: $object_count"
    
    log "Backup verificado correctamente"
}

# ============================================================
# PARSEAR ARGUMENTOS
# ============================================================

CREATE_DB=false
DROP_DB=false
TEST_MODE=false
VERBOSE=false
BACKUP_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -l|--list)
            list_backups
            exit 0
            ;;
        -c|--create-db)
            CREATE_DB=true
            shift
            ;;
        -d|--drop)
            DROP_DB=true
            shift
            ;;
        -t|--test)
            TEST_MODE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -*)
            error_exit "Opción desconocida: $1"
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

if [ -z "$BACKUP_FILE" ]; then
    log "Error: Debe especificar un archivo de backup"
    usage
fi

# Resolver ruta completa si es relativa
if [[ ! "$BACKUP_FILE" = /* ]]; then
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
fi

# ============================================================
# VERIFICACIONES PREVIAS
# ============================================================

# Verificar que pg_restore esté disponible
if ! command -v pg_restore &> /dev/null; then
    error_exit "pg_restore no está instalado. Instalar postgresql-client."
fi

# Verificar que el archivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    error_exit "Archivo de backup no encontrado: $BACKUP_FILE"
fi

# Verificar conexión a PostgreSQL
export PGPASSWORD="$DB_PASSWORD"
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
    error_exit "No se puede conectar a PostgreSQL en $DB_HOST:$DB_PORT"
fi

log "Conexión a PostgreSQL verificada"

# Verificar backup
verify_backup "$BACKUP_FILE"

# Si es modo test, terminar aquí
if [ "$TEST_MODE" = true ]; then
    log "Modo de prueba: verificación completada, no se realizó restauración"
    exit 0
fi

# ============================================================
# PREPARAR RESTAURACIÓN
# ============================================================

# Si se solicita drop, eliminar y recrear la base de datos
if [ "$DROP_DB" = true ]; then
    log "ADVERTENCIA: Se eliminará la base de datos '$DB_NAME'"
    read -p "¿Está seguro? (escriba 'SI' para continuar): " confirm
    if [ "$confirm" != "SI" ]; then
        log "Operación cancelada por el usuario"
        exit 1
    fi
    
    log "Eliminando base de datos '$DB_NAME'..."
    dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --if-exists "$DB_NAME" || true
    
    CREATE_DB=true
fi

# Crear base de datos si es necesario
if [ "$CREATE_DB" = true ]; then
    log "Creando base de datos '$DB_NAME'..."
    createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" || error_exit "No se pudo crear la base de datos"
fi

# ============================================================
# RESTAURAR BACKUP
# ============================================================

log "Iniciando restauración desde: $BACKUP_FILE"

# Opciones de pg_restore
RESTORE_OPTS=""
[ "$VERBOSE" = true ] && RESTORE_OPTS="$RESTORE_OPTS --verbose"

# Restaurar el backup
# --clean: Limpiar (drop) objetos antes de recrearlos
# --if-exists: Usar IF EXISTS al hacer DROP
# --no-owner: No restaurar ownership (útil si el usuario es diferente)
# --no-privileges: No restaurar privilegios
# --jobs=2: Paralelizar (si el formato lo permite)

pg_restore \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    $RESTORE_OPTS \
    "$BACKUP_FILE" \
    2>&1 || {
        # pg_restore retorna 1 si hubo advertencias, verificar si es crítico
        log "Advertencias durante la restauración (esto es normal para algunos objetos)"
    }

# ============================================================
# VERIFICACIÓN POST-RESTAURACIÓN
# ============================================================

log "Verificando restauración..."

# Contar tablas
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
" | tr -d ' ')

log "Tablas restauradas: $TABLE_COUNT"

# Verificar versión de PostgreSQL
PG_VERSION=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT version();" | head -1)
log "PostgreSQL: $PG_VERSION"

# ============================================================
# RESUMEN
# ============================================================

cat <<EOF

============================================================
RESTAURACIÓN COMPLETADA
============================================================
Database:      $DB_NAME
Backup:        $BACKUP_FILE
Host:          $DB_HOST:$DB_PORT
Tablas:        $TABLE_COUNT
============================================================

Verifique que los datos se hayan restaurado correctamente:
  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME

EOF

log "Restauración finalizada exitosamente"
exit 0
