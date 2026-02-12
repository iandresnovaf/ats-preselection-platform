# Configuración de Seguridad - Frontend

## Resumen de Cambios de Seguridad Implementados

### 1. Autenticación con Cookies HttpOnly

**Cambios realizados:**
- Eliminado todo el uso de `localStorage` para tokens JWT
- El backend ahora envía tokens en cookies `httpOnly`
- El frontend usa `withCredentials: true` en todas las peticiones Axios
- El navegador envía automáticamente las cookies en cada request

**Archivos modificados:**
- `src/store/auth.ts` - Eliminado persistencia en localStorage
- `src/services/api.ts` - Agregado `withCredentials: true`
- `src/services/auth.ts` - Eliminado uso de localStorage

### 2. Content Security Policy (CSP)

**Headers configurados en `next.config.js`:**

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'unsafe-eval' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: blob: https:;
  font-src 'self';
  connect-src 'self';
  media-src 'self';
  object-src 'none';
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self'
```

**Headers adicionales de seguridad:**
- `X-Frame-Options: DENY` - Previene clickjacking
- `X-Content-Type-Options: nosniff` - Previene MIME sniffing
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`

### 3. Validación y Sanitización de Inputs

**Nuevo archivo:** `src/lib/validation.ts`

**Validaciones implementadas:**
- Email con regex estricto (RFC 5321)
- Teléfono con formato internacional
- URL con validación de protocolo (http/https)
- Nombres con caracteres permitidos
- Límites de longitud máxima para todos los campos
- Sanitización contra XSS (remoción de scripts, event handlers, iframes)
- Escapado de caracteres HTML peligrosos

**Formularios actualizados:**
- `LoginForm.tsx` - Validación estricta con Zod
- `CandidateForm.tsx` - Validación y sanitización completa
- `JobForm.tsx` - Validación y sanitización completa

### 4. Manejo Seguro de Errores

**Cambios realizados:**
- No se exponen detalles de errores internos al usuario
- Mensajes de error genéricos para errores del servidor
- Logging de errores de seguridad sin mostrar información sensible
- Manejo apropiado de 401/403

### 5. Configuración de Cookies (Requiere Backend)

El backend debe configurar cookies con los siguientes flags:

```python
response.set_cookie(
    'access_token',
    token,
    httponly=True,
    secure=True,  # En producción
    samesite='Strict',
    max_age=3600,  # 1 hora
)

response.set_cookie(
    'refresh_token',
    refresh_token,
    httponly=True,
    secure=True,  # En producción
    samesite='Strict',
    max_age=604800,  # 7 días
)
```

### 6. Protección contra XSS

- React escapa automáticamente todo output (ya implementado)
- No se encontró uso de `dangerouslySetInnerHTML`
- Sanitización implementada para cualquier contenido dinámico
- Validación de URLs antes de renderizar enlaces

## Checklist de Seguridad

- [x] Ningún token en localStorage
- [x] Headers CSP presentes
- [x] Inputs validados y sanitizados
- [x] withCredentials habilitado en todas las peticiones
- [x] X-Frame-Options configurado
- [x] No información sensible en mensajes de error
- [x] Límites de longitud en todos los inputs
- [x] Validación de email con regex estricto
- [x] Sanitización de HTML/nombres/URLs

## Notas de Implementación

### Compatibilidad con Backend

El frontend ahora espera que el backend:
1. Envíe tokens en cookies httpOnly
2. Acepte cookies en endpoints de autenticación
3. Refresque tokens automáticamente basándose en la cookie

### Testing

Para verificar la seguridad:
1. Verificar que no hay tokens visibles en localStorage
2. Verificar que las cookies tienen flag `httpOnly`
3. Verificar headers CSP en respuestas del servidor
4. Probar inyección de scripts en formularios
5. Verificar manejo de errores sin información sensible

## Referencias

- [OWASP CSP Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
- [OWASP XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [MDN: HttpOnly Cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#restrict_access_to_cookies)
