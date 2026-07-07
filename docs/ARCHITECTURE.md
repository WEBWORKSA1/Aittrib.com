# Aittrib Architecture (Stage 1)

## System overview

```
[Shopify]   [Google Ads]   [Meta]   [TikTok]        (read-only OAuth)
    |            |            |         |
    +------------+-----+------+---------+
                       v
              INGESTION WORKERS  (Vercel cron / Python)
                       v
                  SUPABASE (Postgres)
     merchants | channels | touchpoints | journeys
     orders    | spend_daily | recommendations | prediction_outcomes
                       v
                  MATH ENGINE (Python)
        engine/markov.py   -> removal-effect channel values
        engine/mmm.py      -> spend->revenue cross-check
                       v
                REPORT GENERATOR (weekly)
   one page: true channel values + ONE recommendation + prediction
                       v
        +--------------+---------------+
        v                              v
  MERCHANT DASHBOARD           PUBLIC ACCURACY DASHBOARD
  (Next.js, auth)              (Next.js, public — the moat)
```

## Core design decisions

1. **Read-only everywhere.** Stage 1 never writes to ad platforms. No execution liability, minimal API-approval friction, safest scopes.
2. **One recommendation per report.** The action-rate on that single recommendation is the month-6 fork metric (raise for autopilot vs stay bootstrapped). Multiple recommendations make action-rate unmeasurable.
3. **prediction_outcomes is a v1 table, not a later feature.** The public accuracy record needs months of history to be credible. It starts with merchant #1.
4. **Journey capture is dual-source.** (a) UTM/click-id reconstruction from Shopify order attributes + landing params; (b) first-party pixel (later milestone). Markov runs on whatever journeys exist; MMM covers the blind spots because it needs only spend and revenue time series — no user-level tracking.
5. **Markov + MMM disagree sometimes. That is a feature.** The report shows both; divergence is flagged, not hidden. Transparency is the brand.

## The math (summary — full methodology published openly in docs/METHODOLOGY.md)

### Markov removal effect
- States: channels + START + CONVERSION + NULL.
- Build transition matrix from observed journeys.
- Baseline conversion probability P = absorption probability into CONVERSION from START.
- For each channel c: remove c (redirect its transitions to NULL), recompute P_c.
- Removal effect of c = (P − P_c) / P. Normalize removal effects to allocate credited revenue.

### MMM cross-check
- Weekly grain: revenue ~ f(spend per channel) with adstock + saturation (Hill) transforms.
- Small-data regime: Bayesian priors, honest wide intervals. Purpose is direction-of-error checking on Markov, not precision.

## Integration notes

| Source | Scope | Grain | Notes |
|---|---|---|---|
| Shopify | read_orders, read_marketing_events | order-level | journey seeds from landing_site + UTM + click IDs (gclid/fbclid/ttclid) |
| Google Ads | read | daily spend by campaign | OAuth + developer token approval — START DAY ONE, longest approval |
| Meta | ads_read | daily spend by campaign | app review required |
| TikTok | Reporting API read | daily spend | fastest approval, do last |

## Environments

- Vercel: web + api. Cron: ingestion nightly, report weekly (Mon 06:00 merchant-local).
- Supabase: Postgres + Auth + RLS per merchant.
- Python workers: run inside Vercel functions where fast enough; heavy Markov/MMM jobs move to scheduled external workers only if needed — decide at M2, do not pre-build.
