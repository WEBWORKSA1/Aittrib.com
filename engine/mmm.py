"""Aittrib lightweight MMM cross-check (skeleton).

Purpose: direction-of-error check on Markov results using ONLY spend and revenue
time series (no user-level tracking). Not a precision instrument at SMB data
volumes — wide intervals are honest and shown as such.

Model (M2 implementation):
  revenue_t ~ intercept + trend + seasonality
              + sum_c beta_c * hill(adstock(spend_{c,t}))

- adstock: geometric carryover, decay per channel (prior: 0.1-0.6)
- hill: saturation transform (diminishing returns)
- Fit: Bayesian (numpyro or pymc), weekly grain, min 26 weeks of data.
- Output: beta posterior per channel -> marginal ROAS -> compare sign/rank
  against Markov credit shares. Divergence is FLAGGED in the report, not hidden.

Decision: do not implement before the Markov path produces reports for pilot
stores. MMM without 6 months of spend variation is theater.
"""

def adstock(spend: list[float], decay: float) -> list[float]:
    out, carry = [], 0.0
    for s in spend:
        carry = s + decay * carry
        out.append(carry)
    return out


def hill(x: float, half_saturation: float, shape: float = 1.0) -> float:
    if x <= 0:
        return 0.0
    return x**shape / (half_saturation**shape + x**shape)
