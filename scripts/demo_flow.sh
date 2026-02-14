#!/bin/bash
#
# Script de Demo - Flujo Crítico ATS Platform
# Este script automatiza el flujo crítico para demostraciones rápidas
#

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
API_URL="${API_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@topmanagement.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-ChangeMe123!}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       ATS Platform - Demo Script (Flujo Crítico)         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar dependencias
command -v curl >/dev/null 2>&1 || { echo -e "${RED}Error: curl es requerido${NC}"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo -e "${YELLOW}Advertencia: jq no instalado, usando grep/sed${NC}"; }

# ============================================================
# PASO 0: Verificar servicios disponibles
# ============================================================
echo -e "${YELLOW}Paso 0: Verificando servicios...${NC}"

# Verificar backend
if curl -s "${API_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend disponible en ${API_URL}${NC}"
else
    echo -e "${RED}✗ Backend no responde en ${API_URL}${NC}"
    echo "  Inicie el backend: cd backend && uvicorn app.main:app --reload"
    exit 1
fi

# Verificar frontend (opcional)
if curl -s "${FRONTEND_URL}" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend disponible en ${FRONTEND_URL}${NC}"
else
    echo -e "${YELLOW}! Frontend no responde (opcional para API demo)${NC}"
fi

echo ""

# ============================================================
# PASO 1: Login
# ============================================================
echo -e "${YELLOW}Paso 1: Autenticación...${NC}"

LOGIN_RESPONSE=$(curl -s -c /tmp/ats_cookies.txt -X POST "${API_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" 2>/dev/null)

if echo "$LOGIN_RESPONSE" | grep -q "access_token\|user"; then
    echo -e "${GREEN}✓ Login exitoso como ${ADMIN_EMAIL}${NC}"
else
    echo -e "${RED}✗ Login fallido${NC}"
    echo "  Respuesta: $LOGIN_RESPONSE"
    exit 1
fi

# Obtener token para requests posteriores
TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | sed 's/"access_token":"//;s/"$//')
echo ""

# ============================================================
# PASO 2: Verificar datos actuales
# ============================================================
echo -e "${YELLOW}Paso 2: Obteniendo datos actuales...${NC}"

# Obtener jobs existentes
JOBS_RESPONSE=$(curl -s -b /tmp/ats_cookies.txt "${API_URL}/api/v1/jobs" 2>/dev/null)
JOB_COUNT=$(echo "$JOBS_RESPONSE" | grep -o '"id"' | wc -l)
echo -e "  Jobs existentes: ${JOB_COUNT}"

# Obtener candidates existentes
CANDIDATES_RESPONSE=$(curl -s -b /tmp/ats_cookies.txt "${API_URL}/api/v1/candidates" 2>/dev/null)
CANDIDATE_COUNT=$(echo "$CANDIDATES_RESPONSE" | grep -o '"id"' | wc -l)
echo -e "  Candidatos existentes: ${CANDIDATE_COUNT}"

# Obtener matches
MATCHES_RESPONSE=$(curl -s -b /tmp/ats_cookies.txt "${API_URL}/api/v1/matches" 2>/dev/null)
MATCH_COUNT=$(echo "$MATCHES_RESPONSE" | grep -o '"id"' | wc -l)
echo -e "  Matches existentes: ${MATCH_COUNT}"

echo ""

# ============================================================
# PASO 3: Crear Job de prueba
# ============================================================
echo -e "${YELLOW}Paso 3: Creando oferta de trabajo de prueba...${NC}"

JOB_DATA='{
    "title": "Senior Software Engineer - Demo",
    "description": "Buscamos un Senior Software Engineer con experiencia en React, Node.js y AWS. Responsabilidades: Diseñar y desarrollar aplicaciones web escalables, liderar equipo de desarrollo, code reviews.",
    "department": "Engineering",
    "location": "Remoto / Madrid",
    "seniority": "Senior",
    "sector": "Technology",
    "required_skills": ["React", "Node.js", "AWS", "TypeScript", "PostgreSQL"],
    "min_years_experience": 5,
    "education_level": "bachelor",
    "employment_type": "full-time",
    "salary_min": 50000,
    "salary_max": 80000
}'

JOB_RESPONSE=$(curl -s -b /tmp/ats_cookies.txt -X POST "${API_URL}/api/v1/jobs" \
    -H "Content-Type: application/json" \
    -d "$JOB_DATA" 2>/dev/null)

if echo "$JOB_RESPONSE" | grep -q '"id"'; then
    JOB_ID=$(echo "$JOB_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | sed 's/"id":"//;s/"$//')
    echo -e "${GREEN}✓ Job creado con ID: ${JOB_ID}${NC}"
else
    echo -e "${RED}✗ Error creando job${NC}"
    echo "  Respuesta: $JOB_RESPONSE"
    exit 1
fi

echo ""

# ============================================================
# PASO 4: Crear Candidato de prueba
# ============================================================
echo -e "${YELLOW}Paso 4: Creando candidato de prueba...${NC}"

CANDIDATE_DATA="{
    \"first_name\": \"Juan\",
    \"last_name\": \"García\",
    \"email\": \"juan.garcia.demo$(date +%s)@example.com\",
    \"phone\": \"+34612345678\",
    \"job_opening_id\": \"${JOB_ID}\",
    \"source\": \"manual\",
    \"years_experience\": 6,
    \"current_company\": "TechCorp",
    \"current_position\": "Software Developer",
    \"skills\": [\"React\", \"Node.js\", \"AWS\", \"JavaScript\", \"Docker\"]
}"

CANDIDATE_RESPONSE=$(curl -s -b /tmp/ats_cookies.txt -X POST "${API_URL}/api/v1/candidates" \
    -H "Content-Type: application/json" \
    -d "$CANDIDATE_DATA" 2>/dev/null)

if echo "$CANDIDATE_RESPONSE" | grep -q '"id"'; then
    CANDIDATE_ID=$(echo "$CANDIDATE_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | sed 's/"id":"//;s/"$//')
    echo -e "${GREEN}✓ Candidato creado con ID: ${CANDIDATE_ID}${NC}"
else
    echo -e "${RED}✗ Error creando candidato${NC}"
    echo "  Respuesta: $CANDIDATE_RESPONSE"
    exit 1
fi

echo ""

# ============================================================
# PASO 5: Ejecutar Matching
# ============================================================
echo -e "${YELLOW}Paso 5: Ejecutando matching...${NC}"

MATCH_DATA="{
    \"candidate_id\": \"${CANDIDATE_ID}\",
    \"job_opening_id\": \"${JOB_ID}\"
}"

MATCH_RESPONSE=$(curl -s -b /tmp/ats_cookies.txt -X POST "${API_URL}/api/v1/matches/evaluate" \
    -H "Content-Type: application/json" \
    -d "$MATCH_DATA" 2>/dev/null)

if echo "$MATCH_RESPONSE" | grep -q '"score"\|"match"'; then
    echo -e "${GREEN}✓ Matching completado${NC}"
    
    # Extraer datos del match
    SCORE=$(echo "$MATCH_RESPONSE" | grep -o '"score":[0-9.]*' | head -1 | cut -d: -f2)
    DECISION=$(echo "$MATCH_RESPONSE" | grep -o '"decision":"[^"]*"' | head -1 | sed 's/"decision":"//;s/"$//')
    
    echo -e "  Score: ${SCORE:-N/A}"
    echo -e "  Decisión: ${DECISION:-N/A}"
else
    echo -e "${YELLOW}! Matching no completado (posiblemente LLM no configurado)${NC}"
    echo "  Respuesta: $MATCH_RESPONSE"
fi

echo ""

# ============================================================
# PASO 6: Obtener Matches
# ============================================================
echo -e "${YELLOW}Paso 6: Verificando matches...${NC}"

MATCHES_RESPONSE=$(curl -s -b /tmp/ats_cookies.txt "${API_URL}/api/v1/matches?job_opening_id=${JOB_ID}" 2>/dev/null)
NEW_MATCH_COUNT=$(echo "$MATCHES_RESPONSE" | grep -o '"id"' | wc -l)
echo -e "  Total matches para este job: ${NEW_MATCH_COUNT}"

echo ""

# ============================================================
# PASO 7: Dashboard Stats
# ============================================================
echo -e "${YELLOW}Paso 7: Obteniendo estadísticas del dashboard...${NC}"

STATS_RESPONSE=$(curl -s -b /tmp/ats_cookies.txt "${API_URL}/api/v1/dashboard/stats" 2>/dev/null)
echo "  Respuesta: $STATS_RESPONSE"

echo ""

# ============================================================
# PASO 8: Cleanup opcional
# ============================================================
echo -e "${YELLOW}Paso 8: Limpieza (opcional)...${NC}"

if [ "${CLEANUP:-false}" = "true" ]; then
    echo "  Eliminando datos de prueba..."
    
    # Eliminar candidato
    curl -s -b /tmp/ats_cookies.txt -X DELETE "${API_URL}/api/v1/candidates/${CANDIDATE_ID}" > /dev/null 2>&1
    echo "    Candidato eliminado"
    
    # Eliminar job
    curl -s -b /tmp/ats_cookies.txt -X DELETE "${API_URL}/api/v1/jobs/${JOB_ID}" > /dev/null 2>&1
    echo "    Job eliminado"
    
    echo -e "${GREEN}✓ Limpieza completada${NC}"
else
    echo "  Omitiendo limpieza (set CLEANUP=true para eliminar)"
fi

echo ""

# ============================================================
# RESUMEN
# ============================================================
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     RESUMEN DEMO                         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓ Flujo crítico completado:${NC}"
echo "  1. Login exitoso"
echo "  2. Job creado: ${JOB_ID}"
echo "  3. Candidato creado: ${CANDIDATE_ID}"
echo "  4. Matching ejecutado"
echo ""
echo -e "${YELLOW}URLs para acceder:${NC}"
echo "  Frontend: ${FRONTEND_URL}"
echo "  API Docs: ${API_URL}/api/docs"
echo "  Job: ${FRONTEND_URL}/dashboard/jobs/${JOB_ID}"
echo "  Matching: ${FRONTEND_URL}/dashboard/matching?job=${JOB_ID}"
echo ""
echo -e "${BLUE}Credenciales:${NC}"
echo "  Email: ${ADMIN_EMAIL}"
echo "  Password: ${ADMIN_PASSWORD}"
echo ""
echo -e "${GREEN}Demo completada exitosamente!${NC}"

# Cleanup de cookies
rm -f /tmp/ats_cookies.txt
