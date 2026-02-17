# Documentación: Formato de Perfiles de Cargo

## Descripción

Esta guía describe el formato esperado para documentos de perfiles de cargo que serán procesados por el sistema de extracción automática.

## Formatos Soportados

- **PDF** (recomendado): Archivos con texto seleccionable (no escaneados)
- **DOCX**: Documentos de Microsoft Word modernos
- **DOC**: Documentos de Word legacy (soporte limitado)
- **TXT**: Archivos de texto plano

## Estructura Recomendada

El documento debe seguir esta estructura para obtener los mejores resultados:

```
TÍTULO DEL CARGO
[Metadatos opcionales: Empresa | Versión | Fecha]

OBJETIVO DEL ROL
[Descripción del propósito principal del cargo]

ESTRUCTURA DEL CARGO
Personas a cargo: [Número y roles]
Reporta a: [Nombre del cargo supervisor]
Nivel: [Junior/Semi-Senior/Senior/Manager/Director/etc]
Modalidad: [Presencial/Remoto/Híbrido]
Ubicación: [Ciudad/País]

RESPONSABILIDADES POR FRENTE
[Categoría 1]:
- Responsabilidad 1
- Responsabilidad 2
- Responsabilidad 3

[Categoría 2]:
- Responsabilidad 1
- Responsabilidad 2

PERFIL REQUERIDO
Formación: [Nivel académico requerido]
Tiempo de Experiencia: [Años de experiencia mínimos]

PERFIL DISC ESPERADO
[Descripción del perfil comportamental]

CONOCIMIENTOS TÉCNICOS:
1. [Conocimiento técnico 1]
2. [Conocimiento técnico 2]
3. [Conocimiento técnico 3]

COMPETENCIAS CLAVE:
- [Competencia 1]
- [Competencia 2]
- [Competencia 3]

HERRAMIENTAS:
- [Herramienta/Software 1]
- [Herramienta/Software 2]

CONDICIONES
Salario: [Rango salarial o "A convenir"]
Beneficios: [Lista de beneficios]
Ubicación: [Dirección o ciudad]
```

## Secciones y Variantes

El sistema reconoce automáticamente las siguientes secciones con estas variantes de nombre:

### 1. Objetivo del Rol
- **Keywords**: "objetivo del rol", "propósito", "misión", "objetivo", "purpose"
- **Contenido**: Párrafo descriptivo del propósito principal del cargo

### 2. Estructura del Cargo
- **Keywords**: "estructura del cargo", "organización", "jerarquía", "structure", "organigrama"
- **Campos reconocidos**:
  - `reports_to`: "reporta a:", "reports to:"
  - `direct_reports`: "personas a cargo:", "equipo a cargo:", "direct reports:"
  - `level`: "nivel:", "level:", "seniority:"
  - `work_mode`: "modalidad:", "work mode:", "modalidad laboral:"
  - `location`: "ubicación:", "lugar:", "location:"

### 3. Responsabilidades
- **Keywords**: "responsabilidades", "funciones", "tareas", "responsibilities", "functions"
- **Formato**: Puede incluir categorías seguidas de dos puntos, o lista simple de bullets

### 4. Perfil Requerido
- **Keywords**: "perfil requerido", "requisitos", "perfil del candidato", "profile", "requirements"
- **Sub-secciones**:
  - Formación/Educación
  - Experiencia/Tiempo de experiencia

### 5. Conocimientos Técnicos
- **Keywords**: "conocimientos técnicos", "skills técnicos", "competencias técnicas", "technical skills"
- **Formato**: Lista numerada o con bullets

### 6. Competencias Clave
- **Keywords**: "competencias clave", "habilidades", "soft skills", "competencies", "skills"
- **Formato**: Lista con bullets

### 7. Perfil DISC
- **Keywords**: "perfil disc", "comportamiento", "estilo", "disc", "behavioral profile"
- **Formato**: Texto descriptivo o combinación de estilos (ej: "Concienzudo + Dominante")

### 8. Herramientas
- **Keywords**: "herramientas", "tools", "software", "aplicaciones", "programs"
- **Formato**: Lista con bullets

### 9. Condiciones
- **Keywords**: "condiciones", "salario", "beneficios", "ubicación", "conditions", "compensation"
- **Campos reconocidos**:
  - `salary_range`: "salario:", "remuneración:", "salary:"
  - `benefits`: "beneficios:"
  - `location`: "ubicación:", "lugar:"
  - `work_schedule`: "horario:", "jornada:"

## Mapeo a Campos del Sistema

Los datos extraídos se mapean a los campos de la vacante de la siguiente manera:

| Campo Extraído | Campo del Sistema |
|----------------|-------------------|
| `role_title` | Título del Cargo |
| `objective` + `responsibilities` | Descripción |
| `requirements.education` + `requirements.experience_years` | Requisitos |
| `skills.technical` | Skills Técnicas |
| `skills.soft` | Skills Blandas |
| `hierarchy.reports_to` | Reporta a |
| `hierarchy.level` | Nivel de Seniority |
| `hierarchy.work_mode` | Modalidad |
| `hierarchy.location` / `conditions.location` | Ubicación |
| `disc_profile` | Metadata (perfil DISC) |
| `tools` | Metadata (herramientas) |

## Ejemplo Completo

```
Director Administrativo y Financiero
NGDS | Perfil de Cargo | Version 1 | Enero 2026

Objetivo del Rol
Garantizar la sostenibilidad financiera y el orden administrativo de la organización mediante la gestión eficiente de recursos, procesos y equipos.

Estructura del Cargo
Personas a cargo: 1 Analista Financiero y de Nómina
Reporta a: CEO y Junta Directiva
Nivel: Dirección
Modalidad: Presencial
Ubicación: Bogotá, Colombia

Responsabilidades por Frente
Financieras:
- Liderar la gestión financiera integral: P&L, flujo de caja y estados financieros
- Evaluar la viabilidad financiera de proyectos y propuestas comerciales
- Gestionar relaciones con entidades bancarias y financieras

Tesorería y Administrativas:
- Gestionar tesorería diaria, pagos a proveedores y conciliaciones bancarias
- Ejecutar y controlar el proceso de nómina completo
- Supervisar la gestión documental y archivo

Perfil Requerido
Formación: Profesional en Finanzas, Administración de Empresas, Contaduría Pública o carreras afines. Especialización o Maestría deseable.
Tiempo de Experiencia: Mínimo 8-10 años en roles financieros, de los cuales al menos 3 en posiciones de dirección.

Perfil DISC Esperado
Concienzudo + Dominante (C + D) o Concienzudo + Influyente (C + I)

Conocimientos Técnicos:
1. Gestión financiera integral y análisis de estados financieros
2. Modelación financiera avanzada en Excel
3. Normativa contable NIIF y tributaria
4. Manejo de ERP financiero (SAP, Oracle o similar)
5. Inglés técnico avanzado

Competencias Clave:
- Criterio financiero orientado a negocio
- Autonomía y responsabilidad
- Sentido de urgencia
- Comunicación efectiva
- Liderazgo de equipos

Herramientas:
- Excel avanzado (tablas dinámicas, macros)
- SAP / Oracle ERP
- Power BI
- Office 365

Condiciones
Salario: A convenir según experiencia
Ubicación: Bogotá, Colombia
Beneficios: Seguro médico, bonificación por desempeño, alimentación
```

## Buenas Prácticas

### Para Mejores Resultados

1. **Use texto seleccionable**: Evite imágenes escaneadas o PDFs generados desde imágenes
2. **Estructura clara**: Use títulos de sección en líneas separadas
3. **Consistencia**: Mantenga un formato uniforme para bullets y numeración
4. **Evite tablas complejas**: El sistema extrae mejor listas simples
5. **Idioma**: El sistema está optimizado para español, pero soporta inglés

### Formatos de Bullets Soportados

- Guiones: `- Item`
- Viñetas: `• Item`
- Asteriscos: `* Item`
- Numeración: `1. Item`, `1) Item`, `1- Item`

### Títulos Reconocidos

El sistema intenta detectar el título del cargo de estas formas:
- Primera línea del documento
- Línea después de "Perfil de Cargo:"
- Línea después de "Job Profile:"
- Patrones comunes de cargos (Manager, Director, Analyst, etc.)

## Solución de Problemas

### El documento no se procesa
- Verifique que el archivo no esté dañado
- Asegúrese de que sea un formato soportado
- Los PDFs escaneados requieren OCR (no soportado nativamente)

### Información no detectada
- Verifique que las secciones tengan nombres reconocidos
- Use los keywords listados arriba
- Asegúrese de que las secciones estén claramente separadas

### Texto extraído incorrecto
- Algunos PDFs con diseño complejo pueden causar problemas
- Intente guardar el documento como TXT para verificar el contenido extraído
- Use DOCX en lugar de DOC cuando sea posible