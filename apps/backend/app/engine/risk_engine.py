"""
Risk Scoring Engine for Lognis forensic analysis.

Implements the composite risk formula:

    S_total = min(10, ω_H · Φ(H) + ω_Z · Ψ(Z) + Σ Kj)

Where:

* **Φ(H)** — Entropy Factor: normalises Shannon entropy *H* to a [0, 10]
  scale against the configured base (3.0 bits) and maximum (8.0 bits).

* **Ψ(Z)** — Anomaly Factor: converts a per-entry Z-score to a [0, 10]
  signal using a piecewise linear function:
  - Z ≤ 2            → 0          (not anomalous)
  - 2 < Z < 5        → (Z - 2) × (10/3)  (linear ramp, reaches ~10 at Z=5)
  - Z ≥ 5            → 10         (fully anomalous)

* **Σ Kj** — Heuristic Penalties: sum of all applicable static-rule
  penalties drawn from :data:`~app.core.config.settings` (PENALTY_SECRET,
  PENALTY_SQLI, PENALTY_CRITICAL_LEVEL, …).

* **ω_H, ω_Z** — Dimension weights from :data:`~app.core.config.settings`
  (WEIGHT_ENTROPY, WEIGHT_ZSCORE).

All intermediate values are computed at full float precision and the final
``risk_score`` is rounded to 2 decimal places.

Public API
----------
RiskBreakdown
    Frozen dataclass exposing the individual factor contributions for
    transparency / debugging.

RiskResult
    Frozen dataclass carrying the final ``risk_score``, ``risk_level``
    label, and the ``breakdown``.

calculate_composite_risk(entropy, z_score, penalties) -> RiskResult
    Pure function — the single entry-point into this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.core.config import settings

# ---------------------------------------------------------------------------
# Risk level bands
# ---------------------------------------------------------------------------

# Ordered list of (lower_bound_inclusive, label).  The first band whose
# lower bound is ≤ risk_score wins.  Kept in descending threshold order so
# that the loop short-circuits quickly for high scores.
_RISK_BANDS: list[tuple[float, str]] = [
    (8.0, "Critical"),
    (6.0, "High"),
    (3.0, "Medium"),
    (0.0, "Low"),
]


def _risk_level(score: float) -> str:
    """Map a numeric score in [0, 10] to its risk-level label.

    Bands:
    - [0.0, 3.0)  → ``"Low"``
    - [3.0, 6.0)  → ``"Medium"``
    - [6.0, 8.0)  → ``"High"``
    - [8.0, 10.0] → ``"Critical"``
    """
    for threshold, label in _RISK_BANDS:
        if score >= threshold:
            return label
    return "Low"  # unreachable, but keeps type-checkers happy


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RiskBreakdown:
    """Individual factor contributions to the composite risk score.

    All values are rounded to 2 decimal places for readability.

    Attributes
    ----------
    entropy_factor:
        Weighted entropy contribution:  ``ω_H · Φ(H)``
    anomaly_factor:
        Weighted Z-score contribution:  ``ω_Z · Ψ(Z)``
    heuristic_penalty:
        Sum of all heuristic penalties: ``Σ Kj``
    raw_total:
        Unclipped sum of all three contributions.
    """

    entropy_factor: float
    anomaly_factor: float
    heuristic_penalty: float
    raw_total: float


@dataclass(frozen=True, slots=True)
class RiskResult:
    """Output of :func:`calculate_composite_risk`.

    Attributes
    ----------
    risk_score:
        Final composite score clamped to [0.0, 10.0], rounded to 2 d.p.
    risk_level:
        Human-readable severity label derived from ``risk_score``.
    breakdown:
        Factor-level decomposition for audit / transparency.
    """

    risk_score: float
    risk_level: str
    breakdown: RiskBreakdown


# ---------------------------------------------------------------------------
# Factor functions
# ---------------------------------------------------------------------------


def _entropy_factor(entropy: float) -> float:
    """Φ(H) — normalise Shannon entropy to a [0, 10] scale.

    Formula::

        Φ(H) = clamp((H - BASE) / (MAX - BASE), 0, 1) × 10

    Values below ``ENTROPY_BASE`` map to 0; values above ``ENTROPY_MAX``
    map to 10.  The function is monotonically increasing and continuous.

    Parameters
    ----------
    entropy:
        Shannon entropy in bits (output of ``calculate_log_entropy``).

    Returns
    -------
    float
        Normalised entropy factor in [0.0, 10.0].

    Examples
    --------
    >>> _entropy_factor(3.0)   # exactly at base → 0
    0.0
    >>> _entropy_factor(8.0)   # exactly at max → 10
    10.0
    >>> _entropy_factor(5.5)   # midpoint → 5
    5.0
    """
    base: float = settings.ENTROPY_BASE
    maximum: float = settings.ENTROPY_MAX
    span: float = maximum - base  # guaranteed > 0 (8.0 - 3.0 = 5.0)

    normalised = (entropy - base) / span
    clamped = max(0.0, min(1.0, normalised))
    return clamped * 10.0


def _anomaly_factor(z_score: float) -> float:
    """Ψ(Z) — piecewise linear Z-score → [0, 10] factor.

    Piecewise definition::

        Z ≤ 2            →  0
        2 < Z < 5        →  (Z - 2) × (10 / 3)   [linear ramp]
        Z ≥ 5            →  10

    The ramp is scaled so that Z = 5 exactly reaches 10, giving a smooth
    progression without hard cliffs at the boundaries.

    Parameters
    ----------
    z_score:
        Absolute Z-score for this entry relative to the batch's entropy
        distribution.  Pass ``0.0`` when the batch is too small to compute
        a valid Z-score (single entry, all-identical entropies, etc.).

    Returns
    -------
    float
        Anomaly factor in [0.0, 10.0].

    Examples
    --------
    >>> _anomaly_factor(0.0)
    0.0
    >>> _anomaly_factor(2.0)
    0.0
    >>> _anomaly_factor(3.5)   # midway through ramp → 5.0
    5.0
    >>> _anomaly_factor(5.0)
    10.0
    >>> _anomaly_factor(9.9)   # clamped at 10
    10.0
    """
    if z_score <= 2.0:
        return 0.0
    if z_score >= 5.0:
        return 10.0
    # Linear interpolation over (2, 5) → (0, 10)
    return (z_score - 2.0) * (10.0 / 3.0)


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------


def calculate_composite_risk(
    entropy: float,
    z_score: float,
    penalties: Sequence[float],
) -> RiskResult:
    """Compute the composite risk score for a single log entry.

    Applies the formula::

        S_total = min(10, ω_H · Φ(H) + ω_Z · Ψ(Z) + Σ Kj)

    Parameters
    ----------
    entropy:
        Shannon entropy of the log message in bits.  Typically the output
        of :func:`~app.engine.analyzer.calculate_log_entropy`.
    z_score:
        Absolute Z-score of this entry's entropy relative to the batch.
        Pass ``0.0`` when the batch is too small for a valid Z-score
        (fewer than 2 entries, all-identical entropies, etc.).
    penalties:
        Sequence of additive heuristic penalty values that apply to this
        entry.  Callers build this list from :data:`~app.core.config.settings`
        constants (e.g. ``PENALTY_SECRET``, ``PENALTY_SQLI``,
        ``PENALTY_CRITICAL_LEVEL``).  An empty sequence means no penalties.

    Returns
    -------
    RiskResult
        Frozen dataclass with ``risk_score`` (0.0–10.0, 2 d.p.),
        ``risk_level`` label, and a ``breakdown`` for transparency.

    Examples
    --------
    Clean INFO log with low entropy, no anomaly, no penalties::

        result = calculate_composite_risk(entropy=3.5, z_score=0.0, penalties=[])
        # risk_score ≈ 0.30  (only entropy contribution)

    Credential leak at high entropy (Z-score anomaly in batch)::

        result = calculate_composite_risk(
            entropy=5.5,
            z_score=3.8,
            penalties=[settings.PENALTY_SECRET, settings.PENALTY_CRITICAL_LEVEL],
        )
        # risk_score = 10.0  (penalties alone exceed the cap)
    """
    # ── Factor computations ──────────────────────────────────────────────────
    phi_h: float = _entropy_factor(entropy)
    psi_z: float = _anomaly_factor(z_score)
    sigma_k: float = sum(penalties)

    # ── Weighted combination ─────────────────────────────────────────────────
    weighted_entropy: float = settings.WEIGHT_ENTROPY * phi_h
    weighted_anomaly: float = settings.WEIGHT_ZSCORE * psi_z
    raw_total: float = weighted_entropy + weighted_anomaly + sigma_k

    # ── Clamp and round ──────────────────────────────────────────────────────
    risk_score: float = round(min(10.0, raw_total), 2)

    breakdown = RiskBreakdown(
        entropy_factor=round(weighted_entropy, 2),
        anomaly_factor=round(weighted_anomaly, 2),
        heuristic_penalty=round(sigma_k, 2),
        raw_total=round(raw_total, 2),
    )

    return RiskResult(
        risk_score=risk_score,
        risk_level=_risk_level(risk_score),
        breakdown=breakdown,
    )
