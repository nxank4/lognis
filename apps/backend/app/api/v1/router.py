"""
API v1 router - aggregates all v1 endpoint modules.

Route map
---------
GET  /api/v1/logs/          → logs.list_logs
POST /api/v1/logs/analyze   → logs.analyze_logs   (raw string batch)
POST /api/v1/analyze        → forensics.analyze_entries  (structured LogEntry batch)
GET  /api/v1/history        → history.get_history  (user analysis history)
"""

from fastapi import APIRouter

from app.api.v1.endpoints import forensics, history, logs

router = APIRouter()

# Raw log-line analysis (legacy / simple ingestion path).
router.include_router(logs.router, prefix="/logs", tags=["Logs"])

# Structured forensic analysis — entropy + anomaly detection on LogEntry objects.
# Registered with prefix "/analyze" so the full path is POST /api/v1/analyze.
router.include_router(forensics.router, prefix="/analyze", tags=["Forensics"])

# User analysis history — returns persisted report summaries for a Clerk user.
router.include_router(history.router, prefix="/history", tags=["History"])
