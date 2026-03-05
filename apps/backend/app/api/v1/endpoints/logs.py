"""
Log analysis endpoints - v1.
"""

from fastapi import APIRouter, HTTPException, Request, status

from app.core.rate_limit import dynamic_limit, limiter
from app.engine.analyzer import LogAnalyzer
from app.models.schemas import LogAnalysisResponse, LogIngestionRequest

router = APIRouter()
_analyzer = LogAnalyzer()


@router.post(
    "/analyze",
    response_model=LogAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a batch of log entries",
)
@limiter.limit(dynamic_limit)
async def analyze_logs(
    request: Request,
    payload: LogIngestionRequest,
) -> LogAnalysisResponse:
    """
    Accept raw log lines and return structured analysis results.

    - **entries**: list of raw log strings to analyze.
    """
    if not payload.entries:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'entries' must contain at least one log line.",
        )

    result = await _analyzer.analyze(payload.entries)
    return result


@router.get(
    "/",
    summary="List recent analysis summaries",
)
async def list_logs() -> dict:
    """Return a placeholder list of recent analysis jobs."""
    return {"message": "No analyses stored yet.", "data": []}
