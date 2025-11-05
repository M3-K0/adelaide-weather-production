-- TimescaleDB Schema for Adelaide Weather Forecasting System
-- Version 1.0.0
-- Created for T-002: TimescaleDB Schema Setup

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ============================================================
-- Forecast Interactions Table
-- Tracks user interactions with the forecast system
-- ============================================================

CREATE TABLE IF NOT EXISTS forecast_interactions (
    timestamp TIMESTAMPTZ NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,
    horizon TEXT,
    variables TEXT[],
    response_ms INT,
    correlation_id TEXT,
    user_agent TEXT,
    ip_address INET,
    success BOOLEAN DEFAULT true,
    error_type TEXT,
    
    -- Constraints
    CONSTRAINT valid_action CHECK (action IN (
        'forecast_request', 'variable_toggle', 'horizon_change', 
        'analog_export', 'cape_modal_open', 'status_check'
    )),
    CONSTRAINT valid_horizon CHECK (horizon IN ('6h', '12h', '24h', '48h')),
    CONSTRAINT positive_response_time CHECK (response_ms > 0)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('forecast_interactions', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indexes for common queries
CREATE INDEX idx_interactions_user_time ON forecast_interactions (user_id, timestamp DESC);
CREATE INDEX idx_interactions_action_time ON forecast_interactions (action, timestamp DESC);
CREATE INDEX idx_interactions_correlation ON forecast_interactions (correlation_id);

-- ============================================================
-- Forecast Quality Table
-- Tracks forecast accuracy and quality metrics
-- ============================================================

CREATE TABLE IF NOT EXISTS forecast_quality (
    forecast_time TIMESTAMPTZ NOT NULL,
    valid_time TIMESTAMPTZ NOT NULL,
    variable TEXT NOT NULL,
    predicted FLOAT,
    observed FLOAT,
    confidence FLOAT,
    analog_count INT,
    error_absolute FLOAT GENERATED ALWAYS AS (ABS(predicted - observed)) STORED,
    error_percent FLOAT GENERATED ALWAYS AS (
        CASE 
            WHEN observed != 0 THEN ABS((predicted - observed) / observed * 100)
            ELSE NULL
        END
    ) STORED,
    p05 FLOAT,
    p95 FLOAT,
    within_bounds BOOLEAN GENERATED ALWAYS AS (
        observed >= p05 AND observed <= p95
    ) STORED,
    
    -- Metadata
    horizon TEXT,
    model_version TEXT,
    index_version TEXT,
    dataset_hash TEXT,
    
    -- Constraints  
    CONSTRAINT valid_variable CHECK (variable IN (
        't2m', 'u10', 'v10', 'msl', 'cape', 'sp', 'z', 
        'q', 'tcwv', 'lsp', 'cp', 'ssrd', 'strd', 'skt'
    )),
    CONSTRAINT valid_horizon_quality CHECK (horizon IN ('6h', '12h', '24h', '48h')),
    CONSTRAINT valid_confidence CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT valid_analog_count CHECK (analog_count > 0),
    CONSTRAINT forecast_before_valid CHECK (forecast_time < valid_time)
);

-- Convert to hypertable
SELECT create_hypertable('forecast_quality', 'forecast_time',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- Create indexes for analysis queries
CREATE INDEX idx_quality_variable_time ON forecast_quality (variable, forecast_time DESC);
CREATE INDEX idx_quality_valid_time ON forecast_quality (valid_time DESC);
CREATE INDEX idx_quality_horizon_time ON forecast_quality (horizon, forecast_time DESC);
CREATE INDEX idx_quality_confidence ON forecast_quality (confidence);
CREATE INDEX idx_quality_error ON forecast_quality (error_absolute);

-- ============================================================
-- Continuous Aggregates for Performance
-- ============================================================

-- Hourly interaction summary
CREATE MATERIALIZED VIEW hourly_interactions
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS hour,
    action,
    COUNT(*) as count,
    AVG(response_ms) as avg_response_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_ms) as median_response_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_ms) as p95_response_ms,
    SUM(CASE WHEN success THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as success_rate
FROM forecast_interactions
GROUP BY hour, action
WITH NO DATA;

-- Daily quality metrics
CREATE MATERIALIZED VIEW daily_quality_metrics
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', forecast_time) AS day,
    variable,
    horizon,
    COUNT(*) as forecast_count,
    AVG(error_absolute) as avg_error,
    AVG(confidence) as avg_confidence,
    AVG(analog_count) as avg_analog_count,
    SUM(CASE WHEN within_bounds THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as within_bounds_rate,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY error_absolute) as median_error,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY error_absolute) as p95_error
FROM forecast_quality
GROUP BY day, variable, horizon
WITH NO DATA;

-- ============================================================
-- Retention Policies
-- ============================================================

-- Keep raw interaction data for 30 days
SELECT add_retention_policy('forecast_interactions', 
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- Keep raw quality data for 90 days  
SELECT add_retention_policy('forecast_quality',
    INTERVAL '90 days', 
    if_not_exists => TRUE
);

-- Keep hourly aggregates for 1 year
SELECT add_retention_policy('hourly_interactions',
    INTERVAL '365 days',
    if_not_exists => TRUE
);

-- Keep daily aggregates for 2 years
SELECT add_retention_policy('daily_quality_metrics',
    INTERVAL '730 days',
    if_not_exists => TRUE
);

-- ============================================================
-- Refresh Policies for Continuous Aggregates
-- ============================================================

SELECT add_continuous_aggregate_policy('hourly_interactions',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy('daily_quality_metrics',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day', 
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================================
-- Helper Functions
-- ============================================================

-- Get recent forecast performance by variable
CREATE OR REPLACE FUNCTION get_forecast_performance(
    p_variable TEXT,
    p_horizon TEXT DEFAULT NULL,
    p_days INT DEFAULT 7
)
RETURNS TABLE (
    metric TEXT,
    value FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'avg_error'::TEXT, AVG(error_absolute)::FLOAT
    FROM forecast_quality
    WHERE variable = p_variable
        AND forecast_time > NOW() - INTERVAL '1 day' * p_days
        AND (p_horizon IS NULL OR horizon = p_horizon)
    UNION ALL
    SELECT 'median_error'::TEXT, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY error_absolute)::FLOAT
    FROM forecast_quality
    WHERE variable = p_variable
        AND forecast_time > NOW() - INTERVAL '1 day' * p_days
        AND (p_horizon IS NULL OR horizon = p_horizon)
    UNION ALL
    SELECT 'within_bounds_rate'::TEXT, AVG(CASE WHEN within_bounds THEN 1.0 ELSE 0.0 END)::FLOAT
    FROM forecast_quality
    WHERE variable = p_variable
        AND forecast_time > NOW() - INTERVAL '1 day' * p_days
        AND (p_horizon IS NULL OR horizon = p_horizon)
    UNION ALL
    SELECT 'avg_confidence'::TEXT, AVG(confidence)::FLOAT
    FROM forecast_quality
    WHERE variable = p_variable
        AND forecast_time > NOW() - INTERVAL '1 day' * p_days
        AND (p_horizon IS NULL OR horizon = p_horizon);
END;
$$ LANGUAGE plpgsql;

-- Get system usage statistics
CREATE OR REPLACE FUNCTION get_usage_stats(
    p_days INT DEFAULT 7
)
RETURNS TABLE (
    total_requests BIGINT,
    unique_users BIGINT,
    avg_response_ms FLOAT,
    p95_response_ms FLOAT,
    success_rate FLOAT,
    most_used_horizon TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_requests,
        COUNT(DISTINCT user_id)::BIGINT as unique_users,
        AVG(response_ms)::FLOAT as avg_response_ms,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_ms)::FLOAT as p95_response_ms,
        AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END)::FLOAT as success_rate,
        MODE() WITHIN GROUP (ORDER BY horizon) as most_used_horizon
    FROM forecast_interactions
    WHERE timestamp > NOW() - INTERVAL '1 day' * p_days
        AND action = 'forecast_request';
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Grants (adjust based on your user setup)
-- ============================================================

-- Grant usage to application user (replace 'app_user' with actual username)
-- GRANT USAGE ON SCHEMA public TO app_user;
-- GRANT SELECT, INSERT ON forecast_interactions TO app_user;
-- GRANT SELECT, INSERT ON forecast_quality TO app_user;
-- GRANT SELECT ON hourly_interactions TO app_user;
-- GRANT SELECT ON daily_quality_metrics TO app_user;
-- GRANT EXECUTE ON FUNCTION get_forecast_performance TO app_user;
-- GRANT EXECUTE ON FUNCTION get_usage_stats TO app_user;