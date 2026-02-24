#!/bin/bash
# ============================================================
# SCRIPT: Generar certificados SSL para PostgreSQL
# ATS Platform
# ============================================================

set -euo pipefail

# ============================================================
# CONFIGURACIÓN
# ============================================================

SSL_DIR="${SSL_DIR:-./ssl}"
DAYS_VALID="${DAYS_VALID:-365}"
KEY_SIZE="${KEY_SIZE:-4096}"

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
# CREAR DIRECTORIO SSL
# ============================================================

log "Creando directorio SSL: $SSL_DIR"
mkdir -p "$SSL_DIR"
cd "$SSL_DIR"

# ============================================================
# GENERAR AUTORIDAD CERTIFICADORA (CA)
# ============================================================

log "Generando Autoridad Certificadora (CA)..."

# Generar clave privada de CA
openssl genrsa -out ca.key "$KEY_SIZE" 2>/dev/null || error_exit "No se pudo generar ca.key"

# Generar certificado CA autofirmado
openssl req -new -x509 -days "$DAYS_VALID" -key ca.key -out ca.crt \
    -subj "/C=CO/ST=Bogota/L=Bogota/O=ATS Platform/CN=ATS Platform Root CA" \
    2>/dev/null || error_exit "No se pudo generar ca.crt"

log "CA generada: ca.crt, ca.key"

# ============================================================
# GENERAR CERTIFICADO DEL SERVIDOR (PostgreSQL)
# ============================================================

log "Generando certificado del servidor PostgreSQL..."

# Generar clave privada del servidor
openssl genrsa -out server.key "$KEY_SIZE" 2>/dev/null || error_exit "No se pudo generar server.key"

# Generar CSR (Certificate Signing Request)
openssl req -new -key server.key -out server.csr \
    -subj "/C=CO/ST=Bogota/L=Bogota/O=ATS Platform/CN=postgres" \
    2>/dev/null || error_exit "No se pudo generar server.csr"

# Firmar el certificado con la CA
openssl x509 -req -days "$DAYS_VALID" -in server.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out server.crt 2>/dev/null || error_exit "No se pudo firmar server.crt"

# Ajustar permisos (PostgreSQL requiere permisos estrictos)
chmod 600 server.key
chmod 644 server.crt

log "Certificado del servidor generado: server.crt, server.key"

# ============================================================
# GENERAR CERTIFICADO DEL CLIENTE (opcional)
# ============================================================

log "Generando certificado del cliente..."

# Generar clave privada del cliente
openssl genrsa -out client.key "$KEY_SIZE" 2>/dev/null || error_exit "No se pudo generar client.key"

# Generar CSR del cliente
openssl req -new -key client.key -out client.csr \
    -subj "/C=CO/ST=Bogota/L=Bogota/O=ATS Platform/CN=ats_client" \
    2>/dev/null || error_exit "No se pudo generar client.csr"

# Firmar el certificado del cliente
openssl x509 -req -days "$DAYS_VALID" -in client.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out client.crt 2>/dev/null || error_exit "No se pudo firmar client.crt"

chmod 600 client.key
chmod 644 client.crt

log "Certificado del cliente generado: client.crt, client.key"

# ============================================================
# LIMPIAR ARCHIVOS TEMPORALES
# ============================================================

rm -f server.csr client.csr ca.srl

# ============================================================
# VERIFICAR CERTIFICADOS
# ============================================================

log "Verificando certificados..."

# Verificar certificado del servidor
if openssl x509 -in server.crt -text -noout | grep -q "Issuer:.*ATS Platform Root CA"; then
    log "✅ Certificado del servidor verificado"
else
    error_exit "Certificado del servidor inválido"
fi

# Verificar certificado del cliente
if openssl x509 -in client.crt -text -noout | grep -q "Issuer:.*ATS Platform Root CA"; then
    log "✅ Certificado del cliente verificado"
else
    error_exit "Certificado del cliente inválido"
fi

# ============================================================
# RESUMEN
# ============================================================

cat <<EOF

============================================================
CERTIFICADOS SSL GENERADOS EXITOSAMENTE
============================================================
Directorio: $SSL_DIR

Archivos generados:
  - ca.crt          : Certificado de la Autoridad Certificadora
  - ca.key          : Clave privada de la CA (guardar en lugar seguro)
  - server.crt      : Certificado del servidor PostgreSQL
  - server.key      : Clave privada del servidor
  - client.crt      : Certificado del cliente (opcional)
  - client.key      : Clave privada del cliente

Permisos:
  - Claves privadas (.key): 600 (solo propietario)
  - Certificados (.crt): 644 (lectura pública)

Vigencia: $DAYS_VALID días

USO EN DOCKER COMPOSE:
======================
1. Copiar certificados al volumen de PostgreSQL:
   docker cp $SSL_DIR/server.crt ats_postgres:/var/lib/postgresql/ssl/
   docker cp $SSL_DIR/server.key ats_postgres:/var/lib/postgresql/ssl/
   docker cp $SSL_DIR/ca.crt ats_postgres:/var/lib/postgresql/ssl/

2. Reiniciar PostgreSQL con SSL habilitado

3. Configurar aplicación para usar SSL:
   DATABASE_URL=postgresql+asyncpg://user:pass@postgres/db?ssl=require

USO EN CLIENTES:
================
Para conectarse con verificación de certificado:
  psql "host=postgres port=5432 dbname=ats_platform user=ats_app sslmode=require"

Para conectarse con certificado de cliente (máxima seguridad):
  psql "host=postgres port=5432 dbname=ats_platform user=ats_app \\
        sslmode=verify-ca sslrootcert=ca.crt \\
        sslcert=client.crt sslkey=client.key"

============================================================

EOF

log "Generación de certificados completada"
exit 0
