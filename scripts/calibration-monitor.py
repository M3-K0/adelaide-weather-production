#!/usr/bin/env python3
"""
Adelaide Weather Forecasting System - Calibration Monitor
========================================================

Advanced calibration monitoring and regression protection for the Adelaide Weather API.

Features:
- Real-time forecast calibration tracking
- Historical performance regression detection
- Automatic model drift detection
- Forecast accuracy trending and analysis
- Confidence interval validation
- Analog count optimization monitoring
- Data quality assessment
- Automated alerting for calibration degradation

Usage:
    python calibration-monitor.py --monitor          # Continuous calibration monitoring
    python calibration-monitor.py --validate        # Validate current calibration
    python calibration-monitor.py --baseline        # Establish performance baseline
    python calibration-monitor.py --report          # Generate calibration report
    python calibration-monitor.py --regression      # Run regression analysis
"""

import os
import sys
import time
import json
import asyncio
import argparse
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd
import httpx
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


@dataclass
class CalibrationMetrics:
    """Calibration performance metrics."""
    timestamp: datetime
    horizon: str
    variable: str
    forecast_value: float
    observed_value: Optional[float]
    p05: float
    p95: float
    confidence_interval_width: float
    analog_count: int
    is_within_ci: Optional[bool]
    absolute_error: Optional[float]
    relative_error: Optional[float]
    forecast_skill: Optional[float]


@dataclass
class CalibrationBaseline:
    """Baseline calibration performance."""
    established_date: datetime
    horizon: str
    variable: str
    mean_absolute_error: float
    root_mean_square_error: float
    forecast_skill_score: float
    confidence_interval_coverage: float
    optimal_analog_count: int
    expected_accuracy_range: Tuple[float, float]


class CalibrationMonitor:
    """Advanced calibration monitoring and regression detection system."""

    def __init__(self, api_url: str = "http://localhost:8000", 
                 api_token: str = "dev-token-change-in-production"):
        self.api_url = api_url.rstrip('/')
        self.api_token = api_token
        self.calibration_history: List[CalibrationMetrics] = []
        self.baselines: Dict[str, CalibrationBaseline] = {}
        self.data_dir = Path("calibration_data")
        self.data_dir.mkdir(exist_ok=True)
        
        # HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"Authorization": f"Bearer {api_token}"}
        )
        
        # Calibration thresholds
        self.thresholds = {
            "max_mae_degradation": 0.15,  # 15% increase in MAE
            "min_ci_coverage": 0.85,      # 85% confidence interval coverage
            "max_forecast_bias": 0.1,     # Maximum acceptable bias
            "min_forecast_skill": 0.3,    # Minimum forecast skill score
            "regression_window_days": 7,   # Days to look back for regression
        }
        
        # Mock observation data (in production, this would come from actual observations)
        self.mock_observations = self._generate_mock_observations()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _generate_mock_observations(self) -> Dict:
        """Generate mock observation data for testing calibration."""
        # In production, this would be replaced with real observation data
        np.random.seed(42)  # For reproducible testing
        
        observations = {}
        horizons = ["6h", "12h", "24h", "48h"]
        variables = ["t2m", "u10", "v10", "msl"]
        
        for horizon in horizons:
            observations[horizon] = {}
            for var in variables:
                # Generate realistic observations with some seasonal variation
                base_values = {
                    "t2m": 18.0 + 5 * np.sin(np.linspace(0, 2*np.pi, 100)),
                    "u10": 3.0 + 2 * np.random.normal(0, 1, 100),
                    "v10": -1.0 + 2 * np.random.normal(0, 1, 100),
                    "msl": 1013.25 + 10 * np.random.normal(0, 1, 100)
                }
                observations[horizon][var] = base_values[var]
        
        return observations

    async def fetch_forecast(self, horizon: str = "24h", 
                           variables: str = "t2m,u10,v10,msl") -> Optional[Dict]:
        """Fetch forecast data from the API."""
        try:
            response = await self.client.get(
                f"{self.api_url}/forecast",
                params={"horizon": horizon, "vars": variables}
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Failed to fetch forecast: {e}")
            return None

    def get_mock_observation(self, horizon: str, variable: str) -> float:
        """Get mock observation data for calibration testing."""
        obs_data = self.mock_observations.get(horizon, {}).get(variable, [])
        if obs_data:
            # Return a random observation from the generated data
            return float(obs_data[np.random.randint(0, len(obs_data))])
        return 0.0

    async def collect_calibration_metrics(self, horizon: str = "24h") -> List[CalibrationMetrics]:
        """Collect calibration metrics for analysis."""
        forecast_data = await self.fetch_forecast(horizon)
        if not forecast_data:
            return []
        
        metrics = []
        timestamp = datetime.now()
        
        for var_name, var_data in forecast_data.get("variables", {}).items():
            if not var_data.get("available", False):
                continue
            
            # Get mock observation (in production, use real observations)
            observed_value = self.get_mock_observation(horizon, var_name)
            
            # Calculate calibration metrics
            forecast_value = var_data.get("value")
            p05 = var_data.get("p05")
            p95 = var_data.get("p95")
            analog_count = var_data.get("analog_count", 0)
            
            if all(v is not None for v in [forecast_value, p05, p95]):
                ci_width = abs(p95 - p05)
                is_within_ci = p05 <= observed_value <= p95
                abs_error = abs(forecast_value - observed_value)
                rel_error = abs_error / abs(observed_value) if observed_value != 0 else None
                
                # Simple forecast skill score (could be enhanced with climatology)
                forecast_skill = 1.0 - (abs_error / (abs(observed_value) + 1.0))
                
                metric = CalibrationMetrics(
                    timestamp=timestamp,
                    horizon=horizon,
                    variable=var_name,
                    forecast_value=forecast_value,
                    observed_value=observed_value,
                    p05=p05,
                    p95=p95,
                    confidence_interval_width=ci_width,
                    analog_count=analog_count,
                    is_within_ci=is_within_ci,
                    absolute_error=abs_error,
                    relative_error=rel_error,
                    forecast_skill=forecast_skill
                )
                
                metrics.append(metric)
                self.calibration_history.append(metric)
        
        return metrics

    def calculate_baseline_metrics(self, horizon: str, variable: str, 
                                 window_days: int = 30) -> Optional[CalibrationBaseline]:
        """Calculate baseline calibration metrics from historical data."""
        # Filter data for the specified horizon and variable
        cutoff_date = datetime.now() - timedelta(days=window_days)
        relevant_metrics = [
            m for m in self.calibration_history
            if (m.horizon == horizon and 
                m.variable == variable and 
                m.timestamp >= cutoff_date and
                m.observed_value is not None)
        ]
        
        if len(relevant_metrics) < 10:  # Need sufficient data
            print(f"Insufficient data for baseline: {len(relevant_metrics)} samples")
            return None
        
        # Calculate statistical measures
        abs_errors = [m.absolute_error for m in relevant_metrics if m.absolute_error is not None]
        forecast_skills = [m.forecast_skill for m in relevant_metrics if m.forecast_skill is not None]
        ci_coverage = sum(1 for m in relevant_metrics if m.is_within_ci) / len(relevant_metrics)
        
        if not abs_errors:
            return None
        
        mae = statistics.mean(abs_errors)
        rmse = np.sqrt(statistics.mean([e**2 for e in abs_errors]))
        skill_score = statistics.mean(forecast_skills) if forecast_skills else 0.0
        
        # Calculate optimal analog count (simplified analysis)
        analog_counts = [m.analog_count for m in relevant_metrics]
        optimal_analog_count = int(statistics.median(analog_counts))
        
        # Define expected accuracy range (MAE ± 1 std dev)
        mae_std = statistics.stdev(abs_errors) if len(abs_errors) > 1 else 0.0
        accuracy_range = (mae - mae_std, mae + mae_std)
        
        baseline = CalibrationBaseline(
            established_date=datetime.now(),
            horizon=horizon,
            variable=variable,
            mean_absolute_error=mae,
            root_mean_square_error=rmse,
            forecast_skill_score=skill_score,
            confidence_interval_coverage=ci_coverage,
            optimal_analog_count=optimal_analog_count,
            expected_accuracy_range=accuracy_range
        )
        
        return baseline

    def detect_calibration_regression(self, horizon: str, variable: str) -> Dict:
        """Detect calibration regression by comparing recent vs baseline performance."""
        baseline_key = f"{horizon}_{variable}"
        baseline = self.baselines.get(baseline_key)
        
        if not baseline:
            return {"error": f"No baseline available for {baseline_key}"}
        
        # Get recent metrics (last N days)
        cutoff_date = datetime.now() - timedelta(days=self.thresholds["regression_window_days"])
        recent_metrics = [
            m for m in self.calibration_history
            if (m.horizon == horizon and 
                m.variable == variable and 
                m.timestamp >= cutoff_date and
                m.observed_value is not None)
        ]
        
        if len(recent_metrics) < 5:
            return {"error": f"Insufficient recent data: {len(recent_metrics)} samples"}
        
        # Calculate recent performance
        recent_abs_errors = [m.absolute_error for m in recent_metrics if m.absolute_error is not None]
        recent_skills = [m.forecast_skill for m in recent_metrics if m.forecast_skill is not None]
        recent_ci_coverage = sum(1 for m in recent_metrics if m.is_within_ci) / len(recent_metrics)
        
        recent_mae = statistics.mean(recent_abs_errors)
        recent_skill = statistics.mean(recent_skills) if recent_skills else 0.0
        
        # Detect regressions
        regressions = []
        
        # MAE regression
        mae_change = (recent_mae - baseline.mean_absolute_error) / baseline.mean_absolute_error
        if mae_change > self.thresholds["max_mae_degradation"]:
            regressions.append({
                "type": "MAE_degradation",
                "severity": "high" if mae_change > 0.3 else "medium",
                "baseline_mae": baseline.mean_absolute_error,
                "recent_mae": recent_mae,
                "change_percent": mae_change * 100,
                "description": f"Mean Absolute Error increased by {mae_change*100:.1f}%"
            })
        
        # Confidence interval coverage regression
        ci_change = recent_ci_coverage - baseline.confidence_interval_coverage
        if recent_ci_coverage < self.thresholds["min_ci_coverage"]:
            regressions.append({
                "type": "CI_coverage_degradation",
                "severity": "high" if recent_ci_coverage < 0.8 else "medium",
                "baseline_coverage": baseline.confidence_interval_coverage,
                "recent_coverage": recent_ci_coverage,
                "change": ci_change,
                "description": f"Confidence interval coverage dropped to {recent_ci_coverage*100:.1f}%"
            })
        
        # Forecast skill regression
        skill_change = recent_skill - baseline.forecast_skill_score
        if recent_skill < self.thresholds["min_forecast_skill"]:
            regressions.append({
                "type": "forecast_skill_degradation",
                "severity": "medium",
                "baseline_skill": baseline.forecast_skill_score,
                "recent_skill": recent_skill,
                "change": skill_change,
                "description": f"Forecast skill score dropped to {recent_skill:.3f}"
            })
        
        # Overall assessment
        overall_status = "healthy"
        if any(r["severity"] == "high" for r in regressions):
            overall_status = "degraded"
        elif regressions:
            overall_status = "warning"
        
        return {
            "assessment_time": datetime.now(),
            "horizon": horizon,
            "variable": variable,
            "overall_status": overall_status,
            "regressions_detected": len(regressions),
            "regressions": regressions,
            "recent_performance": {
                "mae": recent_mae,
                "skill_score": recent_skill,
                "ci_coverage": recent_ci_coverage,
                "sample_count": len(recent_metrics)
            },
            "baseline_performance": {
                "mae": baseline.mean_absolute_error,
                "skill_score": baseline.forecast_skill_score,
                "ci_coverage": baseline.confidence_interval_coverage
            }
        }

    async def continuous_calibration_monitoring(self, duration_hours: int = 24):
        """Run continuous calibration monitoring."""
        print(f"🔍 Starting calibration monitoring for {duration_hours} hours...")
        
        end_time = time.time() + (duration_hours * 3600)
        check_interval = 1800  # 30 minutes
        
        horizons = ["6h", "12h", "24h", "48h"]
        
        while time.time() < end_time:
            try:
                print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Collecting calibration metrics...")
                
                # Collect metrics for all horizons
                all_metrics = []
                for horizon in horizons:
                    metrics = await self.collect_calibration_metrics(horizon)
                    all_metrics.extend(metrics)
                    print(f"   {horizon}: {len(metrics)} variables monitored")
                
                # Check for regressions
                if all_metrics:
                    self._check_calibration_status()
                
                # Save data
                await self.save_calibration_data()
                
                await asyncio.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped by user")
                break
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                await asyncio.sleep(check_interval)

    def _check_calibration_status(self):
        """Check current calibration status and alert on issues."""
        # Get recent metrics for analysis
        recent_time = datetime.now() - timedelta(hours=1)
        recent_metrics = [m for m in self.calibration_history if m.timestamp >= recent_time]
        
        if not recent_metrics:
            return
        
        # Check overall performance
        recent_skills = [m.forecast_skill for m in recent_metrics if m.forecast_skill is not None]
        recent_ci_coverage = sum(1 for m in recent_metrics if m.is_within_ci) / len(recent_metrics)
        
        avg_skill = statistics.mean(recent_skills) if recent_skills else 0.0
        
        # Alert conditions
        alerts = []
        
        if avg_skill < self.thresholds["min_forecast_skill"]:
            alerts.append(f"Low forecast skill: {avg_skill:.3f}")
        
        if recent_ci_coverage < self.thresholds["min_ci_coverage"]:
            alerts.append(f"Low CI coverage: {recent_ci_coverage*100:.1f}%")
        
        if alerts:
            print(f"🚨 CALIBRATION ALERT: {' | '.join(alerts)}")
        else:
            print(f"✅ Calibration healthy - Skill: {avg_skill:.3f}, CI Coverage: {recent_ci_coverage*100:.1f}%")

    async def save_calibration_data(self):
        """Save calibration data to files."""
        # Save raw metrics
        metrics_data = [asdict(m) for m in self.calibration_history]
        with open(self.data_dir / "calibration_metrics.json", "w") as f:
            json.dump(metrics_data, f, indent=2, default=str)
        
        # Save baselines
        baselines_data = {k: asdict(v) for k, v in self.baselines.items()}
        with open(self.data_dir / "calibration_baselines.json", "w") as f:
            json.dump(baselines_data, f, indent=2, default=str)

    def load_calibration_data(self):
        """Load existing calibration data."""
        try:
            # Load metrics
            metrics_file = self.data_dir / "calibration_metrics.json"
            if metrics_file.exists():
                with open(metrics_file, "r") as f:
                    metrics_data = json.load(f)
                    self.calibration_history = [
                        CalibrationMetrics(**m) for m in metrics_data
                    ]
            
            # Load baselines
            baselines_file = self.data_dir / "calibration_baselines.json"
            if baselines_file.exists():
                with open(baselines_file, "r") as f:
                    baselines_data = json.load(f)
                    self.baselines = {
                        k: CalibrationBaseline(**v) for k, v in baselines_data.items()
                    }
                    
            print(f"✅ Loaded {len(self.calibration_history)} historical metrics and {len(self.baselines)} baselines")
            
        except Exception as e:
            print(f"⚠️  Error loading calibration data: {e}")

    def generate_calibration_report(self) -> Dict:
        """Generate comprehensive calibration analysis report."""
        if not self.calibration_history:
            return {"error": "No calibration data available"}
        
        report = {
            "report_generated": datetime.now(),
            "data_period": {
                "start": min(m.timestamp for m in self.calibration_history),
                "end": max(m.timestamp for m in self.calibration_history),
                "total_samples": len(self.calibration_history)
            },
            "variables_analyzed": list(set(m.variable for m in self.calibration_history)),
            "horizons_analyzed": list(set(m.horizon for m in self.calibration_history)),
            "overall_performance": {},
            "regression_analysis": {},
            "recommendations": []
        }
        
        # Overall performance by variable and horizon
        for horizon in report["horizons_analyzed"]:
            for variable in report["variables_analyzed"]:
                key = f"{horizon}_{variable}"
                
                relevant_metrics = [
                    m for m in self.calibration_history
                    if m.horizon == horizon and m.variable == variable and m.observed_value is not None
                ]
                
                if relevant_metrics:
                    abs_errors = [m.absolute_error for m in relevant_metrics if m.absolute_error is not None]
                    skills = [m.forecast_skill for m in relevant_metrics if m.forecast_skill is not None]
                    ci_coverage = sum(1 for m in relevant_metrics if m.is_within_ci) / len(relevant_metrics)
                    
                    report["overall_performance"][key] = {
                        "sample_count": len(relevant_metrics),
                        "mean_absolute_error": statistics.mean(abs_errors) if abs_errors else None,
                        "forecast_skill_score": statistics.mean(skills) if skills else None,
                        "ci_coverage_percent": ci_coverage * 100,
                        "last_updated": max(m.timestamp for m in relevant_metrics)
                    }
                    
                    # Check for regressions
                    regression_result = self.detect_calibration_regression(horizon, variable)
                    if "error" not in regression_result:
                        report["regression_analysis"][key] = regression_result
        
        # Generate recommendations
        report["recommendations"] = self._generate_calibration_recommendations(report)
        
        return report

    def _generate_calibration_recommendations(self, report: Dict) -> List[str]:
        """Generate calibration improvement recommendations."""
        recommendations = []
        
        # Check for variables with poor performance
        for key, perf in report["overall_performance"].items():
            if perf["ci_coverage_percent"] < 85:
                recommendations.append(
                    f"Improve confidence interval calibration for {key} "
                    f"(current coverage: {perf['ci_coverage_percent']:.1f}%)"
                )
            
            if perf["forecast_skill_score"] and perf["forecast_skill_score"] < 0.3:
                recommendations.append(
                    f"Review analog selection methodology for {key} "
                    f"(current skill: {perf['forecast_skill_score']:.3f})"
                )
        
        # Check regression analysis
        high_severity_regressions = []
        for key, analysis in report["regression_analysis"].items():
            high_severity = [r for r in analysis.get("regressions", []) if r["severity"] == "high"]
            high_severity_regressions.extend(high_severity)
        
        if high_severity_regressions:
            recommendations.append(
                f"Immediate attention required: {len(high_severity_regressions)} high-severity calibration regressions detected"
            )
        
        # General recommendations
        total_samples = sum(perf["sample_count"] for perf in report["overall_performance"].values())
        if total_samples < 100:
            recommendations.append("Increase monitoring frequency to collect more calibration data")
        
        return recommendations


async def main():
    """Main entry point for calibration monitoring."""
    parser = argparse.ArgumentParser(description="Adelaide Weather Calibration Monitor")
    parser.add_argument("--monitor", action="store_true", 
                       help="Run continuous calibration monitoring")
    parser.add_argument("--validate", action="store_true", 
                       help="Validate current calibration")
    parser.add_argument("--baseline", action="store_true", 
                       help="Establish performance baselines")
    parser.add_argument("--report", action="store_true", 
                       help="Generate calibration report")
    parser.add_argument("--regression", action="store_true", 
                       help="Run regression analysis")
    parser.add_argument("--duration", type=int, default=24, 
                       help="Duration in hours for monitoring")
    parser.add_argument("--api-url", default="http://localhost:8000", 
                       help="API URL to monitor")
    parser.add_argument("--api-token", default="dev-token-change-in-production", 
                       help="API authentication token")
    
    args = parser.parse_args()
    
    async with CalibrationMonitor(args.api_url, args.api_token) as monitor:
        # Load existing data
        monitor.load_calibration_data()
        
        if args.monitor:
            await monitor.continuous_calibration_monitoring(args.duration)
            
        elif args.validate:
            print("🔍 Running calibration validation...")
            horizons = ["6h", "12h", "24h", "48h"]
            
            for horizon in horizons:
                metrics = await monitor.collect_calibration_metrics(horizon)
                if metrics:
                    avg_skill = statistics.mean([m.forecast_skill for m in metrics if m.forecast_skill])
                    ci_coverage = sum(1 for m in metrics if m.is_within_ci) / len(metrics)
                    
                    print(f"   {horizon}: Skill={avg_skill:.3f}, CI Coverage={ci_coverage*100:.1f}%")
                    
        elif args.baseline:
            print("📊 Establishing performance baselines...")
            horizons = ["6h", "12h", "24h", "48h"]
            variables = ["t2m", "u10", "v10", "msl"]
            
            # First collect some data
            for _ in range(5):  # Collect several samples
                for horizon in horizons:
                    await monitor.collect_calibration_metrics(horizon)
                await asyncio.sleep(2)
            
            # Establish baselines
            for horizon in horizons:
                for variable in variables:
                    baseline = monitor.calculate_baseline_metrics(horizon, variable, window_days=1)
                    if baseline:
                        monitor.baselines[f"{horizon}_{variable}"] = baseline
                        print(f"   ✅ Baseline established for {horizon}_{variable}")
            
            await monitor.save_calibration_data()
            
        elif args.regression:
            print("🔍 Running regression analysis...")
            horizons = ["6h", "12h", "24h", "48h"]
            variables = ["t2m", "u10", "v10", "msl"]
            
            regressions_found = 0
            for horizon in horizons:
                for variable in variables:
                    result = monitor.detect_calibration_regression(horizon, variable)
                    if "error" not in result and result["regressions_detected"] > 0:
                        regressions_found += result["regressions_detected"]
                        print(f"⚠️  {horizon}_{variable}: {result['overall_status']} - "
                              f"{result['regressions_detected']} regressions")
            
            print(f"\n📊 Total regressions detected: {regressions_found}")
            
        elif args.report:
            print("📋 Generating calibration report...")
            report = monitor.generate_calibration_report()
            print(json.dumps(report, indent=2, default=str))
            
        else:
            # Quick calibration check
            print("🔍 Running quick calibration check...")
            metrics = await monitor.collect_calibration_metrics("24h")
            
            if metrics:
                avg_skill = statistics.mean([m.forecast_skill for m in metrics if m.forecast_skill])
                ci_coverage = sum(1 for m in metrics if m.is_within_ci) / len(metrics)
                avg_error = statistics.mean([m.absolute_error for m in metrics if m.absolute_error])
                
                print(f"📊 24h Forecast Calibration:")
                print(f"   Average Skill Score: {avg_skill:.3f}")
                print(f"   CI Coverage: {ci_coverage*100:.1f}%")
                print(f"   Mean Absolute Error: {avg_error:.2f}")
                print(f"   Variables Checked: {len(metrics)}")


if __name__ == "__main__":
    asyncio.run(main())