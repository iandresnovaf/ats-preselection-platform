"""
Servicio de Multi-Factor Authentication (MFA) usando TOTP.
Implementa Google Authenticator compatible.
"""
import secrets
import hashlib
import base64
from typing import Optional, List, Tuple
from urllib.parse import quote
import pyotp
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_value, decrypt_value
from app.models import User, UserRole


class MFAService:
    """Servicio para gestionar MFA/TOTP."""
    
    # Número de códigos de respaldo
    BACKUP_CODES_COUNT = 10
    # Longitud de cada código de respaldo
    BACKUP_CODE_LENGTH = 8
    
    @staticmethod
    def generate_secret() -> str:
        """Genera un nuevo secret TOTP."""
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp_uri(secret: str, user_email: str, issuer: str = "ATS Platform") -> str:
        """
        Genera la URI para QR code (Google Authenticator).
        
        Args:
            secret: Secret TOTP
            user_email: Email del usuario
            issuer: Nombre del emisor
        
        Returns:
            URI otpauth://
        """
        # Escapar valores para URL
        account_name = quote(user_email)
        issuer_name = quote(issuer)
        
        uri = (
            f"otpauth://totp/{issuer_name}:{account_name}"
            f"?secret={secret}"
            f"&issuer={issuer_name}"
            f"&algorithm=SHA1"
            f"&digits=6"
            f"&period=30"
        )
        return uri
    
    @staticmethod
    def generate_qr_code(uri: str) -> str:
        """
        Genera un QR code en base64 para el URI TOTP.
        
        Args:
            uri: URI otpauth://
        
        Returns:
            Data URI con imagen PNG base64
        """
        try:
            import qrcode
            from io import BytesIO
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
        except ImportError:
            # Si qrcode no está disponible, retornar solo el URI
            return uri
    
    @staticmethod
    def verify_totp(secret: str, token: str) -> bool:
        """
        Verifica un código TOTP.
        
        Args:
            secret: Secret TOTP del usuario
            token: Código ingresado por el usuario
        
        Returns:
            True si el código es válido
        """
        if not secret or not token:
            return False
        
        # Limpiar token
        token = token.strip().replace(" ", "")
        
        # Verificar que sea numérico
        if not token.isdigit():
            return False
        
        # Verificar longitud
        if len(token) != 6:
            return False
        
        try:
            totp = pyotp.TOTP(secret)
            # Valid_window=1 permite 1 paso de tiempo antes/después (30 segundos de tolerancia)
            return totp.verify(token, valid_window=1)
        except Exception:
            return False
    
    @staticmethod
    def generate_backup_codes() -> Tuple[List[str], List[str]]:
        """
        Genera códigos de respaldo.
        
        Returns:
            Tuple de (códigos_planos, códigos_hasheados)
        """
        plain_codes = []
        hashed_codes = []
        
        for _ in range(MFAService.BACKUP_CODES_COUNT):
            # Generar código alfanumérico
            code = secrets.token_hex(MFAService.BACKUP_CODE_LENGTH // 2).upper()
            plain_codes.append(code)
            
            # Hashear para almacenar
            hashed = hashlib.sha256(code.encode()).hexdigest()
            hashed_codes.append(hashed)
        
        return plain_codes, hashed_codes
    
    @staticmethod
    def verify_backup_code(plain_code: str, hashed_codes: List[str]) -> bool:
        """
        Verifica un código de respaldo.
        
        Args:
            plain_code: Código ingresado por el usuario
            hashed_codes: Lista de códigos hasheados almacenados
        
        Returns:
            True si el código es válido
        """
        if not plain_code or not hashed_codes:
            return False
        
        plain_code = plain_code.strip().upper().replace(" ", "")
        code_hash = hashlib.sha256(plain_code.encode()).hexdigest()
        
        return code_hash in hashed_codes
    
    @classmethod
    async def setup_mfa(cls, user: User, db: AsyncSession) -> dict:
        """
        Inicia la configuración de MFA para un usuario.
        
        Args:
            user: Usuario a configurar
            db: Sesión de base de datos
        
        Returns:
            Dict con secret, qr_code_uri y backup_codes
        """
        # Generar secret
        secret = cls.generate_secret()
        
        # Generar códigos de respaldo
        plain_backup_codes, hashed_backup_codes = cls.generate_backup_codes()
        
        # Guardar en usuario (aún no habilitado hasta verificación)
        encrypted_secret = encrypt_value(secret)
        user.mfa_secret = encrypted_secret
        user.mfa_backup_codes = hashed_backup_codes
        user.mfa_enabled = False  # Se habilita después de verificación
        
        await db.flush()
        
        # Generar URI y QR
        uri = cls.get_totp_uri(secret, user.email)
        qr_code = cls.generate_qr_code(uri)
        
        return {
            "secret": secret,  # Mostrar una sola vez
            "qr_code_uri": uri,
            "qr_code_image": qr_code,
            "backup_codes": plain_backup_codes,  # Mostrar una sola vez
        }
    
    @classmethod
    async def verify_and_enable_mfa(
        cls, 
        user: User, 
        token: str, 
        db: AsyncSession
    ) -> bool:
        """
        Verifica el código TOTP y habilita MFA.
        
        Args:
            user: Usuario
            token: Código TOTP de verificación
            db: Sesión de base de datos
        
        Returns:
            True si se habilitó correctamente
        """
        if not user.mfa_secret:
            return False
        
        try:
            secret = decrypt_value(user.mfa_secret)
        except Exception:
            return False
        
        if not cls.verify_totp(secret, token):
            return False
        
        # Habilitar MFA
        user.mfa_enabled = True
        await db.flush()
        
        return True
    
    @classmethod
    async def verify_mfa_login(
        cls, 
        user: User, 
        token: str
    ) -> bool:
        """
        Verifica MFA durante login.
        
        Args:
            user: Usuario
            token: Código TOTP o código de respaldo
        
        Returns:
            True si la verificación es exitosa
        """
        if not user.mfa_enabled or not user.mfa_secret:
            return True  # MFA no está habilitado
        
        try:
            secret = decrypt_value(user.mfa_secret)
        except Exception:
            return False
        
        # Intentar verificar como TOTP
        if cls.verify_totp(secret, token):
            return True
        
        # Intentar verificar como código de respaldo
        if user.mfa_backup_codes:
            if cls.verify_backup_code(token, user.mfa_backup_codes):
                # Remover código de respaldo usado (one-time use)
                plain_code = token.strip().upper().replace(" ", "")
                code_hash = hashlib.sha256(plain_code.encode()).hexdigest()
                user.mfa_backup_codes = [
                    c for c in user.mfa_backup_codes if c != code_hash
                ]
                return True
        
        return False
    
    @classmethod
    async def disable_mfa(
        cls, 
        user: User, 
        password: str,
        current_user: User,
        db: AsyncSession
    ) -> bool:
        """
        Deshabilita MFA para un usuario.
        
        Args:
            user: Usuario a deshabilitar MFA
            password: Contraseña para verificar
            current_user: Usuario que realiza la acción
            db: Sesión de base de datos
        
        Returns:
            True si se deshabilitó correctamente
        """
        from app.core.auth import verify_password
        
        # Solo super admins pueden deshabilitar MFA de otros usuarios
        # Los usuarios normales solo pueden deshabilitar su propio MFA
        if user.id != current_user.id and current_user.role != UserRole.SUPER_ADMIN:
            return False
        
        # Verificar contraseña
        if not verify_password(password, user.hashed_password):
            return False
        
        # Limpiar datos MFA
        user.mfa_secret = None
        user.mfa_enabled = False
        user.mfa_backup_codes = None
        
        await db.flush()
        
        return True
    
    @classmethod
    def requires_mfa(cls, user: User) -> bool:
        """
        Determina si el usuario debe usar MFA.
        Por ahora, solo requerido para admins.
        
        Args:
            user: Usuario
        
        Returns:
            True si debe usar MFA
        """
        if user.role == UserRole.SUPER_ADMIN:
            return True
        
        # Si el usuario ya tiene MFA habilitado, seguir requiriendo
        if user.mfa_enabled:
            return True
        
        return False
