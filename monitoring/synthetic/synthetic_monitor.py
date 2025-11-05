#!/usr/bin/env python3
"""
Adelaide Weather Forecasting - Synthetic Monitoring System
==========================================================

Comprehensive synthetic monitoring with SLO tracking, error budget management,
and geographic distribution checks for the Adelaide Weather Forecasting System.

Features:
- Multi-endpoint synthetic checks with JSON schema validation
- Service Level Objective (SLO) tracking with error budget burn rates
- Geographic distribution monitoring across Australian regions
- Real-time alerting with escalation policies
- Prometheus metrics integration for Grafana dashboards
- Complex end-to-end user journey validation

Author: Monitoring & Observability Engineering
Version: 1.0.0 - Production Synthetic Monitoring
"""

import os
import sys
import time
import json
import asyncio
import logging
import hashlib
import traceback
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

import aiohttp
import yaml
import jsonschema
from prometheus_client import (
    Counter, Histogram, Gauge, Info, generate_latest, 
    CONTENT_TYPE_LATEST, start_http_server, REGISTRY
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics for synthetic monitoring
synthetic_check_total = Counter(
    'synthetic_check_total',
    'Total synthetic check attempts',
    ['check_name', 'endpoint', 'region']
)

synthetic_check_success_total = Counter(
    'synthetic_check_success_total', 
    'Successful synthetic checks',
    ['check_name', 'endpoint', 'region']
)

synthetic_check_duration_seconds = Histogram(
    'synthetic_check_duration_seconds',
    'Synthetic check response time',
    ['check_name', 'endpoint', 'region'],
    buckets=[0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0]
)

synthetic_check_status_code = Counter(
    'synthetic_check_status_code_total',
    'HTTP status codes from synthetic checks',
    ['check_name', 'endpoint', 'region', 'status_code']
)

synthetic_forecast_data_total = Counter(
    'synthetic_forecast_data_total',
    'Total forecast data quality checks'
)

synthetic_forecast_data_valid_total = Counter(
    'synthetic_forecast_data_valid_total',
    'Valid forecast data checks'
)

# SLO metrics
slo_error_budget_remaining = Gauge(
    'slo_error_budget_remaining_ratio',
    'Remaining error budget as ratio (0-1)',
    ['slo_name', 'window']
)

slo_burn_rate = Gauge(
    'slo_burn_rate',
    'Current error budget burn rate',
    ['slo_name', 'window']
)

slo_availability_ratio = Gauge(
    'slo_availability_ratio',
    'Current availability ratio',
    ['slo_name']
)

# System info metrics
synthetic_monitor_info = Info(
    'synthetic_monitor_info',
    'Synthetic monitoring system information'
)

uptime_seconds = Gauge(
    'synthetic_monitor_uptime_seconds',
    'Synthetic monitor uptime in seconds'
)

@dataclass
class CheckResult:
    """Result of a synthetic check."""
    success: bool
    response_time_ms: float
    status_code: Optional[int]
    error_message: Optional[str]
    check_details: Dict[str, Any]
    timestamp: datetime

@dataclass
class SLOStatus:
    """Service Level Objective status."""
    name: str
    target_ratio: float
    current_ratio: float
    error_budget_remaining: float
    burn_rate_1h: float
    burn_rate_6h: float
    burn_rate_24h: float
    is_breached: bool
    time_to_exhaustion: Optional[timedelta]

class GeographicMonitor:
    """Handles monitoring from multiple geographic locations."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.regions = config.get('geographic_locations', [])
        self.session_cache: Dict[str, aiohttp.ClientSession] = {}
        
    async def get_session(self, region: str) -> aiohttp.ClientSession:
        """Get or create HTTP session for a region."""
        if region not in self.session_cache:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session_cache[region] = aiohttp.ClientSession(timeout=timeout)
        return self.session_cache[region]
    
    async def cleanup(self):
        """Clean up HTTP sessions."""
        for session in self.session_cache.values():
            await session.close()
        self.session_cache.clear()

class JSONSchemaValidator:
    """Validates API responses against JSON schemas."""
    
    def __init__(self, schema_dir: Path):
        self.schema_dir = schema_dir
        self.schemas: Dict[str, Dict] = {}
        self._load_schemas()
    
    def _load_schemas(self):
        """Load all JSON schemas from the schema directory."""
        if not self.schema_dir.exists():
            logger.warning(f"Schema directory {self.schema_dir} does not exist")
            return
            
        for schema_file in self.schema_dir.glob("*.json"):
            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                    self.schemas[schema_file.stem] = schema
                    logger.info(f"Loaded schema: {schema_file.stem}")
            except Exception as e:
                logger.error(f"Failed to load schema {schema_file}: {e}")
    
    def validate(self, schema_name: str, data: Dict) -> Tuple[bool, Optional[str]]:
        """Validate data against a schema."""
        if schema_name not in self.schemas:
            return False, f"Schema '{schema_name}' not found"
        
        try:
            jsonschema.validate(data, self.schemas[schema_name])
            return True, None
        except jsonschema.ValidationError as e:
            return False, f"Schema validation failed: {e.message}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

class SLOTracker:
    """Tracks Service Level Objectives and error budgets."""
    
    def __init__(self, slo_config: Dict[str, Any]):
        self.slo_config = slo_config
        self.check_history: Dict[str, List[Tuple[datetime, bool]]] = {}
        
    def record_check(self, slo_name: str, success: bool, timestamp: Optional[datetime] = None):
        """Record a check result for SLO tracking."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        if slo_name not in self.check_history:
            self.check_history[slo_name] = []
            
        self.check_history[slo_name].append((timestamp, success))
        
        # Keep only recent history (configurable window)
        window_hours = 72  # Keep 72 hours of history
        cutoff = timestamp - timedelta(hours=window_hours)
        self.check_history[slo_name] = [
            (ts, result) for ts, result in self.check_history[slo_name] 
            if ts > cutoff
        ]
    
    def calculate_slo_status(self, slo_name: str) -> Optional[SLOStatus]:
        """Calculate current SLO status and error budget."""
        if slo_name not in self.slo_config:
            return None
            
        slo_def = self.slo_config[slo_name]
        target_ratio = slo_def['objective'] / 100.0
        
        history = self.check_history.get(slo_name, [])
        if not history:
            return None
            
        now = datetime.now(timezone.utc)
        
        # Calculate success ratio over measurement window
        window_hours = 24  # 24 hour window for real-time tracking
        cutoff = now - timedelta(hours=window_hours)
        recent_checks = [(ts, result) for ts, result in history if ts > cutoff]
        
        if not recent_checks:
            return None
            
        total_checks = len(recent_checks)
        successful_checks = sum(1 for _, success in recent_checks if success)
        current_ratio = successful_checks / total_checks if total_checks > 0 else 0
        
        # Calculate error budget
        error_budget_remaining = max(0, (current_ratio - target_ratio) / (1 - target_ratio))
        
        # Calculate burn rates for different windows
        burn_rate_1h = self._calculate_burn_rate(recent_checks, 1, target_ratio)
        burn_rate_6h = self._calculate_burn_rate(recent_checks, 6, target_ratio)
        burn_rate_24h = self._calculate_burn_rate(recent_checks, 24, target_ratio)
        
        # Check if SLO is breached
        is_breached = current_ratio < target_ratio
        
        # Calculate time to error budget exhaustion
        time_to_exhaustion = None
        if burn_rate_1h > 0 and error_budget_remaining > 0:
            hours_remaining = error_budget_remaining / burn_rate_1h
            time_to_exhaustion = timedelta(hours=hours_remaining)
        
        return SLOStatus(
            name=slo_name,
            target_ratio=target_ratio,
            current_ratio=current_ratio,
            error_budget_remaining=error_budget_remaining,
            burn_rate_1h=burn_rate_1h,
            burn_rate_6h=burn_rate_6h,
            burn_rate_24h=burn_rate_24h,
            is_breached=is_breached,
            time_to_exhaustion=time_to_exhaustion
        )
    
    def _calculate_burn_rate(self, checks: List[Tuple[datetime, bool]], 
                           window_hours: int, target_ratio: float) -> float:
        """Calculate error budget burn rate for a time window."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=window_hours)
        window_checks = [(ts, result) for ts, result in checks if ts > cutoff]
        
        if not window_checks:
            return 0.0
            
        total = len(window_checks)
        successful = sum(1 for _, success in window_checks if success)
        error_rate = 1 - (successful / total)
        
        # Burn rate is how fast we're consuming error budget
        # Normalized to 1.0 = consuming at exactly the SLO rate
        allowed_error_rate = 1 - target_ratio
        return error_rate / allowed_error_rate if allowed_error_rate > 0 else 0.0

class AlertManager:
    """Manages alerting based on SLO violations and check failures."""
    
    def __init__(self, alert_config: Dict[str, Any]):
        self.alert_config = alert_config
        self.active_alerts: Dict[str, datetime] = {}
        
    async def check_and_alert(self, slo_status: SLOStatus, check_results: Dict[str, CheckResult]):
        """Check SLO status and trigger alerts if needed."""
        # SLO breach alerts
        if slo_status.is_breached:
            await self._trigger_alert(
                'slo_breach',
                f"SLO '{slo_status.name}' breached: {slo_status.current_ratio:.3f} < {slo_status.target_ratio:.3f}",
                'critical'
            )
        
        # Burn rate alerts
        if slo_status.burn_rate_1h > 14.4:  # Very fast burn
            await self._trigger_alert(
                'error_budget_burn_fast',
                f"Error budget burning at {slo_status.burn_rate_1h:.1f}x rate for {slo_status.name}",
                'critical'
            )
        elif slo_status.burn_rate_6h > 6.0:  # Fast burn
            await self._trigger_alert(
                'error_budget_burn_medium',
                f"Error budget burning at {slo_status.burn_rate_6h:.1f}x rate for {slo_status.name}",
                'warning'
            )
        
        # Check failure alerts
        failed_checks = [name for name, result in check_results.items() if not result.success]
        if failed_checks:
            await self._trigger_alert(
                'synthetic_check_failure',
                f"Synthetic checks failing: {', '.join(failed_checks)}",
                'warning'
            )
    
    async def _trigger_alert(self, alert_type: str, message: str, severity: str):
        """Trigger an alert through configured channels."""
        alert_key = f"{alert_type}_{severity}"
        
        # Rate limiting - don't spam the same alert
        if alert_key in self.active_alerts:
            last_sent = self.active_alerts[alert_key]
            if datetime.now(timezone.utc) - last_sent < timedelta(minutes=15):
                return
        
        self.active_alerts[alert_key] = datetime.now(timezone.utc)
        
        logger.error(f"ALERT [{severity.upper()}] {alert_type}: {message}")
        
        # Here you would integrate with actual alerting systems
        # For now, we'll just log the alert
        if severity == 'critical':
            logger.critical(f"🚨 CRITICAL ALERT: {message}")
        else:
            logger.warning(f"⚠️  WARNING ALERT: {message}")

class SyntheticMonitor:
    """Main synthetic monitoring orchestrator."""
    
    def __init__(self, config_path: str):
        self.start_time = datetime.now(timezone.utc)
        self.config = self._load_config(config_path)
        self.schema_validator = JSONSchemaValidator(
            Path(config_path).parent / "schemas"
        )
        self.geo_monitor = GeographicMonitor(self.config['synthetic_monitoring'])
        self.slo_tracker = SLOTracker(self.config.get('slos', {}))
        self.alert_manager = AlertManager(self.config.get('alerting', {}))
        self.is_running = False
        
        # Set system info
        synthetic_monitor_info.info({
            'version': '1.0.0',
            'config_file': config_path,
            'schema_count': str(len(self.schema_validator.schemas)),
            'slo_count': str(len(self.config.get('slos', {}))),
            'region_count': str(len(self.geo_monitor.regions))
        })
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load monitoring configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Expand environment variables
            config_str = yaml.dump(config)
            for env_var in os.environ:
                config_str = config_str.replace(f"${{{env_var}}}", os.environ[env_var])
            
            return yaml.safe_load(config_str)
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            raise
    
    async def perform_check(self, check_name: str, check_config: Dict[str, Any], 
                          region: str = "local") -> CheckResult:
        """Perform a single synthetic check."""
        start_time = time.time()
        synthetic_check_total.labels(
            check_name=check_name, 
            endpoint=check_config['url'],
            region=region
        ).inc()
        
        try:
            session = await self.geo_monitor.get_session(region)
            
            # Prepare request
            method = check_config.get('method', 'GET').upper()
            url = check_config['url']
            headers = check_config.get('headers', {})
            params = check_config.get('query_params', {})
            
            # Make request
            async with session.request(method, url, headers=headers, params=params) as response:
                response_time_ms = (time.time() - start_time) * 1000
                status_code = response.status
                
                # Record response time
                synthetic_check_duration_seconds.labels(
                    check_name=check_name,
                    endpoint=check_config['url'],
                    region=region
                ).observe(response_time_ms / 1000)
                
                # Record status code
                synthetic_check_status_code.labels(
                    check_name=check_name,
                    endpoint=check_config['url'],
                    region=region,
                    status_code=str(status_code)
                ).inc()
                
                # Check expected status code
                expected_status = check_config.get('expected_status', 200)
                if status_code != expected_status:
                    return CheckResult(
                        success=False,
                        response_time_ms=response_time_ms,
                        status_code=status_code,
                        error_message=f"Expected status {expected_status}, got {status_code}",
                        check_details={'url': url, 'method': method},
                        timestamp=datetime.now(timezone.utc)
                    )
                
                # Check response time
                expected_response_time = check_config.get('expected_response_time_ms', 5000)
                if response_time_ms > expected_response_time:
                    return CheckResult(
                        success=False,
                        response_time_ms=response_time_ms,
                        status_code=status_code,
                        error_message=f"Response time {response_time_ms:.0f}ms exceeds {expected_response_time}ms",
                        check_details={'url': url, 'method': method},
                        timestamp=datetime.now(timezone.utc)
                    )
                
                # Parse response for content checks
                try:
                    if 'application/json' in response.headers.get('content-type', ''):
                        response_data = await response.json()
                    else:
                        response_data = await response.text()
                except Exception as e:
                    logger.warning(f"Failed to parse response: {e}")
                    response_data = None
                
                # Perform content checks
                check_details = {'url': url, 'method': method, 'response_size': len(str(response_data))}
                
                for check in check_config.get('checks', []):
                    check_result = await self._perform_content_check(
                        check, response_data, response.headers, check_name
                    )
                    if not check_result[0]:
                        return CheckResult(
                            success=False,
                            response_time_ms=response_time_ms,
                            status_code=status_code,
                            error_message=check_result[1],
                            check_details=check_details,
                            timestamp=datetime.now(timezone.utc)
                        )
                
                # All checks passed
                synthetic_check_success_total.labels(
                    check_name=check_name,
                    endpoint=check_config['url'],
                    region=region
                ).inc()
                
                return CheckResult(
                    success=True,
                    response_time_ms=response_time_ms,
                    status_code=status_code,
                    error_message=None,
                    check_details=check_details,
                    timestamp=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Check {check_name} failed: {e}")
            
            return CheckResult(
                success=False,
                response_time_ms=response_time_ms,
                status_code=None,
                error_message=str(e),
                check_details={'url': check_config['url'], 'method': check_config.get('method', 'GET')},
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _perform_content_check(self, check: Dict[str, Any], response_data: Any, 
                                   headers: Any, check_name: str) -> Tuple[bool, Optional[str]]:
        """Perform content validation checks."""
        check_type = check['type']
        
        try:
            if check_type == 'json_path':
                if not isinstance(response_data, dict):
                    return False, "Response is not JSON"
                
                # Simple JSON path implementation
                path = check['path']
                expected = check.get('expected')
                
                # For this implementation, we'll handle simple paths like "$.key" or "$.key.subkey"
                if path.startswith('$.'):
                    keys = path[2:].split('.')
                    value = response_data
                    for key in keys:
                        if not isinstance(value, dict) or key not in value:
                            return False, f"JSON path {path} not found"
                        value = value[key]
                    
                    if expected is not None and value != expected:
                        return False, f"JSON path {path} value {value} != expected {expected}"
                
            elif check_type == 'content':
                contains = check.get('contains')
                if contains and contains not in str(response_data):
                    return False, f"Content does not contain '{contains}'"
                    
            elif check_type == 'header':
                header_name = check['name']
                expected_value = check.get('contains')
                header_value = headers.get(header_name, '')
                
                if expected_value and expected_value not in header_value:
                    return False, f"Header {header_name} does not contain '{expected_value}'"
                    
            elif check_type == 'json_schema':
                schema_name = check.get('schema_path', '').split('/')[-1].replace('.json', '')
                valid, error = self.schema_validator.validate(schema_name, response_data)
                if not valid:
                    return False, f"Schema validation failed: {error}"
                    
            elif check_type == 'response_size':
                size = len(str(response_data))
                min_size = check.get('min_bytes', 0)
                max_size = check.get('max_bytes', float('inf'))
                
                if size < min_size or size > max_size:
                    return False, f"Response size {size} not in range [{min_size}, {max_size}]"
            
            # Special check for forecast data quality
            if check_name == 'forecast_api' and isinstance(response_data, dict):
                synthetic_forecast_data_total.inc()
                if self._validate_forecast_data_quality(response_data):
                    synthetic_forecast_data_valid_total.inc()
                    
        except Exception as e:
            return False, f"Content check failed: {str(e)}"
        
        return True, None
    
    def _validate_forecast_data_quality(self, forecast_data: Dict) -> bool:
        """Validate forecast data quality for SLO tracking."""
        try:
            variables = forecast_data.get('variables', {})
            if not variables:
                return False
            
            # Check that at least 80% of variables have valid data
            total_vars = len(variables)
            valid_vars = sum(1 for var_data in variables.values() 
                           if var_data.get('available', False) and var_data.get('value') is not None)
            
            return (valid_vars / total_vars) >= 0.8 if total_vars > 0 else False
            
        except Exception:
            return False
    
    async def run_check_cycle(self):
        """Run a complete cycle of all synthetic checks."""
        logger.info("Starting synthetic check cycle")
        
        check_results = {}
        endpoints = self.config['synthetic_monitoring']['endpoints']
        
        # Run checks for each endpoint across regions
        for check_name, check_config in endpoints.items():
            # For now, run from primary region only
            # In production, you'd run from multiple regions
            result = await self.perform_check(check_name, check_config, region="sydney")
            check_results[check_name] = result
            
            # Update SLO tracking
            if check_name in ['forecast_api', 'health_api']:
                slo_name = f"{check_name}_availability"
                self.slo_tracker.record_check(slo_name, result.success)
            
            logger.info(
                f"Check {check_name}: {'✅ PASS' if result.success else '❌ FAIL'} "
                f"({result.response_time_ms:.0f}ms)"
            )
            
            if not result.success:
                logger.error(f"  Error: {result.error_message}")
        
        # Update SLO metrics
        for slo_name in self.config.get('slos', {}):
            slo_status = self.slo_tracker.calculate_slo_status(slo_name)
            if slo_status:
                slo_availability_ratio.labels(slo_name=slo_status.name).set(slo_status.current_ratio)
                slo_error_budget_remaining.labels(slo_name=slo_status.name, window="24h").set(slo_status.error_budget_remaining)
                slo_burn_rate.labels(slo_name=slo_status.name, window="1h").set(slo_status.burn_rate_1h)
                slo_burn_rate.labels(slo_name=slo_status.name, window="6h").set(slo_status.burn_rate_6h)
                slo_burn_rate.labels(slo_name=slo_status.name, window="24h").set(slo_status.burn_rate_24h)
                
                # Check for alerts
                await self.alert_manager.check_and_alert(slo_status, check_results)
        
        return check_results
    
    async def start(self):
        """Start the synthetic monitoring loop."""
        self.is_running = True
        logger.info("🚀 Starting Adelaide Weather Synthetic Monitoring System")
        
        check_interval = self.config['synthetic_monitoring']['global']['check_interval']
        interval_seconds = int(check_interval.rstrip('s'))
        
        while self.is_running:
            try:
                cycle_start = time.time()
                
                # Update uptime
                uptime_seconds.set((datetime.now(timezone.utc) - self.start_time).total_seconds())
                
                # Run check cycle
                await self.run_check_cycle()
                
                # Calculate sleep time to maintain interval
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, interval_seconds - cycle_duration)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    logger.warning(f"Check cycle took {cycle_duration:.1f}s, longer than {interval_seconds}s interval")
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(60)  # Wait before retrying
    
    async def stop(self):
        """Stop the synthetic monitoring loop."""
        self.is_running = False
        await self.geo_monitor.cleanup()
        logger.info("Synthetic monitoring stopped")

def start_metrics_server(port: int = 8080):
    """Start Prometheus metrics server."""
    try:
        start_http_server(port)
        logger.info(f"📊 Metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")

async def main():
    """Main entry point."""
    # Set up environment variables with defaults
    os.environ.setdefault('API_BASE_URL', 'http://api:8000')
    os.environ.setdefault('FRONTEND_BASE_URL', 'http://frontend:3000')
    os.environ.setdefault('API_TOKEN', 'your-api-token-here')
    
    config_path = os.path.join(os.path.dirname(__file__), 'config.yml')
    
    # Start metrics server
    metrics_port = int(os.environ.get('METRICS_PORT', 8080))
    start_metrics_server(metrics_port)
    
    # Initialize and start monitoring
    monitor = SyntheticMonitor(config_path)
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    finally:
        await monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())