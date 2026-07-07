# API layer (Vercel serverless)

Build order — Google Ads first because its developer-token approval is the
longest external dependency in the whole project. Apply on day one.

| Endpoint | Purpose | Milestone |
|---|---|---|
| /api/auth/shopify | Shopify OAuth (read_orders, read_marketing_events) | M1 |
| /api/auth/google | Google Ads OAuth (read) — developer token application FIRST | M1 |
| /api/auth/meta | Meta ads_read OAuth + app review | M1-M2 |
| /api/auth/tiktok | TikTok Reporting API | M2 |
| /api/ingest/orders | Nightly Shopify order sync (cron) | M1 |
| /api/ingest/spend | Nightly spend sync all platforms (cron) | M1-M2 |
| /api/report/run | Weekly attribution run + report generation (cron) | M2 |
| /api/recommendations/act | Merchant marks acted/ignored — feeds fork metric | M2 |
| /api/public/accuracy | Public accuracy dashboard data (aggregate, anonymized) | M2 |

Rules:
- Read-only scopes everywhere. No write access to any ad platform in Stage 1.
- Tokens encrypted at rest. Never logged.
- Every recommendation INSERT must create the report row and the prediction
  fields atomically — the accuracy dashboard depends on no orphan predictions.
