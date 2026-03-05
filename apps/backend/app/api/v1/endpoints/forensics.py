"""
Forensic analysis endpoint — POST /api/v1/analyze.

Accepts a batch of :class:`~app.models.log_schema.LogEntry` objects and
returns a :class:`~app.models.schemas.ForensicAnalysisReport` that includes:

* Per-entry Shannon entropy scores: H(X) = -∑ P(xᵢ) log₂ P(xᵢ)
* Z-score–based anomaly flags across the entropy distribution of the batch.
* Heuristic flags: sensitive-data, SQL injection, and critical-pattern matching.
* A composite ``risk_score`` (0–10) per entry via the Risk Scoring Engine:

      S_total = min(10, ω_H · Φ(H) + ω_Z · Ψ(Z) + Σ Kj)

* A ``risk_level`` label and a ``risk_breakdown`` dict for transparency.
* Batch-level aggregates: ``overall_risk_score``, ``overall_risk_level``,
  ``overall_risk_breakdown``.
"""

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from statistics import mean as _mean
from statistics import stdev as _stdev
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.rate_limit import dynamic_limit, limiter
from app.engine.analyzer import calculate_log_entropy, detect_anomalies
from app.engine.heuristics import HeuristicResult, analyse_message
from app.engine.risk_engine import RiskResult, calculate_composite_risk
from app.models.log_schema import LogEntry, LogLevel
from app.models.schemas import EntryAnalysisReport, ForensicAnalysisReport

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_z_score(value: float, mu: float, sigma: float) -> float:
    """Return the absolute Z-score of *value* given population *mu* and *sigma*.

    Returns ``0.0`` when *sigma* is zero (all values identical — no spread).
    """
    if sigma == 0.0:
        return 0.0
    return abs(value - mu) / sigma


def _collect_penalties(
    heuristic: HeuristicResult,
    level: str,
) -> list[float]:
    """Assemble the full penalty list for a single entry.

    Combines message-level heuristic penalties from the heuristic engine
    with the level-based penalty (``PENALTY_CRITICAL_LEVEL``) which depends
    on the *log level* rather than the message content.

    Parameters
    ----------
    heuristic:
        Result from :func:`~app.engine.heuristics.analyse_message`.
    level:
        The normalised log level string (e.g. ``"ERROR"``).
    """
    penalties = list(heuristic.penalties)  # copy — don't mutate the frozen dataclass
    if level in (LogLevel.ERROR.value, LogLevel.CRITICAL.value):
        penalties.append(settings.PENALTY_CRITICAL_LEVEL)
    return penalties


def _breakdown_to_dict(result: RiskResult) -> dict[str, float]:
    """Convert a :class:`~app.engine.risk_engine.RiskBreakdown` to a plain dict."""
    return {
        "entropy_factor": result.breakdown.entropy_factor,
        "anomaly_factor": result.breakdown.anomaly_factor,
        "heuristic_penalty": result.breakdown.heuristic_penalty,
        "raw_total": result.breakdown.raw_total,
    }


def _mean_breakdown(breakdowns: list[dict[str, float]]) -> dict[str, float]:
    """Return the element-wise mean of a list of breakdown dicts, rounded to 2 d.p."""
    if not breakdowns:
        return {
            "entropy_factor": 0.0,
            "anomaly_factor": 0.0,
            "heuristic_penalty": 0.0,
            "raw_total": 0.0,
        }
    keys = ("entropy_factor", "anomaly_factor", "heuristic_penalty", "raw_total")
    n = len(breakdowns)
    return {k: round(sum(b[k] for b in breakdowns) / n, 2) for k in keys}


async def _fetch_historical_entropy(db: AsyncSession, user_id: str) -> list[float]:
    """Fetch the 100 most recent per-batch mean entropy values for *user_id*.

    Used to build a cross-batch reference distribution for Z-score computation
    so that the anomaly signal reflects deviation from the user's historical
    baseline rather than only the current batch.

    Returns an empty list when the DB is unavailable or no history exists.
    """
    from app.models.database_models import (
        AnalysisResult,
    )  # deferred — avoids circular import

    stmt = (
        select(AnalysisResult.mean_entropy)
        .where(AnalysisResult.user_id == user_id)
        .order_by(AnalysisResult.analyzed_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    return [v for v in result.scalars().all() if v is not None]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=ForensicAnalysisReport,
    status_code=status.HTTP_200_OK,
    summary="Forensic analysis of a batch of log entries",
    response_description=(
        "JSON report with per-entry entropy, heuristic flags, composite risk "
        "scores, and batch-level aggregates."
    ),
)
@limiter.limit(dynamic_limit)
async def analyze_entries(
    request: Request,
    entries: Annotated[list[LogEntry], Body()],
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-Clerk-User-Id"),
) -> ForensicAnalysisReport:
    """Run full forensic analysis on a list of structured log entries.

    **Pipeline**

    1. **Entropy** — compute H(X) = -∑ P(xᵢ) log₂ P(xᵢ) for each message.
    2. **Z-score anomaly detection** — flag entries whose entropy deviates
       more than 3 σ from the batch mean.  Entries in batches too small
       for a valid Z-score (< 2 entries or zero variance) receive
       ``z_score = 0.0`` and ``is_anomaly = False``.
    3. **Heuristic scanning** — detect sensitive data (credentials, Base64
       blobs), SQL injection patterns, and critical operational keywords.
    4. **Risk scoring** — call the Risk Scoring Engine for each entry:

           S_total = min(10, ω_H · Φ(H) + ω_Z · Ψ(Z) + Σ Kj)

    5. **Batch aggregation** — compute batch-level statistics and the
       ``overall_risk_score`` / ``overall_risk_level``.

    **Edge cases**

    * Empty list → zero-count report with all scores ``0.0`` and level
      ``"Low"``.
    * Single entry → Z-score undefined; ``z_score = 0.0``, heuristic and
      entropy signals still apply.
    * All-identical entropy values → zero variance; ``z_score = 0.0``
      for every entry.

    **Request body example**

    ```json
    [
      {"level": "INFO",  "message": "User login successful",                        "source": "auth-service"},
      {"level": "WARN",  "message": "Connection refused to db:5432",                "source": "order-service"},
      {"level": "ERROR", "message": "secret_token=eyJhbGciOiJIUzI1NiJ9.payload",   "source": "api-gateway"},
      {"level": "DEBUG", "message": "SELECT * FROM users WHERE id=1 OR 1=1 --",    "source": "query-log"}
    ]
    ```

    ``"WARN"`` is normalised to ``"WARNING"`` at the Pydantic model layer.
    """
    if not isinstance(entries, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request body must be a JSON array of LogEntry objects.",
        )

    # ── Empty batch fast-path ────────────────────────────────────────────────
    if not entries:
        empty_breakdown: dict[str, float] = {
            "entropy_factor": 0.0,
            "anomaly_factor": 0.0,
            "heuristic_penalty": 0.0,
            "raw_total": 0.0,
        }
        return ForensicAnalysisReport(
            analyzed_at=datetime.now(tz=timezone.utc).isoformat(),
            total_entries=0,
            mean_entropy=0.0,
            anomaly_count=0,
            anomaly_indices=[],
            sensitive_entry_count=0,
            sqli_entry_count=0,
            critical_pattern_count=0,
            overall_risk_score=0.0,
            overall_risk_level="Low",
            overall_risk_breakdown=empty_breakdown,
            entries=[],
        )

    # ── Step 1: Shannon entropy per entry ────────────────────────────────────
    entropy_scores: list[float] = [
        calculate_log_entropy(entry.message) for entry in entries
    ]

    # ── Step 2: Z-score anomaly detection ────────────────────────────────────
    anomaly_indices: list[int] = detect_anomalies(entropy_scores)
    anomaly_set: frozenset[int] = frozenset(anomaly_indices)

    # Build the reference distribution for per-entry Z-score computation.
    # For authenticated users we pull their historical mean_entropy values from
    # Neon Postgres (up to the last 100 batches) so that the Z-score reflects
    # deviation from the user's personal baseline rather than only the current
    # batch.  Anonymous users (or those with fewer than 2 prior analyses) fall
    # back to intra-batch statistics.
    hist_values: list[float] = []
    if x_user_id:
        try:
            hist_values = await _fetch_historical_entropy(db, x_user_id)
        except Exception:
            logger.warning(
                "Failed to fetch historical entropy for user %s — "
                "falling back to intra-batch Z-score.",
                x_user_id,
                exc_info=True,
            )

    # Use historical + current batch when enough history exists (≥ 2 prior
    # analyses), otherwise use only the current batch.
    ref_values: list[float] = (
        hist_values + entropy_scores if len(hist_values) >= 2 else entropy_scores
    )

    if len(ref_values) >= 2:
        mu: float = sum(ref_values) / len(ref_values)
        try:
            sigma: float = _stdev(ref_values)
        except Exception:
            sigma = 0.0
    else:
        mu = entropy_scores[0] if entropy_scores else 0.0
        sigma = 0.0

    # ── Step 3: Heuristic scanning ───────────────────────────────────────────
    heuristic_results: list[HeuristicResult] = [
        analyse_message(entry.message) for entry in entries
    ]

    # ── Step 4: Risk scoring + build per-entry reports ───────────────────────
    entry_reports: list[EntryAnalysisReport] = []
    entry_breakdowns: list[dict[str, float]] = []

    for idx, entry in enumerate(entries):
        h = heuristic_results[idx]
        is_anomaly = idx in anomaly_set
        z_score = _compute_z_score(entropy_scores[idx], mu, sigma)
        penalties = _collect_penalties(h, entry.level.value)

        risk: RiskResult = calculate_composite_risk(
            entropy=entropy_scores[idx],
            z_score=z_score,
            penalties=penalties,
        )

        breakdown_dict = _breakdown_to_dict(risk)
        entry_breakdowns.append(breakdown_dict)

        entry_reports.append(
            EntryAnalysisReport(
                id=entry.id,
                source=entry.source,
                level=entry.level.value,
                message=entry.message,
                entropy=entropy_scores[idx],
                is_anomaly=is_anomaly,
                has_sensitive_data=h.has_sensitive_data,
                sensitive_data_tags=h.sensitive_data_tags,
                has_sqli=h.has_sqli,
                sqli_tags=h.sqli_tags,
                has_critical_pattern=h.has_critical_pattern,
                critical_pattern_tags=h.critical_pattern_tags,
                risk_score=risk.risk_score,
                risk_level=risk.risk_level,
                risk_breakdown=breakdown_dict,
            )
        )

    # ── Step 5: Batch-level aggregation ──────────────────────────────────────
    mean_entropy = round(sum(entropy_scores) / len(entropy_scores), 6)
    sensitive_count = sum(1 for h in heuristic_results if h.has_sensitive_data)
    sqli_count = sum(1 for h in heuristic_results if h.has_sqli)
    critical_count = sum(1 for h in heuristic_results if h.has_critical_pattern)

    overall_risk_score = round(
        sum(r.risk_score for r in entry_reports) / len(entry_reports), 2
    )

    # Derive overall risk level from the same banding used per-entry
    # (reuse the engine's _risk_level by constructing a throwaway RiskResult)
    from app.engine.risk_engine import _risk_level  # noqa: PLC0415 — localised import

    overall_risk_level = _risk_level(overall_risk_score)
    overall_breakdown = _mean_breakdown(entry_breakdowns)

    analyzed_at = datetime.now(tz=timezone.utc).isoformat()

    report = ForensicAnalysisReport(
        analyzed_at=analyzed_at,
        total_entries=len(entries),
        mean_entropy=mean_entropy,
        anomaly_count=len(anomaly_indices),
        anomaly_indices=anomaly_indices,
        sensitive_entry_count=sensitive_count,
        sqli_entry_count=sqli_count,
        critical_pattern_count=critical_count,
        overall_risk_score=overall_risk_score,
        overall_risk_level=overall_risk_level,
        overall_risk_breakdown=overall_breakdown,
        entries=entry_reports,
    )

    # ── Persist report for authenticated users ────────────────────────────────
    if x_user_id:
        await _persist_report(report, x_user_id)

    return report


async def _persist_report(report: ForensicAnalysisReport, user_id: str) -> None:
    """Save a forensic report to the database.

    Non-fatal: if the database is unavailable the analysis result is still
    returned to the client — only persistence is skipped.
    """
    from app.models.database_models import (
        AnalysisResult,
    )  # deferred — avoids circular import

    try:
        analyzed_at_dt = datetime.fromisoformat(report.analyzed_at)
        row = AnalysisResult(
            user_id=user_id,
            analyzed_at=analyzed_at_dt,
            total_entries=report.total_entries,
            overall_risk_score=report.overall_risk_score,
            overall_risk_level=report.overall_risk_level,
            anomaly_count=report.anomaly_count,
            sensitive_entry_count=report.sensitive_entry_count,
            sqli_entry_count=report.sqli_entry_count,
            critical_pattern_count=report.critical_pattern_count,
            mean_entropy=report.mean_entropy,
            report_json=report.model_dump_json(),
        )
        async with AsyncSessionLocal() as db:
            db.add(row)
            await db.commit()
        logger.debug("Persisted analysis result for user %s", user_id)
    except Exception:
        logger.warning(
            "Failed to persist analysis result for user %s — DB may be unavailable.",
            user_id,
            exc_info=True,
        )
