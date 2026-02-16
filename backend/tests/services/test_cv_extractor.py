"""Tests para el CVExtractor."""
import pytest
import pytest_asyncio

from app.services.extraction.cv_extractor import CVExtractor


class TestCVExtractor:
    """Tests para CVExtractor."""
    
    @pytest_asyncio.fixture
    async def extractor(self):
        return CVExtractor()
    
    @pytest.mark.asyncio
    async def test_extract_personal_info(self, extractor):
        """Test extracción de información personal."""
        text = """
        MARÍA GARCÍA LÓPEZ
        
        Email: maria.garcia@email.com
        Teléfono: +52 55 1234 5678
        LinkedIn: linkedin.com/in/mariagarcia
        Ubicación: Ciudad de México
        """
        
        info = extractor._extract_personal_info(text)
        
        assert info["name"] == "María García López"
        assert info["email"] == "maria.garcia@email.com"
        assert info["linkedin"] == "https://linkedin.com/in/mariagarcia"
        assert info["location"] == "Ciudad de México"
    
    @pytest.mark.asyncio
    async def test_extract_experience(self, extractor):
        """Test extracción de experiencia laboral."""
        text = """
        EXPERIENCIA LABORAL
        
        Senior Developer en TechCorp
        Enero 2020 - Presente
        Desarrollo de aplicaciones web
        - Lideré equipo de 5 desarrolladores
        - Implementé arquitectura microservicios
        
        Developer en StartupXYZ
        Junio 2017 - Diciembre 2019
        Desarrollo frontend con React
        """
        
        experience = extractor._extract_experience(text)
        
        assert len(experience) == 2
        assert experience[0].company == "TechCorp"
        assert experience[0].title == "Senior Developer"
        assert experience[0].is_current is True
        assert experience[1].company == "StartupXYZ"
    
    @pytest.mark.asyncio
    async def test_extract_education(self, extractor):
        """Test extracción de educación."""
        text = """
        EDUCACIÓN
        
        Ingeniería en Sistemas en Universidad Nacional
        2013 - 2017
        
        Maestría en Ciencias de la Computación en Tec de Monterrey
        2018 - 2020
        """
        
        education = extractor._extract_education(text)
        
        assert len(education) == 2
        assert "Ingeniería" in education[0].degree or "Engineering" in education[0].degree
        assert "Universidad Nacional" in education[0].institution
    
    @pytest.mark.asyncio
    async def test_extract_skills(self, extractor):
        """Test extracción de skills."""
        text = """
        HABILIDADES
        
        Python, JavaScript, React, Node.js, PostgreSQL, AWS, Docker, Kubernetes
        
        También tengo experiencia con:
        - Machine Learning
        - Data Science
        - CI/CD
        """
        
        skills = extractor._extract_skills(text)
        
        assert len(skills) > 0
        assert "Python" in skills
        assert "JavaScript" in skills or "React" in skills
    
    @pytest.mark.asyncio
    async def test_parse_skills_text(self, extractor):
        """Test parsing de texto de skills."""
        text = "Python, JavaScript, React | Node.js; Docker • Kubernetes"
        
        skills = extractor._parse_skills_text(text)
        
        assert "Python" in skills
        assert "JavaScript" in skills
        assert "React" in skills
    
    @pytest.mark.asyncio
    async def test_extract_technical_skills(self, extractor):
        """Test extracción de skills técnicas del texto."""
        text = """
        Experiencia con Python, Django, Flask, FastAPI, PostgreSQL, Redis,
        Docker, Kubernetes, AWS, GCP, React, Node.js
        """
        
        skills = extractor._extract_technical_skills(text)
        
        assert "Python" in skills
        assert "Docker" in skills
        assert "PostgreSQL" in skills
    
    @pytest.mark.asyncio
    async def test_extract_from_complete_cv(self, extractor):
        """Test extracción de CV completo."""
        cv_text = """
        JUAN PÉREZ GARCÍA
        
        Email: juan.perez@email.com
        Teléfono: +1 555 123 4567
        Ubicación: Miami, FL
        LinkedIn: linkedin.com/in/juanperez
        
        RESUMEN
        Ingeniero de software con 5 años de experiencia en desarrollo web
        y aplicaciones cloud. Especializado en Python y AWS.
        
        EXPERIENCIA LABORAL
        
        Senior Software Engineer en CloudTech Inc.
        Enero 2020 - Presente
        - Desarrollo de microservicios con Python y FastAPI
        - Implementación de pipelines CI/CD
        - Liderazgo técnico de equipo de 4 desarrolladores
        
        Software Engineer en StartupCo
        Marzo 2018 - Diciembre 2019
        - Desarrollo frontend con React y TypeScript
        - Integración con APIs REST
        
        EDUCACIÓN
        
        Ingeniería en Sistemas Computacionales
        Universidad de Tecnología, 2014-2018
        
        HABILIDADES
        
        Python, JavaScript, TypeScript, React, Node.js, FastAPI, Django,
        PostgreSQL, MongoDB, AWS, Docker, Kubernetes, Terraform, CI/CD
        
        IDIOMAS
        
        Español (nativo), Inglés (fluido)
        """
        
        result = await extractor.extract_from_text(cv_text)
        
        assert result.full_name == "Juan Pérez García"
        assert result.email == "juan.perez@email.com"
        assert len(result.experience) == 2
        assert len(result.education) >= 1
        assert len(result.skills) >= 5
        assert "Español" in result.languages or "Spanish" in result.languages
    
    @pytest.mark.asyncio
    async def test_empty_text_raises_error(self, extractor):
        """Test que texto vacío lanza error."""
        with pytest.raises(Exception):
            await extractor.extract_from_text("")
