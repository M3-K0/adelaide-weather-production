-- Forecast Versioning Schema for Adelaide Weather Forecasting System
-- Version 1.0.0
-- Created for T-013: Versioned Storage with UI Access
-- Extends the existing TimescaleDB schema with forecast versioning capabilities

-- ============================================================
-- Forecast Versions Table
-- Stores complete forecast snapshots with metadata
-- ============================================================

CREATE TABLE IF NOT EXISTS forecast_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    forecast_time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    horizon TEXT NOT NULL,
    location_lat FLOAT DEFAULT -34.9285, -- Adelaide coordinates
    location_lon FLOAT DEFAULT 138.6007,
    
    -- Forecast data (JSON for flexibility)
    variables JSONB NOT NULL,
    wind_data JSONB,
    
    -- Metadata
    model_version TEXT NOT NULL,
    index_version TEXT NOT NULL,
    dataset_hash TEXT NOT NULL,
    api_version TEXT NOT NULL DEFAULT 'v1.1.0',
    
    -- Performance metrics
    latency_ms INT,
    analog_count INT,
    total_analogs_used INT,
    
    -- Quality indicators
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    risk_level TEXT CHECK (risk_level IN ('minimal', 'low', 'moderate', 'high', 'extreme')),
    
    -- Narrative and context
    narrative TEXT,
    confidence_explanation TEXT,
    
    -- User/system context
    user_id TEXT,
    correlation_id TEXT,
    request_params JSONB, -- Original request parameters
    
    -- Constraints
    CONSTRAINT valid_horizon_version CHECK (horizon IN ('6h', '12h', '24h', '48h')),
    CONSTRAINT positive_latency CHECK (latency_ms > 0),
    CONSTRAINT valid_analog_count CHECK (analog_count >= 0)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('forecast_versions', 'forecast_time',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- Create indexes for version queries
CREATE INDEX idx_forecast_versions_time ON forecast_versions (forecast_time DESC);
CREATE INDEX idx_forecast_versions_horizon_time ON forecast_versions (horizon, forecast_time DESC);
CREATE INDEX idx_forecast_versions_created ON forecast_versions (created_at DESC);
CREATE INDEX idx_forecast_versions_user ON forecast_versions (user_id, forecast_time DESC);
CREATE INDEX idx_forecast_versions_correlation ON forecast_versions (correlation_id);
CREATE INDEX idx_forecast_versions_model ON forecast_versions (model_version, forecast_time DESC);

-- GIN index for fast JSON queries
CREATE INDEX idx_forecast_versions_variables ON forecast_versions USING GIN (variables);
CREATE INDEX idx_forecast_versions_params ON forecast_versions USING GIN (request_params);

-- ============================================================
-- Forecast Comparisons Table
-- Tracks user-generated forecast comparisons
-- ============================================================

CREATE TABLE IF NOT EXISTS forecast_comparisons (
    comparison_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT,
    
    -- Comparison details
    version_a UUID NOT NULL REFERENCES forecast_versions(version_id),
    version_b UUID NOT NULL REFERENCES forecast_versions(version_id),
    
    -- Comparison metadata
    comparison_type TEXT DEFAULT 'manual' CHECK (comparison_type IN ('manual', 'auto', 'scheduled')),
    variables_compared TEXT[] NOT NULL,
    
    -- Analysis results (pre-computed for performance)
    differences JSONB, -- Detailed diff data
    similarity_score FLOAT CHECK (similarity_score >= 0 AND similarity_score <= 1),
    significant_changes TEXT[], -- Array of change descriptions
    
    -- User annotations
    notes TEXT,
    tags TEXT[],
    
    -- Sharing and access
    is_public BOOLEAN DEFAULT FALSE,
    shared_with TEXT[], -- User IDs with access
    
    CONSTRAINT different_versions CHECK (version_a != version_b)
);

-- Create indexes for comparison queries
CREATE INDEX idx_comparisons_created ON forecast_comparisons (created_at DESC);
CREATE INDEX idx_comparisons_user ON forecast_comparisons (created_by, created_at DESC);
CREATE INDEX idx_comparisons_version_a ON forecast_comparisons (version_a);
CREATE INDEX idx_comparisons_version_b ON forecast_comparisons (version_b);
CREATE INDEX idx_comparisons_public ON forecast_comparisons (is_public, created_at DESC) WHERE is_public = TRUE;
CREATE INDEX idx_comparisons_tags ON forecast_comparisons USING GIN (tags);

-- ============================================================
-- Forecast Exports Table
-- Tracks export operations and provides download links
-- ============================================================

CREATE TABLE IF NOT EXISTS forecast_exports (
    export_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL,
    
    -- Export parameters
    export_type TEXT NOT NULL CHECK (export_type IN ('json', 'csv', 'archive')),
    date_range TSTZRANGE NOT NULL,
    horizons_included TEXT[] NOT NULL,
    variables_included TEXT[] NOT NULL,
    
    -- Filter criteria
    filters JSONB, -- Additional filters applied
    include_metadata BOOLEAN DEFAULT TRUE,
    include_comparisons BOOLEAN DEFAULT FALSE,
    
    -- Export status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'expired')),
    progress_percent INT DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    
    -- Results
    file_path TEXT, -- Server-side file path
    download_url TEXT, -- Temporary download URL
    file_size_bytes BIGINT,
    record_count INT,
    
    -- Lifecycle
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
    downloaded_at TIMESTAMPTZ,
    download_count INT DEFAULT 0,
    
    -- Error handling
    error_message TEXT,
    retry_count INT DEFAULT 0
);

-- Create indexes for export management
CREATE INDEX idx_exports_created ON forecast_exports (created_at DESC);
CREATE INDEX idx_exports_user ON forecast_exports (created_by, created_at DESC);
CREATE INDEX idx_exports_status ON forecast_exports (status, created_at DESC);
CREATE INDEX idx_exports_expires ON forecast_exports (expires_at) WHERE status = 'completed';

-- ============================================================
-- Forecast Accuracy Tracking (Enhanced)
-- Extends forecast_quality with version tracking
-- ============================================================

CREATE TABLE IF NOT EXISTS forecast_accuracy_versions (
    accuracy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID NOT NULL REFERENCES forecast_versions(version_id),
    
    -- Timing
    forecast_time TIMESTAMPTZ NOT NULL,
    valid_time TIMESTAMPTZ NOT NULL,
    verification_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Variable details
    variable TEXT NOT NULL,
    predicted_value FLOAT,
    observed_value FLOAT,
    
    -- Uncertainty bounds
    predicted_p05 FLOAT,
    predicted_p95 FLOAT,
    within_bounds BOOLEAN GENERATED ALWAYS AS (
        observed_value >= predicted_p05 AND observed_value <= predicted_p95
    ) STORED,
    
    -- Error calculations
    absolute_error FLOAT GENERATED ALWAYS AS (ABS(predicted_value - observed_value)) STORED,
    relative_error_percent FLOAT GENERATED ALWAYS AS (
        CASE 
            WHEN observed_value != 0 THEN ABS((predicted_value - observed_value) / observed_value * 100)
            ELSE NULL
        END
    ) STORED,
    
    -- Forecast context
    confidence FLOAT,
    analog_count INT,
    horizon TEXT,
    
    -- Quality scoring
    skill_score FLOAT, -- Calculated against climatology or persistence
    bias FLOAT GENERATED ALWAYS AS (predicted_value - observed_value) STORED,
    
    -- Verification source
    observation_source TEXT DEFAULT 'bom', -- Bureau of Meteorology
    observation_station TEXT,
    observation_quality TEXT DEFAULT 'good' CHECK (observation_quality IN ('excellent', 'good', 'fair', 'poor')),
    
    CONSTRAINT valid_variable_accuracy CHECK (variable IN (
        't2m', 'u10', 'v10', 'msl', 'cape', 'sp', 'z500', 
        'q850', 'tcwv', 'tp6h', 'r850', 't850'
    )),
    CONSTRAINT forecast_before_valid_accuracy CHECK (forecast_time < valid_time),
    CONSTRAINT valid_before_verification CHECK (valid_time <= verification_time),
    CONSTRAINT valid_confidence_accuracy CHECK (confidence >= 0 AND confidence <= 1)
);

-- Convert to hypertable
SELECT create_hypertable('forecast_accuracy_versions', 'forecast_time',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- Create indexes for accuracy analysis
CREATE INDEX idx_accuracy_versions_variable_time ON forecast_accuracy_versions (variable, forecast_time DESC);
CREATE INDEX idx_accuracy_versions_version ON forecast_accuracy_versions (version_id);
CREATE INDEX idx_accuracy_versions_horizon ON forecast_accuracy_versions (horizon, forecast_time DESC);
CREATE INDEX idx_accuracy_versions_skill ON forecast_accuracy_versions (skill_score DESC);

-- ============================================================
-- Continuous Aggregates for Version Analysis
-- ============================================================

-- Daily version statistics
CREATE MATERIALIZED VIEW daily_version_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', forecast_time) AS day,
    horizon,
    COUNT(*) as version_count,
    COUNT(DISTINCT model_version) as model_versions_used,
    AVG(latency_ms) as avg_latency_ms,
    AVG(confidence_score) as avg_confidence,
    AVG(analog_count) as avg_analog_count,
    MODE() WITHIN GROUP (ORDER BY risk_level) as most_common_risk_level,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) as median_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms
FROM forecast_versions
GROUP BY day, horizon
WITH NO DATA;

-- Weekly accuracy trends by version
CREATE MATERIALIZED VIEW weekly_accuracy_trends
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 week', forecast_time) AS week,
    variable,
    horizon,
    COUNT(*) as verification_count,
    AVG(absolute_error) as avg_absolute_error,
    AVG(relative_error_percent) as avg_relative_error_percent,
    AVG(skill_score) as avg_skill_score,
    AVG(CASE WHEN within_bounds THEN 1.0 ELSE 0.0 END) as within_bounds_rate,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY absolute_error) as median_absolute_error,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY absolute_error) as p95_absolute_error
FROM forecast_accuracy_versions
GROUP BY week, variable, horizon
WITH NO DATA;

-- ============================================================
-- Retention Policies for Version Data
-- ============================================================

-- Keep forecast versions for 1 year (configurable based on storage)
SELECT add_retention_policy('forecast_versions',
    INTERVAL '365 days',
    if_not_exists => TRUE
);

-- Keep comparisons for 6 months
SELECT add_retention_policy('forecast_comparisons',
    INTERVAL '180 days',
    if_not_exists => TRUE
);

-- Clean up expired exports
SELECT add_retention_policy('forecast_exports',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- Keep accuracy data for 2 years
SELECT add_retention_policy('forecast_accuracy_versions',
    INTERVAL '730 days',
    if_not_exists => TRUE
);

-- Keep daily stats for 2 years
SELECT add_retention_policy('daily_version_stats',
    INTERVAL '730 days',
    if_not_exists => TRUE
);

-- Keep weekly trends for 3 years
SELECT add_retention_policy('weekly_accuracy_trends',
    INTERVAL '1095 days',
    if_not_exists => TRUE
);

-- ============================================================
-- Refresh Policies for Continuous Aggregates
-- ============================================================

SELECT add_continuous_aggregate_policy('daily_version_stats',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy('weekly_accuracy_trends',
    start_offset => INTERVAL '2 weeks',
    end_offset => INTERVAL '1 week',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================================
-- Helper Functions for Version Management
-- ============================================================

-- Get forecast versions within date range
CREATE OR REPLACE FUNCTION get_forecast_versions(
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ,
    p_horizon TEXT DEFAULT NULL,
    p_limit INT DEFAULT 100
)
RETURNS TABLE (
    version_id UUID,
    forecast_time TIMESTAMPTZ,
    horizon TEXT,
    confidence_score FLOAT,
    narrative TEXT,
    model_version TEXT,
    variables JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        fv.version_id,
        fv.forecast_time,
        fv.horizon,
        fv.confidence_score,
        fv.narrative,
        fv.model_version,
        fv.variables
    FROM forecast_versions fv
    WHERE fv.forecast_time >= p_start_date
        AND fv.forecast_time <= p_end_date
        AND (p_horizon IS NULL OR fv.horizon = p_horizon)
    ORDER BY fv.forecast_time DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Compare two forecast versions
CREATE OR REPLACE FUNCTION compare_forecast_versions(
    p_version_a UUID,
    p_version_b UUID
)
RETURNS TABLE (
    variable TEXT,
    value_a FLOAT,
    value_b FLOAT,
    difference FLOAT,
    percent_change FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH version_a_data AS (
        SELECT jsonb_each_text(variables) AS var_data
        FROM forecast_versions 
        WHERE version_id = p_version_a
    ),
    version_b_data AS (
        SELECT jsonb_each_text(variables) AS var_data
        FROM forecast_versions 
        WHERE version_id = p_version_b
    )
    SELECT 
        (va.var_data).key as variable,
        ((va.var_data).value::jsonb->>'value')::FLOAT as value_a,
        ((vb.var_data).value::jsonb->>'value')::FLOAT as value_b,
        ((vb.var_data).value::jsonb->>'value')::FLOAT - ((va.var_data).value::jsonb->>'value')::FLOAT as difference,
        CASE 
            WHEN ((va.var_data).value::jsonb->>'value')::FLOAT != 0 THEN
                (((vb.var_data).value::jsonb->>'value')::FLOAT - ((va.var_data).value::jsonb->>'value')::FLOAT) / 
                ((va.var_data).value::jsonb->>'value')::FLOAT * 100
            ELSE NULL
        END as percent_change
    FROM version_a_data va
    FULL OUTER JOIN version_b_data vb ON (va.var_data).key = (vb.var_data).key
    WHERE (va.var_data).key IS NOT NULL AND (vb.var_data).key IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- Get accuracy metrics for a specific version
CREATE OR REPLACE FUNCTION get_version_accuracy(
    p_version_id UUID
)
RETURNS TABLE (
    variable TEXT,
    forecast_count INT,
    avg_absolute_error FLOAT,
    avg_relative_error FLOAT,
    within_bounds_rate FLOAT,
    avg_skill_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        av.variable,
        COUNT(*)::INT as forecast_count,
        AVG(av.absolute_error) as avg_absolute_error,
        AVG(av.relative_error_percent) as avg_relative_error,
        AVG(CASE WHEN av.within_bounds THEN 1.0 ELSE 0.0 END) as within_bounds_rate,
        AVG(av.skill_score) as avg_skill_score
    FROM forecast_accuracy_versions av
    WHERE av.version_id = p_version_id
    GROUP BY av.variable
    ORDER BY av.variable;
END;
$$ LANGUAGE plpgsql;

-- Create a forecast comparison record
CREATE OR REPLACE FUNCTION create_forecast_comparison(
    p_version_a UUID,
    p_version_b UUID,
    p_created_by TEXT,
    p_variables TEXT[],
    p_notes TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    comparison_id UUID;
    differences_data JSONB;
    similarity FLOAT;
BEGIN
    -- Generate comparison ID
    comparison_id := gen_random_uuid();
    
    -- Calculate basic differences (simplified - would be more complex in production)
    SELECT jsonb_build_object(
        'computed_at', NOW(),
        'variables_compared', p_variables,
        'summary', 'Differences calculated'
    ) INTO differences_data;
    
    -- Calculate similarity score (simplified)
    similarity := 0.85; -- Would calculate based on actual differences
    
    -- Insert comparison record
    INSERT INTO forecast_comparisons (
        comparison_id,
        created_by,
        version_a,
        version_b,
        variables_compared,
        differences,
        similarity_score,
        notes
    ) VALUES (
        comparison_id,
        p_created_by,
        p_version_a,
        p_version_b,
        p_variables,
        differences_data,
        similarity,
        p_notes
    );
    
    RETURN comparison_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Triggers for Automatic Processing
-- ============================================================

-- Trigger to automatically update comparison differences when created
CREATE OR REPLACE FUNCTION update_comparison_differences()
RETURNS TRIGGER AS $$
BEGIN
    -- This would calculate detailed differences between the two versions
    -- For now, we'll just update the timestamp
    NEW.differences := jsonb_set(
        COALESCE(NEW.differences, '{}'::jsonb),
        '{updated_at}',
        to_jsonb(NOW())
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_comparison_differences
    BEFORE INSERT OR UPDATE ON forecast_comparisons
    FOR EACH ROW
    EXECUTE FUNCTION update_comparison_differences();

-- ============================================================
-- Views for Common Queries
-- ============================================================

-- Recent forecast versions with metadata
CREATE VIEW recent_forecast_versions AS
SELECT 
    version_id,
    forecast_time,
    created_at,
    horizon,
    confidence_score,
    risk_level,
    narrative,
    model_version,
    latency_ms,
    analog_count,
    user_id,
    jsonb_array_length(jsonb_object_keys(variables)) as variable_count
FROM forecast_versions
WHERE forecast_time > NOW() - INTERVAL '30 days'
ORDER BY forecast_time DESC;

-- Forecast version performance summary
CREATE VIEW forecast_version_performance AS
SELECT 
    fv.version_id,
    fv.forecast_time,
    fv.horizon,
    fv.model_version,
    fv.confidence_score,
    COUNT(fav.accuracy_id) as verifications_available,
    AVG(fav.absolute_error) as avg_absolute_error,
    AVG(fav.skill_score) as avg_skill_score,
    AVG(CASE WHEN fav.within_bounds THEN 1.0 ELSE 0.0 END) as accuracy_rate
FROM forecast_versions fv
LEFT JOIN forecast_accuracy_versions fav ON fv.version_id = fav.version_id
GROUP BY fv.version_id, fv.forecast_time, fv.horizon, fv.model_version, fv.confidence_score;

-- ============================================================
-- Sample Data for Testing (Optional)
-- ============================================================

-- Uncomment to insert sample data for testing
/*
INSERT INTO forecast_versions (
    forecast_time,
    horizon,
    variables,
    model_version,
    index_version,
    dataset_hash,
    latency_ms,
    analog_count,
    confidence_score,
    risk_level,
    narrative,
    confidence_explanation
) VALUES (
    NOW() - INTERVAL '1 day',
    '24h',
    '{"t2m": {"value": 22.5, "p05": 20.1, "p95": 24.9, "confidence": 0.85, "available": true}}',
    'v1.0.0',
    'v1.0.0',
    'd4f8a91',
    145,
    42,
    0.85,
    'low',
    'Mild conditions expected with temperature around 22.5°C, light winds, and stable weather patterns.',
    'High confidence (85%) based on 42 strong analog matches from similar historical patterns.'
);
*/

-- ============================================================
-- Security and Grants
-- ============================================================

-- Create application role for version management
-- CREATE ROLE forecast_versioning_app;

-- Grant necessary permissions (uncomment and adjust as needed)
-- GRANT USAGE ON SCHEMA public TO forecast_versioning_app;
-- GRANT SELECT, INSERT, UPDATE ON forecast_versions TO forecast_versioning_app;
-- GRANT SELECT, INSERT, UPDATE ON forecast_comparisons TO forecast_versioning_app;
-- GRANT SELECT, INSERT, UPDATE ON forecast_exports TO forecast_versioning_app;
-- GRANT SELECT, INSERT ON forecast_accuracy_versions TO forecast_versioning_app;
-- GRANT SELECT ON daily_version_stats TO forecast_versioning_app;
-- GRANT SELECT ON weekly_accuracy_trends TO forecast_versioning_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO forecast_versioning_app;