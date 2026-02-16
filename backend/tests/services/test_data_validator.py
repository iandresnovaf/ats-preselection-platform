"""Tests para el DataValidator."""
import pytest
from datetime import date

from app.validators.data_validator import DataValidator


class TestDataValidator:
    """Tests para DataValidator."""
    
    @pytest.fixture
    def validator(self):
        return DataValidator()
    
    def test_validate_score_valid(self, validator):
        """Test validación de score válido."""
        is_valid, error = validator.validate_score(75.5, "test")
        assert is_valid is True
        assert error is None
    
    def test_validate_score_too_high(self, validator):
        """Test validación de score demasiado alto."""
        is_valid, error = validator.validate_score(150, "test")
        assert is_valid is False
        assert "100" in error
    
    def test_validate_score_too_low(self, validator):
        """Test validación de score demasiado bajo."""
        is_valid, error = validator.validate_score(-10, "test")
        assert is_valid is False
        assert "0" in error
    
    def test_validate_score_none(self, validator):
        """Test validación de score nulo."""
        is_valid, error = validator.validate_score(None, "test")
        assert is_valid is False
        assert "no puede ser nulo" in error
    
    def test_validate_phone_valid(self, validator):
        """Test validación de teléfono válido."""
        is_valid, error, normalized = validator.validate_phone("+1234567890")
        assert is_valid is True
        assert error is None
        assert normalized == "+1234567890"
    
    def test_validate_phone_with_spaces(self, validator):
        """Test validación de teléfono con espacios."""
        is_valid, error, normalized = validator.validate_phone("+1 234 567 890")
        assert is_valid is True
        assert normalized == "+1234567890"
    
    def test_validate_phone_invalid(self, validator):
        """Test validación de teléfono inválido."""
        is_valid, error, normalized = validator.validate_phone("abc")
        assert is_valid is False
        assert error is not None
        assert normalized is None
    
    def test_validate_email_valid(self, validator):
        """Test validación de email válido."""
        is_valid, error = validator.validate_email("test@example.com")
        assert is_valid is True
        assert error is None
    
    def test_validate_email_invalid(self, validator):
        """Test validación de email inválido."""
        is_valid, error = validator.validate_email("not-an-email")
        assert is_valid is False
        assert error is not None
    
    def test_validate_date_valid(self, validator):
        """Test validación de fecha válida."""
        is_valid, error, parsed = validator.validate_date("2024-01-15")
        assert is_valid is True
        assert error is None
        assert parsed == date(2024, 1, 15)
    
    def test_validate_date_present(self, validator):
        """Test validación de fecha 'Present'."""
        is_valid, error, parsed = validator.validate_date("Present")
        assert is_valid is True
        assert parsed == date.today()
    
    def test_validate_date_invalid(self, validator):
        """Test validación de fecha inválida."""
        is_valid, error, parsed = validator.validate_date("not-a-date")
        assert is_valid is False
        assert error is not None
        assert parsed is None
    
    def test_validate_assessment_data_valid(self, validator):
        """Test validación de datos de assessment válidos."""
        data = {
            "test_name": "Dark Factor Inventory",
            "scores": [
                {"name": "Egocentrism", "value": 65.5},
                {"name": "Psychopathy", "value": 45.0},
            ],
            "sincerity_score": 85.0
        }
        
        result = validator.validate_assessment_data(data)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.normalized_data["scores"]) == 2
    
    def test_validate_assessment_data_invalid_score(self, validator):
        """Test validación de assessment con score inválido."""
        data = {
            "test_name": "Dark Factor Inventory",
            "scores": [
                {"name": "Egocentrism", "value": 150},  # Inválido
            ],
        }
        
        result = validator.validate_assessment_data(data)
        assert result.is_valid is False
        assert len([e for e in result.errors if e.severity == "error"]) > 0
    
    def test_validate_assessment_data_missing_required(self, validator):
        """Test validación de assessment sin campos requeridos."""
        data = {
            "scores": []  # Falta test_name
        }
        
        result = validator.validate_assessment_data(data)
        assert result.is_valid is False
        assert any(e.field == "test_name" for e in result.errors)
    
    def test_validate_cv_data_valid(self, validator):
        """Test validación de datos de CV válidos."""
        data = {
            "full_name": "Juan Pérez",
            "email": "juan@example.com",
            "phone": "+1234567890",
            "experience": [
                {"company": "Tech Corp", "title": "Developer"}
            ]
        }
        
        result = validator.validate_cv_data(data)
        assert result.is_valid is True
        assert result.normalized_data["email"] == "juan@example.com"
    
    def test_validate_cv_data_invalid_email(self, validator):
        """Test validación de CV con email inválido."""
        data = {
            "full_name": "Juan Pérez",
            "email": "invalid-email",
        }
        
        result = validator.validate_cv_data(data)
        # No debería ser inválido, solo warning
        assert len(result.warnings) > 0
