# TEST_PLAN.md - ATS Platform Testing Strategy

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Backend Tests** | 201 tests |
| **Test Coverage Target** | 70% (initial), 85% (mature) |
| **Critical Tests** | Authentication, Authorization, User Management |
| **Frontend Tests** | 8 tests (initial phase) |
| **Integration Tests** | 20+ scenarios |

---

## 1. Testing Strategy

### 1.1 Test Pyramid

```
        /\
       /  \     E2E Tests (10%)
      /____\    
     /      \   Integration Tests (30%)
    /________\ 
   /          \ Unit Tests (60%)
  /____________\
```

### 1.2 Testing Levels

| Level | Description | Tools | Status |
|-------|-------------|-------|--------|
| **Unit** | Test individual functions, classes | pytest, Jest | ✅ Implemented |
| **Integration** | Test component interactions | pytest-asyncio, httpx | ✅ Implemented |
| **E2E** | Test complete user workflows | Cypress/Playwright | 📝 Planned |

---

## 2. Backend Tests (Python/pytest)

### 2.1 Test Structure

```
backend/tests/
├── conftest.py              # Shared fixtures and configuration
├── test_auth.py             # Authentication & authorization tests (45 tests)
├── test_users.py            # User management tests (55 tests)
├── test_config.py           # Configuration tests (50 tests)
├── test_models.py           # Database model tests (25 tests)
└── test_integration.py      # Integration tests (26 tests)
```

### 2.2 Critical Test Categories

#### 🔐 Authentication Tests (45 tests)
- **Password Hashing**: Hash generation, verification, security
- **Token Management**: JWT creation, validation, refresh, expiration
- **Login Flow**: Valid/invalid credentials, inactive users, rate limiting
- **Password Recovery**: Forgot password, reset token validation
- **Session Management**: Concurrent sessions, logout

#### 👥 User Management Tests (55 tests)
- **CRUD Operations**: Create, read, update, delete users
- **Role-Based Access**: Admin vs Consultant permissions
- **Validation**: Email format, password strength, unique constraints
- **Soft Delete**: Deactivation vs permanent deletion
- **Search & Filter**: By role, status, name, email

#### ⚙️ Configuration Tests (50 tests)
- **Encryption**: Sensitive data encryption at rest
- **Integration Configs**: WhatsApp, Zoho, LLM, Email settings
- **Access Control**: Only admins can manage configuration
- **Connection Testing**: Health checks for external services
- **Data Consistency**: Update isolation between configs

#### 🗄️ Model Tests (25 tests)
- **Data Integrity**: Constraints, defaults, relationships
- **Timestamps**: Created/updated at tracking
- **Enums**: Role and status value validation
- **Relationships**: Foreign key integrity

#### 🔗 Integration Tests (26 tests)
- **End-to-End Flows**: Login → Create User → Configure → Logout
- **Multi-User Scenarios**: Concurrent access, permissions
- **Error Handling**: Consistent error responses
- **Data Consistency**: Database state verification

---

## 3. Frontend Tests (TypeScript/Jest)

### 3.1 Test Structure

```
frontend/src/__tests__/
├── store/
│   └── auth.test.ts         # Zustand auth store tests
└── services/
    └── auth.test.ts         # API service tests
```

### 3.2 Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| Auth Store | 8 tests | ✅ Implemented |
| API Services | 4 tests | ✅ Implemented |
| UI Components | 0 tests | 📝 Planned |

### 3.3 Frontend Test Cases

#### Auth Store Tests
1. User data transformation (snake_case → camelCase)
2. Login success/failure handling
3. Logout state clearing
4. Token refresh flow
5. Error state management
6. localStorage persistence

#### API Service Tests
1. Request/response interceptors
2. Token validation
3. Error handling (401, 403, network)
4. Header injection

---

## 4. Running Tests

### 4.1 Backend Tests

```bash
cd /home/andres/.openclaw/workspace/ats-platform/backend

# Activate virtual environment
source venv/bin/activate

# Install test dependencies
pip install pytest pytest-asyncio httpx aiosqlite

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test categories
pytest tests/test_auth.py -v                    # Authentication only
pytest tests/test_users.py -v                   # User management only
pytest tests/test_config.py -v                  # Configuration only
pytest tests/test_integration.py -v             # Integration only

# Run by markers
pytest -m auth                                  # Auth tests
pytest -m users                                 # User tests
pytest -m config                                # Config tests
pytest -m integration                           # Integration tests

# Run with verbose output
pytest -v --tb=short
```

### 4.2 Frontend Tests

```bash
cd /home/andres/.openclaw/workspace/ats-platform/frontend

# Install dependencies
npm install

# Run tests
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch

# Run specific file
npm test -- auth.test.ts
```

---

## 5. Test Fixtures

### 5.1 Backend Fixtures (conftest.py)

| Fixture | Description |
|---------|-------------|
| `client` | Test HTTP client with DB override |
| `db_session` | Async database session |
| `test_admin` | Pre-created admin user |
| `test_consultant` | Pre-created consultant user |
| `admin_headers` | Auth headers for admin |
| `consultant_headers` | Auth headers for consultant |
| `test_*_config` | Integration configuration fixtures |

### 5.2 Test Isolation

- Each test runs in a database transaction
- Automatic rollback after each test
- In-memory SQLite for fast execution
- No external service dependencies (mocked)

---

## 6. Critical Test Scenarios

### 6.1 Security-Critical Tests

| Scenario | Tests | Priority |
|----------|-------|----------|
| Password hashing (bcrypt) | 5 | 🔴 Critical |
| JWT token validation | 8 | 🔴 Critical |
| Role-based access control | 12 | 🔴 Critical |
| Inactive user blocking | 4 | 🔴 Critical |
| Config encryption | 5 | 🟡 High |
| SQL injection prevention | 3 | 🟡 High |
| CORS configuration | 2 | 🟢 Medium |

### 6.2 Business-Critical Tests

| Scenario | Tests | Priority |
|----------|-------|----------|
| User CRUD operations | 20 | 🔴 Critical |
| Consultant workflow | 6 | 🔴 Critical |
| Configuration management | 15 | 🟡 High |
| Email uniqueness | 4 | 🟡 High |
| Data consistency | 8 | 🟡 High |

---

## 7. Coverage Goals

### 7.1 Backend Coverage Targets

| Module | Target | Current |
|--------|--------|---------|
| `app/core/auth.py` | 95% | 📝 TBD |
| `app/api/auth.py` | 90% | 📝 TBD |
| `app/api/users.py` | 90% | 📝 TBD |
| `app/api/config.py` | 85% | 📝 TBD |
| `app/services/` | 80% | 📝 TBD |
| `app/models/` | 75% | 📝 TBD |

### 7.2 Frontend Coverage Targets

| Module | Target | Current |
|--------|--------|---------|
| `store/auth.ts` | 85% | 📝 TBD |
| `services/auth.ts` | 80% | 📝 TBD |
| Components | 70% | 📝 TBD |

---

## 8. CI/CD Integration

### 8.1 Pre-commit Checks

```yaml
# .github/workflows/tests.yml
- Run backend unit tests
- Run frontend unit tests
- Coverage threshold check (70%)
- Linting checks
```

### 8.2 Test Gates

- ❌ No test failures allowed
- ❌ Coverage must not decrease
- ⚠️ Critical paths must have tests
- ✅ All security tests must pass

---

## 9. External Service Mocking

### 9.1 Mocked Services

| Service | Mock Strategy |
|---------|---------------|
| Zoho API | Response fixtures |
| WhatsApp Business API | HTTP client mocking |
| OpenAI/LLM | Response fixtures |
| Email/SMTP | Mock transport |
| Redis | fakeredis library |

### 9.2 Test Configuration

```python
# Use test database
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Mock external API keys
ZOHO_CLIENT_ID = "test_client_id"
WHATSAPP_ACCESS_TOKEN = "test_token"
OPENAI_API_KEY = "test_api_key"
```

---

## 10. Maintenance & Expansion

### 10.1 Adding New Tests

1. **Identify the module** to test
2. **Create test file** following naming convention (`test_*.py`)
3. **Use existing fixtures** from `conftest.py`
4. **Follow AAA pattern**: Arrange, Act, Assert
5. **Add markers** for categorization

### 10.2 Test Documentation

- Each test should have a docstring explaining its purpose
- Complex scenarios should have inline comments
- Use descriptive test names: `test_<action>_<condition>_<expected_result>`

---

## 11. Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| No E2E tests yet | Medium risk | Cypress planned for Sprint 2 |
| Limited frontend coverage | Low risk | Expand in Sprint 2 |
| No load testing | Low risk | k6 planned for Sprint 3 |
| Mock external services | Low risk | Contract tests planned |

---

## 12. Success Metrics

| Metric | Baseline | Current | Target |
|--------|----------|---------|--------|
| Total Tests | 0 | 201 | 500+ |
| Backend Coverage | 0% | 📝 TBD | 85% |
| Frontend Coverage | 0% | 📝 TBD | 70% |
| Test Execution Time | N/A | <30s | <60s |
| Flaky Tests | N/A | 0 | 0 |
| Critical Path Coverage | 0% | 100% | 100% |

---

## 13. Next Steps

### Sprint 1 (Current) ✅
- [x] Backend authentication tests
- [x] Backend user management tests
- [x] Backend configuration tests
- [x] Backend model tests
- [x] Integration tests
- [x] Frontend auth store tests

### Sprint 2 (Planned)
- [ ] Frontend component tests
- [ ] E2E tests with Cypress
- [ ] API contract tests
- [ ] Performance tests

### Sprint 3 (Planned)
- [ ] Load testing with k6
- [ ] Security penetration tests
- [ ] Accessibility tests
- [ ] Cross-browser tests

---

## 14. Resources

### Documentation
- [pytest Documentation](https://docs.pytest.org/)
- [Jest Documentation](https://jestjs.io/)
- [Testing Library](https://testing-library.com/)

### Commands Cheat Sheet

```bash
# Backend
pytest                           # Run all tests
pytest -x                        # Stop on first failure
pytest --lf                      # Run last failures
pytest -k "test_login"           # Run tests matching pattern
pytest --cov=app --cov-report=html  # Generate coverage report

# Frontend
npm test                         # Run all tests
npm test -- --watch            # Watch mode
npm test -- --coverage         # With coverage
npm test -- auth.test.ts       # Specific file
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-11  
**Author**: QA Testing Team
