"""
Core ATS API v1 - Routers
"""
from fastapi import APIRouter

from app.api.v1 import candidates, clients, roles, applications, documents, assessments, reports
from app.api import message_templates

api_router = APIRouter(prefix="/api/v1")

# HHCandidates - router ya tiene prefix="/candidates"
api_router.include_router(
    candidates.router,
    tags=["HHCandidates"]
)

# HHClients - router ya tiene prefix="/clients"
api_router.include_router(
    clients.router,
    tags=["HHClients"]
)

# HHRoles (Vacantes) - router ya tiene prefix="/roles"
api_router.include_router(
    roles.router,
    tags=["HHRoles"]
)

# HHApplications (Entidad Central) - router ya tiene prefix="/applications"
api_router.include_router(
    applications.router,
    tags=["HHApplications"]
)

# HHDocuments - router ya tiene prefix="/documents"
api_router.include_router(
    documents.router,
    tags=["HHDocuments"]
)

# HHAssessments - router ya tiene prefix="/assessments"
api_router.include_router(
    assessments.router,
    tags=["HHAssessments"]
)

# Reports - router ya tiene prefix="/reports"
api_router.include_router(
    reports.router,
    tags=["Reports"]
)

# Message Templates - router tiene prefix="/message-templates"
api_router.include_router(
    message_templates.router,
    prefix="/message-templates",
    tags=["Message Templates"]
)

# Communications (WhatsApp/Email) - router ya tiene prefix="/communications"
from app.api import communications
api_router.include_router(
    communications.router,
    tags=["Communications"]
)
