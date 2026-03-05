"""
LogEntry schema - canonical Pydantic model for a single structured log record.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class LogLevel(str, Enum):
    """Standard log severity levels accepted on ingest."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# LogEntry
# ---------------------------------------------------------------------------


class LogEntry(BaseModel):
    """Canonical representation of a single log record ingested by Lognis.

    All fields are validated on construction.  The model is intentionally
    strict: unknown extra fields are forbidden so that schema drift is caught
    early at the API boundary.

    Attributes
    ----------
    id:
        UUID v4 that uniquely identifies this log record.  Auto-generated
        when omitted.
    timestamp:
        UTC datetime of when the event occurred.  Defaults to *now* when
        not provided by the caller.
    level:
        Severity level of the log entry.  Case-insensitive on input;
        stored as the canonical uppercase enum value.
    message:
        Human-readable description of the event.  Must be non-empty after
        stripping surrounding whitespace.
    source:
        Identifier of the system or service that emitted the log
        (e.g. ``"auth-service"``, ``"nginx"``).  Must be non-empty.

    Examples
    --------
    Minimal valid entry (id and timestamp are auto-populated)::

        LogEntry(
            level="ERROR",
            message="Database connection refused",
            source="api-gateway",
        )

    Full entry with explicit id and timestamp::

        LogEntry(
            id="123e4567-e89b-12d3-a456-426614174000",
            timestamp="2024-01-15T10:24:01Z",
            level="INFO",
            message="Server started on port 8080",
            source="core-service",
        )
    """

    model_config = {
        "extra": "forbid",
        "str_strip_whitespace": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "timestamp": "2024-01-15T10:24:01Z",
                    "level": "ERROR",
                    "message": "Database connection refused after 3 retries",
                    "source": "db-pool",
                }
            ]
        },
    }

    id: Annotated[
        UUID,
        Field(default_factory=uuid4, description="Unique record identifier (UUIDv4)."),
    ]

    timestamp: Annotated[
        datetime,
        Field(
            default_factory=datetime.utcnow,
            description="UTC datetime of the log event.",
        ),
    ]

    level: Annotated[
        LogLevel,
        Field(description="Severity level of the log entry."),
    ]

    message: Annotated[
        str,
        Field(
            min_length=1,
            max_length=8192,
            description="Human-readable event description (1–8192 chars).",
        ),
    ]

    source: Annotated[
        str,
        Field(
            min_length=1,
            max_length=253,
            description="Originating service or host identifier (1–253 chars).",
        ),
    ]

    # ------------------------------------------------------------------
    # Field-level validators
    # ------------------------------------------------------------------

    @field_validator("level", mode="before")
    @classmethod
    def normalise_level(cls, value: object) -> str:
        """Accept mixed-case level strings and common aliases.

        Normalisation rules applied in order:
        1. Strip surrounding whitespace.
        2. Convert to uppercase.
        3. Map known aliases: ``"WARN"`` → ``"WARNING"``, ``"FATAL"`` → ``"CRITICAL"``.
        """
        if isinstance(value, str):
            normalised = value.strip().upper()
            _ALIASES: dict[str, str] = {
                "WARN": "WARNING",
                "FATAL": "CRITICAL",
            }
            return _ALIASES.get(normalised, normalised)
        return value  # let Pydantic's enum coercion handle the rest

    @field_validator("message", "source", mode="after")
    @classmethod
    def reject_blank(cls, value: str, info) -> str:  # noqa: ANN001
        """Ensure the value is not blank after whitespace stripping."""
        if not value.strip():
            raise ValueError(
                f"'{info.field_name}' must not be empty or whitespace-only."
            )
        return value

    # ------------------------------------------------------------------
    # Model-level validator
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def timestamp_not_in_future(self) -> "LogEntry":
        """Warn callers that far-future timestamps are suspicious.

        Rather than hard-rejecting (which would break replayed logs), we
        allow them through but keep the hook here for future policy tuning.
        This validator intentionally does *not* raise so that malformed
        timestamps from legacy systems are never silently dropped.
        """
        return self
