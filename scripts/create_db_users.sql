-- ============================================================
-- SCRIPT: Creación de usuarios de base de datos con mínimo privilegio
-- ATS Platform - Database Security Hardening
-- ============================================================

-- NOTA: Ejecutar como superusuario (postgres)
-- Este script crea usuarios con principio de mínimo privilegio

-- ============================================================
-- 1. CREAR ROLES
-- ============================================================

-- Rol para la aplicación (operaciones CRUD básicas)
CREATE ROLE ats_app_role;

-- Rol para migraciones (DDL - Data Definition Language)
CREATE ROLE ats_migrator_role;

-- Rol para reportes (solo lectura)
CREATE ROLE ats_readonly_role;

-- ============================================================
-- 2. CONFIGURAR PERMISOS DE ROLES
-- ============================================================

-- Permisos para ats_app_role (SELECT, INSERT, UPDATE, DELETE)
GRANT USAGE ON SCHEMA public TO ats_app_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ats_app_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ats_app_role;

-- Permisos de secuencias (para IDs autoincrementales)
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO ats_app_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO ats_app_role;

-- Permisos para ats_migrator_role (DDL completo)
GRANT ALL PRIVILEGES ON SCHEMA public TO ats_migrator_role;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ats_migrator_role;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ats_migrator_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ats_migrator_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ats_migrator_role;

-- Permisos para ats_readonly_role (solo SELECT)
GRANT USAGE ON SCHEMA public TO ats_readonly_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ats_readonly_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ats_readonly_role;

-- ============================================================
-- 3. CREAR USUARIOS CON CONTRASEÑAS SEGURAS
-- ============================================================

-- Usuario para la aplicación
-- NOTA: Cambiar 'change_this_secure_password' por una contraseña segura en producción
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ats_app') THEN
        CREATE USER ats_app WITH PASSWORD 'change_this_secure_password_app';
    END IF;
END
$$;

-- Usuario para migraciones
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ats_migrator') THEN
        CREATE USER ats_migrator WITH PASSWORD 'change_this_secure_password_migrator';
    END IF;
END
$$;

-- Usuario para reportes
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ats_readonly') THEN
        CREATE USER ats_readonly WITH PASSWORD 'change_this_secure_password_readonly';
    END IF;
END
$$;

-- ============================================================
-- 4. ASIGNAR ROLES A USUARIOS
-- ============================================================

GRANT ats_app_role TO ats_app;
GRANT ats_migrator_role TO ats_migrator;
GRANT ats_readonly_role TO ats_readonly;

-- ============================================================
-- 5. RESTRICCIONES ADICIONALES DE SEGURIDAD
-- ============================================================

-- Limitar conexiones concurrentes
ALTER ROLE ats_app WITH CONNECTION LIMIT 50;
ALTER ROLE ats_migrator WITH CONNECTION LIMIT 5;
ALTER ROLE ats_readonly WITH CONNECTION LIMIT 10;

-- Expiración de contraseñas (opcional - descomentar si se desea)
-- ALTER ROLE ats_app VALID UNTIL '2025-12-31';
-- ALTER ROLE ats_migrator VALID UNTIL '2025-12-31';
-- ALTER ROLE ats_readonly VALID UNTIL '2025-12-31';

-- ============================================================
-- 6. VERIFICACIÓN
-- ============================================================

-- Verificar roles creados
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin 
FROM pg_roles 
WHERE rolname LIKE 'ats_%';

-- Verificar permisos en tablas
SELECT grantee, table_name, privilege_type 
FROM information_schema.table_privileges 
WHERE grantee LIKE 'ats_%'
ORDER BY grantee, table_name;

-- ============================================================
-- NOTAS IMPORTANTES:
-- ============================================================
-- 1. Cambiar las contraseñas antes de ejecutar en producción
-- 2. Las contraseñas deben tener al menos 16 caracteres, mezclando:
--    - Mayúsculas y minúsculas
--    - Números
--    - Caracteres especiales
-- 3. Ejemplo de contraseña segura: At$P_2024!App#Secure99
-- 4. Almacenar contraseñas en un gestor de secretos (Vault, AWS Secrets Manager, etc.)
-- 5. Rotar contraseñas cada 90 días
-- ============================================================
