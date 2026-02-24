#!/bin/bash
# =============================================================================
# ATS Platform - Deployment Verification Script
# =============================================================================
# Verifica que un deployment esté funcionando correctamente:
# - /health retorna 200
# - /metrics está accesible
# - Headers de seguridad presentes
# - No hay secretos expuestos
# - Conectividad a DB y Redis
#
# Uso:
#   ./scripts/verify_deployment.sh [OPTIONS]
#
# Opciones:
#   --endpoint URL      Endpoint base a verificar (default: http://localhost:8000)
#   --timeout SEC       Timeout para requests (default: 30)
#   --json              Output en formato JSON
#   --verbose           Mostrar información detallada
#   --report FILE       Guardar reporte en archivo
#
# Ejemplos:
#   ./scripts/verify_deployment.sh
#   ./scripts/verify_deployment.sh --endpoint https://api.example.com --json
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Defaults
ENDPOINT="http://localhost:8000"
TIMEOUT=30
JSON_OUTPUT=false
VERBOSE=false
REPORT_FILE=""

# Resultados
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_TOTAL=0
ERRORS=()
WARNINGS=()
INFO=()

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

log_info() {
    if [[ "$JSON_OUTPUT" != true ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
    INFO+=("$1")
}

log_success() {
    if [[ "$JSON_OUTPUT" != true ]]; then
        echo -e "${GREEN}[PASS]${NC} $1"
    fi
    ((CHECKS_PASSED++))
    ((CHECKS_TOTAL++))
}

log_warning() {
    if [[ "$JSON_OUTPUT" != true ]]; then
        echo -e "${YELLOW}[WARN]${NC} $1"
    fi
    WARNINGS+=("$1")
    ((CHECKS_TOTAL++))
}

log_error() {
    if [[ "$JSON_OUTPUT" != true ]]; then
        echo -e "${RED}[FAIL]${NC} $1"
    fi
    ERRORS+=("$1")
    ((CHECKS_FAILED++))
    ((CHECKS_TOTAL++))
}

log_section() {
    if [[ "$JSON_OUTPUT" != true ]]; then
        echo -e "\n${BOLD}${CYAN}▶ $1${NC}\n"
    fi
}

# =============================================================================
# PARSE ARGS
# =============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --endpoint)
                ENDPOINT="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --report)
                REPORT_FILE="$2"
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
    
    # Limpiar endpoint (remover trailing slash)
    ENDPOINT="${ENDPOINT%/}"
    
    export ENDPOINT TIMEOUT
}

show_help() {
    cat << EOF
ATS Platform - Deployment Verification Script

Verifica que el deployment esté funcionando correctamente.

Uso: $(basename "$0") [OPTIONS]

OPTIONS:
    --endpoint URL      Endpoint base (default: http://localhost:8000)
    --timeout SEC       Timeout para requests (default: 30)
    --json              Output en formato JSON
    --verbose           Mostrar información detallada
    --report FILE       Guardar reporte en archivo
    --help, -h          Mostrar esta ayuda

EJEMPLOS:
    # Verificación básica
    $(basename "$0")

    # Verificar endpoint remoto con output JSON
    $(basename "$0") --endpoint https://api.example.com --json

    # Verificación verbose con reporte
    $(basename "$0") --verbose --report /tmp/verify_report.txt

EOF
}

# =============================================================================
# CHECKS
# =============================================================================

check_health_endpoint() {
    log_section "HEALTH CHECK"
    
    local health_url="${ENDPOINT}/api/health"
    log_info "Verificando: $health_url"
    
    local response
    local http_code
    
    response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "$health_url" 2>/dev/null || echo "")
    
    if [[ -z "$response" ]]; then
        log_error "No se pudo conectar a $health_url"
        return 1
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [[ "$http_code" == "200" ]]; then
        log_success "Health endpoint responde con HTTP 200"
        
        if [[ "$VERBOSE" == true ]]; then
            echo "  Response: $body"
        fi
        
        # Verificar que el JSON sea válido y tenga status: ok
        if echo "$body" | jq -e '.status == "ok"' > /dev/null 2>&1; then
            log_success "Health status es 'ok'"
        else
            log_warning "Health status no es 'ok' o respuesta no es JSON válido"
        fi
        
        return 0
    else
        log_error "Health endpoint retornó HTTP $http_code"
        return 1
    fi
}

check_metrics_endpoint() {
    log_section "METRICS CHECK"
    
    local metrics_url="${ENDPOINT}/metrics"
    log_info "Verificando: $metrics_url"
    
    local response
    local http_code
    
    response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "$metrics_url" 2>/dev/null || echo "")
    
    if [[ -z "$response" ]]; then
        log_error "No se pudo conectar a $metrics_url"
        return 1
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [[ "$http_code" == "200" ]]; then
        log_success "Metrics endpoint responde con HTTP 200"
        
        # Verificar que sea formato Prometheus
        if echo "$body" | grep -q "# TYPE\|# HELP"; then
            log_success "Formato Prometheus detectado"
        fi
        
        if [[ "$VERBOSE" == true ]]; then
            local metric_count
            metric_count=$(echo "$body" | grep -c "^# TYPE" || echo "0")
            echo "  Métricas expuestas: $metric_count"
        fi
        
        return 0
    else
        log_error "Metrics endpoint retornó HTTP $http_code"
        return 1
    fi
}

check_security_headers() {
    log_section "SECURITY HEADERS CHECK"
    
    local url="${ENDPOINT}/api/health"
    log_info "Verificando headers en: $url"
    
    local headers
    headers=$(curl -sI --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "")
    
    if [[ -z "$headers" ]]; then
        log_error "No se pudieron obtener headers"
        return 1
    fi
    
    # Headers de seguridad a verificar
    local required_headers=(
        "X-Content-Type-Options: nosniff"
    )
    
    local recommended_headers=(
        "X-Frame-Options"
        "X-XSS-Protection"
        "Strict-Transport-Security"
        "Content-Security-Policy"
        "Referrer-Policy"
        "Permissions-Policy"
    )
    
    local all_ok=true
    
    # Verificar headers requeridos
    for header in "${required_headers[@]}"; do
        header_name=$(echo "$header" | cut -d: -f1 | tr '[:upper:]' '[:lower:]')
        header_value=$(echo "$header" | cut -d: -f2- | sed 's/^ *//')
        
        if echo "$headers" | grep -qi "^${header_name}:"; then
            actual_value=$(echo "$headers" | grep -i "^${header_name}:" | head -1)
            if echo "$actual_value" | grep -qi "$header_value"; then
                log_success "Header requerido presente: $header_name"
            else
                log_warning "Header $header_name presente pero con valor diferente"
            fi
        else
            log_error "Header requerido faltante: $header_name"
            all_ok=false
        fi
    done
    
    # Verificar headers recomendados
    for header in "${recommended_headers[@]}"; do
        if echo "$headers" | grep -qi "^${header}:"; then
            log_success "Header de seguridad presente: $header"
        else
            log_warning "Header recomendado faltante: $header"
        fi
    done
    
    # Verificar que no exponer información sensible
    if echo "$headers" | grep -qi "^Server:.*[0-9]"; then
        log_warning "Header Server expone versión del servidor"
    fi
    
    if echo "$headers" | grep -qi "^X-Powered-By:"; then
        log_warning "Header X-Powered-By presente (debería removerse)"
    fi
    
    [[ "$all_ok" == true ]]
}

check_exposed_secrets() {
    log_section "SECRETS EXPOSURE CHECK"
    
    log_info "Verificando que no haya secretos expuestos en respuestas..."
    
    local endpoints=(
        "/api/health"
        "/"
    )
    
    local patterns=(
        "sk-[a-zA-Z0-9]{20,}"  # OpenAI API keys
        "password[=:]\s*\S+"
        "secret[=:]\s*\S+"
        "private[_-]?key"
        "api[_-]?key[=:]\s*\S+"
        "token[=:]\s*[a-zA-Z0-9]{20,}"
        "BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY"
    )
    
    local secrets_found=false
    
    for endpoint in "${endpoints[@]}"; do
        local url="${ENDPOINT}${endpoint}"
        local response
        response=$(curl -s --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "")
        
        if [[ -n "$response" ]]; then
            for pattern in "${patterns[@]}"; do
                if echo "$response" | grep -qiE "$pattern"; then
                    log_error "Posible secreto expuesto en $endpoint"
                    secrets_found=true
                    
                    if [[ "$VERBOSE" == true ]]; then
                        echo "  Patrón detectado: $pattern"
                    fi
                fi
            done
        fi
    done
    
    if [[ "$secrets_found" == false ]]; then
        log_success "No se detectaron secretos expuestos"
    fi
    
    [[ "$secrets_found" == false ]]
}

check_database_connectivity() {
    log_section "DATABASE CONNECTIVITY CHECK"
    
    log_info "Verificando conectividad a base de datos..."
    
    # Intentar obtener información de DB desde el endpoint de health
    local health_url="${ENDPOINT}/api/health"
    local response
    response=$(curl -s --max-time "$TIMEOUT" "$health_url" 2>/dev/null || echo "")
    
    if echo "$response" | jq -e '.database' > /dev/null 2>&1; then
        local db_status
        db_status=$(echo "$response" | jq -r '.database.status // "unknown"')
        
        if [[ "$db_status" == "connected" || "$db_status" == "ok" ]]; then
            log_success "Base de datos conectada (reportado por health check)"
        else
            log_error "Base de datos no conectada: $db_status"
            return 1
        fi
    else
        # Intentar verificar directamente si estamos en el servidor
        if command -v docker &> /dev/null && docker ps | grep -q "ats_postgres"; then
            if docker exec ats_postgres pg_isready -U postgres > /dev/null 2>&1; then
                log_success "Base de datos respondiendo (verificación directa)"
            else
                log_warning "No se pudo verificar base de datos directamente"
            fi
        else
            log_warning "No se pudo verificar conectividad a DB desde este host"
        fi
    fi
    
    return 0
}

check_redis_connectivity() {
    log_section "REDIS CONNECTIVITY CHECK"
    
    log_info "Verificando conectividad a Redis..."
    
    # Intentar obtener información de Redis desde el endpoint de health
    local health_url="${ENDPOINT}/api/health"
    local response
    response=$(curl -s --max-time "$TIMEOUT" "$health_url" 2>/dev/null || echo "")
    
    if echo "$response" | jq -e '.redis' > /dev/null 2>&1; then
        local redis_status
        redis_status=$(echo "$response" | jq -r '.redis.status // "unknown"')
        
        if [[ "$redis_status" == "connected" || "$redis_status" == "ok" ]]; then
            log_success "Redis conectado (reportado por health check)"
        else
            log_warning "Redis no conectado: $redis_status"
        fi
    else
        # Intentar verificar directamente si estamos en el servidor
        if command -v docker &> /dev/null && docker ps | grep -q "ats_redis"; then
            if docker exec ats_redis redis-cli ping > /dev/null 2>&1; then
                log_success "Redis respondiendo (verificación directa)"
            else
                log_warning "No se pudo verificar Redis directamente"
            fi
        else
            log_warning "No se pudo verificar conectividad a Redis desde este host"
        fi
    fi
    
    return 0
}

check_ssl_tls() {
    log_section "SSL/TLS CHECK"
    
    # Solo verificar si usamos HTTPS
    if [[ ! "$ENDPOINT" =~ ^https:// ]]; then
        log_warning "Endpoint no usa HTTPS - se recomienda SSL/TLS en producción"
        return 0
    fi
    
    log_info "Verificando configuración SSL/TLS..."
    
    local host
    host=$(echo "$ENDPOINT" | sed 's|https://||' | cut -d: -f1 | cut -d/ -f1)
    
    # Verificar certificado
    local cert_info
    cert_info=$(echo | openssl s_client -connect "${host}:443" -servername "$host" 2>/dev/null | openssl x509 -noout -dates -subject 2>/dev/null || echo "")
    
    if [[ -n "$cert_info" ]]; then
        log_success "Certificado SSL válido encontrado"
        
        # Verificar expiración
        local not_after
        not_after=$(echo "$cert_info" | grep "notAfter" | cut -d= -f2)
        if [[ -n "$not_after" ]]; then
            local expiry_epoch
            expiry_epoch=$(date -d "$not_after" +%s 2>/dev/null || echo "0")
            local now_epoch
            now_epoch=$(date +%s)
            local days_until_expiry
            days_until_expiry=$(( (expiry_epoch - now_epoch) / 86400 ))
            
            if [[ $days_until_expiry -lt 30 ]]; then
                log_warning "Certificado SSL expira en $days_until_expiry días"
            else
                log_success "Certificado SSL válido por $days_until_expiry días"
            fi
        fi
    else
        log_warning "No se pudo obtener información del certificado SSL"
    fi
}

check_response_times() {
    log_section "RESPONSE TIME CHECK"
    
    log_info "Midiendo tiempos de respuesta..."
    
    local endpoints=(
        "/api/health"
        "/metrics"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local url="${ENDPOINT}${endpoint}"
        local time_ms
        time_ms=$(curl -s -o /dev/null -w "%{time_total}" --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "999")
        time_ms=$(echo "$time_ms * 1000" | bc 2>/dev/null || echo "${time_ms}000" | cut -c1-5)
        
        local time_int
        time_int=${time_ms%.*}
        
        if [[ $time_int -lt 200 ]]; then
            log_success "${endpoint}: ${time_ms}ms"
        elif [[ $time_int -lt 500 ]]; then
            log_warning "${endpoint}: ${time_ms}ms (moderado)"
        else
            log_error "${endpoint}: ${time_ms}ms (lento)"
        fi
    done
}

check_docker_containers() {
    log_section "DOCKER CONTAINERS CHECK"
    
    if ! command -v docker &> /dev/null; then
        log_info "Docker no disponible, omitiendo verificación de contenedores"
        return 0
    fi
    
    log_info "Verificando estado de contenedores..."
    
    local expected_containers=(
        "ats_backend"
        "ats_postgres"
        "ats_redis"
    )
    
    for container in "${expected_containers[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
            local status
            status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
            local health
            health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no healthcheck")
            
            if [[ "$status" == "running" ]]; then
                if [[ "$health" == "healthy" || "$health" == "no healthcheck" ]]; then
                    log_success "$container: running ($health)"
                else
                    log_warning "$container: running pero $health"
                fi
            else
                log_error "$container: $status"
            fi
        else
            log_warning "$container: no encontrado"
        fi
    done
}

# =============================================================================
# REPORTE
# =============================================================================

generate_report() {
    local status="$1"
    
    if [[ "$JSON_OUTPUT" == true ]]; then
        # Generar JSON
        cat << EOF
{
    "timestamp": "$(date -Iseconds)",
    "endpoint": "$ENDPOINT",
    "status": "$status",
    "summary": {
        "total": $CHECKS_TOTAL,
        "passed": $CHECKS_PASSED,
        "failed": $CHECKS_FAILED,
        "warnings": ${#WARNINGS[@]}
    },
    "errors": $(printf '%s\n' "${ERRORS[@]}" | jq -R . | jq -s .),
    "warnings": $(printf '%s\n' "${WARNINGS[@]}" | jq -R . | jq -s .)
}
EOF
    else
        echo -e "\n${BOLD}${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BOLD}${CYAN}║                    VERIFICATION REPORT                      ║${NC}"
        echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
        echo
        echo "Timestamp: $(date)"
        echo "Endpoint: $ENDPOINT"
        echo
        echo -e "${BOLD}Resultado:${NC}"
        
        if [[ "$status" == "PASSED" ]]; then
            echo -e "  Status: ${GREEN}✓ PASSED${NC}"
        else
            echo -e "  Status: ${RED}✗ FAILED${NC}"
        fi
        
        echo "  Total checks: $CHECKS_TOTAL"
        echo -e "  ${GREEN}Passed:${NC} $CHECKS_PASSED"
        echo -e "  ${RED}Failed:${NC} $CHECKS_FAILED"
        echo -e "  ${YELLOW}Warnings:${NC} ${#WARNINGS[@]}"
        
        if [[ ${#ERRORS[@]} -gt 0 ]]; then
            echo
            echo -e "${RED}${BOLD}Errores:${NC}"
            for err in "${ERRORS[@]}"; do
                echo "  - $err"
            done
        fi
        
        if [[ ${#WARNINGS[@]} -gt 0 ]]; then
            echo
            echo -e "${YELLOW}${BOLD}Advertencias:${NC}"
            for warn in "${WARNINGS[@]}"; do
                echo "  - $warn"
            done
        fi
        
        echo
    fi
    
    # Guardar en archivo si se especificó
    if [[ -n "$REPORT_FILE" ]]; then
        if [[ "$JSON_OUTPUT" == true ]]; then
            generate_report "$status" > "$REPORT_FILE"
        else
            generate_report "$status" | tee "$REPORT_FILE" > /dev/null
        fi
        log_info "Reporte guardado en: $REPORT_FILE"
    fi
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    if [[ "$JSON_OUTPUT" != true ]]; then
        echo -e "${BOLD}${CYAN}"
        echo "╔════════════════════════════════════════════════════════════╗"
        echo "║         ATS Platform - Deployment Verification            ║"
        echo "╚════════════════════════════════════════════════════════════╝"
        echo -e "${NC}"
    fi
    
    parse_args "$@"
    
    log_info "Verificando deployment en: $ENDPOINT"
    
    # Ejecutar todos los checks
    check_health_endpoint
    check_metrics_endpoint
    check_security_headers
    check_exposed_secrets
    check_database_connectivity
    check_redis_connectivity
    check_ssl_tls
    check_response_times
    check_docker_containers
    
    # Determinar resultado
    local status
    if [[ $CHECKS_FAILED -eq 0 ]]; then
        status="PASSED"
    else
        status="FAILED"
    fi
    
    # Generar reporte
    generate_report "$status"
    
    # Retornar código de salida
    if [[ "$status" == "PASSED" ]]; then
        exit 0
    else
        exit 1
    fi
}

main "$@"
