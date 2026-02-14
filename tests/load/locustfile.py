"""
Load Tests - Locust Test Suite
==============================
Tests de carga para verificar rendimiento bajo presión.

Ejecutar con:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

O en modo headless:
    locust -f tests/load/locustfile.py --host=http://localhost:8000 -u 10 -r 2 -t 5m --headless
"""

import os
import random
import json
from datetime import datetime
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

# Configuración
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "admin@example.com")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "changeme")

# Umbrales de rendimiento
MAX_RESPONSE_TIME = 2000  # 2 segundos
MAX_ERROR_RATE = 0.05     # 5%


class ATSUser(HttpUser):
    """Usuario simulado para tests de carga."""
    
    wait_time = between(1, 3)  # Espera entre 1-3 segundos entre tareas
    
    def on_start(self):
        """Login al iniciar."""
        self.login()
    
    def login(self):
        """Realizar login y guardar cookies."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        
        if response.status_code == 200:
            # Guardar cookies de sesión
            self.cookies = response.cookies
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
    
    @task(3)
    def get_jobs(self):
        """Listar jobs - operación frecuente."""
        with self.client.get("/api/v1/jobs", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "items" in data:
                    response.success()
                else:
                    response.failure("Invalid response structure")
            elif response.status_code == 401:
                response.failure("Unauthorized - session expired")
                self.login()  # Reintentar login
            elif response.elapsed.total_seconds() > MAX_RESPONSE_TIME / 1000:
                response.failure(f"Response time > {MAX_RESPONSE_TIME}ms")
    
    @task(3)
    def get_candidates(self):
        """Listar candidatos - operación frecuente."""
        with self.client.get("/api/v1/candidates", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "items" in data:
                    response.success()
                else:
                    response.failure("Invalid response structure")
            elif response.elapsed.total_seconds() > MAX_RESPONSE_TIME / 1000:
                response.failure(f"Response time > {MAX_RESPONSE_TIME}ms")
    
    @task(2)
    def get_job_detail(self):
        """Ver detalle de job."""
        # Primero obtener lista de jobs
        jobs_response = self.client.get("/api/v1/jobs")
        if jobs_response.status_code == 200:
            jobs = jobs_response.json().get("items", [])
            if jobs:
                job_id = random.choice(jobs)["id"]
                
                with self.client.get(
                    f"/api/v1/jobs/{job_id}",
                    catch_response=True
                ) as response:
                    if response.status_code == 200:
                        response.success()
                    elif response.elapsed.total_seconds() > MAX_RESPONSE_TIME / 1000:
                        response.failure(f"Response time > {MAX_RESPONSE_TIME}ms")
    
    @task(2)
    def get_candidate_detail(self):
        """Ver detalle de candidato."""
        candidates_response = self.client.get("/api/v1/candidates")
        if candidates_response.status_code == 200:
            candidates = candidates_response.json().get("items", [])
            if candidates:
                candidate_id = random.choice(candidates)["id"]
                
                with self.client.get(
                    f"/api/v1/candidates/{candidate_id}",
                    catch_response=True
                ) as response:
                    if response.status_code == 200:
                        response.success()
                    elif response.elapsed.total_seconds() > MAX_RESPONSE_TIME / 1000:
                        response.failure(f"Response time > {MAX_RESPONSE_TIME}ms")
    
    @task(1)
    def create_job(self):
        """Crear job - operación menos frecuente."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        job_data = {
            "title": f"Load Test Job {timestamp}",
            "department": "QA",
            "location": "Remote",
            "employment_type": "full_time",
            "status": "active",
            "description": "Job created during load testing"
        }
        
        with self.client.post(
            "/api/v1/jobs",
            json=job_data,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
            elif response.elapsed.total_seconds() > MAX_RESPONSE_TIME / 1000:
                response.failure(f"Response time > {MAX_RESPONSE_TIME}ms")
    
    @task(1)
    def create_candidate(self):
        """Crear candidato - operación menos frecuente."""
        # Obtener un job_id primero
        jobs_response = self.client.get("/api/v1/jobs")
        if jobs_response.status_code != 200:
            return
        
        jobs = jobs_response.json().get("items", [])
        if not jobs:
            return
        
        job_id = random.choice(jobs)["id"]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        candidate_data = {
            "email": f"loadtest_{timestamp}@example.com",
            "full_name": f"Load Test User {timestamp}",
            "job_opening_id": job_id,
            "phone": f"+1-555-{random.randint(1000, 9999)}",
            "source": "load_test"
        }
        
        with self.client.post(
            "/api/v1/candidates",
            json=candidate_data,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
            elif response.elapsed.total_seconds() > MAX_RESPONSE_TIME / 1000:
                response.failure(f"Response time > {MAX_RESPONSE_TIME}ms")
    
    @task(1)
    def health_check(self):
        """Health check - monitoreo constante."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure("Health check returned unhealthy")
            elif response.elapsed.total_seconds() > 1000:  # 1s para health
                response.failure("Health check too slow")


class MatchingUser(HttpUser):
    """Usuario enfocado en operaciones de matching."""
    
    wait_time = between(2, 5)
    
    def on_start(self):
        """Login al iniciar."""
        self.login()
    
    def login(self):
        """Realizar login."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        
        if response.status_code == 200:
            self.cookies = response.cookies
    
    @task(5)
    def get_matching_results(self):
        """Obtener resultados de matching - operación frecuente."""
        with self.client.get("/api/v1/matching", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [401, 403]:
                response.failure("Unauthorized")
            elif response.elapsed.total_seconds() > MAX_RESPONSE_TIME / 1000:
                response.failure(f"Response time > {MAX_RESPONSE_TIME}ms")
    
    @task(1)
    def run_matching_evaluation(self):
        """Ejecutar evaluación de matching (más pesado)."""
        # Obtener candidatos
        candidates_response = self.client.get("/api/v1/candidates")
        if candidates_response.status_code != 200:
            return
        
        candidates = candidates_response.json().get("items", [])
        if not candidates:
            return
        
        candidate_id = random.choice(candidates)["id"]
        
        # Este endpoint puede tardar debido a llamadas a OpenAI
        with self.client.post(
            f"/api/v1/candidates/{candidate_id}/evaluate",
            json={"force": False},
            catch_response=True,
            timeout=30.0  # Timeout extendido para evaluaciones
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            elif response.elapsed.total_seconds() > 10:  # 10s para matching
                response.failure("Matching evaluation too slow")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, 
               response, context, exception, **kwargs):
    """Listener para tracking de requests."""
    # Log requests lentos
    if response_time > MAX_RESPONSE_TIME:
        print(f"⚠️ Slow request: {name} took {response_time}ms")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Al finalizar el test, imprimir resumen."""
    stats = environment.stats
    
    print("\n" + "="*60)
    print("LOAD TEST SUMMARY")
    print("="*60)
    
    total_requests = stats.total.num_requests
    failed_requests = stats.total.num_failures
    error_rate = failed_requests / total_requests if total_requests > 0 else 0
    
    print(f"Total Requests: {total_requests}")
    print(f"Failed Requests: {failed_requests}")
    print(f"Error Rate: {error_rate:.2%}")
    print(f"Avg Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Min Response Time: {stats.total.min_response_time:.2f}ms")
    print(f"Max Response Time: {stats.total.max_response_time:.2f}ms")
    
    # Verificar umbrales
    print("\n" + "-"*60)
    print("THRESHOLD CHECKS")
    print("-"*60)
    
    if stats.total.max_response_time > MAX_RESPONSE_TIME:
        print(f"❌ Max response time exceeded: {stats.total.max_response_time}ms > {MAX_RESPONSE_TIME}ms")
    else:
        print(f"✅ Max response time OK: {stats.total.max_response_time}ms <= {MAX_RESPONSE_TIME}ms")
    
    if error_rate > MAX_ERROR_RATE:
        print(f"❌ Error rate exceeded: {error_rate:.2%} > {MAX_ERROR_RATE:.2%}")
    else:
        print(f"✅ Error rate OK: {error_rate:.2%} <= {MAX_ERROR_RATE:.2%}")
    
    # Stats por endpoint
    print("\n" + "-"*60)
    print("ENDPOINT STATS")
    print("-"*60)
    
    for name in sorted(stats.entries.keys()):
        entry = stats.entries[name]
        print(f"\n{name}:")
        print(f"  Requests: {entry.num_requests}")
        print(f"  Failures: {entry.num_failures}")
        print(f"  Avg Time: {entry.avg_response_time:.2f}ms")
        print(f"  Max Time: {entry.max_response_time:.2f}ms")
    
    print("\n" + "="*60)
