"""Backward-compat re-exports for legacy imports."""
from .api.client import (
    GCBadApiError,
    GCBadCannotConnectError,
    GCBadRateLimitError,
    GCBadResponseError,
    GoCardlessApiClient,
)

# Legacy alias used by older tests/imports.
GoCardlessAPIClient = GoCardlessApiClient
