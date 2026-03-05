"""
Heuristic engine for static anomaly detection in log messages.

This module provides *rule-based* (non-statistical) signal extraction that
complements the Z-score / Shannon-entropy analysis in :mod:`app.engine.analyzer`.
It is designed as a pure penalty-source for the Risk Scoring Engine
(:mod:`app.engine.risk_engine`): each fired rule contributes a configured
penalty value drawn from :data:`~app.core.config.settings`.

Two categories of heuristics are implemented:

1. **Sensitive Data Detection** — patterns that indicate credentials or encoded
   payloads embedded in log lines (API keys, secret tokens, passwords, long
   Base64 blobs).  Fires ``PENALTY_SECRET`` per match.

2. **SQL Injection Detection** — patterns that suggest a SQL injection attempt
   was logged.  Fires ``PENALTY_SQLI`` per match.

3. **Critical Pattern Matching** — well-known operational failure keywords
   that warrant attention regardless of the declared log level (e.g. a DEBUG
   line containing "connection refused" is still operationally significant).
   These do **not** add a heuristic penalty directly; instead the caller
   passes ``PENALTY_CRITICAL_LEVEL`` when the *log level* itself is
   ERROR/CRITICAL.  Critical pattern tags are preserved for display purposes.

Public API
----------
HeuristicResult
    Immutable dataclass carrying the flags and penalty list produced for a
    single message.

analyse_message(message: str) -> HeuristicResult
    Entry-point: run all heuristic rules against *message* and return the
    combined result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.config import settings


# ---------------------------------------------------------------------------
# Compiled regex patterns — sensitive data
# ---------------------------------------------------------------------------

# Long Base64-like strings (≥ 20 contiguous Base64 chars).  Catches JWT
# segments, encoded secrets, and similar blobs that should not appear in logs.
_BASE64_BLOB = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")

# Explicit credential keywords followed by an assignment/separator and a
# non-whitespace value.  Covers both ENV-style and URL-style notation.
#   e.g.  secret_token=abc123   password: hunter2   api_key=xyz
_CREDENTIAL_KV = re.compile(
    r"""
    (?:
        secret[_\-]?token   |   # secret_token, secrettoken, secret-token
        api[_\-]?key        |   # api_key, apikey, api-key
        access[_\-]?token   |   # access_token …
        auth[_\-]?token     |
        private[_\-]?key    |
        client[_\-]?secret  |
        passwd              |
        password
    )
    \s*[:=]\s*\S+               # separator + at least one non-ws char
    """,
    re.IGNORECASE | re.VERBOSE,
)

# AWS-style access key IDs (20-char uppercase alphanumeric starting with AKIA).
_AWS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")

# Generic bearer / token header values that leaked into a log line.
_BEARER_TOKEN = re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Compiled regex patterns — SQL injection
# ---------------------------------------------------------------------------

# Each tuple: (pattern, human-readable tag).  Patterns are ordered from most
# specific to most generic to minimise false positives.
_SQLI_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Classic tautology attacks: ' OR '1'='1, " OR 1=1 --, etc.
    (
        re.compile(
            r"""['"]?\s*(?:OR|AND)\s+['"]?\w+['"]?\s*=\s*['"]?\w+['"]?""",
            re.IGNORECASE,
        ),
        "tautology",
    ),
    # UNION-based extraction: UNION SELECT, UNION ALL SELECT
    (
        re.compile(r"\bUNION\s+(?:ALL\s+)?SELECT\b", re.IGNORECASE),
        "union_select",
    ),
    # Stacked / batched queries: ; DROP TABLE, ; INSERT INTO …
    (
        re.compile(r";\s*(?:DROP|INSERT|UPDATE|DELETE|ALTER|EXEC)\b", re.IGNORECASE),
        "stacked_query",
    ),
    # Inline comment injection used to terminate clauses: --, #, /*
    (
        re.compile(r"(?:--|#|/\*)\s*$", re.MULTILINE),
        "comment_terminator",
    ),
    # Hex/char encoding bypass: 0x41414141, CHAR(65)
    (
        re.compile(r"\b(?:0x[0-9a-fA-F]{4,}|CHAR\s*\(\s*\d+\s*\))\b", re.IGNORECASE),
        "encoding_bypass",
    ),
    # Blind injection timing: SLEEP(n), WAITFOR DELAY
    (
        re.compile(r"\b(?:SLEEP\s*\(\s*\d+|WAITFOR\s+DELAY)\b", re.IGNORECASE),
        "time_based_blind",
    ),
    # Literal keyword "sql injection" appearing in message (may be logged by WAF)
    (
        re.compile(r"sql\s+injection", re.IGNORECASE),
        "keyword_match",
    ),
]


# ---------------------------------------------------------------------------
# Compiled regex patterns — critical operational errors
# ---------------------------------------------------------------------------

# Each tuple: (pattern, human-readable tag)
_CRITICAL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"connection\s+refused", re.IGNORECASE), "connection_refused"),
    (re.compile(r"disk\s+full", re.IGNORECASE), "disk_full"),
    (re.compile(r"no\s+space\s+left", re.IGNORECASE), "disk_full"),
    (re.compile(r"access\s+denied", re.IGNORECASE), "access_denied"),
    (re.compile(r"permission\s+denied", re.IGNORECASE), "access_denied"),
    (re.compile(r"unauthorized", re.IGNORECASE), "unauthorized"),
    (re.compile(r"authentication\s+fail(?:ed|ure)", re.IGNORECASE), "auth_failure"),
    (re.compile(r"out\s+of\s+memory", re.IGNORECASE), "out_of_memory"),
    (re.compile(r"\boom\b", re.IGNORECASE), "out_of_memory"),
    (re.compile(r"segmentation\s+fault", re.IGNORECASE), "segfault"),
    (re.compile(r"null\s*pointer", re.IGNORECASE), "null_pointer"),
    (re.compile(r"stack\s+overflow", re.IGNORECASE), "stack_overflow"),
    (re.compile(r"deadlock", re.IGNORECASE), "deadlock"),
    (re.compile(r"timeout(?:ed)?", re.IGNORECASE), "timeout"),
    (re.compile(r"remote\s+code\s+execution", re.IGNORECASE), "rce"),
]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HeuristicResult:
    """Aggregated heuristic flags for a single log message.

    Attributes
    ----------
    has_sensitive_data:
        ``True`` when at least one sensitive-data pattern matched.
    sensitive_data_tags:
        Sorted list of rule names that fired (e.g. ``["credential_kv",
        "base64_blob"]``).
    has_sqli:
        ``True`` when at least one SQL injection pattern matched.
    sqli_tags:
        Sorted list of SQL injection sub-type tags that fired
        (e.g. ``["tautology", "union_select"]``).
    has_critical_pattern:
        ``True`` when at least one critical operational-error pattern matched.
    critical_pattern_tags:
        Sorted list of operational-error tags that fired
        (e.g. ``["connection_refused", "disk_full"]``).
    penalties:
        List of penalty values (floats) that this entry contributes to the
        risk engine's ``Σ Kj`` term.  Callers pass this directly to
        :func:`~app.engine.risk_engine.calculate_composite_risk`.

        Penalty sources:
        - ``PENALTY_SECRET`` — added once when ``has_sensitive_data`` is True.
        - ``PENALTY_SQLI``   — added once when ``has_sqli`` is True.

        Note: ``PENALTY_CRITICAL_LEVEL`` is applied by the *endpoint* based
        on the entry's declared log level, not here, because that information
        lives on the :class:`~app.models.log_schema.LogEntry` object rather
        than the raw message string.
    """

    has_sensitive_data: bool = False
    sensitive_data_tags: list[str] = field(default_factory=list)
    has_sqli: bool = False
    sqli_tags: list[str] = field(default_factory=list)
    has_critical_pattern: bool = False
    critical_pattern_tags: list[str] = field(default_factory=list)
    penalties: list[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public analysis function
# ---------------------------------------------------------------------------


def analyse_message(message: str) -> HeuristicResult:
    """Run all heuristic rules against *message* and return a :class:`HeuristicResult`.

    The function is intentionally **pure** (no I/O, no side effects) so that
    it can be called safely from async contexts and unit-tested without mocking.

    Parameters
    ----------
    message:
        The log message string to inspect.  Empty / whitespace-only strings
        are handled gracefully — all flags will be ``False`` and the penalty
        list will be empty.

    Returns
    -------
    HeuristicResult
        Frozen dataclass with detection flags, matched tags, and the list of
        applicable penalty values.

    Examples
    --------
    >>> from app.core.config import settings
    >>> r = analyse_message("secret_token=abc123XYZ")
    >>> r.has_sensitive_data
    True
    >>> settings.PENALTY_SECRET in r.penalties
    True

    >>> r = analyse_message("SELECT * FROM users WHERE id=1 OR 1=1")
    >>> r.has_sqli
    True
    >>> settings.PENALTY_SQLI in r.penalties
    True

    >>> r = analyse_message("Connection refused after 3 retries")
    >>> r.has_critical_pattern
    True
    >>> r.critical_pattern_tags
    ['connection_refused']
    """
    if not message or not message.strip():
        return HeuristicResult()

    penalties: list[float] = []

    # ── Sensitive data detection ─────────────────────────────────────────────
    sensitive_tags: list[str] = []

    if _CREDENTIAL_KV.search(message):
        sensitive_tags.append("credential_kv")
    if _AWS_KEY.search(message):
        sensitive_tags.append("aws_access_key")
    if _BEARER_TOKEN.search(message):
        sensitive_tags.append("bearer_token")
    if _BASE64_BLOB.search(message):
        sensitive_tags.append("base64_blob")

    sensitive_tags = sorted(set(sensitive_tags))

    if sensitive_tags:
        penalties.append(settings.PENALTY_SECRET)

    # ── SQL injection detection ──────────────────────────────────────────────
    sqli_tags: list[str] = []

    for pattern, tag in _SQLI_PATTERNS:
        if pattern.search(message):
            sqli_tags.append(tag)

    sqli_tags = sorted(set(sqli_tags))

    if sqli_tags:
        penalties.append(settings.PENALTY_SQLI)

    # ── Critical pattern matching ────────────────────────────────────────────
    critical_tags: list[str] = []

    for pattern, tag in _CRITICAL_PATTERNS:
        if pattern.search(message):
            critical_tags.append(tag)

    critical_tags = sorted(set(critical_tags))

    return HeuristicResult(
        has_sensitive_data=bool(sensitive_tags),
        sensitive_data_tags=sensitive_tags,
        has_sqli=bool(sqli_tags),
        sqli_tags=sqli_tags,
        has_critical_pattern=bool(critical_tags),
        critical_pattern_tags=critical_tags,
        penalties=penalties,
    )
