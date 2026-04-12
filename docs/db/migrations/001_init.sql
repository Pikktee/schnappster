-- Schnappster MVP schema bootstrap for PostgreSQL (Supabase)

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id UUID PRIMARY KEY,
    display_name TEXT NOT NULL DEFAULT '',
    display_name_user_set BOOLEAN NOT NULL DEFAULT FALSE,
    telegram_chat_id TEXT NULL,
    notify_telegram BOOLEAN NOT NULL DEFAULT FALSE,
    notify_min_score INTEGER NOT NULL DEFAULT 8,
    deletion_pending BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS ad_searches (
    id BIGSERIAL PRIMARY KEY,
    owner_id UUID NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    prompt_addition TEXT NULL,
    min_price DOUBLE PRECISION NULL,
    max_price DOUBLE PRECISION NULL,
    blacklist_keywords TEXT NULL,
    is_exclude_images BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    scrape_interval_minutes INTEGER NOT NULL DEFAULT 30,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_scraped_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS ads (
    id BIGSERIAL PRIMARY KEY,
    owner_id UUID NOT NULL,
    adsearch_id BIGINT NULL REFERENCES ad_searches(id) ON DELETE CASCADE,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NULL,
    price DOUBLE PRECISION NULL,
    postal_code TEXT NULL,
    city TEXT NULL,
    url TEXT NOT NULL,
    image_urls TEXT NULL,
    condition TEXT NULL,
    shipping_cost TEXT NULL,
    seller_name TEXT NULL,
    seller_url TEXT NULL,
    seller_rating INTEGER NULL,
    seller_is_friendly BOOLEAN NOT NULL DEFAULT FALSE,
    seller_is_reliable BOOLEAN NOT NULL DEFAULT FALSE,
    seller_type TEXT NULL,
    seller_active_since TEXT NULL,
    bargain_score DOUBLE PRECISION NULL,
    ai_summary TEXT NULL,
    ai_reasoning TEXT NULL,
    is_analyzed BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id BIGSERIAL PRIMARY KEY,
    adsearch_id BIGINT NULL REFERENCES ad_searches(id) ON DELETE SET NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ NULL,
    ads_found INTEGER NOT NULL DEFAULT 0,
    ads_filtered INTEGER NOT NULL DEFAULT 0,
    ads_new INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS error_logs (
    id BIGSERIAL PRIMARY KEY,
    adsearch_id BIGINT NULL REFERENCES ad_searches(id) ON DELETE SET NULL,
    error_type TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_analysis_logs (
    id BIGSERIAL PRIMARY KEY,
    ad_id BIGINT NULL REFERENCES ads(id) ON DELETE SET NULL,
    adsearch_id BIGINT NULL REFERENCES ad_searches(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    prompt_text TEXT NOT NULL DEFAULT '',
    ad_title TEXT NOT NULL DEFAULT '',
    score DOUBLE PRECISION NOT NULL,
    ai_summary TEXT NULL,
    ai_reasoning TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_ad_searches_owner_id ON ad_searches(owner_id);
CREATE INDEX IF NOT EXISTS idx_ads_owner_id ON ads(owner_id);
CREATE INDEX IF NOT EXISTS idx_ads_adsearch_id ON ads(adsearch_id);
