# Database Migrations

Este directorio contiene las migraciones de base de datos para el sistema ATS usando Alembic.

## Estructura

```
migrations/
├── versions/          # Archivos de migración
├── env.py            # Configuración del entorno Alembic
├── script.py.mako    # Template para nuevas migraciones
└── README.md         # Este archivo
```

## Comandos Disponibles

Ver scripts en `/scripts/`:

- `migrate.sh` - Ejecutar migraciones pendientes
- `seed.sh` - Cargar datos de prueba (solo desarrollo)
- `reset_db.sh` - Reset completo de la base de datos (solo desarrollo)

## Crear Nueva Migración

```bash
cd /home/andres/.openclaw/workspace/ats-platform/backend
alembic revision --autogenerate -m "descripcion"
```

## Ejecutar Migraciones Manualmente

```bash
# Upgrade
alembic upgrade head

# Downgrade
alembic downgrade -1

# Ver historial
alembic history

# Ver versión actual
alembic current
```

## Convenciones

1. Las migraciones deben ser reversibles (implementar `downgrade()`)
2. Usar transacciones cuando sea posible
3. Documentar cambios significativos en los campos
4. Probar migraciones en ambiente de desarrollo antes de producción

## Modelos Actuales

- `users` - Usuarios del sistema (consultores y admins)
- `configurations` - Configuración del sistema
- `job_openings` - Ofertas laborales
- `candidates` - Candidatos
- `evaluations` - Evaluaciones con IA
- `candidate_decisions` - Decisiones de consultores
- `communications` - Comunicaciones (email, WhatsApp)
- `audit_logs` - Logs de auditoría
