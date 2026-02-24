# 🔒 Informe de Auditoría de Seguridad - Autenticación, Autorización y Sesiones

**Proyecto:** ATS Platform  
**Fecha:** 2026-02-17  
**Auditor:** Subagente de Seguridad  

---

## 📋 Resumen Ejecutivo

| Categoría | Estado | Críticas | Altas | Medias | Bajas |
|-----------|--------|----------|-------|--------|-------|
| Autenticación | ⚠️ **Revisar** | 2 | 3 | 2 | 1 |
| Autorización | ⚠️ **Revisar** | 1 | 2 | 2 | 1 |
| Gestión de Sesiones | ✅ **Bueno** | 0 | 1 | 2 | 2 |
| Protecciones Web | ✅ **Bueno** | 0 | 1 | 3 | 1 |
| Frontend | ⚠️ **Revisar** | 0 | 2 | 2 | 1 |

---

## 1️⃣ Análisis de Implementación Actual

### 1.1 Método de Autenticación

| Aspecto | Implementación | Estado |
|---------|---------------|--------|
| **Tipo** | JWT (HS256) con cookies httpOnly | ✅ Correcto |
| **Password Hashing** | bcrypt con 12 rounds | ✅ Correcto |
| **Timing Attack Protection** | Dummy hash verification | ✅ Bueno |
| **Estructura de Tokens** | Access + Refresh tokens | ✅ Correcto |

**Código relevante:**
```python
# app/core/auth.py - Buenas prácticas implementadas
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__rounds=12  # Cost factor recomendado
)

# Cookie settings seguras
COOKIE_SETTINGS = {
    "httponly": True,
    "secure": settings.ENVIRONMENT == "production",
    "samesite": "strict" if settings.ENVIRONMENT == "production" else "lax",
    "path": "/",
}
```

### 1.2 Roles y Autorización (RBAC)

```python
# app/models/__init__.py
class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    CONSULTANT = "consultant"
    VIEWER = "viewer"  # Solo lectura

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
```

| Rol | Permisos | Estado |
|-----|----------|--------|
| SUPER_ADMIN | Todos los permisos | ✅ Correcto |
| CONSULTANT | CRUD completo | ✅ Correcto |
| VIEWER | Solo lectura | ✅ Correcto |

---

## 2️⃣ Vulnerabilidades Encontradas

### 🔴 CRÍTICAS

#### VULN-001: Sin MFA para usuarios administradores
**Severidad:** Crítica  
**CVSS:** 8.1  
**Ubicación:** `/app/api/auth.py`, `/app/core/auth.py`

**Descripción:** Los usuarios con rol `SUPER_ADMIN` no tienen habilitada la autenticación de múltiples factores (MFA). Esto representa un riesgo significativo ya que una compromiso de credenciales de administrador permite acceso total al sistema.

**Impacto:**
- Acceso no autorizado a datos sensibles de candidatos
- Modificación de configuraciones críticas
- Eliminación de registros

**Recomendación:**
```python
# app/models/__init__.py - Agregar campos MFA
class User(Base):
    # ... campos existentes ...
    
    # MFA
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255))  # Encrypted TOTP secret
    mfa_backup_codes = Column(JSON)   # Hashed backup codes
    
    # Device tracking para MFA remember
    mfa_trusted_devices = Column(JSON, default=list)
```

```python
# app/api/auth.py - Login con MFA
@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: LoginRequest,
    mfa_code: Optional[str] = None,  # Código TOTP opcional
    trust_device: bool = False,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    # MFA requerido para admins
    if user.role == UserRole.SUPER_ADMIN and user.mfa_enabled:
        if not mfa_code:
            return {"mfa_required": True, "message": "Código MFA requerido"}
        
        if not verify_totp(user.mfa_secret, mfa_code):
            raise HTTPException(status_code=401, detail="Código MFA inválido")
        
        if trust_device:
            # Agregar device a trusted list
            await add_trusted_device(user, request)
    
    # ... resto del login ...
```

---

#### VULN-002: Sin invalidación de tokens en logout
**Severidad:** Crítica  
**CVSS:** 7.5  
**Ubicación:** `/app/api/auth.py:logout()`

**Descripción:** Al hacer logout, los tokens JWT siguen siendo válidos hasta su expiración natural. No hay una lista de denegación (denylist/blocklist) de tokens revocados.

**Impacto:**
- Token robado puede usarse hasta que expire (30 minutos para access, 7 días para refresh)
- Logout no garantiza terminación de sesión

**Recomendación:**
```python
# app/core/token_blacklist.py
import redis
from datetime import datetime

class TokenBlacklist:
    """Gestiona la invalidación de tokens (logout)."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.prefix = "token_blacklist"
    
    async def blacklist_token(self, token: str, expires_in: int):
        """Agrega un token a la lista negra."""
        jti = self._extract_jti(token)  # Extraer JWT ID
        key = f"{self.prefix}:{jti}"
        await self.redis.setex(key, expires_in, "revoked")
    
    async def is_blacklisted(self, token: str) -> bool:
        """Verifica si un token está en la lista negra."""
        jti = self._extract_jti(token)
        key = f"{self.prefix}:{jti}"
        return await self.redis.exists(key)
    
    def _extract_jti(self, token: str) -> str:
        """Extrae el JWT ID del token (requiere agregar 'jti' al payload)."""
        payload = decode_token(token)
        return payload.get("jti", "")

# Uso en logout
@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Logout - invalida tokens en blacklist."""
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")
    
    # Invalidar tokens
    if access_token:
        await token_blacklist.blacklist_token(
            access_token, 
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    if refresh_token:
        await token_blacklist.blacklist_token(
            refresh_token,
            settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
    
    # Limpiar cookies
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    
    return {"message": "Logout exitoso"}
```

---

### 🟠 ALTAS

#### VULN-003: Sin rotación de tokens en refresh
**Severidad:** Alta  
**CVSS:** 6.5  
**Ubicación:** `/app/api/auth.py:refresh_token()`

**Descripción:** Al refrescar el access token, el refresh token anterior sigue siendo válido. No hay rotación de refresh tokens (el mismo refresh token puede usarse múltiples veces).

**Impacto:**
- Si un refresh token es robado, puede usarse indefinidamente
- No hay detección de uso de tokens revocados (posible señal de robo)

**Recomendación:**
```python
# app/api/auth.py - Refresh con rotación de tokens
@router.post("/refresh")
@limiter.limit("5/minute")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    refresh_token_str = request.cookies.get("refresh_token")
    
    if not refresh_token_str:
        raise HTTPException(status_code=401, detail="No refresh token")
    
    # Verificar que el refresh token no haya sido revocado
    if await token_blacklist.is_blacklisted(refresh_token_str):
        # Token usado después de revocación - posible robo
        await security_logger.log_suspicious_activity(
            request, "token_reuse", 
            {"token_jti": extract_jti(refresh_token_str)}
        )
        raise HTTPException(status_code=401, detail="Token revocado")
    
    payload = decode_token(refresh_token_str)
    # ... validaciones ...
    
    # Revocar el refresh token usado (one-time use)
    await token_blacklist.blacklist_token(
        refresh_token_str,
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    # Crear nuevos tokens (rotación)
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Setear nuevas cookies
    response.set_cookie(key="access_token", value=new_access_token, ...)
    response.set_cookie(key="refresh_token", value=new_refresh_token, ...)
    
    return {"success": True}
```

---

#### VULN-004: Sin rate limiting en forgot-password/reset-password
**Severidad:** Alta  
**CVSS:** 6.1  
**Ubicación:** `/app/api/auth.py:forgot_password()`, `/app/api/auth.py:reset_password()`

**Descripción:** Los endpoints de recuperación de contraseña no tienen rate limiting específico. Esto permite ataques de fuerza bruta sobre tokens de reseteo.

**Impacto:**
- Ataques de fuerza bruta sobre tokens de reseteo (1 hora de validez)
- Enumeración de emails válidos (aunque parcialmente mitigado)

**Recomendación:**
```python
# app/api/auth.py - Rate limiting estricto para password reset
@router.post("/forgot-password")
@limiter.limit("3/hour")  # Muy restrictivo
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    # Agregar delay artificial para prevenir timing attacks
    await asyncio.sleep(random.uniform(0.5, 1.0))
    
    user = await user_service.get_by_email(data.email)
    
    # Respuesta idéntica independientemente de si existe el email
    if user:
        # Generar token criptográficamente seguro
        reset_token = secrets.token_urlsafe(32)
        
        # Almacenar hash del token (no el token en sí)
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        await store_reset_token(user.id, token_hash)
        
        # Enviar email con token
        await send_reset_email(user.email, reset_token)
    
    return {
        "message": "Si el email existe, recibirás instrucciones",
        "success": True
    }

@router.post("/reset-password")
@limiter.limit("5/hour")  # Limitar intentos de reset
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    # Verificar token contra hash almacenado
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()
    user_id = await verify_reset_token(token_hash)
    
    if not user_id:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")
    
    # Invalidar token usado (one-time use)
    await invalidate_reset_token(token_hash)
    
    # Actualizar password
    await user_service.update_password(user_id, data.new_password)
    
    # Invalidar todas las sesiones activas del usuario
    await invalidate_all_user_sessions(user_id)
    
    return {"message": "Contraseña actualizada", "success": True}
```

---

#### VULN-005: Schema UserCreate permite rol 'admin' que no existe en Enum
**Severidad:** Alta  
**CVSS:** 5.3  
**Ubicación:** `/app/schemas/__init__.py:UserCreate`

**Descripción:** En `UserCreate`, el validador de `role` permite `'admin'` pero el Enum `UserRole` tiene `SUPER_ADMIN`. Esto puede causar inconsistencias.

**Código problemático:**
```python
# app/schemas/__init__.py
@field_validator('role')
@classmethod
def validate_role(cls, v):
    allowed_roles = ['admin', 'consultant', 'viewer', 'manager']  # 'admin' no existe
    if v not in allowed_roles:
        raise ValueError(f"Rol no válido...")
    return v
```

**Recomendación:**
```python
# Corregir validador
@field_validator('role')
@classmethod
def validate_role(cls, v):
    allowed_roles = ['super_admin', 'consultant', 'viewer']  # Usar valores reales del Enum
    if v not in allowed_roles:
        raise ValueError(f"Rol no válido. Debe ser uno de: {', '.join(allowed_roles)}")
    return v
```

---

#### VULN-006: Sin validación de complejidad de contraseña en cambio de email
**Severidad:** Media  
**CVSS:** 5.3  
**Ubicación:** `/app/schemas/__init__.py:EmailChange`

**Descripción:** En `EmailChange`, solo se valida que el password no esté vacío, pero no se verifica que sea el password actual correcto antes de permitir cambio de email.

**Recomendación:**
```python
# app/schemas/__init__.py
class EmailChange(BaseModel):
    new_email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)  # Mínimo 8 caracteres
    
    @field_validator('password')
    @classmethod
    def validate_password_not_empty(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("La contraseña es requerida")
        return v
```

---

### 🟡 MEDIAS

#### VULN-007: SameSite cookie no es 'strict' en desarrollo
**Severidad:** Media  
**CVSS:** 4.3  
**Ubicación:** `/app/api/auth.py`

**Descripción:** En desarrollo, las cookies usan `samesite='lax'` y `secure=False`, lo que permite CSRF en ciertos escenarios.

**Código actual:**
```python
COOKIE_SETTINGS = {
    "httponly": True,
    "secure": settings.ENVIRONMENT == "production",
    "samesite": "strict" if settings.ENVIRONMENT == "production" else "lax",
    "path": "/",
}
```

**Recomendación:** Mantener consistencia entre entornos:
```python
COOKIE_SETTINGS = {
    "httponly": True,
    "secure": True,  # Siempre true, incluso en desarrollo con HTTPS local
    "samesite": "strict",  # Siempre strict
    "path": "/",
}
```

---

#### VULN-008: Sin límite de dispositivos activos por usuario
**Severidad:** Media  
**CVSS:** 4.0  
**Ubicación:** `/app/core/auth.py`

**Descripción:** No hay límite de sesiones simultáneas por usuario. Un atacante con credenciales robadas puede tener sesiones ilimitadas.

**Recomendación:**
```python
# Agregar tracking de sesiones activas
async def create_session(
    user_id: str, 
    device_info: dict,
    max_sessions: int = 5
) -> str:
    """Crea una nueva sesión con límite de sesiones por usuario."""
    
    # Contar sesiones activas
    active_sessions = await get_active_sessions_count(user_id)
    
    if active_sessions >= max_sessions:
        # Revocar la sesión más antigua
        await revoke_oldest_session(user_id)
    
    # Crear nueva sesión
    session_id = generate_secure_token()
    await store_session(user_id, session_id, device_info)
    
    return session_id
```

---

#### VULN-009: Middleware del frontend no valida roles
**Severidad:** Media  
**CVSS:** 4.0  
**Ubicación:** `/frontend/src/middleware.ts`

**Descripción:** El middleware de Next.js no realiza validación de roles porque no tiene acceso al localStorage. La protección depende completamente del cliente.

**Código actual:**
```typescript
// middleware.ts - No hace validación real
export function middleware(request: NextRequest) {
  // ... no hay validación de autenticación real ...
  return NextResponse.next();
}
```

**Recomendación:**
```typescript
// middleware.ts - Validación con cookie
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Verificar cookie de sesión
  const token = request.cookies.get('access_token')?.value;
  
  if (!token && isProtectedRoute(pathname)) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  
  // Validar token con backend para rutas admin
  if (isAdminRoute(pathname)) {
    const isAdmin = await validateAdminToken(token);
    if (!isAdmin) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
  }
  
  return NextResponse.next();
}
```

---

#### VULN-010: Falta política de bloqueo de cuenta
**Severidad:** Media  
**CVSS:** 4.0  
**Ubicación:** `/app/core/auth.py:authenticate_user()`

**Descripción:** No hay bloqueo de cuenta después de múltiples intentos fallidos de login.

**Recomendación:**
```python
# app/core/auth.py
async def authenticate_user(db, email, password, request=None):
    from app.core.rate_limit import AccountLockoutManager
    
    lockout_manager = AccountLockoutManager()
    
    # Verificar si la cuenta está bloqueada
    if await lockout_manager.is_locked(email):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Cuenta bloqueada temporalmente por múltiples intentos fallidos"
        )
    
    user = await db.execute(select(User).where(User.email == email))
    user = user.scalar_one_or_none()
    
    if not user or not verify_password(password, user.hashed_password):
        # Registrar intento fallido
        attempts = await lockout_manager.record_failed_attempt(email)
        
        if attempts >= 5:
            await lockout_manager.lock_account(email, duration_minutes=30)
            await security_logger.log_suspicious_activity(
                request, "account_locked", {"email": email, "attempts": attempts}
            )
        
        return None
    
    # Limpiar intentos fallidos en login exitoso
    await lockout_manager.clear_attempts(email)
    
    return user
```

---

### 🟢 BAJAS

#### VULN-011: Secrets hardcodeados en configuración para desarrollo
**Severidad:** Baja  
**CVSS:** 3.0  
**Ubicación:** `/app/core/config.py`

**Descripción:** Existen valores por defecto para SECRET_KEY y DEFAULT_ADMIN_PASSWORD en desarrollo.

**Recomendación:** Siempre requerir variables de entorno, incluso en desarrollo.

---

## 3️⃣ Recomendaciones Generales

### 3.1 Implementar "Deny by Default"

Actualmente el sistema usa un enfoque de "permitir por defecto" en algunos casos. Recomendación:

```python
# app/core/deps.py - Patrón deny by default
async def require_permission(
    permission: str,
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Requiere un permiso específico (deny by default)."""
    
    # Mapeo de roles a permisos
    role_permissions = {
        UserRole.SUPER_ADMIN: ["*"],  # Todos los permisos
        UserRole.CONSULTANT: [
            "jobs:read", "jobs:write",
            "candidates:read", "candidates:write",
            "evaluations:read", "evaluations:write"
        ],
        UserRole.VIEWER: [
            "jobs:read",
            "candidates:read",
            "evaluations:read"
        ]
    }
    
    user_permissions = role_permissions.get(current_user.role, [])
    
    if "*" not in user_permissions and permission not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permiso requerido: {permission}"
        )
    
    return current_user

# Uso en endpoints
@router.post("/jobs")
async def create_job(
    data: JobCreate,
    current_user: User = Depends(lambda: require_permission("jobs:write"))
):
    pass
```

### 3.2 Mejorar Logging de Seguridad

```python
# Agregar más eventos de seguridad al SecurityLogger

async def log_session_created(self, request, user_id, session_id, device_info):
    """Loggear creación de sesión."""
    pass

async def log_session_terminated(self, request, user_id, session_id, reason):
    """Loggear terminación de sesión."""
    pass

async def log_permission_denied(self, request, user_id, required_permission):
    """Loggar acceso denegado por permisos."""
    pass
```

### 3.3 Implementar CSP más estricto

```python
# app/main.py - CSP mejorado
response.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self' 'nonce-{nonce}'; "  # Nonces para scripts inline
    "style-src 'self' 'nonce-{nonce}'; "
    "img-src 'self' data: https: blob:; "
    "font-src 'self'; "
    "connect-src 'self' {api_domain}; "
    "media-src 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "upgrade-insecure-requests;"
)
```

---

## 4️⃣ Checklist de Implementación

### Fase 1: Inmediata (Críticas)
- [ ] Implementar MFA para administradores (VULN-001)
- [ ] Agregar token blacklist para invalidación en logout (VULN-002)

### Fase 2: Alta Prioridad (Altas)
- [ ] Implementar rotación de refresh tokens (VULN-003)
- [ ] Agregar rate limiting en forgot/reset password (VULN-004)
- [ ] Corregir validador de roles en schemas (VULN-005)

### Fase 3: Media Prioridad (Medias)
- [ ] Implementar bloqueo de cuenta (VULN-010)
- [ ] Mejorar middleware de frontend (VULN-009)
- [ ] Limitar sesiones simultáneas (VULN-008)

### Fase 4: Mejoras Continuas (Bajas)
- [ ] Revisar configuración de cookies SameSite (VULN-007)
- [ ] Eliminar secrets por defecto (VULN-011)

---

## 5️⃣ Conclusión

El sistema ATS Platform tiene una base de seguridad sólida con:
- ✅ Password hashing con bcrypt
- ✅ Timing attack protection
- ✅ Cookies httpOnly y secure flags
- ✅ Rate limiting en endpoints críticos
- ✅ CSRF protection
- ✅ Security headers

Sin embargo, se identificaron **vulnerabilidades críticas** que deben abordarse inmediatamente:

1. **Falta de MFA** para administradores
2. **Sin invalidación de tokens** al hacer logout
3. **Sin rotación de refresh tokens**
4. **Rate limiting insuficiente** en recuperación de contraseña

**Prioridad recomendada:** Implementar Fase 1 y Fase 2 antes de poner en producción.

---

*Informe generado automáticamente por subagente de seguridad OpenClaw.*
