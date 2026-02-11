# 📖 Core ATS - User Guide

## Guía de Usuario para el Sistema de Seguimiento de Candidatos

---

## 📑 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Crear una Oferta de Trabajo](#crear-una-oferta-de-trabajo)
3. [Agregar Candidatos](#agregar-candidatos)
4. [Evaluar Candidatos con IA](#evaluar-candidatos-con-ia)
5. [Sincronizar con Zoho/Odoo](#sincronizar-con-zohoodoo)
6. [Enviar WhatsApp](#enviar-whatsapp)
7. [Gestionar el Pipeline](#gestionar-el-pipeline)
8. [Preguntas Frecuentes](#preguntas-frecuentes)

---

## Introducción

Core ATS es un sistema de seguimiento de candidatos diseñado para automatizar y optimizar el proceso de reclutamiento. Permite:

- 📝 Gestionar ofertas de trabajo
- 👥 Administrar candidatos
- 🤖 Evaluar automáticamente con IA
- 🔄 Sincronizar con Zoho Recruit u Odoo
- 📱 Comunicarse por WhatsApp y Email
- 📊 Visualizar el pipeline de reclutamiento

### Roles de Usuario

| Rol | Permisos |
|-----|----------|
| **Super Admin** | Acceso total al sistema, gestión de usuarios, configuración |
| **Consultor** | Crear jobs, gestionar candidatos, evaluaciones, comunicaciones |
| **Viewer** | Solo lectura de jobs y candidatos asignados |

---

## Crear una Oferta de Trabajo

### Paso 1: Acceder al Módulo de Jobs

1. Inicia sesión en el sistema
2. En el menú lateral, haz clic en **"Jobs"** o **"Ofertas"**
3. Verás el listado de ofertas activas

### Paso 2: Crear Nueva Oferta

1. Haz clic en el botón **"Nueva Oferta"** (o **"+ New Job"**)
2. Completa el formulario con la siguiente información:

#### Información Básica
| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **Título** | Nombre del cargo | "Desarrollador Senior Python" |
| **Descripción** | Detalle de responsabilidades y requisitos | Texto completo del JD |
| **Departamento** | Área de la empresa | "Ingeniería" |
| **Ubicación** | Lugar de trabajo | "Remoto", "Santiago, Chile" |
| **Seniority** | Nivel de experiencia requerido | "Senior", "Junior", "Lead" |
| **Sector** | Industria o rubro | "Tecnología", "Retail" |

#### Asignación
- Selecciona el **Consultor** asignado a esta oferta
- El consultor será responsable de gestionar los candidatos

### Paso 3: Guardar y Publicar

1. Haz clic en **"Guardar como Borrador"** para editar después
2. O haz clic en **"Publicar"** para activar la oferta inmediatamente

> 💡 **Tip:** Las ofertas en borrador no son visibles para sincronización externa hasta que se publiquen.

### Paso 4: Obtener Link de Postulación (Opcional)

1. En el detalle de la oferta, haz clic en **"Obtener Link"**
2. Copia el URL para compartir en redes sociales o emails
3. Los candidatos podrán aplicar directamente mediante este link

---

## Agregar Candidatos

### Método 1: Manual (Uno a Uno)

1. Entra al detalle de una oferta de trabajo
2. Haz clic en la pestaña **"Candidatos"**
3. Click en **"+ Agregar Candidato"**
4. Completa los datos:
   - Nombre completo
   - Email
   - Teléfono (con código de país: +569...)
   - CV (adjuntar archivo o pegar texto)
5. Click en **"Guardar"**

### Método 2: Importación Masiva

1. En la página de candidatos, click en **"Importar"**
2. Descarga la plantilla Excel/CSV
3. Completa con los datos de los candidatos
4. Sube el archivo
5. El sistema detectará automáticamente duplicados

### Método 3: Webhook/Integración

Si tienes configurada una integración:
- Los candidatos se agregan automáticamente desde:
  - Formularios web
  - Portales de empleo
  - Zoho Recruit
  - Email de CVs

### Detección de Duplicados

El sistema detecta automáticamente candidatos duplicados por:
- **Email** (normalizado)
- **Teléfono** (normalizado)

Si se detecta un duplicado:
1. El sistema mostrará una alerta
2. Puedes vincular al candidato existente
3. O crear un nuevo registro si es diferente

---

## Evaluar Candidatos con IA

### Evaluación Automática

Cuando agregas un candidato con CV:
1. El sistema procesa automáticamente el CV
2. Extrae información clave (skills, experiencia, educación)
3. Genera una evaluación con IA en 2-5 segundos

### Ver la Evaluación

1. Entra al perfil del candidato
2. Ve a la pestaña **"Evaluación"**
3. Verás:

#### Score General (0-100)
```
┌─────────────────────────────┐
│  Score: 85/100              │
│  ████████████████████░░░    │
│  Decisión: PROCEED ✅       │
└─────────────────────────────┘
```

#### Decisión de IA
- **PROCEED** ✅ - Candidato recomendado, cumple requisitos
- **REVIEW** ⚠️ - Requiere revisión manual, hay aspectos a evaluar
- **REJECT_HARD** ❌ - No cumple filtros duros (ej: ubicación, disponibilidad)

#### Análisis Detallado
| Sección | Descripción |
|---------|-------------|
| **Fortalezas** | Aspectos destacados del candidato (ej: "5+ años Python", "Experiencia en startups") |
| **Gaps** | Áreas donde no cumple 100% (ej: "No tiene AWS", "Inglés intermedio") |
| **Red Flags** | Alertas importantes (ej: "Saltos frecuentes de trabajo", "Falta título universitario") |
| **Evidencia** | Fragmentos del CV que sustentan el análisis |

### Re-generar Evaluación

Si quieres una nueva evaluación:
1. En la pestaña de evaluación, click en **"Re-evaluar"**
2. Opcional: Añade notas de contexto (ej: "Enfócate en experiencia con React")
3. La IA generará una nueva evaluación

### Evaluación Manual

Si prefieres evaluar tú mismo:
1. En el perfil del candidato, click en **"Evaluación Manual"**
2. Asigna un score (0-100)
3. Deja comentarios
4. Toma una decisión: **CONTINUE** o **DISCARD**

---

## Sincronizar con Zoho/Odoo

### Configuración Inicial (Super Admin)

#### Zoho Recruit
1. Ve a **Configuración > Integraciones > Zoho**
2. Ingresa:
   - Client ID
   - Client Secret
   - Redirect URI
3. Click en **"Conectar"**
4. Autoriza la aplicación en Zoho
5. El sistema almacenará el refresh token automáticamente

#### Odoo
1. Ve a **Configuración > Integraciones > Odoo**
2. Ingresa:
   - URL de instancia Odoo
   - Base de datos
   - Usuario y API Key
3. Click en **"Probar Conexión"**
4. Guarda la configuración

### Sincronización de Jobs

#### Push a Zoho (ATS → Zoho)
1. En el detalle de un job, click en **"Sincronizar con Zoho"**
2. El job se creará/actualizará en Zoho Recruit
3. Verás el **Zoho Job ID** asignado

#### Pull desde Zoho (Zoho → ATS)
1. Ve a **Jobs > Sincronización**
2. Click en **"Importar desde Zoho"**
3. Selecciona los jobs a importar
4. Los jobs aparecerán en el listado

### Sincronización de Candidatos

#### Push Candidate
1. En el perfil del candidato, click **"Enviar a Zoho"**
2. El candidato se creará en Zoho con su evaluación
3. Se vinculará automáticamente al Job correspondiente

#### Update Status Bidireccional
- Cuando cambias el estado en ATS → Se actualiza en Zoho
- Cuando cambias el estado en Zoho → Se actualiza en ATS (vía webhook)

### Configuración de Mapeo de Campos

Puedes personalizar qué campos se sincronizan:
1. **Configuración > Integraciones > Zoho > Mapeo**
2. Asocia campos ATS con campos Zoho
3. Ejemplos:
   - `job_openings.title` → `Job_Openings.Job_Title`
   - `candidates.status` → `Candidates.Candidate_Status`

---

## Enviar WhatsApp

### Configuración (Super Admin)

1. Ve a **Configuración > Comunicaciones > WhatsApp**
2. Ingresa:
   - Access Token de Meta
   - Phone Number ID
   - Verify Token para webhooks
3. Configura el webhook en Meta Developer Console
4. Verifica que el estado muestre **"Conectado"**

### Templates Disponibles

Los templates deben estar pre-aprobados por Meta:

| Template | Uso | Variables |
|----------|-----|-----------|
| **bienvenida** | Primer contacto | `{nombre}`, `{puesto}` |
| **seguimiento** | Estado del proceso | `{nombre}`, `{estado}` |
| **entrevista** | Agendar entrevista | `{nombre}`, `{fecha}`, `{link}` |
| **rechazo** | Comunicar rechazo | `{nombre}`, `{puesto}` |
| **oferta** | Enviar oferta | `{nombre}`, `{puesto}`, `{salario}` |

### Enviar Mensaje

1. Entra al perfil del candidato
2. Ve a la pestaña **"Comunicaciones"**
3. Click en **"Enviar WhatsApp"**
4. Selecciona el template
5. Completa las variables:
   - Nombre: Juan Pérez
   - Puesto: Desarrollador Senior
6. Previsualiza el mensaje
7. Click **"Enviar"**

### Ver Estado del Mensaje

El sistema rastrea el estado:
- ⏳ **Pendiente** - En cola de envío
- ✅ **Enviado** - Entregado a WhatsApp
- 📬 **Entregado** - Llegó al teléfono del candidato
- 👁️ **Leído** - El candidato abrió el mensaje
- ❌ **Fallido** - Error de envío (ver detalle)

### Respuestas del Candidato

Cuando el candidato responde:
1. El mensaje aparece en su perfil
2. Puedes responder manualmente
3. O configurar respuestas automáticas (chatbot básico)

---

## Gestionar el Pipeline

### Vista Kanban del Pipeline

En el dashboard principal:
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   NUEVO     │  │  EN REVISIÓN│  │ PRESELECC.  │  │ ENTREVISTA  │
│    (15)     │  │    (8)      │  │    (5)      │  │    (3)      │
├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│ • Juan P.   │  │ • María G.  │  │ • Pedro R.  │  │ • Ana L.    │
│ Score: 85   │  │ Score: 72   │  │ Score: 90   │  │ Score: 88   │
├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│ • Carlos M. │  │ • Luis S.   │  │ • Diego T.  │  │             │
│ Score: 62   │  │ Score: 68   │  │ Score: 85   │  │             │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

### Mover Candidatos entre Etapas

**Método 1: Drag & Drop**
1. Arrastra la tarjeta del candidato a la columna deseada
2. Opcional: Agrega una nota del cambio

**Método 2: Botón de Acción**
1. En el perfil del candidato
2. Click en **"Cambiar Estado"**
3. Selecciona el nuevo estado
4. Opcional: Enviar notificación automática al candidato

### Estados del Pipeline

| Estado | Descripción | Acción Típica |
|--------|-------------|---------------|
| **New** | Recién ingresado | Revisar CV, ejecutar evaluación IA |
| **In Review** | En revisión | Analizar evaluación, decidir continuar |
| **Shortlisted** | Preseleccionado | Contactar candidato, agendar entrevista |
| **Interview** | En entrevistas | Realizar entrevistas, evaluar fit cultural |
| **Offer** | Oferta enviada | Negociar términos, esperar respuesta |
| **Hired** | Contratado | Iniciar onboarding |
| **Discarded** | Descartado | Enviar rechazo, archivar |

### Filtros y Búsqueda

Usa los filtros para encontrar candidatos:
- **Por Job:** Selecciona la oferta específica
- **Por Estado:** Nuevo, En Revisión, etc.
- **Por Score:** Mayor a 80, entre 60-80, etc.
- **Por Decisión IA:** PROCEED, REVIEW, REJECT
- **Por Fecha:** Últimos 7 días, 30 días, etc.
- **Por Texto:** Busca en nombre, email, skills

---

## Preguntas Frecuentes

### General

**¿Puedo usar el sistema en español e inglés?**
> Sí, la interfaz soporta ambos idiomas. Cambia en tu perfil de usuario.

**¿Cómo recupero mi contraseña?**
> En el login, click en "¿Olvidaste tu contraseña?". Recibirás un email para resetearla.

**¿Puedo exportar los datos?**
> Sí, en cada listado hay un botón "Exportar" que genera Excel/CSV.

### Jobs

**¿Qué pasa si borro un Job?**
> Los candidatos asociados NO se borran, quedan sin job asignado (puedes reasignarlos).

**¿Puedo clonar un Job?**
> Sí, en el menú de acciones del job hay "Duplicar". Copia toda la información para editar.

### Candidatos

**¿Cómo detecta duplicados el sistema?**
> Por email y teléfono normalizados. Si juan@email.com y JUAN@EMAIL.COM se detectan como el mismo.

**¿Puedo adjuntar archivos al candidato?**
> Sí, en su perfil hay una sección "Documentos" donde subir CVs, certificados, etc.

**¿Qué pasa si un candidato aplica a múltiples jobs?**
> Se crea un registro por job, pero el sistema marca que es el mismo candidato (vista de duplicados).

### Evaluaciones

**¿Qué modelo de IA usa?**
> Por defecto GPT-4o-mini de OpenAI. Se puede configurar Claude (Anthropic) u otros.

**¿Puedo personalizar los prompts de evaluación?**
> Sí, Super Admin puede editar los prompts en Configuración > IA > Prompts.

**¿Qué tan precisa es la evaluación?**
> Es una herramienta de apoyo. Siempre recomendamos revisión humana, especialmente para decisiones finales.

**¿Puedo desactivar la evaluación automática?**
> Sí, en Configuración > IA > Automatización, desactiva "Evaluación automática al crear candidato".

### Integraciones

**¿Zoho se sincroniza en tiempo real?**
> Push (ATS→Zoho) es inmediato. Pull (Zoho→ATS) puede configurarse en tiempo real (webhook) o periódico (cada 15 min).

**¿Qué pasa si Zoho está caído?**
> El sistema encola las sincronizaciones y reintenta automáticamente.

**¿Puedo usar WhatsApp sin Meta Business?**
> No, necesitas una cuenta de WhatsApp Business API verificada por Meta.

### Soporte

**¿Dónde reporto un bug?**
> Ve a Ayuda > Reportar Problema, o contacta al administrador del sistema.

**¿Cómo solicito una nueva funcionalidad?**
> Envía tu sugerencia a través del formulario en Ayuda > Feedback.

---

## Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl + J` | Ir a Jobs |
| `Ctrl + C` | Ir a Candidatos |
| `Ctrl + E` | Ir a Evaluaciones |
| `Ctrl + N` | Crear nuevo (contexto actual) |
| `Ctrl + F` | Buscar |
| `Ctrl + /` | Mostrar ayuda de atajos |
| `Esc` | Cerrar modal/volver |

---

**Versión:** 1.0  
**Última actualización:** 2026-02-11  
**Para más ayuda:** contacta al equipo de soporte
