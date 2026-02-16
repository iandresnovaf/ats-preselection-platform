"""
Core ATS API v1 - Routers
"""
from fastapi import APIRouter

from app.api.v1 import candidates, clients, roles, applications, documents, assessments, reports

api_router = APIRouter(prefix="/api/v1")

# Candidates
api_router.include_router(
    candidates.router,
    prefix="/candidates",
    tags=["Candidates"]
)

# Clients
api_router.include_router(
    clients.router,
    prefix="/clients",
    tags=["Clients"]
)

# Roles (Vacantes)
api_router.include_router(
    roles.router,
    prefix="/roles",
    tags=["Roles"]
)

# Applications (Entidad Central)
api_router.include_router(
    applications.router,
    prefix="/applications",
    tags=["Applications"]
)

# Documents
api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"]
)

# Assessments
api_router.include_router(
    assessments.router,
    prefix="/assessments",
    tags=["Assessments"]
)

# Reports
api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"]
)
