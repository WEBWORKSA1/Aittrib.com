-- Aittrib core schema v0.1
-- Run in Supabase SQL editor. RLS policies in 0002 (after auth model lands).

create table merchants (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  shop_domain text unique not null,          -- myshop.myshopify.com
  name text,
  plan text not null default 'trial',        -- trial | starter | growth | scale
  timezone text not null default 'America/New_York',
  monthly_ad_spend_usd numeric,              -- self-reported at onboarding, for segmentation
  autopilot_answer text,                     -- Option 2 validation: yes | no | maybe | unasked
  autopilot_asked_at timestamptz
);

create table channels (
  id serial primary key,
  merchant_id uuid not null references merchants(id) on delete cascade,
  key text not null,                         -- google_ads | meta | tiktok | email | organic | direct | referral
  display_name text not null,
  unique (merchant_id, key)
);

create table connections (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references merchants(id) on delete cascade,
  provider text not null,                    -- shopify | google_ads | meta | tiktok
  status text not null default 'pending',    -- pending | active | error | revoked
  external_account_id text,
  access_token_enc text,                     -- encrypted at rest; never log
  refresh_token_enc text,
  scopes text,
  last_sync_at timestamptz,
  error_detail text,
  unique (merchant_id, provider)
);

create table orders (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references merchants(id) on delete cascade,
  external_order_id text not null,
  customer_key text,                         -- hashed customer identifier
  total_usd numeric not null,
  occurred_at timestamptz not null,
  landing_site text,
  utm_source text, utm_medium text, utm_campaign text,
  gclid text, fbclid text, ttclid text,
  unique (merchant_id, external_order_id)
);
create index on orders (merchant_id, occurred_at);

create table touchpoints (
  id bigserial primary key,
  merchant_id uuid not null references merchants(id) on delete cascade,
  customer_key text not null,
  channel_key text not null,
  occurred_at timestamptz not null,
  source text not null,                      -- utm_reconstruction | pixel | platform_click_export
  meta jsonb
);
create index on touchpoints (merchant_id, customer_key, occurred_at);

-- Materialized journeys: ordered channel paths ending in CONVERSION or NULL.
create table journeys (
  id bigserial primary key,
  merchant_id uuid not null references merchants(id) on delete cascade,
  customer_key text not null,
  path text[] not null,                      -- e.g. {tiktok, email, google_ads}
  converted boolean not null,
  revenue_usd numeric not null default 0,
  window_days int not null default 30,
  computed_at timestamptz not null default now()
);
create index on journeys (merchant_id, computed_at);

create table spend_daily (
  id bigserial primary key,
  merchant_id uuid not null references merchants(id) on delete cascade,
  channel_key text not null,
  day date not null,
  spend_usd numeric not null,
  platform_reported_conversions numeric,     -- what the platform claims — kept to show over/under-credit
  platform_reported_revenue_usd numeric,
  unique (merchant_id, channel_key, day)
);

create table attribution_runs (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references merchants(id) on delete cascade,
  run_at timestamptz not null default now(),
  window_days int not null,
  method text not null,                      -- markov | mmm
  results jsonb not null,                    -- {channel_key: {removal_effect, credited_revenue, ...}}
  engine_version text not null
);

create table recommendations (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references merchants(id) on delete cascade,
  created_at timestamptz not null default now(),
  report_week date not null,
  action text not null,                      -- human sentence: "Shift $500/wk from Meta prospecting to TikTok"
  from_channel text, to_channel text,
  amount_weekly_usd numeric,
  predicted_metric text not null,            -- blended_roas | revenue
  predicted_delta_pct numeric not null,      -- e.g. +9.0
  prediction_interval jsonb,                 -- {low, high}
  merchant_action text not null default 'pending', -- pending | acted | ignored | partial
  merchant_action_at timestamptz
);

-- THE MOAT TABLE. Public accuracy dashboard reads from here. v1, day one.
create table prediction_outcomes (
  id uuid primary key default gen_random_uuid(),
  recommendation_id uuid not null references recommendations(id) on delete cascade,
  merchant_id uuid not null references merchants(id) on delete cascade,
  evaluated_at timestamptz not null default now(),
  observed_delta_pct numeric,
  hit boolean,                               -- observed within prediction interval
  publishable boolean not null default true, -- merchant can opt out; aggregate stays
  notes text
);
