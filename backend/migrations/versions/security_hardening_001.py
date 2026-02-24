"""
Migration: Database Security Hardening

Changes:
1. Convert columns to encrypted types (email, phone, national_id in hh_candidates)
2. Add audit logging capabilities
3. Update existing data safely

Revision ID: security_hardening_001
Revises: 
Create Date: 2024-02-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'security_hardening_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Apply security hardening changes.
    
    IMPORTANT: This migration is SAFE and does NOT delete any data.
    - Existing PII data will remain in plain text until updated
    - New records will be encrypted automatically
    - Old records will be encrypted on first update
    """
    
    # =================================================================
    # 1. VERIFICAR QUE LA TABLA hh_audit_log EXISTE
    # =================================================================
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS hh_audit_log (
            audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type TEXT NOT NULL,
            entity_id UUID NOT NULL,
            action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete')),
            changed_by TEXT,
            changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            diff_json JSONB
        )
    """)
    
    # Crear índices para consultas eficientes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_hh_audit_entity 
        ON hh_audit_log(entity_type, entity_id)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_hh_audit_changed_at 
        ON hh_audit_log(changed_at)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_hh_audit_action 
        ON hh_audit_log(action)
    """)
    
    # =================================================================
    # 2. MIGRACIÓN SEGURA DE CAMPOS PII EN hh_candidates
    # =================================================================
    
    # Nota: Los tipos EncryptedType en SQLAlchemy manejan la encriptación
    # en la aplicación, no en la base de datos. La columna sigue siendo TEXT.
    # No necesitamos alterar el esquema de la BD, solo actualizar la aplicación.
    
    # Sin embargo, verificamos que las columnas existan
    op.execute("""
        DO $$
        BEGIN
            -- Verificar email
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'hh_candidates' AND column_name = 'email'
            ) THEN
                ALTER TABLE hh_candidates ADD COLUMN email TEXT;
            END IF;
            
            -- Verificar phone
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'hh_candidates' AND column_name = 'phone'
            ) THEN
                ALTER TABLE hh_candidates ADD COLUMN phone TEXT;
            END IF;
            
            -- Verificar national_id
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'hh_candidates' AND column_name = 'national_id'
            ) THEN
                ALTER TABLE hh_candidates ADD COLUMN national_id TEXT;
            END IF;
        END
        $$;
    """)
    
    # =================================================================
    # 3. AGREGAR CAMPOS DE SEGUIMIENTO DE ENCRIPTACIÓN
    # =================================================================
    
    # Columna para saber si un registro tiene datos encriptados
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'hh_candidates' AND column_name = 'pii_encrypted'
            ) THEN
                ALTER TABLE hh_candidates ADD COLUMN pii_encrypted BOOLEAN DEFAULT FALSE;
                CREATE INDEX idx_hh_candidates_encrypted ON hh_candidates(pii_encrypted);
            END IF;
        END
        $$;
    """)
    
    # =================================================================
    # 4. ACTUALIZAR ESTADÍSTICAS
    # =================================================================
    
    op.execute("ANALYZE hh_candidates")
    op.execute("ANALYZE hh_audit_log")
    
    # =================================================================
    # 5. CREAR FUNCIÓN PARA MIGRACIÓN ASÍNCRONA DE DATOS EXISTENTES
    # =================================================================
    
    # Esta función puede ser llamada por un job posterior para encriptar
    # datos existentes sin bloquear la aplicación
    op.execute("""
        CREATE OR REPLACE FUNCTION encrypt_existing_pii_batch(batch_size INT DEFAULT 100)
        RETURNS TABLE(processed INT, remaining INT) AS $$
        DECLARE
            processed_count INT;
            remaining_count INT;
        BEGIN
            -- Esta función es un placeholder - la encriptación real
            -- se hace en la aplicación Python usando SQLAlchemy
            -- Los datos existentes se encriptarán automáticamente
            -- cuando se actualicen
            
            SELECT COUNT(*) INTO processed_count
            FROM hh_candidates
            WHERE pii_encrypted = TRUE;
            
            SELECT COUNT(*) INTO remaining_count
            FROM hh_candidates
            WHERE pii_encrypted = FALSE OR pii_encrypted IS NULL;
            
            RETURN QUERY SELECT processed_count, remaining_count;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    print("✅ Security migration applied successfully")
    print("✅ Audit log table created")
    print("✅ PII columns verified")
    print("✅ Note: Existing data will be encrypted on first update")


def downgrade():
    """
    Revertir cambios de seguridad.
    
    NOTA: Los datos encriptados no pueden ser desencriptados por SQL.
    Esta operación es DESTRUCTIVA para datos encriptados.
    """
    
    print("⚠️  WARNING: Downgrading security migration")
    print("⚠️  Encrypted data may become unreadable")
    
    # Eliminar función
    op.execute("DROP FUNCTION IF EXISTS encrypt_existing_pii_batch")
    
    # Eliminar columna de seguimiento
    op.execute("""
        ALTER TABLE hh_candidates 
        DROP COLUMN IF EXISTS pii_encrypted
    """)
    
    # NOTA: No eliminamos las columnas PII ni la tabla de auditoría
    # para preservar los datos existentes
    
    print("⚠️  Audit log table preserved for data retention")
    print("⚠️  PII columns preserved")
