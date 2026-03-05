"""
History endpoint — GET /api/v1/history.

Returns the 50 most recent forensic analysis summaries for the authenticated
user identified by the ``X-Clerk-User-Id`` request header (Clerk user ID).

Design notes
------------
* Authentication is handled at the Next.js edge via Clerk middleware — the
  backend trusts the ``X-Clerk-User-Id`` value forwarded by the verified
  frontend.  For production hardening, verify the Clerk JWT instead of
  trusting the header directly.
* Only summary columns are returned (no per-entry details) to keep the
  response lean.  The full ``report_json`` blob is available for a future
  detail endpoint.
* The query is bounded to 50 rows ordered by ``analyzed_at DESC`` to prevent
  unbounded result sets.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import dynamic_limit, limiter
from app.models.database_models import AnalysisResult
from app.models.schemas import AnalysisResultSummary

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_HISTORY_ROWS = 50


@router.get(
    "",
    response_model=list[AnalysisResultSummary],
    status_code=status.HTTP_200_OK,
    summary="Retrieve forensic analysis history for the authenticated user",
    response_description="List of analysis summaries ordered by date descending.",
)
@limiter.limit(dynamic_limit)
async def get_history(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-Clerk-User-Id"),
) -> list[AnalysisResultSummary]:
    """Return the *N* most recent analysis summaries for the requesting user.

    The caller must supply a ``X-Clerk-User-Id`` header whose value is their
    Clerk user ID.  Requests without this header receive ``401 Unauthorized``.

    Results are ordered newest-first and capped at
    :data:`_MAX_HISTORY_ROWS` to bound response size.
    """
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Clerk-User-Id header is required to retrieve history.",
        )

    stmt = (
        select(AnalysisResult)
        .where(AnalysisResult.user_id == x_user_id)
        .order_by(AnalysisResult.analyzed_at.desc())
        .limit(_MAX_HISTORY_ROWS)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        AnalysisResultSummary(
            id=str(row.id),
            analyzed_at=row.analyzed_at.isoformat(),
            total_entries=row.total_entries,
            overall_risk_score=row.overall_risk_score,
            overall_risk_level=row.overall_risk_level,
            anomaly_count=row.anomaly_count,
            sensitive_entry_count=row.sensitive_entry_count,
            sqli_entry_count=row.sqli_entry_count,
            critical_pattern_count=row.critical_pattern_count,
            mean_entropy=row.mean_entropy,
        )
        for row in rows
    ]
