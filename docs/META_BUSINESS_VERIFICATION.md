# Guía de Verificación Meta Business para WhatsApp Business API

## 📋 Tabla de Contenidos
1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Requisitos Previos](#requisitos-previos)
3. [Proceso Paso a Paso](#proceso-paso-a-paso)
4. [Documentos Requeridos](#documentos-requeridos)
5. [Tiempos y Costos](#tiempos-y-costos)
6. [Solución de Problemas](#solución-de-problemas)
7. [Checklist Final](#checklist-final)

---

## Resumen Ejecutivo

La **Meta Business Verification** es un proceso obligatorio para usar la **WhatsApp Business API** a través de Meta directamente (sin proveedores intermedios como Twilio). Este proceso verifica que tu empresa es legítima y cumple con las políticas de Meta.

### ⚠️ Importante
- **Sin verificación:** Solo puedes enviar mensajes a números de prueba
- **Con verificación:** Puedes enviar mensajes a cualquier número de WhatsApp
- **Tiempo estimado:** 3-5 días hábiles (puede extenderse si hay problemas)

---

## Requisitos Previos

### ✅ Antes de Comenzar

1. **Cuenta de Facebook/Instagram existente** (personal está bien)
2. **Página web de la empresa** activa y funcional
3. **Correo electrónico corporativo** con dominio propio (no Gmail/Yahoo)
4. **Número de teléfono de la empresa** (no personal)
5. **Documentos legales de la empresa** (ver sección de documentos)

### 📋 Lista de Verificación Previa

```markdown
☐ Tienes acceso a una cuenta de Facebook
☐ Tu empresa tiene página web activa
☐ Tienes email corporativo (@tuempresa.com)
☐ Tienes teléfono de empresa
☐ Tienes documentos legales listos
☐ Puedes recibir llamadas/códigos en el teléfono de empresa
```

---

## Proceso Paso a Paso

### **PASO 1: Crear Cuenta Meta Business**

**Tiempo estimado:** 15-30 minutos

1. Ir a [business.facebook.com](https://business.facebook.com)
2. Click en **"Crear Cuenta"** (Create Account)
3. Iniciar sesión con tu cuenta de Facebook personal
4. Completar información básica:
   - **Nombre del Negocio:** (exactamente como aparece legalmente)
   - **Nombre de usuario:** (para la URL de Business Manager)
   - **Sitio web:** (debe coincidir con documentos legales)
   - **País:** (donde está registrada la empresa)
5. Click en **"Enviar"**

**⚠️ Nota importante:** El nombre del negocio debe coincidir EXACTAMENTE con los documentos legales que presentarás posteriormente.

**Resultado:** Tendrás un Business Manager ID (formato: 123456789012345)

---

### **PASO 2: Verificar Empresa (Business Verification)**

**Tiempo estimado:** 30-60 minutos + tiempo de revisión

#### 2.1 Iniciar Proceso de Verificación

1. En Meta Business Suite, ir a **Configuración del Negocio** (Business Settings)
2. Click en **"Seguridad del Centro"** (Security Center) en el menú lateral
3. Click en **"Comenzar"** en la sección "Verificación de Negocio"

#### 2.2 Métodos de Verificación Disponibles

Meta ofrece **2 métodos** de verificación:

**Método A: Verificación por Documentos Legales** (Recomendado)
- Más común y confiable
- Requiere subir documentos legales
- Tiempo de revisión: 2-5 días hábiles

**Método B: Verificación por Teléfono/Email** (Solo algunos países)
- Disponible para ciertos países
- Recibes código por llamada SMS/email
- Tiempo de revisión: Inmediato a 24 horas

#### 2.3 Verificación por Documentos (Detallado)

**Paso 2.3.1: Seleccionar Tipo de Negocio**
- Selecciona el tipo de empresa que coincide con tus documentos:
  - Sociedad Anónima (S.A.)
  - Sociedad de Responsabilidad Limitada (S. de R.L. / Ltda. / LLC)
  - Empresa Individual
  - Otras formas legales

**Paso 2.3.2: Subir Documentos de Verificación**

Ver sección [Documentos Requeridos](#documentos-requeridos) para lista completa.

**Paso 2.3.3: Confirmar Información Legal**
- Nombre legal exacto
- Dirección registrada
- Número de registro/identificación fiscal
- Nombre del representante legal

**Paso 2.3.4: Seleccionar Método de Confirmación**

Meta te dará opciones para confirmar la verificación:

1. **Llamada telefónica automática** (Recomendado - Más rápido)
   - Recibirás una llamada en el número de empresa
   - Sistema automatizado te dará un código
   - Ingresas el código en la plataforma

2. **Correo postal con código** (Muy lento - 1-2 semanas)
   - Meta envía carta con código a la dirección registrada
   - No recomendado por tiempo

3. **Email** (Solo algunos países)
   - Código enviado al email corporativo

**Paso 2.3.5: Esperar Revisión**
- Estado inicial: **"Pendiente"** (Pending)
- Revisión manual por equipo de Meta
- Puedes recibir solicitud de documentos adicionales

**Resultado esperado:** 
- ✅ **"Verificado"** (Verified) - Puedes continuar
- ⚠️ **"Revisión Adicional"** (Additional Review) - Requiere más documentos
- ❌ **"Rechazado"** (Rejected) - Necesitas apelar o corregir

---

### **PASO 3: Crear Aplicación de WhatsApp Business**

**Tiempo estimado:** 20-30 minutos

#### 3.1 Crear Nueva App en Meta for Developers

1. Ir a [developers.facebook.com](https://developers.facebook.com)
2. Click en **"Mis Apps"** → **"Crear App"**
3. Seleccionar tipo: **"Business"**
4. Completar información:
   - **Nombre de la app:** (ej: "RHMatch WhatsApp Integration")
   - **Email de contacto:** (tu email corporativo)
   - **Cuenta de Business Manager:** (selecciona la creada en Paso 1)
5. Click en **"Crear App"**

#### 3.2 Agregar Producto WhatsApp

1. En el dashboard de la app, busca **"WhatsApp"**
2. Click en **"Configurar"** (Set Up)
3. Aceptar términos y condiciones

#### 3.3 Configurar WhatsApp Business Account

1. Seleccionar o crear **Cuenta de WhatsApp Business** (WABA)
2. Vincular con tu Business Manager verificado
3. Seleccionar **Número de teléfono**:
   - Opción A: Usar número existente (migrar de WhatsApp personal)
   - Opción B: Nuevo número de teléfono

**⚠️ Advertencia importante sobre números:**
- El número NO puede estar vinculado a WhatsApp personal o Business App
- Debes poder recibir SMS o llamada en ese número
- Números de línea fija funcionan
- Números de VoIP NO funcionan (Google Voice, Skype, etc.)

---

### **PASO 4: Obtener Token de Acceso**

**Tiempo estimado:** 10-15 minutos

#### 4.1 Token Temporal (para pruebas)

1. En el panel de WhatsApp → **"Getting Started"**
2. Buscar **"Token de Acceso"** (Access Token)
3. Copiar el token mostrado (válido por 24 horas)

#### 4.2 Token Permanente (para producción)

1. Ir a **"Roles"** → **"Usuarios del Sistema"** (System Users)
2. Crear nuevo usuario del sistema:
   - Nombre: "WhatsApp API User"
   - Rol: "Admin" o "Developer"
3. Generar token:
   - Seleccionar el usuario creado
   - Click en **"Generar Token"**
   - Seleccionar tu app
   - Seleccionar permisos:
     - `whatsapp_business_messaging`
     - `whatsapp_business_management`
   - Copiar y guardar el token (¡no se mostrará de nuevo!)

**Resultado:** Token de acceso permanente (cadena larga que comienza con EAA...)

---

### **PASO 5: Configurar Número de Teléfono**

**Tiempo estimado:** 15-30 minutos

#### 5.1 Agregar Número

1. En WhatsApp Manager → **"Números de Teléfono"** (Phone Numbers)
2. Click en **"Agregar Número"**
3. Ingresar número de teléfono (con código de país, ej: +57 para Colombia)
4. Seleccionar método de verificación:
   - **SMS** (recomendado)
   - **Llamada de voz**

#### 5.2 Verificar Número

1. Recibirás código de 6 dígitos por SMS o llamada
2. Ingresar código en la plataforma
3. Click en **"Verificar"**

**Resultado:** Número verificado y listo para enviar mensajes

#### 5.3 Configurar Webhook (Opcional pero Recomendado)

Para recibir respuestas de usuarios:

1. Ir a **"Configuración"** → **"Webhook"**
2. Click en **"Configurar Webhook"**
3. Ingresar:
   - **URL del webhook:** `https://tu-dominio.com/api/webhooks/whatsapp`
   - **Token de verificación:** (string aleatorio seguro)
4. Guardar configuración
5. Seleccionar campos a suscribir:
   - `messages`
   - `message_deliveries`
   - `message_reads`

---

### **PASO 6: Aprobar Plantillas de Mensajes**

**Tiempo estimado:** 5-15 minutos por plantilla + 1-24 horas de revisión

#### 6.1 Entender Plantillas

Las plantillas son mensajes pre-aprobados que puedes enviar a usuarios que NO te han contactado primero (mensajes iniciativos).

**Tipos de plantillas:**
- **MARKETING:** Promociones, anuncios
- **UTILITY:** Confirmaciones, recordatorios
- **AUTHENTICATION:** Códigos de verificación

#### 6.2 Crear Plantilla

1. En WhatsApp Manager → **"Plantillas de Mensajes"** (Message Templates)
2. Click en **"Crear Plantilla"**
3. Seleccionar:
   - **Categoría:** UTILITY (recomendado para ATS)
   - **Idioma:** Español (o el de tu preferencia)
   - **Nombre:** (solo letras minúsculas y guiones bajos, ej: `contacto_inicial`)

4. Estructura del mensaje:
   - **Header (opcional):** Texto o imagen
   - **Body:** Contenido principal
   - **Footer (opcional):** Texto corto
   - **Buttons (opcional):** Botones de respuesta rápida

#### 6.3 Ejemplo de Plantilla para ATS

```
Nombre: contacto_inicial_candidato
Categoría: UTILITY
Idioma: Spanish

Header: Oportunidad laboral - {{1}}

Body:
Hola {{2}},

Somos {{3}}. Tenemos una oportunidad para el cargo de {{4}} que podría interesarte.

¿Te gustaría conocer más detalles?

Responde SÍ para más información o NO si no estás interesado.

Footer:
Saludos,
{{5}}

Buttons:
[ SÍ, estoy interesado ]
[ NO, gracias ]
```

**Variables:**
- `{{1}}` = Nombre de la vacante
- `{{2}}` = Nombre del candidato
- `{{3}}` = Nombre de tu empresa
- `{{4}}` = Cargo específico
- `{{5}}` = Nombre del consultor

#### 6.4 Enviar para Aprobación

1. Revisar vista previa
2. Click en **"Enviar"** (Submit)
3. Esperar aprobación (generalmente 1-24 horas)

**Posibles estados:**
- ✅ **APPROVED** - Lista para usar
- ⚠️ **PENDING** - En revisión
- ❌ **REJECTED** - Rechazada (revisar políticas y corregir)

#### 6.5 Plantillas Recomendadas para ATS

| Nombre | Uso | Prioridad |
|--------|-----|-----------|
| `contacto_inicial` | Primer contacto con candidato | Alta |
| `seguimiento` | Recordatorio (48h sin respuesta) | Media |
| `confirmacion_entrevista` | Confirmar entrevista agendada | Alta |
| `oferta_laboral` | Enviar propuesta económica | Media |
| `rechazo_amable` | Rechazo con feedback | Baja |

---

## Documentos Requeridos

### 📄 Lista de Documentos Aceptados

#### **Documentos Primarios** (Uno de estos)

| Documento | Países Válidos | Notas |
|-----------|----------------|-------|
| Certificado de Constitución | Todos | Documento que crea la empresa |
| Licencia de Negocios/Business License | Todos | Emitida por gobierno local |
| Registro Mercantil | LATAM, España | Del registro público de comercio |
| Escritura Pública de Constitución | LATAM, España | Con sello de notaría |
| Certificado de Existencia y Representación Legal | Colombia | De Cámara de Comercio |
| Tax ID / EIN Letter (EE.UU.) | Estados Unidos | Del IRS |
| VAT Registration | Europa | Documento de registro de IVA |

#### **Documentos Secundarios** (Para confirmar dirección)

| Documento | Uso |
|-----------|-----|
| Factura de servicios (últimos 3 meses) | Confirmar dirección operativa |
| Estado de cuenta bancario | Confirmar dirección de facturación |
| Contrato de arrendamiento | Confirmar dirección física |
| Escritura de inmueble | Confirmar propiedad |

### 📝 Requisitos de los Documentos

✅ **DEBE incluir:**
- Nombre legal completo de la empresa (EXACTO)
- Dirección registrada
- Número de registro/ID fiscal
- Fecha de emisión (no mayor a 12 meses para secundarios)
- Sello oficial o firma autorizada

❌ **NO debe:**
- Estar borroso o ilegible
- Tener marcas de agua que oculten información
- Estar alterado o modificado
- Tener fecha de vencimiento vencida

### 📤 Formato de Subida

- **Formatos aceptados:** PDF, JPG, PNG
- **Tamaño máximo:** 8 MB por archivo
- **Resolución mínima:** 300 DPI recomendado
- **Color:** Color o escala de grises (no blanco y negro puro)

---

## Tiempos y Costos

### ⏱️ Tiempos Estimados

| Etapa | Tiempo Estimado | Factores que Afectan |
|-------|-----------------|---------------------|
| Crear Meta Business | 15-30 min | Experiencia del usuario |
| Verificación de empresa | 3-5 días hábiles | Carga de trabajo de Meta, completitud de documentos |
| Crear App WhatsApp | 20-30 min | Familiaridad con plataforma |
| Configurar número | 15-30 min | Disponibilidad para recibir SMS |
| Aprobación de plantillas | 1-24 horas | Tipo de plantilla, claridad del contenido |
| **TOTAL ESTIMADO** | **5-7 días hábiles** | Desde inicio hasta envío de mensajes |

### 💰 Costos

#### **Meta Business Verification**
- **Costo:** **GRATIS** (sin costo directo)

#### **WhatsApp Business API (Conversaciones)**

Modelo de precios por conversación (no por mensaje individual):

| Tipo de Conversación | Costo aprox. (USD) | Descripción |
|---------------------|-------------------|-------------|
| Conversación iniciada por usuario | GRATIS* | Usuario te escribe primero |
| Conversación iniciada por empresa (Marketing) | $0.030 - $0.080 | Mensajes promocionales |
| Conversación iniciada por empresa (Utility) | $0.005 - $0.040 | Mensajes transaccionales |
| Conversación iniciada por empresa (Authentication) | $0.005 - $0.030 | Códigos de verificación |

*Nota: Primeras 1,000 conversaciones iniciadas por usuarios son gratuitas por mes

**Precios por región (ejemplos):**

| Región | Marketing | Utility | Authentication |
|--------|-----------|---------|----------------|
| España | $0.0619 | $0.0367 | $0.0305 |
| México | $0.0437 | $0.0196 | $0.0178 |
| Colombia | $0.0425 | $0.0190 | $0.0174 |
| Argentina | $0.0537 | $0.0273 | $0.0237 |
| Chile | $0.0466 | $0.0213 | $0.0193 |

**Precios actualizados en:** [business.whatsapp.com/products/business-platform/pricing](https://business.whatsapp.com/products/business-platform/pricing)

#### **Costos Adicionales Potenciales**

| Concepto | Costo Estimado |
|----------|---------------|
| Desarrollo de integración | Variable (interno/externo) |
| Servidor para webhook | $5-50 USD/mes |
| Número de teléfono dedicado | $1-10 USD/mes |
| **Estimación mensual (1,000 conversaciones)** | **$20-80 USD** |

---

## Solución de Problemas

### ❌ Problemas Comunes

#### **Problema 1: "Nombre del negocio no coincide"**
**Síntoma:** Rechazo de verificación por diferencia en nombre

**Solución:**
- Asegúrate de que el nombre en Meta Business sea EXACTAMENTE igual al documento legal
- Incluye las siglas (S.A., S.L., Ltda., etc.) si están en el documento
- No uses acentos si el documento no los tiene
- Si hay error, edita el nombre en Configuración del Negocio antes de reintentar

#### **Problema 2: "Documento no legible"**
**Síntoma:** Rechazo por calidad del documento

**Solución:**
- Escanea a 300 DPI o más
- Usa escáner plano (no fotos con celular)
- Asegúrate de que todo el texto sea legible
- Evita sombras o reflejos
- Convierte a PDF si el formato original lo permite

#### **Problema 3: "No recibo el código de verificación"**
**Síntoma:** El SMS o llamada no llega al teléfono

**Solución:**
- Verifica que el número incluya código de país (+57, +52, etc.)
- Asegúrate de tener cobertura celular
- Intenta con llamada de voz si SMS falla (o viceversa)
- El número no debe estar en lista negra o ser VoIP
- Espera 5 minutos antes de reintentar

#### **Problema 4: "Plantilla rechazada"**
**Síntoma:** Meta rechaza la plantilla de mensaje

**Razones comunes:**
- Contenido promocional en plantilla UTILITY
- Uso de palabras prohibidas (promesas de ganancias, medicinas, etc.)
- Falta de claridad en el propósito
- Demasiadas variables

**Solución:**
- Revisa las [políticas de WhatsApp](https://business.whatsapp.com/policy)
- Usa categoría MARKETING si es promocional
- Sé específico y claro en el contenido
- No uses texto genérico
- Asegúrate de que las variables estén bien formateadas ({{1}})

#### **Problema 5: "La app no tiene permisos de WhatsApp"**
**Síntoma:** No puedes enviar mensajes aunque todo esté configurado

**Solución:**
- Ve a tu app en developers.facebook.com
- Revisa "Roles" → "Usuarios del Sistema"
- Asegúrate de que el usuario tenga permisos de WhatsApp
- Genera un nuevo token con los scopes correctos
- Verifica que la cuenta de WhatsApp Business esté vinculada

#### **Problema 6: "El número ya está en uso"**
**Síntoma:** No puedes agregar el número porque está vinculado a otra cuenta

**Solución:**
- El número debe estar libre de cualquier cuenta de WhatsApp (personal o business)
- Si estaba en WhatsApp personal: elimínalo primero
- Si estaba en otra WABA: contacta a soporte de Meta para migrarlo
- Considera usar un número nuevo dedicado

---

### 📞 Contactar Soporte de Meta

Si necesitas ayuda adicional:

1. **Meta Business Help Center:**
   - URL: [facebook.com/business/help](https://www.facebook.com/business/help)
   - Busca "Business Verification" o "WhatsApp API"

2. **Meta for Developers Support:**
   - URL: [developers.facebook.com/support](https://developers.facebook.com/support)
   - Requiere cuenta de desarrollador verificada
   - Puedes crear tickets de soporte

3. **Chat de soporte (solo cuentas verificadas):**
   - Disponible en Business Manager
   - Icono de "?" en la esquina superior derecha

---

## Checklist Final

### ✅ Pre-Implementación

```markdown
☐ Cuenta Meta Business creada
☐ Empresa verificada por Meta
☐ Aplicación de WhatsApp creada
☐ Token de acceso generado
☐ Número de teléfono configurado y verificado
☐ Webhook configurado (para recibir respuestas)
☐ Al menos 1 plantilla aprobada
☐ Documentación guardada de:
    - Business Manager ID
    - App ID
    - Phone Number ID
    - Access Token (almacenado seguro)
```

### ✅ Integración Técnica

```markdown
☐ Variables de entorno configuradas:
    - WHATSAPP_ACCESS_TOKEN
    - WHATSAPP_PHONE_NUMBER_ID
    - WHATSAPP_BUSINESS_ACCOUNT_ID
☐ Endpoint de webhook implementado
☐ Verificación de webhook funcionando
☐ Envío de mensajes de plantilla probado
☐ Recepción de mensajes probado
☐ Manejo de errores implementado
☐ Logs de comunicación activados
```

### ✅ Producción

```markdown
☐ Límites de rate conocidos y respetados
☐ Monitoreo de errores configurado
☐ Proceso de recarga de créditos establecido
☐ Plan de respaldo si WhatsApp falla
☐ Política de privacidad actualizada (menciona WhatsApp)
☐ Términos de servicio incluyen uso de mensajería
☐ Consentimiento de usuarios documentado
```

---

## 📚 Recursos Adicionales

### Documentación Oficial
- [Meta Business Verification Guide](https://www.facebook.com/business/help/2058515294227817)
- [WhatsApp Business API Docs](https://developers.facebook.com/docs/whatsapp)
- [WhatsApp Business Policy](https://business.whatsapp.com/policy)
- [WhatsApp Pricing](https://business.whatsapp.com/products/business-platform/pricing)

### Comunidad y Foros
- [Meta Developers Community](https://developers.facebook.com/community)
- [Stack Overflow - WhatsApp Business API](https://stackoverflow.com/questions/tagged/whatsapp-business-api)

### Herramientas Útiles
- [WhatsApp Business API Postman Collection](https://developers.facebook.com/docs/whatsapp/guides/postman)
- [Webhook Tester](https://webhook.site/) - Para probar webhooks

---

## 🚀 Próximos Pasos después de la Verificación

1. **Configurar en tu aplicación ATS:**
   ```bash
   WHATSAPP_ACCESS_TOKEN=tu_token_aqui
   WHATSAPP_PHONE_NUMBER_ID=tu_phone_id
   WHATSAPP_BUSINESS_ACCOUNT_ID=tu_waba_id
   WHATSAPP_WEBHOOK_VERIFY_TOKEN=tu_token_secreto
   ```

2. **Implementar endpoints:**
   - `POST /api/whatsapp/send` - Enviar mensajes
   - `POST /api/webhooks/whatsapp` - Recibir respuestas

3. **Crear flujo de mensajes:**
   - Mapear estados de candidatos a mensajes
   - Configurar triggers automáticos
   - Implementar templates dinámicos

4. **Monitorear métricas:**
   - Tasa de entrega
   - Tasa de lectura
   - Tasa de respuesta
   - Errores y fallos

---

**Documento creado:** 2026-02-16  
**Versión:** 1.0  
**Última actualización:** 2026-02-16
