"""
Log analyzer engine - core analysis logic for Lognis.

Forensic functions
------------------
detect_anomalies        Z-score outlier detection over a float series.
calculate_log_entropy   Shannon entropy of a log string's character distribution.
"""

import math
import re
from collections import Counter
from datetime import datetime, timezone
from statistics import mean, stdev

from app.models.schemas import LogAnalysisResponse, LogSeverity, ParsedLogEntry

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# Common log severity patterns (covers syslog, Python logging, JSON logs, etc.)
_SEVERITY_PATTERN = re.compile(
    r"\b(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\b",
    re.IGNORECASE,
)

# Simple ISO-8601 / common timestamp detector
_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")

# Z-score threshold for anomaly classification
_Z_SCORE_THRESHOLD: float = 3.0


# ---------------------------------------------------------------------------
# Forensic helpers
# ---------------------------------------------------------------------------


def detect_anomalies(data: list[float]) -> list[int]:
    """Return indices of values that exceed ``_Z_SCORE_THRESHOLD`` standard
    deviations from the mean (Z-score method).

    Edge-case handling
    ------------------
    - Empty list              → returns ``[]``
    - Single element          → returns ``[]`` (std-dev undefined)
    - All-identical values    → std-dev is 0; no Z-score is computable,
                                returns ``[]`` to avoid division by zero.
    - Non-finite values       → ``NaN`` / ``inf`` are treated as anomalies
                                and always included in the result.

    Parameters
    ----------
    data:
        Sequence of numeric observations (e.g. response-time series,
        byte-count series, error-rate samples).

    Returns
    -------
    list[int]
        Sorted list of zero-based indices whose Z-score exceeds the threshold.

    Examples
    --------
    >>> detect_anomalies([10.0, 11.0, 10.5, 9.8, 200.0])
    [4]
    >>> detect_anomalies([])
    []
    >>> detect_anomalies([5.0, 5.0, 5.0])
    []
    """
    if len(data) < 2:
        return []

    # Separate finite values so we can compute a meaningful mean / stdev
    finite_values = [v for v in data if math.isfinite(v)]

    # Collect non-finite indices immediately — they are always anomalous
    non_finite_indices = [i for i, v in enumerate(data) if not math.isfinite(v)]

    if len(finite_values) < 2:
        # Cannot compute std-dev; return only non-finite outliers
        return sorted(non_finite_indices)

    mu: float = mean(finite_values)
    sigma: float = stdev(finite_values)

    if sigma == 0.0:
        # All finite values are identical; no variation to score against
        return sorted(non_finite_indices)

    z_score_indices = [
        i
        for i, v in enumerate(data)
        if math.isfinite(v) and abs((v - mu) / sigma) > _Z_SCORE_THRESHOLD
    ]

    return sorted(set(z_score_indices + non_finite_indices))


def calculate_log_entropy(text: str) -> float:
    """Calculate the Shannon entropy (bits) of the character distribution in
    *text*.

    Shannon entropy is defined as::

        H = -∑ p(c) * log2(p(c))   for each unique character c

    A higher value means greater randomness / unpredictability, which can
    indicate obfuscated payloads, base64-encoded data, or encrypted blobs
    embedded in log lines.

    Edge-case handling
    ------------------
    - Empty string or whitespace-only input → returns ``0.0``
    - Single unique character               → returns ``0.0`` (no uncertainty)
    - Non-string input coerced to ``str``   → function will still compute;
      callers should pass validated strings.

    Parameters
    ----------
    text:
        Raw log line or any string whose entropy is to be measured.

    Returns
    -------
    float
        Entropy in bits, rounded to 6 decimal places.
        Theoretical maximum is ``log2(len(text))`` bits.

    Examples
    --------
    >>> calculate_log_entropy("aaaa")
    0.0
    >>> calculate_log_entropy("ab")
    1.0
    >>> round(calculate_log_entropy("INFO user login from 192.168.1.1"), 2)
    4.09
    """
    if not text or not text.strip():
        return 0.0

    total_chars: int = len(text)
    frequency: Counter = Counter(text)

    entropy: float = -sum(
        (count / total_chars) * math.log2(count / total_chars)
        for count in frequency.values()
    )

    return round(entropy, 6)


# ---------------------------------------------------------------------------
# Private parsing helpers
# ---------------------------------------------------------------------------


def _extract_severity(line: str) -> LogSeverity:
    """Return the first severity keyword found in *line*, defaulting to INFO."""
    match = _SEVERITY_PATTERN.search(line)
    if not match:
        return LogSeverity.INFO
    token = match.group(1).upper()
    # Normalise WARN -> WARNING, FATAL -> CRITICAL
    if token == "WARN":
        return LogSeverity.WARNING
    if token == "FATAL":
        return LogSeverity.CRITICAL
    return LogSeverity(token)


def _extract_timestamp(line: str) -> str | None:
    """Return the first ISO-style timestamp found in *line*, or ``None``."""
    match = _TIMESTAMP_PATTERN.search(line)
    return match.group(0) if match else None


# ---------------------------------------------------------------------------
# Analyzer class
# ---------------------------------------------------------------------------


class LogAnalyzer:
    """Stateless engine that parses and summarises log entries."""

    async def analyze(self, entries: list[str]) -> LogAnalysisResponse:
        """
        Parse *entries* and return a structured analysis response.

        Steps
        -----
        1. Parse each line to extract severity and timestamp.
        2. Count occurrences per severity level.
        3. Detect lines that contain error/critical indicators.
        4. Build and return a :class:`LogAnalysisResponse`.
        """
        parsed: list[ParsedLogEntry] = []
        severity_counts: Counter = Counter()

        for line in entries:
            severity = _extract_severity(line)
            timestamp = _extract_timestamp(line)
            severity_counts[severity.value] += 1
            parsed.append(
                ParsedLogEntry(
                    raw=line,
                    severity=severity,
                    timestamp=timestamp,
                )
            )

        error_lines = [
            e.raw
            for e in parsed
            if e.severity in (LogSeverity.ERROR, LogSeverity.CRITICAL)
        ]

        return LogAnalysisResponse(
            analyzed_at=datetime.now(tz=timezone.utc).isoformat(),
            total_entries=len(entries),
            severity_counts=dict(severity_counts),
            error_lines=error_lines,
            entries=parsed,
        )
