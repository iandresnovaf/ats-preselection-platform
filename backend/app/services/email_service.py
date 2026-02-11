"""Servicio de Email para notificaciones."""
import logging
import smtplib
import ssl
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import mimetypes

from jinja2 import Template
from tenacity import retry, stop_after_attempt, wait_exponential

from app.schemas import EmailConfig
from app.services.configuration_service import ConfigurationService

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para envío de emails."""
    
    # Templates predefinidos
    TEMPLATES = {
        "candidate_received": {
            "subject": "Hemos recibido tu aplicación - {{job_title}}",
            "body": """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>¡Hola {{candidate_name}}!</h2>
    <p>Hemos recibido tu aplicación para el puesto de <strong>{{job_title}}</strong>.</p>
    <p>Nuestro equipo revisará tu perfil y nos pondremos en contacto contigo en los próximos días.</p>
    <p>Mientras tanto, puedes visitar nuestra web para conocer más sobre nosotros.</p>
    <br>
    <p>Saludos cordiales,</p>
    <p><strong>Equipo de Reclutamiento</strong></p>
</body>
</html>
"""
        },
        "evaluation_complete": {
            "subject": "Actualización sobre tu aplicación - {{job_title}}",
            "body": """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>¡Hola {{candidate_name}}!</h2>
    <p>Hemos completado la revisión inicial de tu aplicación para <strong>{{job_title}}</strong>.</p>
    <p>{{message}}</p>
    <br>
    <p>Saludos cordiales,</p>
    <p><strong>Equipo de Reclutamiento</strong></p>
</body>
</html>
"""
        },
        "interview_invitation": {
            "subject": "Invitación a entrevista - {{job_title}}",
            "body": """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>¡Hola {{candidate_name}}!</h2>
    <p>Nos complace invitarte a una entrevista para el puesto de <strong>{{job_title}}</strong>.</p>
    <p><strong>Fecha:</strong> {{interview_date}}</p>
    <p><strong>Modalidad:</strong> {{interview_mode}}</p>
    {{#if interview_link}}
    <p><strong>Enlace:</strong> <a href="{{interview_link}}">{{interview_link}}</a></p>
    {{/if}}
    <p>Por favor confirma tu asistencia respondiendo a este email.</p>
    <br>
    <p>Saludos cordiales,</p>
    <p><strong>Equipo de Reclutamiento</strong></p>
</body>
</html>
"""
        },
        "application_rejected": {
            "subject": "Actualización sobre tu aplicación - {{job_title}}",
            "body": """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>Hola {{candidate_name}},</h2>
    <p>Agradecemos tu interés en el puesto de <strong>{{job_title}}</strong>.</p>
    <p>Después de una cuidadosa revisión, hemos decidido continuar con otros candidatos cuyos perfiles se ajustan más a nuestras necesidades actuales.</p>
    <p>Te deseamos éxito en tu búsqueda profesional.</p>
    <br>
    <p>Saludos cordiales,</p>
    <p><strong>Equipo de Reclutamiento</strong></p>
</body>
</html>
"""
        },
        "password_reset": {
            "subject": "Recuperación de contraseña",
            "body": """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>Hola {{user_name}},</h2>
    <p>Has solicitado restablecer tu contraseña.</p>
    <p>Haz clic en el siguiente enlace para crear una nueva contraseña:</p>
    <p><a href="{{reset_link}}" style="background: #0066cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Restablecer Contraseña</a></p>
    <p>Este enlace expirará en {{expiry_hours}} horas.</p>
    <p>Si no solicitaste este cambio, puedes ignorar este email.</p>
    <br>
    <p>Saludos cordiales,</p>
    <p><strong>Soporte Técnico</strong></p>
</body>
</html>
"""
        }
    }
    
    def __init__(self, config: Optional[EmailConfig] = None):
        """Inicializa el servicio de email.
        
        Args:
            config: Configuración SMTP. Si es None, se carga desde BD.
        """
        self.config = config
        self._smtp_server: Optional[smtplib.SMTP] = None
        
    async def initialize(self, db_session=None):
        """Inicializa el servicio cargando configuración si es necesario."""
        if self.config is None and db_session:
            service = ConfigurationService(db_session)
            self.config = await service.get_email_config()
            
        if self.config is None:
            raise ValueError("No email configuration found")
            
        logger.info(f"Email service initialized with provider: {self.config.provider}")
    
    def _connect_smtp(self) -> smtplib.SMTP:
        """Establece conexión SMTP."""
        context = ssl.create_default_context()
        
        if self.config.use_tls:
            server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            server.starttls(context=context)
        else:
            server = smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port, context=context)
        
        server.login(self.config.smtp_user, self.config.smtp_password)
        return server
    
    @retry(
        retry=retry_if_exception_type((smtplib.SMTPException, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _send_email_smtp(
        self, 
        to: str, 
        subject: str, 
        body: str, 
        attachments: Optional[List[Dict[str, Any]]] = None,
        is_html: bool = True
    ) -> bool:
        """Envía email via SMTP con retry logic.
        
        Args:
            to: Destinatario
            subject: Asunto
            body: Cuerpo del mensaje
            attachments: Lista de archivos adjuntos
            is_html: Si el cuerpo es HTML
            
        Returns:
            True si se envió correctamente
        """
        msg = MIMEMultipart()
        msg['From'] = f"{self.config.default_from_name} <{self.config.default_from}>"
        msg['To'] = to
        msg['Subject'] = subject
        
        # Cuerpo del mensaje
        content_type = 'html' if is_html else 'plain'
        msg.attach(MIMEText(body, content_type, 'utf-8'))
        
        # Adjuntos
        if attachments:
            for attachment in attachments:
                filepath = attachment.get('path')
                filename = attachment.get('filename', Path(filepath).name if filepath else 'attachment')
                content = attachment.get('content')
                
                if filepath and Path(filepath).exists():
                    with open(filepath, 'rb') as f:
                        content = f.read()
                
                if content:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{filename}"'
                    )
                    msg.attach(part)
        
        # Enviar
        server = self._connect_smtp()
        try:
            server.sendmail(self.config.default_from, to, msg.as_string())
            logger.info(f"Email sent successfully to {to}")
            return True
        finally:
            server.quit()
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        is_html: bool = True
    ) -> bool:
        """Envía un email.
        
        Args:
            to: Destinatario
            subject: Asunto
            body: Cuerpo del mensaje
            attachments: Archivos adjuntos
            is_html: Si es HTML
            
        Returns:
            True si se envió correctamente
        """
        if not self.config:
            raise ValueError("Email service not initialized")
        
        try:
            # SMTP es bloqueante, ejecutar en thread
            import asyncio
            return await asyncio.to_thread(
                self._send_email_smtp,
                to, subject, body, attachments, is_html
            )
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False
    
    def _render_template(self, template_name: str, variables: Dict[str, Any]) -> tuple[str, str]:
        """Renderiza una plantilla.
        
        Args:
            template_name: Nombre de la plantilla
            variables: Variables para renderizar
            
        Returns:
            Tuple (subject, body)
        """
        template = self.TEMPLATES.get(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Renderizar usando Jinja2
        subject_template = Template(template["subject"])
        body_template = Template(template["body"])
        
        subject = subject_template.render(**variables)
        body = body_template.render(**variables)
        
        return subject, body
    
    async def send_template_email(
        self,
        to: str,
        template_name: str,
        variables: Dict[str, Any],
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Envía un email usando una plantilla.
        
        Args:
            to: Destinatario
            template_name: Nombre de la plantilla
            variables: Variables para renderizar
            attachments: Archivos adjuntos
            
        Returns:
            True si se envió correctamente
        """
        try:
            subject, body = self._render_template(template_name, variables)
            return await self.send_email(to, subject, body, attachments, is_html=True)
        except Exception as e:
            logger.error(f"Failed to send template email: {e}")
            return False
    
    async def send_candidate_notification(
        self,
        candidate: Dict[str, Any],
        template: str,
        extra_variables: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Envía notificación a un candidato.
        
        Args:
            candidate: Datos del candidato
            template: Nombre de la plantilla
            extra_variables: Variables adicionales
            
        Returns:
            True si se envió correctamente
        """
        email = candidate.get('email')
        if not email:
            logger.warning(f"No email for candidate {candidate.get('id')}")
            return False
        
        variables = {
            "candidate_name": candidate.get('full_name', 'Candidato'),
            "candidate_email": email,
            "candidate_phone": candidate.get('phone', ''),
        }
        
        if extra_variables:
            variables.update(extra_variables)
        
        return await self.send_template_email(email, template, variables)
    
    async def test_connection(self) -> tuple[bool, str]:
        """Prueba la conexión SMTP.
        
        Returns:
            Tuple (success, message)
        """
        try:
            server = self._connect_smtp()
            server.quit()
            return True, "Conexión SMTP exitosa"
        except Exception as e:
            return False, f"Error de conexión: {str(e)}"


# Singleton
_email_service: Optional[EmailService] = None


async def get_email_service(db_session=None) -> EmailService:
    """Obtiene instancia singleton del servicio de email."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
        await _email_service.initialize(db_session)
    return _email_service
