#!/bin/bash
# =============================================================================
# ATS Platform - Production Deployment Script
# =============================================================================
# Script de deploy automatizado con:
# - Build de imagen Docker con tag de versión
# - Tests de seguridad (bandit, safety)
# - Migraciones de DB
# - Health check
# - Rollback automático si falla
#
# Uso:
#   ./scripts/deploy_production.sh [VERSION] [OPTIONS]
#
# Opciones:
#   --skip-tests        Saltar tests de seguridad
#   --skip-migrations   Saltar migraciones de DB
#   --force             Forzar deploy sin confirmación
#   --dry-run           Simular deploy sin ejecutar cambios
#   --no-rollback       Deshabilitar rollback automático
#
# Ejemplos:
#   ./scripts/deploy_production.sh v1.2.3
#   ./scripts/deploy_production.sh --force
#   VERSION=1.2.3 ./scripts/deploy_production.sh --dry-run
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${PROJECT_DIR}/backups"
LOG_DIR="${PROJECT_DIR}/logs"
DEPLOY_LOG="${LOG_DIR}/deploy_$(date +%Y%m%d_%H%M%S).log"

# Configuración de tiempo
HEALTH_CHECK_TIMEOUT=120
HEALTH_CHECK_INTERVAL=5
ROLLBACK_RETENTION=10  # Número de versiones anteriores a mantener

# Flags
SKIP_TESTS=false
SKIP_MIGRATIONS=false
FORCE_DEPLOY=false
DRY_RUN=false
NO_ROLLBACK=false

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_section() {
    echo -e "\n${BOLD}${CYAN}▶ $1${NC}\n" | tee -a "$DEPLOY_LOG"
}

error_exit() {
    log_error "$1"
    exit 1
}

# Verificar si estamos en el directorio correcto
check_project_root() {
    if [[ ! -f "${PROJECT_DIR}/docker-compose.yml" ]]; then
        error_exit "No se encontró docker-compose.yml. ¿Estás en el directorio correcto?"
    fi
    
    if [[ ! -f "${PROJECT_DIR}/backend/Dockerfile" ]]; then
        error_exit "No se encontró backend/Dockerfile"
    fi
}

# Crear directorios necesarios
setup_directories() {
    mkdir -p "$BACKUP_DIR" "$LOG_DIR"
    touch "$DEPLOY_LOG"
}

# Parsear argumentos
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-migrations)
                SKIP_MIGRATIONS=true
                shift
                ;;
            --force)
                FORCE_DEPLOY=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --no-rollback)
                NO_ROLLBACK=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            --*)
                log_warning "Opción desconocida: $1"
                shift
                ;;
            *)
                # Asumimos que es la versión
                if [[ -z "${VERSION:-}" ]]; then
                    VERSION="$1"
                fi
                shift
                ;;
        esac
    done
    
    # Si no se especificó versión, generar una
    if [[ -z "${VERSION:-}" ]]; then
        VERSION="$(date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
    fi
    
    export VERSION
}

show_help() {
    cat << EOF
ATS Platform - Production Deployment Script

Uso: $(basename "$0") [VERSION] [OPTIONS]

ARGUMENTS:
    VERSION             Tag de versión para el deploy (default: timestamp-gitsha)

OPTIONS:
    --skip-tests        Saltar tests de seguridad
    --skip-migrations   Saltar migraciones de DB
    --force             Forzar deploy sin confirmación interactiva
    --dry-run           Simular deploy sin ejecutar cambios reales
    --no-rollback       Deshabilitar rollback automático en caso de fallo
    --help, -h          Mostrar esta ayuda

EJEMPLOS:
    # Deploy con versión específica
    $(basename "$0") v1.2.3

    # Deploy forzado sin confirmación
    $(basename "$0") --force

    # Deploy con versión desde variable de entorno
    VERSION=2.0.0 $(basename "$0")

    # Simular deploy (sin cambios reales)
    $(basename "$0") --dry-run

EOF
}

# =============================================================================
# CHECKS PRE-DEPLOY
# =============================================================================

run_pre_deploy_checks() {
    log_section "PRE-DEPLOY CHECKS"
    
    # Ejecutar script de verificación
    if [[ -f "${SCRIPT_DIR}/pre_deploy_check.py" ]]; then
        log_info "Ejecutando pre_deploy_check.py..."
        if ! python3 "${SCRIPT_DIR}/pre_deploy_check.py"; then
            error_exit "Pre-deploy checks fallaron. Corrige los errores antes de continuar."
        fi
    else
        log_warning "pre_deploy_check.py no encontrado, omitiendo verificaciones"
    fi
}

# =============================================================================
# BACKUP ANTES DEL DEPLOY
# =============================================================================

create_backup() {
    log_section "CREANDO BACKUP"
    
    local backup_file="${BACKUP_DIR}/pre_deploy_$(date +%Y%m%d_%H%M%S).sql"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Se crearía backup en: $backup_file"
        return 0
    fi
    
    # Verificar si hay backup script
    if [[ -f "${SCRIPT_DIR}/backup.sh" ]]; then
        log_info "Ejecutando backup.sh..."
        bash "${SCRIPT_DIR}/backup.sh"
    else
        log_info "Creando backup de base de datos..."
        
        # Obtener credenciales del environment
        source "${PROJECT_DIR}/backend/.env" 2>/dev/null || true
        
        if [[ -n "${DATABASE_URL:-}" ]]; then
            # Parse DATABASE_URL (simplificado)
            docker compose exec -T postgres pg_dumpall -c -U postgres > "$backup_file" || {
                log_warning "No se pudo crear backup con pg_dumpall"
                backup_file=""
            }
        fi
    fi
    
    # Guardar versión actual para posible rollback
    local current_version
    current_version=$(docker compose ps -q backend 2>/dev/null | head -1 | xargs docker inspect --format='{{.Config.Image}}' 2>/dev/null || echo "unknown")
    echo "$current_version" > "${BACKUP_DIR}/.current_version"
    
    # Guardar estado de las imágenes
    docker compose config --images > "${BACKUP_DIR}/.images_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
    
    if [[ -n "$backup_file" && -f "$backup_file" ]]; then
        log_success "Backup creado: $backup_file"
        echo "$backup_file" > "${BACKUP_DIR}/.last_backup"
    else
        log_warning "No se pudo crear backup de base de datos"
    fi
}

# =============================================================================
# TESTS DE SEGURIDAD
# =============================================================================

run_security_tests() {
    log_section "TESTS DE SEGURIDAD"
    
    if [[ "$SKIP_TESTS" == true ]]; then
        log_warning "Tests de seguridad omitidos (--skip-tests)"
        return 0
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Se ejecutarían tests de seguridad"
        return 0
    fi
    
    local backend_dir="${PROJECT_DIR}/backend"
    local has_errors=false
    
    # Bandit - análisis de código estático
    if command -v bandit &> /dev/null; then
        log_info "Ejecutando Bandit (security linter)..."
        if bandit -r "$backend_dir" -f json -o "${LOG_DIR}/bandit_$(date +%Y%m%d_%H%M%S).json" 2>/dev/null || \
           bandit -r "$backend_dir" -ll || true; then
            log_success "Bandit completado"
        else
            log_warning "Bandit encontró problemas (revisar logs)"
        fi
    else
        log_warning "Bandit no instalado, omitiendo"
    fi
    
    # Safety - verificar dependencias vulnerables
    if command -v safety &> /dev/null; then
        log_info "Ejecutando Safety (dependency vulnerability check)..."
        local requirements_file="${backend_dir}/requirements.txt"
        if [[ -f "$requirements_file" ]]; then
            if safety check -r "$requirements_file" --json --output "${LOG_DIR}/safety_$(date +%Y%m%d_%H%M%S).json" 2>/dev/null || \
               safety check -r "$requirements_file" || true; then
                log_success "Safety completado"
            else
                log_warning "Safety encontró vulnerabilidades (revisar logs)"
            fi
        fi
    else
        log_warning "Safety no instalado, omitiendo"
    fi
    
    # Semgrep (si está disponible)
    if command -v semgrep &> /dev/null; then
        log_info "Ejecutando Semgrep..."
        if semgrep --config=auto "$backend_dir" --json -o "${LOG_DIR}/semgrep_$(date +%Y%m%d_%H%M%S).json" 2>/dev/null || \
           semgrep --config=auto "$backend_dir" || true; then
            log_success "Semgrep completado"
        else
            log_warning "Semgrep encontró problemas (revisar logs)"
        fi
    fi
    
    # Verificar secrets en el código
    if command -v git &> /dev/null && git rev-parse --git-dir > /dev/null 2>&1; then
        log_info "Verificando secrets en git history..."
        if git log --all --full-history --source -- .env* 2>/dev/null | head -1; then
            log_warning "Se encontraron commits con archivos .env - revisar historial"
        else
            log_success "No se encontraron secrets en historial de commits"
        fi
    fi
}

# =============================================================================
# BUILD DE IMÁGENES DOCKER
# =============================================================================

build_images() {
    log_section "BUILD DE IMÁGENES DOCKER"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Se construirían las imágenes con tag: $VERSION"
        return 0
    fi
    
    # Verificar docker disponible
    if ! command -v docker &> /dev/null; then
        error_exit "Docker no está instalado"
    fi
    
    log_info "Construyendo imágenes con versión: $VERSION"
    
    # Build del backend
    log_info "Building backend image..."
    docker build -t "ats-backend:${VERSION}" \
        -t "ats-backend:latest" \
        -f "${PROJECT_DIR}/backend/Dockerfile" \
        "${PROJECT_DIR}/backend" || error_exit "Fallo al construir imagen backend"
    
    # Build del frontend
    if [[ -f "${PROJECT_DIR}/frontend/Dockerfile" ]]; then
        log_info "Building frontend image..."
        docker build -t "ats-frontend:${VERSION}" \
            -t "ats-frontend:latest" \
            -f "${PROJECT_DIR}/frontend/Dockerfile" \
            "${PROJECT_DIR}/frontend" || error_exit "Fallo al construir imagen frontend"
    fi
    
    log_success "Imágenes construidas exitosamente"
    
    # Guardar versiones en archivo
    echo "${VERSION}" > "${PROJECT_DIR}/.deploy_version"
}

# =============================================================================
# MIGRACIONES DE BASE DE DATOS
# =============================================================================

run_migrations() {
    log_section "MIGRACIONES DE BASE DE DATOS"
    
    if [[ "$SKIP_MIGRATIONS" == true ]]; then
        log_warning "Migraciones omitidas (--skip-migrations)"
        return 0
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Se ejecutarían migraciones de DB"
        return 0
    fi
    
    log_info "Verificando servicios..."
    docker compose up -d postgres redis || error_exit "No se pudieron iniciar servicios de DB"
    
    # Esperar a que postgres esté listo
    log_info "Esperando a que PostgreSQL esté listo..."
    local retries=0
    while [[ $retries -lt 30 ]]; do
        if docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
            break
        fi
        sleep 2
        ((retries++))
    done
    
    if [[ $retries -eq 30 ]]; then
        error_exit "PostgreSQL no está respondiendo"
    fi
    
    log_info "Ejecutando migraciones Alembic..."
    
    # Ejecutar migraciones en un contenedor temporal
    docker run --rm \
        --network ats-platform_ats-network \
        -v "${PROJECT_DIR}/backend:/app" \
        -w /app \
        --env-file "${PROJECT_DIR}/backend/.env" \
        "ats-backend:${VERSION}" \
        alembic upgrade head || error_exit "Fallo al ejecutar migraciones"
    
    log_success "Migraciones completadas"
}

# =============================================================================
# DEPLOY
# =============================================================================

deploy_services() {
    log_section "DEPLOY DE SERVICIOS"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Se haría deploy de los servicios"
        return 0
    fi
    
    log_info "Actualizando servicios..."
    
    # Usar docker compose para el deploy
    docker compose up -d --build || error_exit "Fallo al actualizar servicios"
    
    log_info "Esperando a que los servicios inicien..."
    sleep 5
    
    # Verificar que los contenedores estén corriendo
    local failed_services
    failed_services=$(docker compose ps -q | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null | grep -v "running" || true)
    
    if [[ -n "$failed_services" ]]; then
        log_error "Algunos servicios no están corriendo correctamente"
        docker compose ps
        return 1
    fi
    
    log_success "Servicios deployados"
}

# =============================================================================
# HEALTH CHECK
# =============================================================================

health_check() {
    log_section "HEALTH CHECK"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Se ejecutaría health check"
        return 0
    fi
    
    local endpoint="http://localhost:8000/api/health"
    local elapsed=0
    local healthy=false
    
    log_info "Verificando salud del backend en $endpoint..."
    log_info "Timeout: ${HEALTH_CHECK_TIMEOUT}s"
    
    while [[ $elapsed -lt $HEALTH_CHECK_TIMEOUT ]]; do
        if curl -sf "$endpoint" > /dev/null 2>&1; then
            healthy=true
            break
        fi
        
        echo -n "."
        sleep $HEALTH_CHECK_INTERVAL
        ((elapsed+=HEALTH_CHECK_INTERVAL))
    done
    echo
    
    if [[ "$healthy" == true ]]; then
        log_success "Health check exitoso (${elapsed}s)"
        
        # Verificar métricas también
        if curl -sf "http://localhost:8000/metrics" > /dev/null 2>&1; then
            log_success "Endpoint de métricas respondiendo"
        fi
        
        return 0
    else
        log_error "Health check falló después de ${HEALTH_CHECK_TIMEOUT}s"
        return 1
    fi
}

# =============================================================================
# ROLLBACK
# =============================================================================

rollback() {
    log_section "ROLLBACK AUTOMÁTICO"
    
    if [[ "$NO_ROLLBACK" == true ]]; then
        log_warning "Rollback automático deshabilitado (--no-rollback)"
        return 1
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Se ejecutaría rollback"
        return 0
    fi
    
    log_error "El deploy falló. Iniciando rollback..."
    
    # Restaurar versión anterior
    local previous_version
    previous_version=$(cat "${BACKUP_DIR}/.current_version" 2>/dev/null || echo "")
    
    if [[ -n "$previous_version" && "$previous_version" != "unknown" ]]; then
        log_info "Restaurando versión anterior: $previous_version"
        
        # Rollback de docker images
        docker compose down || true
        
        # Intentar restaurar backup de DB si existe
        local last_backup
        last_backup=$(cat "${BACKUP_DIR}/.last_backup" 2>/dev/null || echo "")
        
        if [[ -n "$last_backup" && -f "$last_backup" ]]; then
            log_info "Restaurando base de datos desde backup..."
            docker compose up -d postgres
            sleep 5
            
            if docker compose exec -T postgres psql -U postgres < "$last_backup"; then
                log_success "Base de datos restaurada"
            else
                log_error "No se pudo restaurar la base de datos"
            fi
        fi
        
        # Re-iniciar con versión anterior
        docker compose up -d || true
        
        log_info "Verificando servicios después del rollback..."
        sleep 10
        
        if curl -sf "http://localhost:8000/api/health" > /dev/null 2>&1; then
            log_success "Rollback completado exitosamente"
        else
            log_error "El rollback también falló - intervención manual requerida"
        fi
    else
        log_warning "No se encontró versión anterior para rollback"
    fi
    
    return 1
}

# =============================================================================
# LIMPIEZA
# =============================================================================

cleanup() {
    log_section "LIMPIEZA"
    
    if [[ "$DRY_RUN" == true ]]; then
        return 0
    fi
    
    log_info "Limpiando imágenes antiguas..."
    
    # Mantener solo las últimas N versiones
    local images_to_remove
    images_to_remove=$(docker images "ats-backend" --format "{{.Tag}}" | grep -v "latest\|${VERSION}" | sort -r | tail -n +$((ROLLBACK_RETENTION + 1)))
    
    for tag in $images_to_remove; do
        log_info "Eliminando imagen antigua: ats-backend:$tag"
        docker rmi "ats-backend:$tag" 2>/dev/null || true
    done
    
    # Limpiar backups antiguos (mantener 30 días)
    find "$BACKUP_DIR" -name "*.sql" -type f -mtime +30 -delete 2>/dev/null || true
    
    # Prune de imágenes dangling
    docker image prune -f > /dev/null 2>&1 || true
    
    log_success "Limpieza completada"
}

# =============================================================================
# NOTIFICACIÓN
# =============================================================================

send_notification() {
    local status="$1"
    local message="$2"
    
    # Notificar al equipo (puedes configurar webhook de Slack, Discord, etc.)
    local webhook_url="${SLACK_WEBHOOK_URL:-${DISCORD_WEBHOOK_URL:-}}"
    
    if [[ -n "$webhook_url" && "$DRY_RUN" != true ]]; then
        log_info "Enviando notificación..."
        
        local payload
        if [[ "$status" == "success" ]]; then
            payload="{\"text\":\"✅ Deploy exitoso: ATS Platform v${VERSION}\",\"attachments\":[{\"color\":\"good\",\"text\":\"${message}\"}]}"
        else
            payload="{\"text\":\"❌ Deploy fallido: ATS Platform\",\"attachments\":[{\"color\":\"danger\",\"text\":\"${message}\"}]}"
        fi
        
        curl -s -X POST -H 'Content-type: application/json' --data "$payload" "$webhook_url" > /dev/null 2>&1 || true
    fi
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo -e "${BOLD}${CYAN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     ATS Platform - Production Deployment Script           ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    log_info "Iniciando deploy a producción"
    log_info "Fecha: $(date)"
    log_info "Log: $DEPLOY_LOG"
    
    # Setup
    check_project_root
    setup_directories
    parse_args "$@"
    
    log_info "Versión a deployar: $VERSION"
    log_info "Directorio del proyecto: $PROJECT_DIR"
    
    # Confirmación interactiva
    if [[ "$FORCE_DEPLOY" != true && "$DRY_RUN" != true ]]; then
        echo
        read -p "¿Continuar con el deploy a producción? [y/N]: " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            log_info "Deploy cancelado por el usuario"
            exit 0
        fi
    fi
    
    local deploy_success=false
    
    # Pipeline de deploy
    if run_pre_deploy_checks && \
       create_backup && \
       run_security_tests && \
       build_images && \
       run_migrations && \
       deploy_services; then
        
        if health_check; then
            deploy_success=true
        fi
    fi
    
    # Resultado
    if [[ "$deploy_success" == true ]]; then
        cleanup
        
        log_section "DEPLOY COMPLETADO EXITOSAMENTE"
        log_success "Versión: $VERSION"
        log_success "Timestamp: $(date)"
        log_info "Logs disponibles en: $DEPLOY_LOG"
        
        send_notification "success" "Versión $VERSION deployada exitosamente"
        
        echo -e "\n${GREEN}✅ Deploy exitoso${NC}\n"
        exit 0
    else
        send_notification "error" "Fallo en deploy - revisar logs en $DEPLOY_LOG"
        
        # Rollback automático
        rollback
        
        echo -e "\n${RED}❌ Deploy falló${NC}\n"
        exit 1
    fi
}

# Manejar señales
trap 'log_error "Deploy interrumpido"; exit 130' INT TERM

# Ejecutar
main "$@"
