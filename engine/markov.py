"""Aittrib Markov removal-effect attribution engine.

Method (Anderl et al., 2014): model journeys as a first-order Markov chain over
channel states plus START / CONVERSION / NULL absorbing states. A channel's value
is its removal effect: how much total conversion probability drops when the
channel is deleted from the chain.

Transparency rule: this file is the published methodology. Keep it readable.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

START = "__start__"
CONV = "__conversion__"
NULL = "__null__"


@dataclass
class AttributionResult:
    baseline_conversion_prob: float
    removal_effects: dict[str, float]          # channel -> raw removal effect
    credit_shares: dict[str, float]            # normalized to sum to 1.0
    credited_revenue: dict[str, float]
    n_journeys: int
    n_conversions: int


def build_transition_counts(journeys: list[tuple[list[str], bool]]) -> dict[str, dict[str, int]]:
    """journeys: list of (channel_path, converted)."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for path, converted in journeys:
        states = [START] + list(path) + [CONV if converted else NULL]
        for a, b in zip(states, states[1:]):
            counts[a][b] += 1
    return counts


def to_matrix(counts, states: list[str]) -> np.ndarray:
    idx = {s: i for i, s in enumerate(states)}
    m = np.zeros((len(states), len(states)))
    for a, outs in counts.items():
        if a not in idx:
            continue
        total = sum(c for b, c in outs.items() if b in idx)
        if total == 0:
            continue
        for b, c in outs.items():
            if b in idx:
                m[idx[a], idx[b]] = c / total
    # absorbing states
    for absorbing in (CONV, NULL):
        i = idx[absorbing]
        m[i, :] = 0.0
        m[i, i] = 1.0
    return m


def conversion_probability(m: np.ndarray, states: list[str], max_iter: int = 500, tol: float = 1e-12) -> float:
    """Absorption probability into CONV starting from START (power iteration)."""
    idx = {s: i for i, s in enumerate(states)}
    v = np.zeros(len(states))
    v[idx[START]] = 1.0
    prev_conv = 0.0
    for _ in range(max_iter):
        v = v @ m
        conv = v[idx[CONV]]
        if abs(conv - prev_conv) < tol:
            break
        prev_conv = conv
    return float(v[idx[CONV]])


def remove_channel(counts, channel: str):
    """Redirect all transitions INTO `channel` to NULL; drop transitions out of it."""
    new: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for a, outs in counts.items():
        if a == channel:
            continue
        for b, c in outs.items():
            new[a][NULL if b == channel else b] += c
    return new


def run_attribution(journeys: list[tuple[list[str], bool]], revenues: list[float]) -> AttributionResult:
    """Main entry point.

    journeys: [(path, converted), ...] aligned with revenues (0 for non-converting).
    """
    channels = sorted({ch for path, _ in journeys for ch in path})
    states = [START, *channels, CONV, NULL]

    counts = build_transition_counts(journeys)
    p_base = conversion_probability(to_matrix(counts, states), states)

    removal_effects: dict[str, float] = {}
    for ch in channels:
        reduced_states = [s for s in states if s != ch]
        p_removed = conversion_probability(
            to_matrix(remove_channel(counts, ch), reduced_states), reduced_states
        )
        removal_effects[ch] = max(0.0, (p_base - p_removed) / p_base) if p_base > 0 else 0.0

    total_re = sum(removal_effects.values())
    credit_shares = {
        ch: (re / total_re if total_re > 0 else 0.0) for ch, re in removal_effects.items()
    }
    total_revenue = float(sum(revenues))
    credited_revenue = {ch: share * total_revenue for ch, share in credit_shares.items()}

    return AttributionResult(
        baseline_conversion_prob=p_base,
        removal_effects=removal_effects,
        credit_shares=credit_shares,
        credited_revenue=credited_revenue,
        n_journeys=len(journeys),
        n_conversions=sum(1 for _, c in journeys if c),
    )


if __name__ == "__main__":
    # Smoke test with a toy dataset.
    demo = [
        (["tiktok", "email"], True),
        (["google_ads"], True),
        (["meta", "google_ads"], False),
        (["tiktok"], False),
        (["meta", "email"], True),
        (["google_ads", "email"], False),
    ]
    revs = [120.0, 80.0, 0.0, 0.0, 95.0, 0.0]
    r = run_attribution(demo, revs)
    print(f"baseline P(conv) = {r.baseline_conversion_prob:.4f}")
    for ch, share in sorted(r.credit_shares.items(), key=lambda x: -x[1]):
        print(f"{ch:12s} removal={r.removal_effects[ch]:.4f} share={share:.2%} revenue=${r.credited_revenue[ch]:.2f}")

# TODO (M2):
# - Higher-order chains (order-2) once journey volume supports it; compare stability.
# - Minimum journey threshold + confidence via bootstrap resampling.
# - Time-decay weighting within window.
