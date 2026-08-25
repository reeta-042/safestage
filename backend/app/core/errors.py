"""
SafeStage standardized error codes and exception classes.

Every failure must produce a clear, typed error — never a silent fallback.
"""

from fastapi import HTTPException, status
from typing import Optional


# ── Error Codes ──────────────────────────────────────────────────────────────

class ErrorCode:
    FORTYGUARD_UNAVAILABLE = "FORTYGUARD_UNAVAILABLE"
    AI_SERVICE_UNAVAILABLE = "AI_SERVICE_UNAVAILABLE"
    AI_OUTPUT_INVALID = "AI_OUTPUT_INVALID"
    LOCATION_RESOLUTION_FAILED = "LOCATION_RESOLUTION_FAILED"
    CLIMATE_DATA_UNAVAILABLE = "CLIMATE_DATA_UNAVAILABLE"
    INVALID_EVENT = "INVALID_EVENT"
    ANALYSIS_REQUIRED = "ANALYSIS_REQUIRED"


# ── Exception Classes ────────────────────────────────────────────────────────

class SafeStageError(Exception):
    """Base exception for SafeStage application errors."""
    def __init__(self, code: str, message: str, detail: Optional[str] = None):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


class FortyGuardError(SafeStageError):
    """FortyGuard API call failed or returned an error."""
    def __init__(self, message: str = "FortyGuard climate intelligence is currently unavailable.", detail: Optional[str] = None):
        super().__init__(ErrorCode.FORTYGUARD_UNAVAILABLE, message, detail)


class AIServiceError(SafeStageError):
    """Gemini/AI service call failed."""
    def __init__(self, message: str = "SafeStage could not generate the requested analysis.", detail: Optional[str] = None):
        super().__init__(ErrorCode.AI_SERVICE_UNAVAILABLE, message, detail)


class AIOutputError(SafeStageError):
    """AI returned malformed or unparseable output."""
    def __init__(self, message: str = "AI returned an invalid response that could not be processed.", detail: Optional[str] = None):
        super().__init__(ErrorCode.AI_OUTPUT_INVALID, message, detail)


class LocationResolutionError(SafeStageError):
    """Geocoding failed to resolve venue/address to coordinates."""
    def __init__(self, message: str = "Could not resolve the venue address to geographic coordinates.", detail: Optional[str] = None):
        super().__init__(ErrorCode.LOCATION_RESOLUTION_FAILED, message, detail)


class ClimateDataUnavailableError(SafeStageError):
    """No climate data available for the requested context."""
    def __init__(self, message: str = "Climate data is unavailable for this location or time period.", detail: Optional[str] = None):
        super().__init__(ErrorCode.CLIMATE_DATA_UNAVAILABLE, message, detail)


# ── HTTP Error Helper ────────────────────────────────────────────────────────

def safestage_error_response(error: SafeStageError, status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE) -> HTTPException:
    """Convert a SafeStageError into a FastAPI HTTPException with structured error body."""
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": error.code,
                "message": error.message,
                "detail": error.detail
            }
        }
    )


# ── Status code mapping ─────────────────────────────────────────────────────

ERROR_STATUS_MAP = {
    ErrorCode.FORTYGUARD_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.AI_SERVICE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.AI_OUTPUT_INVALID: status.HTTP_502_BAD_GATEWAY,
    ErrorCode.LOCATION_RESOLUTION_FAILED: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.CLIMATE_DATA_UNAVAILABLE: status.HTTP_404_NOT_FOUND,
    ErrorCode.INVALID_EVENT: status.HTTP_400_BAD_REQUEST,
    ErrorCode.ANALYSIS_REQUIRED: status.HTTP_409_CONFLICT,
}


def raise_safestage_error(error: SafeStageError):
    """Raise the appropriate HTTPException for a SafeStageError."""
    status_code = ERROR_STATUS_MAP.get(error.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    raise safestage_error_response(error, status_code)
