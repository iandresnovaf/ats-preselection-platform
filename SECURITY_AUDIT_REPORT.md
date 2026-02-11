# 🔒 Reporte de Seguridad - ATS Platform

**Fecha:** 2026-02-11  
**Proyecto:** ATS Preselection Platform  
**Revisado por:** Subagente de Seguridad

---

## 📋 Resumen Ejecutivo

El proyecto ATS Platform cuenta con una base de seguridad sólida en términos de arquitectura, pero presenta **vulnerabilidades críticas** que deben solucionarse antes de producción. La mayoría son configuraciones inseguras por defecto y falta de rate limiting.

**Nivel de Riesgo General:** 🔴 **ALTO** (antes de producción)

---

## ✅ Fortalezas de Seguridad Encontradas

### Backend (FastAPI/Python)

| Aspecto | Estado | Descripción |
|---------|--------|-------------|
| **Hashing de Contraseñas** | ✅ | Uso de `passlib` con `bcrypt` - Estándar de la industria |
| **JWT Tokens** | ✅ | Implementación con expiración (30 min access, 7 días refresh) |
| **Encriptación de Datos** | ✅ | Uso de `cryptography.fernet` para credenciales sensibles en BD |
| **Validación de Inputs** | ✅ | Pydantic schemas con validadores estrictos |
| **Role-Based Access Control** | ✅ | Decoradores `require_admin`, `require_consultant` |
| **Soft Delete** | ✅ | Los usuarios se desactivan, no se eliminan (auditoría) |
| **Password Reset Seguro** | ✅ | No revela si el email existe; tokens con expiración de 1 hora |
| **SQL Injection Prevention** | ✅ | Uso de SQLAlchemy ORM con parámetros parametrizados |
| **Audit Logging** | ✅ | Modelo `AuditLog` para trazabilidad |
| **CORS Configurado** | ✅ | Orígenes permitidos configurables vía env |

### Frontend (Next.js/TypeScript)

| Aspecto | Estado | Descripción |
|---------|--------|-------------|
| **Protección de Rutas** | ✅ | Componente `ProtectedRoute` con verificación de roles |
| **Validación de Forms** | ✅ | React Hook Form + Zod para validación client-side |
| **Sanitización de Inputs** | ✅ | Uso de tipos TypeScript estrictos |
| **Manejo de Errores** | ✅ | No expone detalles sensibles en errores |
| **Token Expiration Check** | ✅ | Verificación de expiración en cliente (`isTokenValid`) |

### Base de Datos

| Aspecto | Estado | Descripción |
|---------|--------|-------------|
| **Credenciales Encriptadas** | ✅ | Configuraciones sensibles cifradas con Fernet |
| **UUID como PK** | ✅ | Uso de UUID v4 en lugar de IDs secuenciales |
| **Constraints** | ✅ | Unique constraints en emails, índices en campos buscados |

---

## ⚠️ Vulnerabilidades y Riesgos Identificados

### 🚨 CRÍTICO - Debe solucionarse antes de producción

#### 1. SECRET_KEY Hardcodeada en Archivo .env
**Archivo:** `backend/.env`
```bash
SECRET_KEY=ats-platform-secret-key-for-development-only-change-in-production
```
**Riesgo:** Alta - Compromiso total de sesiones JWT si se filtra el código  
**Impacto:** Un atacante puede generar tokens válidos para cualquier usuario  
**Solución:** Generar clave segura de 32+ bytes en producción; nunca commitar a git

#### 2. Contraseña de Admin Default Expuesta
**Archivo:** `backend/.env`
```bash
DEFAULT_ADMIN_PASSWORD=ChangeMe123!
```
**Riesgo:** Crítico - Acceso no autorizado al sistema  
**Impacto:** Cualquiera puede hacer login como admin con estas credenciales  
**Solución:** Requerir configuración de contraseña en primer setup; generar password aleatoria

#### 3. Almacenamiento de Tokens en localStorage
**Archivos:** `frontend/src/store/auth.ts`, `frontend/src/services/api.ts`
```typescript
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('refresh_token', response.refresh_token);
```
**Riesgo:** Alto - Vulnerable a ataques XSS  
**Impacto:** Un script malicioso puede robar tokens y suplantar identidad  
**Solución:** Usar cookies `httpOnly`, `Secure`, `SameSite=Strict`

#### 4. Sin Rate Limiting
**Archivo:** `backend/app/main.py` y endpoints de autenticación  
**Riesgo:** Crítico - Vulnerable a ataques de fuerza bruta  
**Impacto:** Ataques de diccionario, credential stuffing, DoS  
**Solución:** Implementar `slowapi` o `fastapi-limiter` con Redis

#### 5. CORS Excesivamente Permisivo
**Archivo:** `backend/app/main.py`
```python
allow_methods=["*"],
allow_headers=["*"],
```
**Riesgo:** Medio-Alto - Exposición a CSRF y otros ataques  
**Impacto:** Orígenes no autorizados pueden hacer peticiones  
**Solución:** Especificar métodos y headers explícitamente

---

### 🔶 ALTO - Recomendado solucionar antes de producción

#### 6. Sin Headers de Seguridad HTTP
**Faltan:**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy`

**Archivo:** `backend/app/main.py`  
**Solución:** Agregar middleware con `fastapi-security-headers` o manualmente

#### 7. Sin Validación de Fortaleza de Contraseña en Backend
**Archivo:** `backend/app/schemas/__init__.py`
```python
password: str = Field(..., min_length=8)  # Solo longitud mínima
```
**Riesgo:** Usuarios pueden usar passwords débiles como "Password1"  
**Solución:** Implementar validación de complejidad (mayúsculas, minúsculas, números, símbolos)

#### 8. Sin Protección CSRF Explícita
**Estado actual:** El middleware CORS permite credenciales pero no hay tokens CSRF  
**Riesgo:** Medio - Vulnerable a ataques CSRF si el token es robado  
**Solución:** Implementar doble cookie pattern o CSRF tokens para mutaciones

#### 9. Logs de Password Reset Expuestos
**Archivo:** `backend/app/api/auth.py`
```python
print(f"[PASSWORD RESET] Token para {data.email}: {reset_token}")
```
**Riesgo:** Los tokens de reseteo quedan en logs  
**Impacto:** Si los logs se filtran, los tokens pueden ser reutilizados  
**Solución:** Eliminar logs de tokens; usar sistema de email real

#### 10. Sin Rate Limiting en Endpoints de Configuración
**Archivo:** `backend/app/api/config.py`  
**Riesgo:** Posible enumeración de configuraciones sensibles  
**Solución:** Rate limiting por IP y/o por usuario

---

### 🔸 MEDIO - Mejoras recomendadas

#### 11. Timeout de Token de Refresh Largo
**Archivo:** `backend/app/core/config.py`
```python
REFRESH_TOKEN_EXPIRE_DAYS: int = 7
```
**Recomendación:** Reducir a 1-3 días; implementar rotación de refresh tokens

#### 12. Sin Blacklist de Tokens en Logout
**Archivo:** `backend/app/api/auth.py` - función `logout`
```python
# TODO: Agregar a blacklist en Redis
```
**Recomendación:** Implementar invalidación de tokens en Redis

#### 13. Validación de Archivos de Upload Limitada
**Archivo:** `backend/app/core/config.py`
```python
MAX_FILE_SIZE: int = 10485760  # 10MB
```
**Falta:** Validación de tipo MIME/extensiones permitidas  
**Riesgo:** Posible subida de archivos maliciosos  
**Solución:** Validar extensiones (.pdf, .doc, .docx) y magic numbers

#### 14. Sin Sanitización de Output HTML
**Riesgo:** Si se renderiza contenido dinámico del usuario, puede haber XSS  
**Solución:** Usar `bleach` o `html-sanitizer` para contenido HTML

#### 15. Sin Limitación de Tamaño de Payload
**Riesgo:** Posible ataque de denegación de servicio con payloads grandes  
**Solución:** Configurar límite en nginx o middleware FastAPI

---

## 🔧 Recomendaciones para Mejorar

### Backend

1. **Implementar Rate Limiting** (Prioridad: Alta)
   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address
   
   limiter = Limiter(key_func=get_remote_address)
   app = FastAPI()
   app.state.limiter = limiter
   
   @router.post("/login")
   @limiter.limit("5/minute")
   async def login(...)
   ```

2. **Agregar Headers de Seguridad**
   ```python
   from fastapi.middleware.trustedhost import TrustedHostMiddleware
   from fastapi.middleware.cors import CORSMiddleware
   
   # Security headers middleware
   @app.middleware("http")
   async def security_headers(request, call_next):
       response = await call_next(request)
       response.headers["X-Content-Type-Options"] = "nosniff"
       response.headers["X-Frame-Options"] = "DENY"
       response.headers["X-XSS-Protection"] = "1; mode=block"
       response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
       return response
   ```

3. **Validación de Contraseña Robusta**
   ```python
   import re
   from pydantic import validator
   
   @field_validator('password')
   def validate_password(cls, v):
       if len(v) < 8:
           raise ValueError('Password must be at least 8 characters')
       if not re.search(r'[A-Z]', v):
           raise ValueError('Password must contain uppercase letter')
       if not re.search(r'[a-z]', v):
           raise ValueError('Password must contain lowercase letter')
       if not re.search(r'\d', v):
           raise ValueError('Password must contain digit')
       if not re.search(r'[!@#$%^&*]', v):
           raise ValueError('Password must contain special character')
       return v
   ```

4. **Configuración de CORS Más Estricta**
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],  # Específico
       allow_credentials=True,
       allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Específico
       allow_headers=["Authorization", "Content-Type"],  # Específico
       expose_headers=["X-Request-ID"],
       max_age=600,
   )
   ```

### Frontend

1. **Migrar a Cookies httpOnly** (Prioridad: Crítica)
   ```typescript
   // En lugar de localStorage
   document.cookie = `access_token=${token}; HttpOnly; Secure; SameSite=Strict; Max-Age=1800`;
   ```
   *Nota: Esto requiere cambios en el backend para leer cookies*

2. **Implementar Content Security Policy**
   ```typescript
   // next.config.js
   async headers() {
     return [{
       source: '/:path*',
       headers: [
         {
           key: 'Content-Security-Policy',
           value: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
         }
       ]
     }]
   }
   ```

3. **Sanitizar Contenido Dinámico**
   ```typescript
   import DOMPurify from 'dompurify';
   
   const sanitized = DOMPurify.sanitize(userInput);
   ```

### Infraestructura

1. **Variables de Entorno en Producción**
   - Usar AWS Secrets Manager, Azure Key Vault, o HashiCorp Vault
   - Nunca commitar archivos `.env` con secrets reales
   - Rotar secrets periódicamente

2. **HTTPS/TLS**
   - Forzar HTTPS en producción
   - Usar certificados válidos (Let's Encrypt)
   - Configurar HSTS

3. **WAF (Web Application Firewall)**
   - Considerar Cloudflare, AWS WAF, o mod_security

4. **Logging y Monitoreo**
   - Implementar SIEM para detectar intentos de intrusión
   - Alertas para múltiples intentos de login fallidos
   - Logs de auditoría para cambios críticos

---

## 🚨 Issues Críticos - Checklist Pre-Producción

- [ ] **Cambiar SECRET_KEY** - Generar nueva clave de 32+ bytes aleatorios
- [ ] **Eliminar/Eliminar DEFAULT_ADMIN_PASSWORD** - Requerir setup inicial seguro
- [ ] **Implementar Rate Limiting** - En login, forgot-password, y endpoints sensibles
- [ ] **Migrar tokens a cookies httpOnly** - Eliminar localStorage para tokens
- [ ] **Agregar headers de seguridad** - X-Frame-Options, HSTS, CSP
- [ ] **Validación de contraseña robusta** - Backend debe validar complejidad
- [ ] **Eliminar logs de tokens** - No loggear tokens de reset de password
- [ ] **CORS restrictivo** - Especificar orígenes, métodos y headers exactos
- [ ] **Configurar HTTPS** - TLS 1.2+ obligatorio
- [ ] **Validación de uploads** - Whitelist de extensiones y tipos MIME
- [ ] **Blacklist de tokens** - Implementar logout efectivo con Redis
- [ ] **Review de dependencias** - `pip-audit` y `npm audit`

---

## 📊 Matriz de Riesgos

| Vulnerabilidad | Severidad | Probabilidad | Impacto | Esfuerzo de Fix |
|----------------|-----------|--------------|---------|-----------------|
| SECRET_KEY hardcodeada | 🔴 Crítico | Alta | Total | Bajo |
| Admin password default | 🔴 Crítico | Alta | Total | Bajo |
| Tokens en localStorage | 🔴 Crítico | Media | Alto | Medio |
| Sin rate limiting | 🔴 Crítico | Alta | Alto | Bajo |
| CORS permisivo | 🟠 Alto | Media | Medio | Bajo |
| Sin security headers | 🟠 Alto | Baja | Medio | Bajo |
| Password débil permitida | 🟠 Alto | Alta | Medio | Bajo |
| Logs de tokens | 🟠 Alto | Baja | Alto | Bajo |
| Refresh token 7 días | 🟡 Medio | Baja | Medio | Bajo |
| Sin blacklist tokens | 🟡 Medio | Media | Medio | Medio |
| Upload sin validación | 🟡 Medio | Media | Medio | Bajo |

---

## 📚 Referencias

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Next.js Security Headers](https://nextjs.org/docs/advanced-features/security-headers)
- [CSP Quick Reference](https://content-security-policy.com/)

---

**Nota:** Este reporte debe revisarse y actualizarse periódicamente. La seguridad es un proceso continuo, no un estado final.
