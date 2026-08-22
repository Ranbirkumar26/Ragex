create extension if not exists pgcrypto with schema extensions;

create table if not exists public.products (
    sku_id text primary key,
    name text not null,
    category text not null,
    floor_price_inr numeric(12, 2) not null check (floor_price_inr > 0),
    ceiling_price_inr numeric(12, 2) not null check (ceiling_price_inr > floor_price_inr),
    base_price_inr numeric(12, 2) not null check (base_price_inr > 0),
    unit_cost_inr numeric(12, 2) not null check (unit_cost_inr >= 0),
    channel text not null,
    region text not null,
    created_at timestamptz not null default now()
);

create table if not exists public.historical_pricing_events (
    event_id text primary key,
    occurred_at timestamptz not null,
    sku_id text not null references public.products (sku_id),
    channel text not null,
    region text not null,
    inventory integer not null check (inventory >= 0),
    competitor_price_inr numeric(12, 2) not null check (competitor_price_inr > 0),
    demand_index numeric(6, 4) not null check (demand_index >= 0 and demand_index <= 1),
    price_inr numeric(12, 2) not null check (price_inr > 0),
    units_sold integer not null check (units_sold >= 0),
    margin_inr numeric(12, 2) not null,
    reward_inr numeric(14, 2) not null,
    created_at timestamptz not null default now()
);

create table if not exists public.simulator_decisions (
    decision_id text primary key,
    occurred_at timestamptz not null,
    sku_id text not null references public.products (sku_id),
    guardrail_status text not null check (guardrail_status in ('pass', 'review', 'block')),
    envelope_json jsonb not null,
    created_at timestamptz not null default now()
);

create table if not exists public.guardrail_flags (
    flag_id uuid primary key default gen_random_uuid(),
    decision_id text not null references public.simulator_decisions (decision_id) on delete cascade,
    code text not null,
    severity text not null check (severity in ('low', 'medium', 'high', 'critical')),
    message text not null,
    metric text not null,
    observed_value numeric(18, 4) not null,
    threshold_value numeric(18, 4) not null,
    policy_ref text not null,
    created_at timestamptz not null default now()
);

create table if not exists public.policy_documents (
    doc_id text primary key,
    title text not null,
    body text not null,
    created_at timestamptz not null default now()
);

create index if not exists historical_pricing_events_sku_time_idx
    on public.historical_pricing_events (sku_id, occurred_at);

create index if not exists simulator_decisions_time_idx
    on public.simulator_decisions (occurred_at desc);

create index if not exists simulator_decisions_guardrail_status_idx
    on public.simulator_decisions (guardrail_status);

create index if not exists guardrail_flags_decision_id_idx
    on public.guardrail_flags (decision_id);

alter table public.products enable row level security;
alter table public.historical_pricing_events enable row level security;
alter table public.simulator_decisions enable row level security;
alter table public.guardrail_flags enable row level security;
alter table public.policy_documents enable row level security;

revoke all on table public.products from anon, authenticated;
revoke all on table public.historical_pricing_events from anon, authenticated;
revoke all on table public.simulator_decisions from anon, authenticated;
revoke all on table public.guardrail_flags from anon, authenticated;
revoke all on table public.policy_documents from anon, authenticated;

grant select, insert, update, delete on table public.products to service_role;
grant select, insert, update, delete on table public.historical_pricing_events to service_role;
grant select, insert, update, delete on table public.simulator_decisions to service_role;
grant select, insert, update, delete on table public.guardrail_flags to service_role;
grant select, insert, update, delete on table public.policy_documents to service_role;
