"""Integrations module for external ATS and recruitment platforms."""

from app.integrations.base import (
    BaseConnector,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    RateLimiter,
    RateLimitConfig,
    SyncResult,
    WebhookHandler,
    with_retry,
)

from app.integrations.zoho_recruit import (
    ZohoRecruitConnector,
    ZohoWebhookHandler,
    ZohoTokens,
    ZohoRateLimits,
)

from app.integrations.odoo_connector import (
    OdooConnector,
    OdooWebhookHandler,
    OdooConnectionInfo,
    OdooAPIError,
)

from app.integrations.linkedin import (
    LinkedInConnector,
    LinkedInProfile,
    LinkedInTokens,
    LinkedInRateLimits,
)

__all__ = [
    # Base
    "BaseConnector",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpen",
    "RateLimiter",
    "RateLimitConfig",
    "SyncResult",
    "WebhookHandler",
    "with_retry",
    # Zoho
    "ZohoRecruitConnector",
    "ZohoWebhookHandler",
    "ZohoTokens",
    "ZohoRateLimits",
    # Odoo
    "OdooConnector",
    "OdooWebhookHandler",
    "OdooConnectionInfo",
    "OdooAPIError",
    # LinkedIn
    "LinkedInConnector",
    "LinkedInProfile",
    "LinkedInTokens",
    "LinkedInRateLimits",
]
