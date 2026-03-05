"""
Pydantic schemas for request / response models used across Lognis.
"""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class LogSeverity(str, Enum):
    """Normalised log severity levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class LogIngestionRequest(BaseModel):
    """Payload for the log analysis endpoint."""

    entries: list[str] = Field(
        ...,
        min_length=1,
        description="Raw log lines to be analysed.",
        examples=[
            [
                "2024-01-15T10:23:45 INFO  Server started on port 8080",
                "2024-01-15T10:24:01 ERROR Database connection refused",
                "2024-01-15T10:24:02 CRITICAL Out of memory",
            ]
        ],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "entries": [
                        "2024-01-15T10:23:45 INFO  Server started",
                        "2024-01-15T10:24:01 ERROR DB connection failed",
                    ]
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# Internal / intermediate schemas
# ---------------------------------------------------------------------------


class ParsedLogEntry(BaseModel):
    """A single log line after parsing."""

    raw: str = Field(..., description="Original log line.")
    severity: LogSeverity = Field(..., description="Detected severity level.")
    timestamp: str | None = Field(
        default=None,
        description="Extracted ISO-style timestamp, if present.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class LogAnalysisResponse(BaseModel):
    """Structured result returned by the analysis engine."""

    analyzed_at: str = Field(
        ..., description="UTC timestamp when analysis was performed."
    )
    total_entries: int = Field(..., description="Total number of log lines processed.")
    severity_counts: dict[str, int] = Field(
        ..., description="Count of entries per severity level."
    )
    error_lines: list[str] = Field(
        default_factory=list,
        description="Raw lines whose severity is ERROR or CRITICAL.",
    )
    entries: list[ParsedLogEntry] = Field(
        default_factory=list,
        description="Parsed representation of every submitted log line.",
    )


# ---------------------------------------------------------------------------
# Forensic analysis schemas  (used by POST /api/v1/analyze)
# ---------------------------------------------------------------------------


class EntryAnalysisReport(BaseModel):
    """Per-entry result produced by the forensic analysis engine.

    Attributes
    ----------
    id:
        UUID of the originating :class:`~app.models.log_schema.LogEntry`.
    source:
        Service or host that emitted the entry.
    level:
        Severity level string (e.g. ``"ERROR"``).
    message:
        The raw log message that was analysed.
    entropy:
        Shannon entropy of *message* in bits (rounded to 6 d.p.).

        Computed as H(X) = -∑ P(xᵢ) log₂ P(xᵢ) over the character
        distribution of the message.  Values above ~4.5 bits often indicate
        obfuscated payloads, Base64 blobs, or encrypted content.
    is_anomaly:
        ``True`` when this entry's entropy score was flagged as a statistical
        outlier (Z-score > 3 σ) relative to the rest of the batch.
    has_sensitive_data:
        ``True`` when a heuristic rule detected a potential credential or
        encoded secret in the message (e.g. API key, bearer token, Base64 blob).
    sensitive_data_tags:
        List of rule names that fired for sensitive-data detection
        (e.g. ``["credential_kv", "base64_blob"]``).
    has_sqli:
        ``True`` when at least one SQL injection pattern was detected.
    sqli_tags:
        List of SQL injection sub-type tags that fired
        (e.g. ``["tautology", "union_select"]``).
    has_critical_pattern:
        ``True`` when a critical operational-error keyword was found in the
        message regardless of the declared log level.
    critical_pattern_tags:
        List of matched operational-error tags
        (e.g. ``["connection_refused", "disk_full"]``).
    risk_score:
        Composite risk score in **0–10** produced by the Risk Scoring Engine:
        S_total = min(10, ω_H · Φ(H) + ω_Z · Ψ(Z) + Σ Kj)
    risk_level:
        Human-readable severity band for ``risk_score``:
        ``"Low"`` (0–3) · ``"Medium"`` (3–6) · ``"High"`` (6–8) ·
        ``"Critical"`` (8–10).
    risk_breakdown:
        Factor-level decomposition showing individual contributions to
        ``risk_score`` for audit and transparency:

        * ``entropy_factor``   — weighted entropy contribution ω_H · Φ(H)
        * ``anomaly_factor``   — weighted Z-score contribution ω_Z · Ψ(Z)
        * ``heuristic_penalty``— sum of all applicable heuristic penalties Σ Kj
        * ``raw_total``        — unclipped sum before the min(10, …) cap
    """

    id: UUID = Field(..., description="UUID of the source LogEntry.")
    source: str = Field(..., description="Originating service / host.")
    level: str = Field(..., description="Log severity level.")
    message: str = Field(..., description="Raw log message.")
    entropy: float = Field(
        ...,
        description="Shannon entropy H(X) = -∑ P(xᵢ) log₂ P(xᵢ) in bits.",
    )
    is_anomaly: bool = Field(
        ...,
        description="True when the entry is a Z-score outlier in this batch.",
    )
    has_sensitive_data: bool = Field(
        default=False,
        description="True when a credential or encoded-secret pattern was detected.",
    )
    sensitive_data_tags: list[str] = Field(
        default_factory=list,
        description="Heuristic rule names that fired for sensitive-data detection.",
    )
    has_sqli: bool = Field(
        default=False,
        description="True when at least one SQL injection pattern was detected.",
    )
    sqli_tags: list[str] = Field(
        default_factory=list,
        description="SQL injection sub-type tags that fired.",
    )
    has_critical_pattern: bool = Field(
        default=False,
        description="True when a critical operational-error keyword was matched.",
    )
    critical_pattern_tags: list[str] = Field(
        default_factory=list,
        description="Operational-error tags matched in the message.",
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Composite risk score (0–10): S_total = min(10, ω_H·Φ(H) + ω_Z·Ψ(Z) + ΣKj).",
    )
    risk_level: str = Field(
        ...,
        description="Risk band: 'Low' (0–3), 'Medium' (3–6), 'High' (6–8), 'Critical' (8–10).",
    )
    risk_breakdown: dict[str, float] = Field(
        ...,
        description=(
            "Factor contributions to risk_score: "
            "{entropy_factor, anomaly_factor, heuristic_penalty, raw_total}."
        ),
    )


class ForensicAnalysisReport(BaseModel):
    """Full forensic report returned by ``POST /api/v1/analyze``.

    Attributes
    ----------
    analyzed_at:
        UTC ISO-8601 timestamp of when the analysis was performed.
    total_entries:
        Number of :class:`~app.models.log_schema.LogEntry` objects processed.
    mean_entropy:
        Arithmetic mean of all per-entry entropy scores, rounded to 6 d.p.
        ``0.0`` when no entries are present.
    anomaly_count:
        Total number of entries flagged as Z-score anomalies.
    anomaly_indices:
        Zero-based positions in *entries* that were flagged as Z-score
        anomalies.  Useful for quick look-ups without scanning the full list.
    sensitive_entry_count:
        Number of entries that triggered at least one sensitive-data heuristic.
    sqli_entry_count:
        Number of entries that triggered at least one SQL injection heuristic.
    critical_pattern_count:
        Number of entries that triggered at least one critical-pattern heuristic.
    overall_risk_score:
        Batch-level risk score (0–10): the mean of all per-entry ``risk_score``
        values, rounded to 2 d.p.  ``0.0`` for an empty batch.
    overall_risk_level:
        Risk band label derived from ``overall_risk_score``.
    overall_risk_breakdown:
        Batch-level mean of each factor contribution, rounded to 2 d.p.:
        ``{entropy_factor, anomaly_factor, heuristic_penalty, raw_total}``.
    entries:
        Ordered list of per-entry analysis results, preserving the original
        submission order.
    """

    analyzed_at: str = Field(
        ...,
        description="UTC ISO-8601 timestamp of the analysis.",
    )
    total_entries: int = Field(
        ...,
        description="Total number of LogEntry objects processed.",
    )
    mean_entropy: float = Field(
        ...,
        description="Mean Shannon entropy across all entries (bits).",
    )
    anomaly_count: int = Field(
        ...,
        description="Number of entries flagged as Z-score anomalies.",
    )
    anomaly_indices: list[int] = Field(
        default_factory=list,
        description="Zero-based indices of Z-score anomalous entries.",
    )
    sensitive_entry_count: int = Field(
        default=0,
        description="Number of entries with at least one sensitive-data match.",
    )
    sqli_entry_count: int = Field(
        default=0,
        description="Number of entries with at least one SQL injection match.",
    )
    critical_pattern_count: int = Field(
        default=0,
        description="Number of entries with at least one critical-pattern match.",
    )
    overall_risk_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Batch-level mean risk score (0–10), rounded to 2 d.p.",
    )
    overall_risk_level: str = Field(
        ...,
        description="Risk band label for overall_risk_score.",
    )
    overall_risk_breakdown: dict[str, float] = Field(
        ...,
        description="Mean of each factor contribution across all entries.",
    )
    entries: list[EntryAnalysisReport] = Field(
        default_factory=list,
        description="Per-entry analysis results in submission order.",
    )


# ---------------------------------------------------------------------------
# History schemas  (used by GET /api/v1/history)
# ---------------------------------------------------------------------------


class AnalysisResultSummary(BaseModel):
    """Summary row returned by the history endpoint.

    Contains only denormalised columns — no per-entry detail — so the listing
    can be served from a single indexed SQL query.
    """

    id: str = Field(..., description="UUID of the persisted analysis result.")
    analyzed_at: str = Field(..., description="UTC ISO-8601 analysis timestamp.")
    total_entries: int = Field(..., description="Number of log entries analysed.")
    overall_risk_score: float = Field(..., description="Batch risk score (0–10).")
    overall_risk_level: str = Field(..., description="Risk band label.")
    anomaly_count: int = Field(default=0, description="Z-score anomaly count.")
    sensitive_entry_count: int = Field(
        default=0, description="Entries with sensitive-data hits."
    )
    sqli_entry_count: int = Field(
        default=0, description="Entries with SQL-injection hits."
    )
    critical_pattern_count: int = Field(
        default=0, description="Entries with critical-pattern hits."
    )
    mean_entropy: float = Field(default=0.0, description="Mean Shannon entropy (bits).")
