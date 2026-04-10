-- Enable Row Level Security and owner/admin policies.

ALTER TABLE ad_searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE ads ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ad_searches_owner_policy ON ad_searches;
CREATE POLICY ad_searches_owner_policy ON ad_searches
    FOR ALL
    USING (owner_id = (current_setting('request.jwt.claims', true)::json ->> 'sub')::uuid)
    WITH CHECK (owner_id = (current_setting('request.jwt.claims', true)::json ->> 'sub')::uuid);

DROP POLICY IF EXISTS ads_owner_policy ON ads;
CREATE POLICY ads_owner_policy ON ads
    FOR ALL
    USING (owner_id = (current_setting('request.jwt.claims', true)::json ->> 'sub')::uuid)
    WITH CHECK (owner_id = (current_setting('request.jwt.claims', true)::json ->> 'sub')::uuid);

DROP POLICY IF EXISTS user_settings_owner_policy ON user_settings;
CREATE POLICY user_settings_owner_policy ON user_settings
    FOR ALL
    USING (user_id = (current_setting('request.jwt.claims', true)::json ->> 'sub')::uuid)
    WITH CHECK (user_id = (current_setting('request.jwt.claims', true)::json ->> 'sub')::uuid);

DROP POLICY IF EXISTS app_settings_admin_policy ON app_settings;
CREATE POLICY app_settings_admin_policy ON app_settings
    FOR ALL
    USING ((current_setting('request.jwt.claims', true)::json -> 'app_metadata' ->> 'role') = 'admin')
    WITH CHECK ((current_setting('request.jwt.claims', true)::json -> 'app_metadata' ->> 'role') = 'admin');
