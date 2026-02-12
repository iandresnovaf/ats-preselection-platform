"""LinkedIn connector for candidate profile extraction.

Implements OAuth2 authentication and profile data extraction
using LinkedIn API (compliance with LinkedIn's terms of service).
"""
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.integrations.base import (
    BaseConnector,
    CircuitBreakerConfig,
    RateLimitConfig,
    SyncResult,
    with_retry,
)
from app.models import Candidate
from app.schemas import ConfigurationCreate

logger = logging.getLogger(__name__)


@dataclass
class LinkedInRateLimits:
    """Rate limits de LinkedIn API.
    
    LinkedIn tiene límites bastante restrictivos:
    - Basic profile: 500 requests/día
    - Compartir contenido: 10 posts/día
    - Mensajes: 100/día
    """
    REQUESTS_PER_DAY = 500
    REQUESTS_PER_SECOND = 0.1  # Muy conservador
    BURST_SIZE = 5


@dataclass
class LinkedInProfile:
    """Perfil de LinkedIn parseado."""
    linkedin_id: str
    linkedin_url: str
    first_name: str
    last_name: str
    full_name: str
    headline: Optional[str] = None
    summary: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    
    # Experiencia
    experience: List[Dict] = None
    
    # Educación
    education: List[Dict] = None
    
    # Skills
    skills: List[str] = None
    
    # Idiomas
    languages: List[Dict] = None
    
    def __post_init__(self):
        if self.experience is None:
            self.experience = []
        if self.education is None:
            self.education = []
        if self.skills is None:
            self.skills = []
        if self.languages is None:
            self.languages = []
    
    def to_candidate_data(self) -> Dict[str, Any]:
        """Convertir a datos de candidato."""
        return {
            "full_name": self.full_name,
            "email": self.email,
            "linkedin_url": self.linkedin_url,
            "extracted_experience": self.experience,
            "extracted_education": self.education,
            "extracted_skills": self.skills,
            "raw_data": {
                "linkedin_id": self.linkedin_id,
                "headline": self.headline,
                "summary": self.summary,
                "industry": self.industry,
                "location": self.location,
                "languages": self.languages,
            }
        }


@dataclass
class LinkedInTokens:
    """Tokens OAuth de LinkedIn."""
    access_token: str
    refresh_token: Optional[str]
    expires_at: datetime
    scope: str


class LinkedInConnector(BaseConnector):
    """Conector para LinkedIn API.
    
    IMPORTANTE: LinkedIn tiene políticas muy restrictivas sobre scraping
    y uso de datos. Este conector usa solamente:
    - OAuth2 para autenticación del usuario
    - API oficial de LinkedIn (con permisos apropiados)
    - Extracción de datos que el usuario autoriza explícitamente
    
    Scopes necesarios:
    - r_liteprofile: Perfil básico (nombre, foto, headline)
    - r_emailaddress: Email del usuario
    - r_basicprofile: Perfil completo (experiencia, educación)
    - r_fullprofile: (deprecated) Requiere partnership
    """
    
    # OAuth2 endpoints
    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    
    # API endpoints
    API_BASE_URL = "https://api.linkedin.com/v2"
    
    # Scopes mínimos necesarios (compliance con LinkedIn)
    SCOPES = [
        "r_liteprofile",      # Perfil básico
        "r_emailaddress",     # Email
        "r_basicprofile",     # Experiencia, educación
    ]
    
    def __init__(
        self,
        db: AsyncSession,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8000/api/v1/linkedin/callback"
    ):
        rate_config = RateLimitConfig(
            requests_per_second=LinkedInRateLimits.REQUESTS_PER_SECOND,
            burst_size=LinkedInRateLimits.BURST_SIZE,
            max_retries=3,
            base_delay=2.0,
            max_delay=60.0
        )
        circuit_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=300,  # 5 minutos (LinkedIn es estricto)
            half_open_max_calls=1,
            success_threshold=1
        )
        
        # Crear config dummy para BaseConnector
        config = type('Config', (), {
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri
        })()
        
        super().__init__(db, config, rate_config, circuit_config)
        self.tokens: Optional[LinkedInTokens] = None
    
    async def __aenter__(self):
        await super().__aenter__()
        return self
    
    @with_retry(max_retries=2, base_delay=2.0)
    async def authenticate(self) -> bool:
        """Autenticar con LinkedIn.
        
        Nota: LinkedIn requiere que el usuario autorice manualmente
        mediante OAuth2. Este método verifica si tenemos tokens válidos.
        
        Returns:
            True si tenemos tokens válidos.
        """
        cached_tokens = await self._get_cached("tokens")
        if cached_tokens:
            self.tokens = LinkedInTokens(**cached_tokens)
            if self.tokens.expires_at > datetime.utcnow() + timedelta(minutes=5):
                return True
            # Refrescar si es necesario
            if self.tokens.refresh_token:
                return await self._refresh_access_token()
        
        return False
    
    async def _refresh_access_token(self) -> bool:
        """Refrescar access token.
        
        Nota: LinkedIn no siempre devuelve refresh_token.
        Depende del flujo OAuth2 utilizado.
        """
        if not self.tokens or not self.tokens.refresh_token:
            return False
        
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.tokens.refresh_token,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
            }
            
            response = await self._make_request(
                "POST",
                self.TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                params=data  # LinkedIn espera params para POST de token
            )
            
            token_data = response.json()
            
            expires_in = token_data.get("expires_in", 3600)
            self.tokens = LinkedInTokens(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token") or self.tokens.refresh_token,
                expires_at=datetime.utcnow() + timedelta(seconds=expires_in - 300),
                scope=token_data.get("scope", "")
            )
            
            await self._set_cached("tokens", {
                "access_token": self.tokens.access_token,
                "refresh_token": self.tokens.refresh_token,
                "expires_at": self.tokens.expires_at.isoformat(),
                "scope": self.tokens.scope
            }, ttl=expires_in - 300)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh LinkedIn token: {e}")
            return False
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Obtener headers de autorización."""
        if not self.tokens:
            raise RuntimeError("Not authenticated")
        return {
            "Authorization": f"Bearer {self.tokens.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json"
        }
    
    async def test_connection(self) -> Tuple[bool, str]:
        """Probar conexión con LinkedIn.
        
        Returns:
            (success, message)
        """
        try:
            # Verificar token obteniendo perfil básico
            response = await self._make_request(
                "GET",
                f"{self.API_BASE_URL}/me",
                headers=self._get_auth_headers()
            )
            
            data = response.json()
            first_name = data.get("firstName", {}).get("localized", {}).get("es_ES") or \
                        data.get("firstName", {}).get("localized", {}).get("en_US", "Unknown")
            
            return True, f"Connected to LinkedIn as {first_name}"
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return False, "Authentication failed: Invalid or expired token"
            return False, f"HTTP Error: {e.response.status_code}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def get_auth_url(self, state: Optional[str] = None) -> str:
        """Generar URL de autorización OAuth2.
        
        Args:
            state: Estado para prevenir CSRF
            
        Returns:
            URL de autorización
        """
        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.SCOPES),
        }
        
        if state:
            params["state"] = state
        
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, code: str) -> Tuple[bool, Dict[str, Any]]:
        """Intercambiar código de autorización por tokens.
        
        Args:
            code: Código de autorización
            
        Returns:
            (success, data)
        """
        try:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.config.redirect_uri,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
            }
            
            response = await self._make_request(
                "POST",
                self.TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                params=data
            )
            
            token_data = response.json()
            
            expires_in = token_data.get("expires_in", 3600)
            self.tokens = LinkedInTokens(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_at=datetime.utcnow() + timedelta(seconds=expires_in - 300),
                scope=token_data.get("scope", "")
            )
            
            await self._set_cached("tokens", {
                "access_token": self.tokens.access_token,
                "refresh_token": self.tokens.refresh_token,
                "expires_at": self.tokens.expires_at.isoformat(),
                "scope": self.tokens.scope
            }, ttl=expires_in - 300)
            
            return True, token_data
            
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            return False, {"error": str(e)}
    
    # ==================== PROFILE EXTRACTION ====================
    
    async def get_profile(self, person_id: Optional[str] = None) -> Optional[LinkedInProfile]:
        """Obtener perfil de LinkedIn.
        
        Args:
            person_id: ID del perfil (si None, obtiene el perfil del usuario autenticado)
            
        Returns:
            Perfil parseado o None
        """
        try:
            # Obtener perfil básico
            profile_url = f"{self.API_BASE_URL}/me"
            if person_id:
                profile_url = f"{self.API_BASE_URL}/people/(id:{person_id})"
            
            response = await self._make_request(
                "GET",
                profile_url,
                headers=self._get_auth_headers()
            )
            
            profile_data = response.json()
            
            # Obtener email (requiere scope separado)
            email = await self._get_email()
            
            # Construir perfil
            profile = LinkedInProfile(
                linkedin_id=profile_data.get("id"),
                linkedin_url=f"https://www.linkedin.com/in/{profile_data.get('vanityName', profile_data.get('id'))}",
                first_name=self._get_localized_value(profile_data.get("firstName", {})),
                last_name=self._get_localized_value(profile_data.get("lastName", {})),
                full_name="",
                headline=self._get_localized_value(profile_data.get("headline", {})),
                summary=self._get_localized_value(profile_data.get("summary", {})),
                industry=profile_data.get("industryName"),
                location=self._get_location(profile_data.get("location", {})),
                email=email
            )
            
            profile.full_name = f"{profile.first_name} {profile.last_name}".strip()
            
            # Obtener experiencia (requiere r_basicprofile)
            profile.experience = await self._get_experience(profile.linkedin_id)
            
            # Obtener educación
            profile.education = await self._get_education(profile.linkedin_id)
            
            # Obtener skills
            profile.skills = await self._get_skills(profile.linkedin_id)
            
            return profile
            
        except Exception as e:
            logger.error(f"Failed to get LinkedIn profile: {e}")
            return None
    
    async def _get_email(self) -> Optional[str]:
        """Obtener email del usuario autenticado."""
        try:
            response = await self._make_request(
                "GET",
                f"{self.API_BASE_URL}/emailAddress?q=members&projection=(elements*(handle~))",
                headers=self._get_auth_headers()
            )
            
            data = response.json()
            elements = data.get("elements", [])
            if elements:
                return elements[0].get("handle~", {}).get("emailAddress")
            return None
            
        except Exception as e:
            logger.warning(f"Could not get email: {e}")
            return None
    
    async def _get_experience(self, person_id: str) -> List[Dict]:
        """Obtener experiencia laboral."""
        try:
            response = await self._make_request(
                "GET",
                f"{self.API_BASE_URL}/positions",
                headers=self._get_auth_headers()
            )
            
            # LinkedIn API v2 usa projection para campos
            # Nota: La API pública tiene limitaciones
            # Para datos completos se necesita el programa de partners
            
            data = response.json()
            positions = []
            
            for position in data.get("elements", []):
                positions.append({
                    "title": position.get("title"),
                    "company": position.get("companyName"),
                    "location": position.get("locationName"),
                    "start_date": self._parse_date(position.get("startDate")),
                    "end_date": self._parse_date(position.get("endDate")),
                    "current": position.get("endDate") is None,
                    "description": position.get("description"),
                })
            
            return positions
            
        except Exception as e:
            logger.warning(f"Could not get experience: {e}")
            return []
    
    async def _get_education(self, person_id: str) -> List[Dict]:
        """Obtener educación."""
        try:
            response = await self._make_request(
                "GET",
                f"{self.API_BASE_URL}/educations",
                headers=self._get_auth_headers()
            )
            
            data = response.json()
            educations = []
            
            for edu in data.get("elements", []):
                educations.append({
                    "school": edu.get("schoolName"),
                    "degree": edu.get("degreeName"),
                    "field": edu.get("fieldOfStudy"),
                    "start_year": edu.get("startDate", {}).get("year"),
                    "end_year": edu.get("endDate", {}).get("year"),
                })
            
            return educations
            
        except Exception as e:
            logger.warning(f"Could not get education: {e}")
            return []
    
    async def _get_skills(self, person_id: str) -> List[str]:
        """Obtener skills."""
        try:
            # LinkedIn API v2 requiere permisos especiales para skills
            # Este endpoint puede no estar disponible en la API básica
            response = await self._make_request(
                "GET",
                f"{self.API_BASE_URL}/skills",
                headers=self._get_auth_headers()
            )
            
            data = response.json()
            skills = []
            
            for skill in data.get("elements", []):
                skill_name = skill.get("name")
                if skill_name:
                    skills.append(skill_name)
            
            return skills
            
        except Exception as e:
            logger.warning(f"Could not get skills: {e}")
            return []
    
    def _get_localized_value(self, field_data: Dict) -> str:
        """Obtener valor localizado de un campo."""
        if not field_data:
            return ""
        
        localized = field_data.get("localized", {})
        
        # Intentar español primero
        for key in localized:
            if key.startswith("es"):
                return localized[key]
        
        # Luego inglés
        for key in localized:
            if key.startswith("en"):
                return localized[key]
        
        # Cualquier otro
        if localized:
            return list(localized.values())[0]
        
        return ""
    
    def _get_location(self, location_data: Dict) -> Optional[str]:
        """Obtener ubicación formateada."""
        if not location_data:
            return None
        
        location = location_data.get("name")
        if location:
            return location
        
        # Intentar construir de campos
        parts = []
        if "country" in location_data:
            parts.append(location_data["country"])
        if "city" in location_data:
            parts.append(location_data["city"])
        
        return ", ".join(parts) if parts else None
    
    def _parse_date(self, date_data: Optional[Dict]) -> Optional[str]:
        """Parsear fecha de LinkedIn."""
        if not date_data:
            return None
        
        year = date_data.get("year")
        month = date_data.get("month")
        
        if year and month:
            return f"{year}-{month:02d}"
        elif year:
            return str(year)
        return None
    
    # ==================== CANDIDATE IMPORT ====================
    
    async def import_candidate_from_url(
        self,
        linkedin_url: str,
        job_opening_id: Optional[str] = None
    ) -> Tuple[bool, Optional[Candidate], str]:
        """Importar candidato desde URL de LinkedIn.
        
        IMPORTANTE: Esta función solo funciona si:
        1. El candidato ha autorizado nuestra app
        2. Tenemos access_token válido
        
        Para candidatos que no han autorizado, se debe usar
        el flujo de "Apply with LinkedIn" o pedirle que complete
        un formulario.
        
        Args:
            linkedin_url: URL del perfil de LinkedIn
            job_opening_id: ID de la vacante opcional
            
        Returns:
            (success, candidate, message)
        """
        try:
            # Validar URL
            if not self._validate_linkedin_url(linkedin_url):
                return False, None, "Invalid LinkedIn URL"
            
            # Extraer ID de la URL (si es posible)
            person_id = self._extract_person_id_from_url(linkedin_url)
            
            # Obtener perfil
            profile = await self.get_profile(person_id)
            
            if not profile:
                return False, None, "Could not retrieve LinkedIn profile"
            
            # Verificar si ya existe
            existing = await self.db.execute(
                select(Candidate).where(
                    (Candidate.linkedin_url == linkedin_url) |
                    (Candidate.email == profile.email)
                )
            )
            candidate = existing.scalar_one_or_none()
            
            # Preparar datos
            data = profile.to_candidate_data()
            data["source"] = "linkedin"
            
            if job_opening_id:
                from uuid import UUID
                data["job_opening_id"] = UUID(job_opening_id)
            
            if candidate:
                # Actualizar
                for key, value in data.items():
                    if hasattr(candidate, key) and value is not None:
                        setattr(candidate, key, value)
                candidate.updated_at = datetime.utcnow()
                message = "Candidate updated from LinkedIn"
            else:
                # Crear nuevo
                candidate = Candidate(**data)
                self.db.add(candidate)
                message = "Candidate imported from LinkedIn"
            
            await self.db.commit()
            await self.db.refresh(candidate)
            
            return True, candidate, message
            
        except Exception as e:
            logger.error(f"Failed to import from LinkedIn: {e}")
            return False, None, f"Import failed: {str(e)}"
    
    def _validate_linkedin_url(self, url: str) -> bool:
        """Validar que sea una URL de LinkedIn válida."""
        try:
            parsed = urlparse(url)
            
            if parsed.netloc not in ["linkedin.com", "www.linkedin.com"]:
                return False
            
            # Debe ser perfil (/in/) o compañía (/company/)
            if not parsed.path.startswith("/in/"):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _extract_person_id_from_url(self, url: str) -> Optional[str]:
        """Extraer ID de persona de URL de LinkedIn.
        
        Nota: LinkedIn usa 'vanity names' (/in/nombre-apellido) en lugar de IDs
        numéricos en las URLs públicas. Para obtener el ID numérico necesitamos
        usar la API de búsqueda (si está disponible).
        """
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")
            
            if len(path_parts) >= 2 and path_parts[0] == "in":
                vanity_name = path_parts[1]
                return vanity_name
            
            return None
            
        except Exception:
            return None
    
    # ==================== SYNC OPERATIONS (stubs) ====================
    
    async def sync_jobs(self, **kwargs) -> SyncResult:
        """LinkedIn no tiene 'jobs' que sincronizar en el sentido tradicional."""
        return SyncResult(
            success=True,
            items_processed=0,
            warnings=["LinkedIn connector does not sync jobs. Use for candidate import only."]
        )
    
    async def sync_candidates(self, **kwargs) -> SyncResult:
        """Sincronizar candidatos desde LinkedIn.
        
        Nota: LinkedIn no permite listar todos los candidatos.
        Solo importar perfiles específicos con autorización.
        """
        return SyncResult(
            success=True,
            items_processed=0,
            warnings=["LinkedIn requires individual profile authorization. Use import_candidate_from_url."]
        )
    
    async def search_candidates(
        self,
        keywords: str,
        location: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Buscar candidatos en LinkedIn.
        
        IMPORTANTE: LinkedIn restringe severamente la búsqueda de perfiles
        via API. Esta función puede no estar disponible sin el programa de partners.
        
        Args:
            keywords: Palabras clave de búsqueda
            location: Ubicación
            limit: Máximo de resultados
            
        Returns:
            Lista de resultados
        """
        # Nota: La API de búsqueda de LinkedIn requiere permisos especiales
        # Este es un stub que documenta la limitación
        logger.warning(
            "LinkedIn profile search requires LinkedIn Partnership Program. "
            "Please apply at https://developer.linkedin.com/partner-programs"
        )
        return []
