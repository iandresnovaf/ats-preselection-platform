#!/bin/bash
# =============================================================================
# ATS Platform - Emergency Rollback Script
# =============================================================================
# Script de rollback rápido para situaciones de emergencia:
# - Rollback a versión anterior de Docker
# - Restauración de base de datos desde backup
# - Notificación al equipo
#
# ⚠️  ADVERTENCIA: Este script debe usarse solo en emergencias
#
# Uso:
#   ./scripts/emergency_rollback.sh [OPTIONS]
#
# Opciones:
#   --version TAG       Rollback a versión específica
#   --restore-db        Restaurar base de datos desde backup
#   --backup FILE       Usar backup específico
#   --force             No pedir confirmación
#   --notify            Notificar al equipo (requiere webhook configurado)
#   --reason TEXT       Razón del rollback (para logs/notificaciones)
#
# Ejemplos:
#   # Rollback rápido a versión anterior
#   ./scripts/emergency_rollback.sh
#
#   # Rollback con restauración de DB
#   ./scripts/emergency_rollback.sh --restore-db --force
#
#   # Rollback a versión específica
#   ./scripts/emergency_rollback.sh --version v1.2.0
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${PROJECT_DIR}/backups"
LOG_DIR="${PROJECT_DIR}/logs"
ROLLBACK_LOG="${LOG_DIR}/rollback_$(date +%Y%m%d_%H%M%S).log"

# Variables
TARGET_VERSION=""
RESTORE_DB=false
BACKUP_FILE=""
FORCE=false
NOTIFY=false
ROLLBACK_REASON=""
PREVIOUS_VERSION=""
ROLLBACK_START_TIME=""

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

log_section() {
    echo -e "\n${BOLD}${CYAN}▶ $1${NC}\n" | tee -a "$ROLLBACK_LOG"
}

log_emergency() {
    echo -e "\n${MAGENTA}${BOLD}🚨 EMERGENCY: $1${NC}\n" | tee -a "$ROLLBACK_LOG"
}

error_exit() {
    log_error "$1"
    send_notification "failed" "Rollback fallido: $1"
    exit 1
}

# =============================================================================
# SETUP
# =============================================================================

setup() {
    mkdir -p "$BACKUP_DIR" "$LOG_DIR"
    touch "$ROLLBACK_LOG"
    ROLLBACK_START_TIME=$(date +%s)
    
    # Verificar que estamos en el proyecto correcto
    if [[ ! -f "${PROJECT_DIR}/docker-compose.yml" ]]; then
        error_exit "No se encontró docker-compose.yml. ¿Estás en el directorio correcto?"
    fi
    
    # Detectar versión anterior
    detect_previous_version
}

detect_previous_version() {
    # Intentar obtener la versión anterior de varias fuentes
    if [[ -f "${BACKUP_DIR}/.current_version" ]]; then
        PREVIOUS_VERSION=$(cat "${BACKUP_DIR}/.current_version")
    fi
    
    # Si no hay versión anterior, buscar en imágenes Docker
    if [[ -z "$PREVIOUS_VERSION" ]]; then
        PREVIOUS_VERSION=$(docker images "ats-backend" --format "{{.Tag}}" | grep -v "latest\|$(cat "${PROJECT_DIR}/.deploy_version" 2>/dev/null || echo 'none')" | head -1)
    fi
}

# =============================================================================
# PARSE ARGS
# =============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --version)
                TARGET_VERSION="$2"
                shift 2
                ;;
            --restore-db)
                RESTORE_DB=true
                shift
                ;;
            --backup)
                BACKUP_FILE="$2"
                shift 2
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --notify)
                NOTIFY=true
                shift
                ;;
            --reason)
                ROLLBACK_REASON="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_warning "Opción desconocida: $1"
                shift
                ;;
        esac
    done
}

show_help() {
    cat << EOF
ATS Platform - Emergency Rollback Script

⚠️  Este script debe usarse SOLO en situaciones de emergencia.

Uso: $(basename "$0") [OPTIONS]

OPTIONS:
    --version TAG       Rollback a versión específica de imagen Docker
    --restore-db        Restaurar base de datos desde backup
    --backup FILE       Usar archivo de backup específico
    --force             No pedir confirmación (⚠️  peligroso)
    --notify            Notificar al equipo vía webhook
    --reason TEXT       Razón del rollback (para logs)
    --help, -h          Mostrar esta ayuda

EJEMPLOS:
    # Rollback a versión anterior (interactivo)
    $(basename "$0")

    # Rollback con restauración de DB (sin confirmación)
    $(basename "$0") --restore-db --force

    # Rollback a versión específica
    $(basename "$0") --version v1.2.0

    # Rollback con notificación
    $(basename "$0") --notify --reason "Critical bug in v1.3.0"

EOF
}

# =============================================================================
# CONFIRMACIÓN
# =============================================================================

confirm_rollback() {
    if [[ "$FORCE" == true ]]; then
        return 0
    fi
    
    echo -e "\n${MAGENTA}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}${BOLD}║              ⚠️  EMERGENCY ROLLBACK ⚠️                      ║${NC}"
    echo -e "${MAGENTA}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}\n"
    
    echo -e "${YELLOW}Estás a punto de ejecutar un ROLLBACK de emergencia.${NC}"
    echo -e "${YELLOW}Esta acción:${NC}"
    echo "  - Revertirá la aplicación a una versión anterior"
    
    if [[ "$RESTORE_DB" == true ]]; then
        echo "  - ${RED}RESTAURARÁ LA BASE DE DATOS${NC} (puede causar pérdida de datos)"
    fi
    
    echo "  - Interrumpirá el servicio temporalmente"
    echo
    
    if [[ -n "$TARGET_VERSION" ]]; then
        echo "Versión objetivo: $TARGET_VERSION"
    else
        echo "Versión objetivo: ${PREVIOUS_VERSION:-"anterior disponible"}"
    fi
    
    if [[ -n "$ROLLBACK_REASON" ]]; then
        echo "Razón: $ROLLBACK_REASON"
    fi
    
    echo
    read -p "¿Estás SEGURO de que quieres continuar? Escribe 'ROLLBACK' para confirmar: " confirm
    
    if [[ "$confirm" != "ROLLBACK" ]]; then
        log_info "Rollback cancelado por el usuario"
        exit 0
    fi
    
    # Doble confirmación si es restore de DB
    if [[ "$RESTORE_DB" == true ]]; then
        echo
        read -p "⚠️  La base de datos será restaurada. Esto puede causar PÉRDIDA DE DATOS. ¿Continuar? [yes/NO]: " confirm_db
        if [[ "$confirm_db" != "yes" ]]; then
            log_info "Rollback cancelado por el usuario"
            exit 0
        fi
    fi
}

# =============================================================================
# BACKUP DE SEGURIDAD
# =============================================================================

create_emergency_backup() {
    log_section "BACKUP DE SEGURIDAD"
    
    log_info "Creando backup de seguridad antes del rollback..."
    
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local emergency_backup="${BACKUP_DIR}/emergency_pre_rollback_${timestamp}.sql"
    
    # Backup de la DB actual (por si acaso)
    if docker ps | grep -q "ats_postgres"; then
        if docker exec ats_postgres pg_dumpall -c -U postgres > "$emergency_backup" 2>/dev/null; then
            log_success "Backup de seguridad creado: $emergency_backup"
            echo "$emergency_backup" > "${BACKUP_DIR}/.emergency_backup"
        else
            log_warning "No se pudo crear backup de seguridad"
        fi
    else
        log_warning "PostgreSQL no está corriendo, no se pudo crear backup"
    fi
    
    # Guardar estado actual de contenedores
    docker compose ps > "${BACKUP_DIR}/.containers_before_rollback_${timestamp}.txt" 2>/dev/null || true
}

# =============================================================================
# ROLLBACK DE APLICACIÓN
# =============================================================================

rollback_application() {
    log_section "ROLLBACK DE APLICACIÓN"
    
    local target="${TARGET_VERSION:-$PREVIOUS_VERSION}"
    
    if [[ -z "$target" ]]; then
        log_warning "No se detectó versión anterior, intentando rollback manual..."
        target="latest"
    fi
    
    log_info "Target version: $target"
    
    # Detener servicios actuales
    log_info "Deteniendo servicios actuales..."
    docker compose down --timeout 30 || true
    
    # Verificar que la imagen existe
    if ! docker image inspect "ats-backend:${target}" > /dev/null 2>&1; then
        log_warning "Imagen ats-backend:${target} no encontrada localmente"
        
        # Intentar pull si hay registry configurado
        if docker info --format '{{.IndexServerAddress}}' | grep -v "docker.io" > /dev/null 2>&1; then
            log_info "Intentando descargar imagen del registry..."
            if docker pull "ats-backend:${target}" 2>/dev/null; then
                log_success "Imagen descargada exitosamente"
            else
                log_error "No se pudo obtener la imagen ${target}"
                return 1
            fi
        else
            log_error "Imagen no disponible y no hay registry configurado"
            return 1
        fi
    fi
    
    # Actualizar tag 'latest' para apuntar a la versión objetivo
    log_info "Actualizando tags de imagen..."
    docker tag "ats-backend:${target}" ats-backend:latest
    
    if docker image inspect "ats-frontend:${target}" > /dev/null 2>&1; then
        docker tag "ats-frontend:${target}" ats-frontend:latest
    fi
    
    # Iniciar servicios con versión anterior
    log_info "Iniciando servicios con versión anterior..."
    
    # Modificar temporalmente docker-compose para usar la imagen específica
    export BACKEND_IMAGE="ats-backend:${target}"
    export FRONTEND_IMAGE="ats-frontend:${target}"
    
    docker compose up -d || {
        log_error "Fallo al iniciar servicios"
        return 1
    }
    
    # Esperar a que los servicios inicien
    log_info "Esperando a que los servicios inicien..."
    sleep 10
    
    # Verificar que el backend esté respondiendo
    local retries=0
    local max_retries=12
    
    while [[ $retries -lt $max_retries ]]; do
        if curl -sf "http://localhost:8000/api/health" > /dev/null 2>&1; then
            log_success "Servicios iniciados correctamente"
            return 0
        fi
        
        log_info "Esperando servicio... ($((retries + 1))/$max_retries)"
        sleep 5
        ((retries++))
    done
    
    log_error "Servicios no responden después de $((max_retries * 5)) segundos"
    return 1
}

# =============================================================================
# RESTAURACIÓN DE BASE DE DATOS
# =============================================================================

restore_database() {
    log_section "RESTAURACIÓN DE BASE DE DATOS"
    
    if [[ "$RESTORE_DB" != true ]]; then
        log_info "Restauración de DB omitida"
        return 0
    fi
    
    # Determinar archivo de backup a usar
    local backup_to_restore=""
    
    if [[ -n "$BACKUP_FILE" && -f "$BACKUP_FILE" ]]; then
        backup_to_restore="$BACKUP_FILE"
    elif [[ -f "${BACKUP_DIR}/.last_backup" ]]; then
        local last_backup
        last_backup=$(cat "${BACKUP_DIR}/.last_backup")
        if [[ -f "$last_backup" ]]; then
            backup_to_restore="$last_backup"
        fi
    fi
    
    # Buscar backups disponibles
    if [[ -z "$backup_to_restore" ]]; then
        log_info "Buscando backups disponibles..."
        
        local available_backups
        available_backups=$(find "$BACKUP_DIR" -name "*.sql" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -5 | cut -d' ' -f2-)
        
        if [[ -z "$available_backups" ]]; then
            log_error "No se encontraron backups disponibles"
            return 1
        fi
        
        echo
        echo "Backups disponibles:"
        local i=1
        while IFS= read -r backup; do
            local size
            size=$(du -h "$backup" 2>/dev/null | cut -f1)
            local date
            date=$(stat -c %y "$backup" 2>/dev/null | cut -d' ' -f1,2 | cut -d'.' -f1)
            echo "  $i) $(basename "$backup") ($size) - $date"
            ((i++))
        done <<< "$available_backups"
        echo
        
        if [[ "$FORCE" != true ]]; then
            read -p "Selecciona el número del backup a restaurar: " selection
            backup_to_restore=$(echo "$available_backups" | sed -n "${selection}p")
        else
            backup_to_restore=$(echo "$available_backups" | tail -1)
        fi
    fi
    
    if [[ ! -f "$backup_to_restore" ]]; then
        log_error "Archivo de backup no válido: $backup_to_restore"
        return 1
    fi
    
    log_info "Backup seleccionado: $backup_to_restore"
    log_info "Tamaño: $(du -h "$backup_to_restore" | cut -f1)"
    
    # Verificar que PostgreSQL esté corriendo
    if ! docker ps | grep -q "ats_postgres"; then
        log_info "Iniciando PostgreSQL..."
        docker compose up -d postgres
        sleep 5
    fi
    
    # Esperar a que PostgreSQL esté listo
    log_info "Esperando a que PostgreSQL esté listo..."
    local retries=0
    while [[ $retries -lt 30 ]]; do
        if docker exec ats_postgres pg_isready -U postgres > /dev/null 2>&1; then
            break
        fi
        sleep 2
        ((retries++))
    done
    
    # Restaurar backup
    log_info "Restaurando base de datos (esto puede tomar varios minutos)..."
    
    if docker exec -i ats_postgres psql -U postgres < "$backup_to_restore" 2>&1 | tee -a "$ROLLBACK_LOG"; then
        log_success "Base de datos restaurada exitosamente"
        return 0
    else
        log_error "Fallo al restaurar la base de datos"
        return 1
    fi
}

# =============================================================================
# VERIFICACIÓN POST-ROLLBACK
# =============================================================================

verify_rollback() {
    log_section "VERIFICACIÓN POST-ROLLBACK"
    
    local max_retries=12
    local retries=0
    
    while [[ $retries -lt $max_retries ]]; do
        if curl -sf "http://localhost:8000/api/health" > /dev/null 2>&1; then
            log_success "Servicio respondiendo correctamente"
            
            # Verificar versión
            local version_response
            version_response=$(curl -sf "http://localhost:8000/api/health" 2>/dev/null || echo "")
            
            if [[ -n "$version_response" ]]; then
                log_info "Respuesta del health check: $version_response"
            fi
            
            return 0
        fi
        
        log_info "Esperando servicio... ($((retries + 1))/$max_retries)"
        sleep 5
        ((retries++))
    done
    
    log_error "Servicio no respondiendo después del rollback"
    return 1
}

# =============================================================================
# NOTIFICACIÓN
# =============================================================================

send_notification() {
    local status="$1"
    local message="$2"
    
    if [[ "$NOTIFY" != true ]]; then
        return 0
    fi
    
    log_info "Enviando notificación al equipo..."
    
    local webhook_url="${SLACK_WEBHOOK_URL:-${DISCORD_WEBHOOK_URL:-${TEAMS_WEBHOOK_URL:-}}}"
    
    if [[ -z "$webhook_url" ]]; then
        log_warning "No hay webhook configurado para notificaciones"
        return 0
    fi
    
    local duration
    local end_time
    end_time=$(date +%s)
    duration=$((end_time - ROLLBACK_START_TIME))
    
    local payload
    local emoji
    local color
    
    if [[ "$status" == "success" ]]; then
        emoji="🔄"
        color="warning"
    else
        emoji="❌"
        color="danger"
    fi
    
    # Slack format
    if [[ "$webhook_url" == *"slack"* ]] || [[ "$webhook_url" == *"hooks.slack"* ]]; then
        payload=$(cat <<EOF
{
    "text": "${emoji} EMERGENCY ROLLBACK: ATS Platform",
    "attachments": [{
        "color": "${color}",
        "fields": [
            {"title": "Status", "value": "${status}", "short": true},
            {"title": "Duration", "value": "${duration}s", "short": true},
            {"title": "Target Version", "value": "${TARGET_VERSION:-$PREVIOUS_VERSION}", "short": true},
            {"title": "Reason", "value": "${ROLLBACK_REASON:-Not specified}", "short": false},
            {"title": "Details", "value": "${message}", "short": false}
        ],
        "footer": "ATS Platform",
        "ts": $(date +%s)
    }]
}
EOF
)
        curl -s -X POST -H 'Content-type: application/json' --data "$payload" "$webhook_url" > /dev/null 2>&1 || true
    fi
    
    # Email notification (si hay comando mail configurado)
    if command -v mail &> /dev/null && [[ -n "${ALERT_EMAIL:-}" ]]; then
        echo "$message" | mail -s "[EMERGENCY] ATS Platform Rollback ${status}" "$ALERT_EMAIL" || true
    fi
}

# =============================================================================
# LIMPIEZA
# =============================================================================

cleanup() {
    log_section "LIMPIEZA"
    
    # Limpiar imágenes huérfanas
    log_info "Limpiando imágenes Docker no utilizadas..."
    docker image prune -f > /dev/null 2>&1 || true
    
    # Rotar logs antiguos
    find "$LOG_DIR" -name "rollback_*.log" -type f -mtime +30 -delete 2>/dev/null || true
    
    log_success "Limpieza completada"
}

# =============================================================================
# REPORTE FINAL
# =============================================================================

print_summary() {
    local status="$1"
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - ROLLBACK_START_TIME))
    
    echo -e "\n${BOLD}${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║                   ROLLBACK SUMMARY                          ║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo "Timestamp: $(date)"
    echo "Duration: ${duration}s"
    echo "Log file: $ROLLBACK_LOG"
    echo
    
    if [[ "$status" == "success" ]]; then
        echo -e "${GREEN}${BOLD}✓ ROLLBACK COMPLETADO EXITOSAMENTE${NC}"
    else
        echo -e "${RED}${BOLD}✗ ROLLBACK FALLÓ${NC}"
        echo
        echo -e "${YELLOW}Acciones recomendadas:${NC}"
        echo "  1. Revisar logs: tail -f $ROLLBACK_LOG"
        echo "  2. Verificar estado: docker compose ps"
        echo "  3. Si es necesario, intervención manual"
    fi
    
    echo
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo -e "${MAGENTA}${BOLD}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║        ATS Platform - Emergency Rollback Script           ║"
    echo "║                                                            ║"
    echo "║     ⚠️  USE ONLY IN EMERGENCY SITUATIONS  ⚠️              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    parse_args "$@"
    setup
    
    log_info "Iniciando rollback de emergencia"
    log_info "Fecha: $(date)"
    log_info "Log: $ROLLBACK_LOG"
    
    if [[ -n "$ROLLBACK_REASON" ]]; then
        log_info "Razón: $ROLLBACK_REASON"
    fi
    
    # Confirmación
    confirm_rollback
    
    # Ejecutar rollback
    local rollback_success=false
    
    if create_emergency_backup && \
       rollback_application && \
       restore_database && \
       verify_rollback; then
        rollback_success=true
    fi
    
    # Resultado
    if [[ "$rollback_success" == true ]]; then
        cleanup
        print_summary "success"
        send_notification "success" "Rollback a ${TARGET_VERSION:-$PREVIOUS_VERSION} completado"
        
        echo -e "${GREEN}${BOLD}✅ Rollback completado${NC}\n"
        exit 0
    else
        print_summary "failed"
        send_notification "failed" "Rollback falló - revisar $ROLLBACK_LOG"
        
        echo -e "${RED}${BOLD}❌ Rollback falló${NC}\n"
        exit 1
    fi
}

# Manejar señales
trap 'log_error "Rollback interrumpido"; send_notification "failed" "Rollback interrumpido por usuario"; exit 130' INT TERM

# Ejecutar
main "$@"
