"""
ORM models for Lognis.

Tables
------
analysis_results
    Stores a persisted summary of every forensic analysis that was triggered
    by an authenticated user.  The full report JSON is retained alongside
    denormalised summary columns so that history listings can be served with
    a single indexed query without deserialising the payload.

Schema notes
------------
* ``user_id`` is the Clerk user ID string (e.g. ``user_2abc...``).  It is
  **not** a foreign key — we trust the value provided by the frontend via the
  ``X-User-Id`` header (gated behind Clerk's middleware on the client).
* ``report_json`` stores the complete ``ForensicAnalysisReport`` as a JSON
  text blob.  This allows future expansion without schema migrations.
* ``created_at`` uses a server-side default so the DB records insertion time
  independently of ``analyzed_at`` (which is the analysis timestamp).
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class AnalysisResult(Base):
    """Persisted record of a single forensic analysis run.

    Attributes
    ----------
    id:
        UUID primary key — auto-generated on creation.
    user_id:
        Clerk user ID string supplied by the authenticated client via the
        ``X-User-Id`` request header.  Indexed for fast per-user queries.
    analyzed_at:
        UTC timestamp embedded in the ``ForensicAnalysisReport`` — when the
        analysis was actually executed.
    total_entries:
        Number of log entries that were analysed.
    overall_risk_score:
        Batch-level composite risk score (0–10).
    overall_risk_level:
        Human-readable risk band (``"Low"`` / ``"Medium"`` / ``"High"`` /
        ``"Critical"``).
    anomaly_count:
        Number of Z-score anomaly entries detected.
    sensitive_entry_count:
        Number of entries with sensitive-data heuristic hits.
    sqli_entry_count:
        Number of entries with SQL-injection heuristic hits.
    critical_pattern_count:
        Number of entries with critical-pattern heuristic hits.
    mean_entropy:
        Mean Shannon entropy across all entries (bits).
    report_json:
        Full ``ForensicAnalysisReport`` serialised as a JSON string for
        on-demand retrieval.
    created_at:
        Server-side insertion timestamp (set by the database).
    """

    __tablename__ = "analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    total_entries: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    overall_risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    anomaly_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sensitive_entry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    sqli_entry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    critical_pattern_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    mean_entropy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
