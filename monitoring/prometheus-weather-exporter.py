#!/usr/bin/env python3
"""
Prometheus Weather Exporter for Grafana Weather Forecast Panel
Exports weather observations, forecasts, and analog pattern metrics
"""

import time
import json
import logging
import asyncio
import sqlite3
import psycopg2
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from prometheus_client import start_http_server, Gauge, Histogram, Counter, Info

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
weather_observation = Gauge(
    'weather_observation',
    'Current weather observations',
    ['location', 'variable', 'station_id']
)

weather_forecast = Gauge(
    'weather_forecast', 
    'Weather forecast values',
    ['location', 'variable', 'horizon', 'model']
)

analog_similarity_score = Gauge(
    'analog_similarity_score',
    'Analog pattern similarity scores',
    ['location', 'horizon', 'pattern_id']
)

ensemble_spread_current = Gauge(
    'ensemble_spread_current',
    'Current ensemble spread for uncertainty quantification',
    ['location', 'variable', 'horizon']
)

forecast_accuracy_score = Gauge(
    'forecast_accuracy_score',
    'Forecast accuracy scores from verification',
    ['location', 'horizon', 'variable']
)

cape_distribution_values = Histogram(
    'cape_distribution_values',
    'CAPE value distribution by forecast horizon',
    ['location', 'horizon'],
    buckets=[0, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, float('inf')]
)

# Processing metrics
analog_processing_requests_total = Counter(
    'analog_processing_requests_total',
    'Total analog processing requests'
)

analog_processing_errors_total = Counter(
    'analog_processing_errors_total', 
    'Total analog processing errors',
    ['error_type']
)

timescaledb_query_duration_seconds = Histogram(
    'timescaledb_query_duration_seconds',
    'TimescaleDB query duration'
)

prometheus_query_duration_seconds = Histogram(
    'prometheus_query_duration_seconds',
    'Prometheus query duration for metrics'
)

# Panel usage metrics
weather_panel_animation_starts_total = Counter(
    'weather_panel_animation_starts_total',
    'Total animation starts in weather panel'
)

weather_panel_horizon_changes_total = Counter(
    'weather_panel_horizon_changes_total',
    'Total horizon changes in weather panel',
    ['from_horizon', 'to_horizon']
)

weather_panel_variable_toggles_total = Counter(
    'weather_panel_variable_toggles_total',
    'Total variable toggles in weather panel',
    ['variable', 'action']
)

@dataclass
class WeatherObservation:
    timestamp: datetime
    location: str
    variable: str
    value: float
    quality: float
    station_id: str

@dataclass 
class WeatherForecast:
    timestamp: datetime
    valid_time: datetime
    location: str
    variable: str
    value: float
    horizon_hours: int
    model: str
    ensemble_member: Optional[int] = None

@dataclass
class AnalogPattern:
    pattern_id: str
    location: str
    horizon_hours: int
    similarity_score: float
    reference_date: datetime
    confidence: float

class WeatherExporter:
    """Main weather data exporter for Prometheus metrics"""
    
    def __init__(self, config_path: str = "weather_exporter_config.json"):
        self.config = self._load_config(config_path)
        self.timescaledb_conn = None
        self.prometheus_conn = None
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """Default configuration"""
        return {
            "location": "adelaide",
            "stations": ["adelaide_airport", "adelaide_kent_town"],
            "variables": ["temperature", "pressure", "cape", "wind_speed", "humidity"],
            "horizons": [6, 12, 24, 48],
            "models": ["gfs", "ecmwf", "analog_ensemble"],
            "timescaledb": {
                "host": "localhost",
                "port": 5432,
                "database": "weather_data",
                "user": "weather_user",
                "password": "weather_pass"
            },
            "update_interval": 60,
            "analog_processing": {
                "max_patterns": 10,
                "similarity_threshold": 0.5,
                "temporal_window_hours": 168
            }
        }
    
    async def initialize_connections(self):
        """Initialize database connections"""
        try:
            # TimescaleDB connection
            self.timescaledb_conn = psycopg2.connect(
                host=self.config["timescaledb"]["host"],
                port=self.config["timescaledb"]["port"],
                database=self.config["timescaledb"]["database"],
                user=self.config["timescaledb"]["user"],
                password=self.config["timescaledb"]["password"]
            )
            logger.info("Connected to TimescaleDB")
            
        except Exception as e:
            logger.error(f"Failed to connect to TimescaleDB: {e}")
            # Fall back to mock data for development
            logger.warning("Using mock data mode")
    
    async def export_weather_observations(self):
        """Export current weather observations"""
        try:
            if self.timescaledb_conn:
                observations = await self._fetch_observations_from_db()
            else:
                observations = self._generate_mock_observations()
            
            for obs in observations:
                weather_observation.labels(
                    location=obs.location,
                    variable=obs.variable,
                    station_id=obs.station_id
                ).set(obs.value)
                
            logger.info(f"Exported {len(observations)} observations")
            
        except Exception as e:
            logger.error(f"Error exporting observations: {e}")
    
    async def export_weather_forecasts(self):
        """Export weather forecasts for all horizons"""
        try:
            if self.timescaledb_conn:
                forecasts = await self._fetch_forecasts_from_db()
            else:
                forecasts = self._generate_mock_forecasts()
            
            for forecast in forecasts:
                weather_forecast.labels(
                    location=forecast.location,
                    variable=forecast.variable,
                    horizon=f"{forecast.horizon_hours}h",
                    model=forecast.model
                ).set(forecast.value)
                
                # Update CAPE distribution
                if forecast.variable == "cape":
                    cape_distribution_values.labels(
                        location=forecast.location,
                        horizon=f"{forecast.horizon_hours}h"
                    ).observe(forecast.value)
            
            logger.info(f"Exported {len(forecasts)} forecasts")
            
        except Exception as e:
            logger.error(f"Error exporting forecasts: {e}")
    
    async def export_analog_patterns(self):
        """Export analog pattern similarity scores"""
        try:
            analog_processing_requests_total.inc()
            
            if self.timescaledb_conn:
                patterns = await self._fetch_analog_patterns_from_db()
            else:
                patterns = self._generate_mock_analog_patterns()
            
            for pattern in patterns:
                analog_similarity_score.labels(
                    location=pattern.location,
                    horizon=f"{pattern.horizon_hours}h",
                    pattern_id=pattern.pattern_id
                ).set(pattern.similarity_score)
            
            logger.info(f"Exported {len(patterns)} analog patterns")
            
        except Exception as e:
            logger.error(f"Error exporting analog patterns: {e}")
            analog_processing_errors_total.labels(error_type="export_error").inc()
    
    async def export_uncertainty_metrics(self):
        """Export ensemble spread and uncertainty metrics"""
        try:
            for location in [self.config["location"]]:
                for variable in self.config["variables"]:
                    for horizon in self.config["horizons"]:
                        # Calculate ensemble spread
                        if self.timescaledb_conn:
                            spread = await self._calculate_ensemble_spread(location, variable, horizon)
                        else:
                            spread = np.random.uniform(0.1, 0.5)  # Mock data
                        
                        ensemble_spread_current.labels(
                            location=location,
                            variable=variable,
                            horizon=f"{horizon}h"
                        ).set(spread)
            
            logger.info("Exported uncertainty metrics")
            
        except Exception as e:
            logger.error(f"Error exporting uncertainty metrics: {e}")
    
    async def export_forecast_verification(self):
        """Export forecast accuracy and verification metrics"""
        try:
            for location in [self.config["location"]]:
                for variable in self.config["variables"]:
                    for horizon in self.config["horizons"]:
                        if self.timescaledb_conn:
                            accuracy = await self._calculate_forecast_accuracy(location, variable, horizon)
                        else:
                            # Mock accuracy that decreases with horizon
                            base_accuracy = 0.9
                            decay = 0.02 * horizon
                            accuracy = max(0.5, base_accuracy - decay + np.random.uniform(-0.1, 0.1))
                        
                        forecast_accuracy_score.labels(
                            location=location,
                            horizon=f"{horizon}h",
                            variable=variable
                        ).set(accuracy)
            
            logger.info("Exported forecast verification metrics")
            
        except Exception as e:
            logger.error(f"Error exporting verification metrics: {e}")
    
    def _generate_mock_observations(self) -> List[WeatherObservation]:
        """Generate mock observation data for development"""
        observations = []
        now = datetime.now()
        
        for station in self.config["stations"]:
            for variable in self.config["variables"]:
                # Generate realistic values based on variable type
                if variable == "temperature":
                    value = 15 + 10 * np.sin(now.hour * np.pi / 12) + np.random.normal(0, 2)
                elif variable == "pressure":
                    value = 1013 + np.random.normal(0, 5)
                elif variable == "cape":
                    value = max(0, 800 + np.random.normal(0, 500))
                elif variable == "wind_speed":
                    value = max(0, 10 + np.random.normal(0, 5))
                elif variable == "humidity":
                    value = np.clip(60 + np.random.normal(0, 15), 0, 100)
                else:
                    value = np.random.uniform(0, 100)
                
                observations.append(WeatherObservation(
                    timestamp=now,
                    location=self.config["location"],
                    variable=variable,
                    value=value,
                    quality=np.random.uniform(0.8, 1.0),
                    station_id=station
                ))
        
        return observations
    
    def _generate_mock_forecasts(self) -> List[WeatherForecast]:
        """Generate mock forecast data for development"""
        forecasts = []
        now = datetime.now()
        
        for horizon in self.config["horizons"]:
            valid_time = now + timedelta(hours=horizon)
            
            for model in self.config["models"]:
                for variable in self.config["variables"]:
                    # Generate values with increasing uncertainty over time
                    uncertainty_factor = 1 + (horizon / 24) * 0.3
                    
                    if variable == "temperature":
                        base_value = 15 + 10 * np.sin(valid_time.hour * np.pi / 12)
                        value = base_value + np.random.normal(0, 2 * uncertainty_factor)
                    elif variable == "pressure":
                        value = 1013 + np.random.normal(0, 5 * uncertainty_factor)
                    elif variable == "cape":
                        value = max(0, 800 + np.random.normal(0, 500 * uncertainty_factor))
                    elif variable == "wind_speed":
                        value = max(0, 10 + np.random.normal(0, 5 * uncertainty_factor))
                    elif variable == "humidity":
                        value = np.clip(60 + np.random.normal(0, 15 * uncertainty_factor), 0, 100)
                    else:
                        value = np.random.uniform(0, 100)
                    
                    forecasts.append(WeatherForecast(
                        timestamp=now,
                        valid_time=valid_time,
                        location=self.config["location"],
                        variable=variable,
                        value=value,
                        horizon_hours=horizon,
                        model=model
                    ))
        
        return forecasts
    
    def _generate_mock_analog_patterns(self) -> List[AnalogPattern]:
        """Generate mock analog pattern data"""
        patterns = []
        max_patterns = self.config["analog_processing"]["max_patterns"]
        
        for horizon in self.config["horizons"]:
            for i in range(max_patterns):
                similarity = np.random.beta(8, 2)  # Skewed towards higher similarity
                
                if similarity >= self.config["analog_processing"]["similarity_threshold"]:
                    patterns.append(AnalogPattern(
                        pattern_id=f"pattern_{horizon}h_{i:03d}",
                        location=self.config["location"],
                        horizon_hours=horizon,
                        similarity_score=similarity,
                        reference_date=datetime.now() - timedelta(
                            days=np.random.randint(1, 365)
                        ),
                        confidence=np.random.uniform(0.6, 0.95)
                    ))
        
        return sorted(patterns, key=lambda p: p.similarity_score, reverse=True)
    
    async def _fetch_observations_from_db(self) -> List[WeatherObservation]:
        """Fetch observations from TimescaleDB"""
        with timescaledb_query_duration_seconds.time():
            cursor = self.timescaledb_conn.cursor()
            
            query = """
                SELECT time, location, variable, value, quality, station_id
                FROM weather_observations 
                WHERE time >= NOW() - INTERVAL '1 hour'
                ORDER BY time DESC
                LIMIT 1000
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            observations = []
            for row in rows:
                observations.append(WeatherObservation(
                    timestamp=row[0],
                    location=row[1],
                    variable=row[2],
                    value=float(row[3]),
                    quality=float(row[4]),
                    station_id=row[5]
                ))
            
            return observations
    
    async def _fetch_forecasts_from_db(self) -> List[WeatherForecast]:
        """Fetch forecasts from TimescaleDB"""
        with timescaledb_query_duration_seconds.time():
            cursor = self.timescaledb_conn.cursor()
            
            query = """
                SELECT forecast_time, valid_time, location, variable, 
                       value, horizon_hours, model
                FROM weather_forecasts 
                WHERE forecast_time >= NOW() - INTERVAL '6 hours'
                AND valid_time >= NOW()
                ORDER BY forecast_time DESC
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            forecasts = []
            for row in rows:
                forecasts.append(WeatherForecast(
                    timestamp=row[0],
                    valid_time=row[1],
                    location=row[2],
                    variable=row[3],
                    value=float(row[4]),
                    horizon_hours=int(row[5]),
                    model=row[6]
                ))
            
            return forecasts
    
    async def _fetch_analog_patterns_from_db(self) -> List[AnalogPattern]:
        """Fetch analog patterns from TimescaleDB"""
        with timescaledb_query_duration_seconds.time():
            cursor = self.timescaledb_conn.cursor()
            
            query = """
                SELECT pattern_id, location, horizon_hours, similarity_score,
                       reference_date, confidence
                FROM analog_patterns 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                AND similarity_score >= %s
                ORDER BY similarity_score DESC
                LIMIT %s
            """
            
            cursor.execute(query, (
                self.config["analog_processing"]["similarity_threshold"],
                self.config["analog_processing"]["max_patterns"]
            ))
            rows = cursor.fetchall()
            
            patterns = []
            for row in rows:
                patterns.append(AnalogPattern(
                    pattern_id=row[0],
                    location=row[1], 
                    horizon_hours=int(row[2]),
                    similarity_score=float(row[3]),
                    reference_date=row[4],
                    confidence=float(row[5])
                ))
            
            return patterns
    
    async def _calculate_ensemble_spread(self, location: str, variable: str, horizon: int) -> float:
        """Calculate ensemble spread for uncertainty quantification"""
        cursor = self.timescaledb_conn.cursor()
        
        query = """
            SELECT STDDEV(value) as spread
            FROM weather_forecasts 
            WHERE location = %s AND variable = %s 
            AND horizon_hours = %s
            AND forecast_time >= NOW() - INTERVAL '1 hour'
        """
        
        cursor.execute(query, (location, variable, horizon))
        result = cursor.fetchone()
        
        return float(result[0]) if result and result[0] else 0.0
    
    async def _calculate_forecast_accuracy(self, location: str, variable: str, horizon: int) -> float:
        """Calculate forecast accuracy from verification data"""
        cursor = self.timescaledb_conn.cursor()
        
        query = """
            SELECT AVG(1.0 - ABS(forecast_value - observed_value) / 
                       NULLIF(observed_value, 0)) as accuracy
            FROM forecast_verification 
            WHERE location = %s AND variable = %s 
            AND horizon_hours = %s
            AND forecast_time >= NOW() - INTERVAL '24 hours'
        """
        
        cursor.execute(query, (location, variable, horizon))
        result = cursor.fetchone()
        
        return max(0.0, min(1.0, float(result[0]))) if result and result[0] else 0.5
    
    async def run_export_cycle(self):
        """Run one complete export cycle"""
        logger.info("Starting export cycle")
        
        try:
            await self.export_weather_observations()
            await self.export_weather_forecasts() 
            await self.export_analog_patterns()
            await self.export_uncertainty_metrics()
            await self.export_forecast_verification()
            
            logger.info("Export cycle completed successfully")
            
        except Exception as e:
            logger.error(f"Error in export cycle: {e}")
    
    async def run(self):
        """Main export loop"""
        await self.initialize_connections()
        
        logger.info(f"Starting weather exporter, update interval: {self.config['update_interval']}s")
        
        while True:
            try:
                await self.run_export_cycle()
                await asyncio.sleep(self.config["update_interval"])
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                await asyncio.sleep(self.config["update_interval"])
        
        # Cleanup
        if self.timescaledb_conn:
            self.timescaledb_conn.close()
            logger.info("Closed database connections")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Weather Prometheus Exporter')
    parser.add_argument('--config', default='weather_exporter_config.json',
                       help='Configuration file path')
    parser.add_argument('--port', type=int, default=8000,
                       help='Prometheus metrics port')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Log level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Start Prometheus metrics server
    start_http_server(args.port)
    logger.info(f"Started Prometheus metrics server on port {args.port}")
    
    # Create and run exporter
    exporter = WeatherExporter(args.config)
    
    try:
        asyncio.run(exporter.run())
    except KeyboardInterrupt:
        logger.info("Exporter stopped by user")
    except Exception as e:
        logger.error(f"Exporter failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())