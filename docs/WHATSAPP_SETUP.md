# Configuración de WhatsApp Business API

Esta guía describe cómo configurar la integración con WhatsApp Business API de Meta para enviar mensajes a candidatos.

## Requisitos Previos

1. **Cuenta de Meta Business** - Regístrate en [business.facebook.com](https://business.facebook.com)
2. **Página de Facebook** - Necesaria para verificar tu negocio
3. **Sitio Web** - Con política de privacidad visible
4. **Teléfono** - Número de teléfono para WhatsApp Business (puede ser el mismo que uses personalmente)

## Paso a Paso

### 1. Crear App en Meta Developers

1. Ve a [developers.facebook.com](https://developers.facebook.com)
2. Crea una nueva app:
   - Tipo: **Business**
   - Nombre: `ATS WhatsApp Integration`
3. En el panel de la app, agrega el producto **WhatsApp**

### 2. Configurar WhatsApp Business Account

1. Desde el panel de WhatsApp en tu app:
   - Selecciona o crea una **WhatsApp Business Account (WABA)**
   - Agrega un número de teléfono de prueba (sandbox) o un número real

2. Para producción, necesitas:
   - Verificar tu negocio en Meta Business Manager
   - Verificar tu dominio web
   - Solicitar acceso a la API de WhatsApp Business

### 3. Obtener Credenciales

En el panel de WhatsApp de tu app, encuentra:

```
- Phone Number ID: <Número de teléfono ID>
- WhatsApp Business Account ID: <Business Account ID>
```

Genera un token de acceso:
1. Ve a **System Users** en Business Manager
2. Crea un usuario de sistema con rol de admin
3. Genera un token con permisos:
   - `whatsapp_business_management`
   - `whatsapp_business_messaging`

### 4. Configurar Webhook

1. En tu app de Meta, ve a **Webhooks** > **WhatsApp Business Account**
2. Configura la URL de callback: `https://tu-dominio.com/webhook/whatsapp`
3. Token de verificación: Crea un string seguro (ej: `tu_webhook_secret_123`)
4. Suscríbete a estos eventos:
   - `messages` (mensajes entrantes)
   - `message_status` (actualizaciones de estado)

### 5. Configurar Variables de Entorno

En tu archivo `.env`:

```bash
# WhatsApp Business API
WHATSAPP_ENABLED=true
WHATSAPP_MOCK_MODE=false
WHATSAPP_API_VERSION=v18.0
WHATSAPP_BUSINESS_ACCOUNT_ID=tu_business_account_id
WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id
WHATSAPP_ACCESS_TOKEN=tu_access_token_largo
WHATSAPP_WEBHOOK_VERIFY_TOKEN=tu_webhook_verify_token
WHATSAPP_APP_SECRET=tu_app_secret
```

Para obtener el **App Secret**:
- Ve a **Settings** > **Basic** en tu app de Meta
- El App Secret está oculto, haz clic en "Show"

### 6. Aprobar Plantillas de Mensajes

Los mensajes iniciales deben usar plantillas aprobadas por Meta:

1. En el panel de WhatsApp, ve a **Message Templates**
2. Crea plantillas con categoría **Utility** o **Authentication**
3. Espera aprobación (generalmente en minutos, a veces horas)

Plantillas recomendadas:

**contacto_inicial** (Utility):
```
Hola {{1}}, soy {{2}} de Top Management. Tenemos una oportunidad 
laboral que podría interesarte: {{3}}. ¿Te gustaría conocer más detalles?
```

**seguimiento** (Utility):
```
Hola {{1}}, te escribo para hacer seguimiento a la oportunidad que 
te compartí. ¿Tuviste chance de revisarla? Quedo atento a tu respuesta.
```

**recordatorio_entrevista** (Utility):
```
Hola {{1}}, te recordamos que tienes una entrevista programada para 
{{2}} a las {{3}}. {{4}}
```

## Testing con Sandbox

Para probar sin un número de producción:

1. En el panel de WhatsApp, ve a la sección **API Setup**
2. Usa el número de teléfono de prueba proporcionado
3. Agrega números de destinatarios de prueba
4. Envía mensajes usando el token temporal

Limitaciones del sandbox:
- Solo puedes enviar a números registrados previamente
- Los mensajes tienen prefijo "[TEMPLATE TEST]"

## Modo Mock (Desarrollo Local)

Para desarrollar sin conexión a Meta:

```bash
WHATSAPP_MOCK_MODE=true
WHATSAPP_ENABLED=true
```

En modo mock:
- Los mensajes "se envían" exitosamente
- Los webhooks se procesan normalmente
- No se consume cuota de Meta
- Útil para testing local

## Verificar Configuración

Una vez configurado, verifica:

```bash
# Health check del webhook
curl https://tu-dominio.com/webhook/whatsapp/health

# Estado de WhatsApp
curl -H "Authorization: Bearer tu_token" \
  https://tu-dominio.com/api/v1/communications/whatsapp/status

# Listar templates
curl -H "Authorization: Bearer tu_token" \
  https://tu-dominio.com/api/v1/communications/whatsapp/templates
```

## Uso de la API

### Enviar Mensaje

```bash
curl -X POST https://tu-dominio.com/api/v1/communications/send \
  -H "Authorization: Bearer tu_token" \
  -H "Content-Type: application/json" \
  -d '{
    "application_id": "uuid-de-la-aplicacion",
    "candidate_id": "uuid-del-candidato",
    "phone": "573001234567",
    "template_name": "contacto_inicial",
    "template_variables": ["Juan Pérez", "María González", "Gerente de Ventas"],
    "message_type": "initial"
  }'
```

### Listar Comunicaciones

```bash
curl "https://tu-dominio.com/api/v1/communications?candidate_id=uuid&status=sent" \
  -H "Authorization: Bearer tu_token"
```

### Reintentar Mensaje Fallido

```bash
curl -X POST https://tu-dominio.com/api/v1/communications/{id}/retry \
  -H "Authorization: Bearer tu_token"
```

## Webhook - Respuestas de Candidatos

Cuando un candidato responde:

1. Meta envía un POST a `/webhook/whatsapp`
2. El sistema procesa la respuesta y determina si está interesado
3. Se actualiza el estado de la aplicación (INTERESTED / NOT_INTERESTED)
4. Se guarda la respuesta en la tabla de comunicaciones

## Flujo de Estados

```
PENDING → SENT → DELIVERED → READ
                ↓
             FAILED (puede reintentarse)
                ↓
             REPLIED (cuando candidato responde)
```

## Limitaciones Importantes

1. **Ventana de 24 horas**: Solo puedes enviar mensajes de texto libre si el candidato respondió en las últimas 24 horas. Para iniciar conversaciones, usa templates.

2. **Rate Limits**: Meta limita el número de mensajes por segundo. El sistema tiene retry automático.

3. **Aprobación de Plantillas**: Las plantillas deben ser aprobadas antes de usarlas en producción.

## Solución de Problemas

### Error: "Phone number not registered"
- Verifica que el número esté en formato E.164 (sin +, sin espacios)
- Ejemplo correcto: `573001234567`

### Error: "Template not found"
- Verifica que el nombre del template coincida exactamente
- Asegúrate de que el template esté aprobado

### Error: "Invalid credentials"
- Verifica que el access_token no haya expirado
- Los tokens de sistema no expiran, los de usuario sí

### No recibo webhooks
- Verifica que la URL del webhook sea accesible desde internet
- Usa ngrok para desarrollo local: `ngrok http 8000`
- Verifica el token de verificación

### Mensajes marcados como failed
- Revisa los logs en `docker-compose logs -f backend`
- Verifica que el candidato haya respondido en las últimas 24h (para mensajes de texto)
- Usa templates para mensajes iniciales

## Seguridad

1. **Nunca** expongas el ACCESS_TOKEN o APP_SECRET en el código
2. Usa variables de entorno
3. El token de verificación debe ser único y seguro
4. Habilita la verificación de firma de webhooks con APP_SECRET

## Recursos Útiles

- [Documentación oficial de WhatsApp Business API](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Guía de webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks)
- [Referencia de templates](https://developers.facebook.com/docs/whatsapp/business-management-api/message-templates)
- [Rate limits](https://developers.facebook.com/docs/whatsapp/cloud-api/overview/rate-limits)

## Soporte

Para problemas con Meta:
- [Centro de ayuda de Meta Business](https://www.facebook.com/business/help)
- [Developer Support](https://developers.facebook.com/support/)

Para problemas con esta integración:
- Revisa los logs del backend
- Verifica que todas las variables de entorno estén configuradas
- Asegúrate de que el webhook sea accesible públicamente
