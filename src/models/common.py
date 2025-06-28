"""Common Pydantic models used across the application."""

from typing import Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response model for API endpoints.

    Used to provide consistent error formatting across all endpoints.
    """

    error: str = Field(
        ..., description="Error type or category", example="ValidationError"
    )
    detail: Optional[str] = Field(
        None, description="Detailed error message", example="Invalid input format"
    )
    status_code: int = Field(..., description="HTTP status code", example=400)


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Overall application status", example="ready")
    services: dict = Field(
        default_factory=dict, description="Status of individual services"
    )
    error: Optional[str] = Field(
        None, description="Error message if status is not ready"
    )
