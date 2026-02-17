# FLUJO COMPLETO RHMatch 2.0 - Proceso de Headhunting

## 📋 FLUJO DE TRABAJO

### **FASE 1: CONFIGURACIÓN INICIAL**
1. **Crear Cliente** (Empresa que contrata)
   - Nombre, industria, datos de contacto
   
2. **Crear Vacante (Role)**
   - Título, descripción, requisitos
   - Asociar al cliente
   - Asignar al Consultor Senior responsable

3. **Crear Candidatos**
   - Datos personales completos
   - CV/Experiencia/Educación
   - Asociar a la vacante específica (Application)

---

### **FASE 2: SELECCIÓN POR EL CONSULTOR SENIOR**

El Consultor Senior revisa los candidatos y decide:

**Candidatos seleccionados (CONTINUAR):**
- Estado: **ACTIVO**
- Pasan a la siguiente fase de contacto

**Candidatos descartados (NO CONTINUAR):**
- Estado: **NO ACTIVO**
- Se archivan con motivo del descarte

---

### **FASE 3: CONTACTO INICIAL**

#### **3.1 Verificación de Datos de Contacto**

Para cada candidato ACTIVO, el sistema verifica:

```
¿Tiene email?     [SÍ/NO]
¿Tiene celular?   [SÍ/NO]
```

**CASO A: Tiene ambos datos** ✅
- Enviar mensaje automático (email + WhatsApp)
- Estado: "CONTACTADO"

**CASO B: Falta email o celular** ⚠️
- Mostrar **POP-UP** al Consultor Senior:
  ```
  "El candidato [Nombre] no tiene:
   [ ] Email
   [ ] Celular
   
   Por favor ingrese los datos faltantes"
  ```
- Consultor ingresa datos manualmente
- Luego enviar mensaje

---

### **FASE 4: RESPUESTAS DEL CANDIDATO**

#### **Canal de Comunicación:**
- **Email:** SMTP/API de correo
- **WhatsApp:** API de WhatsApp Business

#### **Posibles Respuestas:**

**1. RESPUESTA POSITIVA** ✅
```
Candidato: "Sí estoy interesado"
Sistema:
  → Estado: "INTERESADO"
  → Notificar a Consultor Senior
  → Agendar entrevista
```

**2. RESPUESTA NEGATIVA** ❌
```
Candidato: "No estoy interesado"
Sistema:
  → Estado: "NO INTERESADO"
  → Motivo: "Rechazó oferta"
  → Archivar candidato
```

**3. SIN RESPUESTA** ⏰
```
Sistema después de 48-72 horas:
  → Estado: "SIN RESPUESTA"
  → Notificar a Consultor Senior:
     "El candidato [Nombre] no ha respondido
      ¿Desea reintentar contacto?"
  
  Opciones del Consultor:
  [ ] Sí, reenviar mensaje
  [ ] No, descartar candidato
  [ ] Llamar manualmente
```

---

## 🛠️ MÓDULOS FALTANTES POR IMPLEMENTAR

### **1. MÓDULO DE PLANTILLAS DE MENSAJES**

**Ubicación:** `/templates` o `/message-templates`

**Funcionalidad:**
- Crear/editar plantillas de mensajes
- Variables dinámicas: `{nombre}`, `{vacante}`, `{empresa}`
- Canales: Email, WhatsApp, SMS

**Ejemplos de Plantillas:**

```
Plantilla: "Contacto Inicial"
Asunto: Oportunidad laboral - {vacante}

Hola {nombre},

Tenemos una oportunidad para el cargo de {vacante} 
en {empresa} que podría interesarte.

¿Te gustaría conocer más detalles?

Responde:
✅ SÍ - Estoy interesado
❌ NO - No estoy interesado

Saludos,
{consultor_nombre}
{consultor_telefono}
```

**Base de Datos:**
```sql
CREATE TABLE message_templates (
    template_id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    channel ENUM('email', 'whatsapp', 'sms') NOT NULL,
    subject VARCHAR(255), -- solo para email
    body TEXT NOT NULL,
    variables JSONB, -- ["nombre", "vacante", "empresa"]
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

### **2. MÓDULO DE COMUNICACIONES**

**Ubicación:** `/communications`

**Funcionalidad:**
- Enviar mensajes masivos a candidatos activos
- Registrar historial de comunicaciones
- Webhook para recibir respuestas

**Base de Datos:**
```sql
CREATE TABLE communications (
    communication_id UUID PRIMARY KEY,
    candidate_id UUID REFERENCES candidates(id),
    application_id UUID REFERENCES applications(id),
    template_id UUID REFERENCES message_templates(id),
    channel ENUM('email', 'whatsapp', 'sms'),
    direction ENUM('outbound', 'inbound'),
    message_content TEXT,
    status ENUM('sent', 'delivered', 'read', 'failed', 'replied'),
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    read_at TIMESTAMP,
    reply_content TEXT,
    reply_received_at TIMESTAMP,
    created_at TIMESTAMP
);
```

---

### **3. INTEGRACIÓN WHATSAPP API**

**Proveedores recomendados:**
- **Twilio** (más estable)
- **Meta Business API** (directo, más complejo)
- **Wati** / **360dialog** (especializados)

**Configuración:**
```python
# app/integrations/whatsapp.py

class WhatsAppService:
    def __init__(self):
        self.api_key = settings.WHATSAPP_API_KEY
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        
    async def send_template_message(
        self, 
        to_phone: str, 
        template_name: str,
        variables: dict
    ):
        """Enviar mensaje usando plantilla aprobada"""
        pass
        
    async def send_custom_message(
        self,
        to_phone: str,
        message: str
    ):
        """Enviar mensaje personalizado"""
        pass
        
    def parse_incoming_message(self, webhook_data: dict):
        """Procesar respuesta entrante"""
        pass
```

---

### **4. SISTEMA DE ESTADOS DE CANDIDATOS**

**Estados actuales a modificar:**
```
sourcing → shortlist → terna → interview → offer → hired/rejected
```

**Nuevos estados adicionales:**
```
ACTIVES:
  - CONTACT_PENDING (Pendiente de contacto)
  - CONTACTED (Contactado)
  - INTERESTED (Interesado - respondió SÍ)
  - INTERVIEW_SCHEDULED (Entrevista agendada)
  - FOLLOW_UP (Seguimiento)

INACTIVES:
  - NO_CONTACT_INFO (Sin datos de contacto)
  - NOT_INTERESTED (No interesado - respondió NO)
  - NO_RESPONSE (Sin respuesta)
  - DISCARDED (Descartado por consultor)
```

---

### **5. POP-UP DE DATOS FALTANTES**

**Componente React:**
```tsx
// components/modals/MissingContactModal.tsx

interface MissingContactModalProps {
  isOpen: boolean;
  candidate: Candidate;
  onSubmit: (data: { email?: string; phone?: string }) => void;
  onSkip: () => void;
}

export function MissingContactModal({
  isOpen,
  candidate,
  onSubmit,
  onSkip
}: MissingContactModalProps) {
  return (
    <Dialog open={isOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            Datos de Contacto Faltantes
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <p>
            El candidato <strong>{candidate.full_name}</strong> no tiene:
          </p>
          
          {!candidate.email && (
            <div>
              <Label>Email</Label>
              <Input 
                type="email"
                placeholder="correo@ejemplo.com"
              />
            </div>
          )}
          
          {!candidate.phone && (
            <div>
              <Label>Celular</Label>
              <Input 
                placeholder="+57 300 123 4567"
              />
            </div>
          )}
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={onSkip}>
            Saltar por ahora
          </Button>
          <Button onClick={onSubmit}>
            Guardar y Contactar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

---

### **6. DASHBOARD DE SEGUIMIENTO**

**Vista para Consultor Senior:**

```
┌─────────────────────────────────────────────────────┐
│  VACANTE: Director de Operaciones - TechCorp        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  PENDIENTES DE CONTACTO (3)                        │
│  ├─ Juan Pérez              [Falta email] ⚠️       │
│  ├─ María López             [Listo para enviar] ✅ │
│  └─ Carlos Ruiz             [Listo para enviar] ✅ │
│                                                     │
│  CONTACTADOS (5)                                   │
│  ├─ Ana Gómez               [Interesada] ✅        │
│  ├─ Pedro Sánchez           [No respondió] ⏰      │
│  ├─ Laura Martínez          [No interesada] ❌     │
│  └─ ...                                            │
│                                                     │
│  ACCIONES RÁPIDAS:                                 │
│  [Contactar pendientes] [Reenviar a no respuesta]  │
└─────────────────────────────────────────────────────┘
```

---

## 📊 ESTRUCTURA DE DATOS ACTUALIZADA

### **Tabla: applications (modificada)**
```sql
ALTER TABLE hh_applications ADD COLUMN (
    consultant_decision VARCHAR(20), -- 'CONTINUE', 'DISCARD'
    decision_reason TEXT,
    contact_status VARCHAR(30), -- 'PENDING', 'CONTACTED', 'INTERESTED', 'NOT_INTERESTED', 'NO_RESPONSE'
    contacted_at TIMESTAMP,
    responded_at TIMESTAMP,
    response_type VARCHAR(20), -- 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
    follow_up_count INTEGER DEFAULT 0
);
```

### **Tabla: communications (nueva)**
```sql
CREATE TABLE hh_communications (
    communication_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES hh_applications(application_id),
    candidate_id UUID REFERENCES hh_candidates(candidate_id),
    template_id UUID,
    channel VARCHAR(20), -- 'email', 'whatsapp', 'sms'
    message_type VARCHAR(20), -- 'initial', 'follow_up', 'reminder'
    content TEXT,
    direction VARCHAR(10), -- 'outbound', 'inbound'
    status VARCHAR(20), -- 'sent', 'delivered', 'read', 'failed', 'replied'
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    read_at TIMESTAMP,
    replied_at TIMESTAMP,
    reply_content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### **Prioridad ALTA (Semana 1-2)**
- [ ] Módulo de plantillas de mensajes
- [ ] Estados adicionales de candidatos
- [ ] Popup de datos faltantes
- [ ] Envío de mensajes (email + WhatsApp mock)

### **Prioridad MEDIA (Semana 3)**
- [ ] Integración WhatsApp API real
- [ ] Webhook para recibir respuestas
- [ ] Dashboard de seguimiento
- [ ] Notificaciones al consultor

### **Prioridad BAJA (Semana 4)**
- [ ] Reportes de comunicación
- [ ] Estadísticas de respuesta
- [ ] Automatización de follow-ups

---

## 💰 ESTIMACIÓN DE COSTOS WHATSAPP API

**Twilio WhatsApp:**
- Mensaje de sesión: ~$0.005 USD
- Mensaje de plantilla: ~$0.013 USD
- 1000 mensajes/mes: ~$13 USD

**Meta Business API (directo):**
- Primeros 1000 conversaciones/mes: GRATIS
- Conversaciones adicionales: ~$0.03-0.08 USD

**Recomendación:** Comenzar con Twilio (más simple) y migrar a Meta si el volumen crece.

---

## 🚀 PRÓXIMOS PASOS

1. **¿Aprobamos este flujo?**
2. **¿Qué proveedor de WhatsApp prefieren?** (Twilio/Meta/Otro)
3. **¿Tienen cuenta de Meta Business verificada?**
4. **¿Quieren comenzar con email primero y luego WhatsApp?**

**¿Por cuál módulo quieren que empecemos?**
