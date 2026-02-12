"""Modelos de base de datos para RHTools."""
from app.models.rhtools.client import Client
from app.models.rhtools.pipeline import (
    PipelineTemplate,
    PipelineStage,
    StageRequiredField,
)
from app.models.rhtools.submission import (
    Submission,
    SubmissionStageHistory,
)
from app.models.rhtools.document import (
    Document,
    DocumentTextExtraction,
    DocumentType,
    DocumentStatus,
)
from app.models.rhtools.communication import (
    MessageTemplate,
    StageMessageRule,
    Message,
)
from app.models.rhtools.candidate_extended import (
    CandidateOfflimits,
    ResumeParse,
    CandidateProfileVersion,
)

__all__ = [
    "Client",
    "PipelineTemplate",
    "PipelineStage",
    "StageRequiredField",
    "Submission",
    "SubmissionStageHistory",
    "Document",
    "DocumentTextExtraction",
    "DocumentType",
    "DocumentStatus",
    "MessageTemplate",
    "StageMessageRule",
    "Message",
    "CandidateOfflimits",
    "ResumeParse",
    "CandidateProfileVersion",
]
