# Analog Weather Patterns - Integration Guide

A comprehensive guide for integrating the `/api/analogs` endpoint to unlock powerful historical weather pattern analysis in your applications.

## 🌟 Overview

The `/api/analogs` endpoint provides FAISS-powered analog weather pattern search, enabling developers to:

- **Discover Historical Precedents**: Find similar weather patterns from historical data
- **Quantify Uncertainty**: Analyze ensemble statistics across analog patterns  
- **Understand Evolution**: Explore detailed weather timeline progressions
- **Assess Risk**: Evaluate outcomes from similar historical conditions
- **Research Patterns**: Conduct meteorological analysis and studies

## 🚀 Quick Start

### Basic Pattern Search

```bash
# Find 10 most similar 24h weather patterns
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.adelaideweather.example.com/api/analogs?horizon=24h&k=10"
```

### Response Structure

```json
{
  "forecast_horizon": "24h",
  "top_analogs": [
    {
      "date": "2023-03-15T12:00:00Z",
      "similarity_score": 0.89,
      "initial_conditions": {...},
      "timeline": [...],
      "outcome_narrative": "Pattern evolution description",
      "season_info": {"month": 3, "season": "autumn"}
    }
  ],
  "ensemble_stats": {
    "mean_outcomes": {...},
    "outcome_uncertainty": {...},
    "common_events": [...]
  }
}
```

## 🔧 Integration Patterns

### 1. Weather Pattern Recognition

Identify and classify current atmospheric conditions based on historical patterns:

```python
import requests
from datetime import datetime
from typing import Dict, List, Any

class WeatherPatternAnalyzer:
    def __init__(self, api_token: str, base_url: str = "https://api.adelaideweather.example.com"):
        self.base_url = base_url
        self.headers = {'Authorization': f'Bearer {api_token}'}
    
    def classify_current_pattern(self, horizon: str = "24h", k: int = 5) -> Dict[str, Any]:
        """Classify current weather pattern based on historical analogs."""
        
        # Get analog patterns
        response = requests.get(
            f"{self.base_url}/api/analogs",
            headers=self.headers,
            params={"horizon": horizon, "k": k}
        )
        response.raise_for_status()
        analogs = response.json()
        
        # Analyze pattern characteristics
        top_analog = analogs["top_analogs"][0]
        ensemble_stats = analogs["ensemble_stats"]
        
        # Extract pattern classification
        pattern_type = self._classify_by_season_and_conditions(
            top_analog["season_info"],
            ensemble_stats["mean_outcomes"]
        )
        
        # Assess reliability
        avg_similarity = sum(a["similarity_score"] for a in analogs["top_analogs"]) / len(analogs["top_analogs"])
        reliability = "high" if avg_similarity > 0.8 else "medium" if avg_similarity > 0.6 else "low"
        
        return {
            "pattern_type": pattern_type,
            "best_match_date": top_analog["date"],
            "similarity_score": top_analog["similarity_score"],
            "reliability": reliability,
            "expected_outcome": top_analog["outcome_narrative"],
            "seasonal_context": top_analog["season_info"],
            "common_events": ensemble_stats["common_events"],
            "uncertainty": ensemble_stats["outcome_uncertainty"]
        }
    
    def _classify_by_season_and_conditions(self, season_info: dict, mean_outcomes: dict) -> str:
        """Classify weather pattern based on season and conditions."""
        season = season_info["season"]
        temp = mean_outcomes.get("t2m", 20)
        pressure = mean_outcomes.get("msl", 101300)
        
        if season == "summer":
            if temp > 35:
                return "extreme_heat"
            elif temp > 30:
                return "hot_dry" 
            else:
                return "mild_summer"
        elif season == "winter":
            if temp < 5:
                return "cold_front"
            elif pressure < 100500:
                return "low_pressure_system"
            else:
                return "stable_winter"
        elif season == "autumn":
            if pressure > 102000:
                return "high_pressure_ridge"
            else:
                return "transitional_autumn"
        else:  # spring
            return "variable_spring"

# Usage Example
analyzer = WeatherPatternAnalyzer("your-api-token")
pattern_analysis = analyzer.classify_current_pattern(horizon="24h", k=10)

print(f"Current Pattern: {pattern_analysis['pattern_type']}")
print(f"Reliability: {pattern_analysis['reliability']}")
print(f"Expected: {pattern_analysis['expected_outcome']}")
```

### 2. Risk Assessment Dashboard

Build a risk assessment system using historical pattern outcomes:

```javascript
class WeatherRiskAssessment {
    constructor(apiToken, baseUrl = 'https://api.adelaideweather.example.com') {
        this.apiToken = apiToken;
        this.baseUrl = baseUrl;
    }

    async assessRisks(horizon = '48h', variables = 't2m,msl,cape,u10,v10') {
        try {
            const response = await fetch(`${this.baseUrl}/api/analogs?horizon=${horizon}&variables=${variables}&k=20`, {
                headers: { 'Authorization': `Bearer ${this.apiToken}` }
            });
            
            if (!response.ok) throw new Error(`API Error: ${response.status}`);
            const analogs = await response.json();
            
            return this.calculateRiskMetrics(analogs);
            
        } catch (error) {
            console.error('Risk assessment failed:', error);
            throw error;
        }
    }

    calculateRiskMetrics(analogs) {
        const { top_analogs, ensemble_stats } = analogs;
        
        // Extract risk indicators from historical outcomes
        const heatRisk = this.assessHeatRisk(ensemble_stats.mean_outcomes, ensemble_stats.outcome_uncertainty);
        const windRisk = this.assessWindRisk(ensemble_stats.mean_outcomes);
        const convectiveRisk = this.assessConvectiveRisk(ensemble_stats.mean_outcomes, ensemble_stats.common_events);
        const overallReliability = this.calculateReliability(top_analogs);
        
        return {
            risks: {
                heat_stress: heatRisk,
                wind_damage: windRisk, 
                severe_weather: convectiveRisk
            },
            reliability: overallReliability,
            historical_precedents: top_analogs.length,
            uncertainty_range: this.calculateUncertaintyRange(ensemble_stats.outcome_uncertainty),
            recommendations: this.generateRecommendations(heatRisk, windRisk, convectiveRisk),
            last_updated: new Date().toISOString()
        };
    }

    assessHeatRisk(meanOutcomes, uncertainty) {
        const temp = meanOutcomes.t2m || 20;
        const tempUncertainty = uncertainty.t2m || 2;
        
        // High temperature with low uncertainty = high confidence heat risk
        if (temp > 40 && tempUncertainty < 3) return { level: 'extreme', confidence: 'high' };
        if (temp > 35 && tempUncertainty < 4) return { level: 'high', confidence: 'medium' };
        if (temp > 30) return { level: 'moderate', confidence: 'low' };
        return { level: 'low', confidence: 'high' };
    }

    assessWindRisk(meanOutcomes) {
        const uWind = meanOutcomes.u10 || 0;
        const vWind = meanOutcomes.v10 || 0;
        const windSpeed = Math.sqrt(uWind * uWind + vWind * vWind);
        
        if (windSpeed > 15) return { level: 'high', speed_ms: windSpeed };
        if (windSpeed > 10) return { level: 'moderate', speed_ms: windSpeed };
        return { level: 'low', speed_ms: windSpeed };
    }

    assessConvectiveRisk(meanOutcomes, commonEvents) {
        const cape = meanOutcomes.cape || 0;
        const hasThunderstormEvents = commonEvents.some(event => 
            event.toLowerCase().includes('thunder') || 
            event.toLowerCase().includes('storm') ||
            event.toLowerCase().includes('convect')
        );
        
        if (cape > 2000 || hasThunderstormEvents) return { level: 'high', cape_value: cape };
        if (cape > 1000) return { level: 'moderate', cape_value: cape };
        return { level: 'low', cape_value: cape };
    }

    calculateReliability(topAnalogs) {
        const avgSimilarity = topAnalogs.reduce((sum, a) => sum + a.similarity_score, 0) / topAnalogs.length;
        const minSimilarity = Math.min(...topAnalogs.map(a => a.similarity_score));
        
        return {
            average_similarity: avgSimilarity,
            minimum_similarity: minSimilarity,
            pattern_count: topAnalogs.length,
            classification: avgSimilarity > 0.8 ? 'high' : avgSimilarity > 0.6 ? 'medium' : 'low'
        };
    }

    calculateUncertaintyRange(outcomeUncertainty) {
        return {
            temperature: `±${(outcomeUncertainty.t2m || 2).toFixed(1)}°C`,
            pressure: `±${((outcomeUncertainty.msl || 500) / 100).toFixed(0)} hPa`,
            wind: `±${Math.sqrt((outcomeUncertainty.u10 || 1)**2 + (outcomeUncertainty.v10 || 1)**2).toFixed(1)} m/s`
        };
    }

    generateRecommendations(heatRisk, windRisk, convectiveRisk) {
        const recommendations = [];
        
        if (heatRisk.level === 'extreme') {
            recommendations.push('⚠️ Extreme heat warning - avoid outdoor activities during peak hours');
        }
        if (windRisk.level === 'high') {
            recommendations.push('💨 High wind alert - secure loose objects, avoid high-profile vehicles');
        }
        if (convectiveRisk.level === 'high') {
            recommendations.push('⛈️ Severe weather potential - monitor radar and warnings closely');
        }
        if (recommendations.length === 0) {
            recommendations.push('✅ No significant weather risks identified for this period');
        }
        
        return recommendations;
    }
}

// Usage Example
const riskAssessment = new WeatherRiskAssessment('your-api-token');

async function updateDashboard() {
    try {
        const risks = await riskAssessment.assessRisks('48h', 't2m,msl,cape,u10,v10');
        
        // Update dashboard UI
        document.getElementById('heat-risk-level').textContent = risks.risks.heat_stress.level;
        document.getElementById('wind-risk-level').textContent = risks.risks.wind_damage.level;
        document.getElementById('weather-risk-level').textContent = risks.risks.severe_weather.level;
        document.getElementById('reliability').textContent = risks.reliability.classification;
        
        // Update recommendations
        const recommendationsEl = document.getElementById('recommendations');
        recommendationsEl.innerHTML = risks.recommendations.map(rec => `<li>${rec}</li>`).join('');
        
        console.log('Risk dashboard updated:', risks);
        
    } catch (error) {
        console.error('Failed to update risk dashboard:', error);
    }
}
```

### 3. Meteorological Research Tool

Advanced pattern analysis for research and operational meteorology:

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List, Dict, Any
import requests

class MeteorologicalResearchTool:
    def __init__(self, api_token: str, base_url: str = "https://api.adelaideweather.example.com"):
        self.api_token = api_token
        self.base_url = base_url
        self.headers = {'Authorization': f'Bearer {api_token}'}
    
    def analyze_seasonal_patterns(self, season: str, year: int = 2023, k: int = 50) -> Dict[str, Any]:
        """Analyze analog patterns for a specific season."""
        
        # Define season date ranges
        season_ranges = {
            'summer': [('-12-01', '-02-28'), ('-06-01', '-08-31')],  # Both hemispheres
            'autumn': [('-03-01', '-05-31'), ('-09-01', '-11-30')],
            'winter': [('-06-01', '-08-31'), ('-12-01', '-02-28')],
            'spring': [('-09-01', '-11-30'), ('-03-01', '-05-31')]
        }
        
        season_data = []
        for date_range in season_ranges.get(season, []):
            start_date = f"{year}{date_range[0]}"
            end_date = f"{year}{date_range[1]}"
            patterns = self._get_patterns_for_period(start_date, end_date, k)
            season_data.extend(patterns)
        
        return self._analyze_pattern_characteristics(season_data, season)
    
    def compare_event_types(self, event_keywords: List[str], horizon: str = "24h", k: int = 30) -> Dict[str, Any]:
        """Compare analog patterns for different weather event types."""
        
        event_analyses = {}
        
        for event_type in event_keywords:
            # Search for patterns containing this event type
            patterns = self._search_event_patterns(event_type, horizon, k)
            event_analyses[event_type] = self._analyze_event_patterns(patterns, event_type)
        
        return {
            'event_comparisons': event_analyses,
            'cross_analysis': self._compare_events(event_analyses),
            'generated_at': datetime.now().isoformat()
        }
    
    def trend_analysis(self, variable: str, horizon: str = "24h", lookback_days: int = 30) -> Dict[str, Any]:
        """Analyze trends in analog pattern characteristics over time."""
        
        trend_data = []
        end_date = datetime.now()
        
        for i in range(lookback_days):
            query_date = end_date - timedelta(days=i)
            
            # Get analogs for this specific date
            analogs = self._get_analogs_for_date(query_date, horizon, variable)
            if analogs:
                trend_data.append({
                    'date': query_date.isoformat(),
                    'similarity_scores': [a['similarity_score'] for a in analogs['top_analogs']],
                    'mean_similarity': np.mean([a['similarity_score'] for a in analogs['top_analogs']]),
                    'uncertainty': analogs['ensemble_stats']['outcome_uncertainty'].get(variable, 0),
                    'mean_outcome': analogs['ensemble_stats']['mean_outcomes'].get(variable, 0)
                })
        
        return self._compute_trend_statistics(trend_data, variable)
    
    def _get_patterns_for_period(self, start_date: str, end_date: str, k: int) -> List[Dict]:
        """Get analog patterns for a specific time period."""
        # This would implement date-range pattern searching
        # For now, return sample structure
        return []
    
    def _search_event_patterns(self, event_type: str, horizon: str, k: int) -> Dict[str, Any]:
        """Search for patterns related to specific weather events."""
        
        # Customize search parameters based on event type
        variables = self._get_event_variables(event_type)
        
        response = requests.get(
            f"{self.base_url}/api/analogs",
            headers=self.headers,
            params={
                'horizon': horizon,
                'variables': variables,
                'k': k
            }
        )
        response.raise_for_status()
        return response.json()
    
    def _get_event_variables(self, event_type: str) -> str:
        """Get relevant variables for different event types."""
        event_variable_map = {
            'thunderstorm': 't2m,msl,cape,r850',
            'heat_wave': 't2m,msl,r850',
            'cold_front': 't2m,msl,u10,v10',
            'high_pressure': 'msl,t2m,u10,v10',
            'wind_event': 'u10,v10,msl',
            'general': 't2m,msl,u10,v10'
        }
        return event_variable_map.get(event_type.lower(), event_variable_map['general'])
    
    def _analyze_pattern_characteristics(self, patterns: List[Dict], season: str) -> Dict[str, Any]:
        """Analyze characteristics of pattern data."""
        if not patterns:
            return {'error': 'No patterns found for analysis'}
        
        return {
            'season': season,
            'pattern_count': len(patterns),
            'average_similarity': np.mean([p.get('similarity_score', 0) for p in patterns]),
            'similarity_distribution': self._compute_distribution([p.get('similarity_score', 0) for p in patterns]),
            'common_narratives': self._extract_common_narratives([p.get('outcome_narrative', '') for p in patterns]),
            'temporal_distribution': self._analyze_temporal_distribution(patterns)
        }
    
    def _analyze_event_patterns(self, patterns: Dict[str, Any], event_type: str) -> Dict[str, Any]:
        """Analyze patterns for a specific event type."""
        if not patterns.get('top_analogs'):
            return {'error': f'No patterns found for {event_type}'}
        
        top_analogs = patterns['top_analogs']
        ensemble_stats = patterns['ensemble_stats']
        
        return {
            'event_type': event_type,
            'pattern_count': len(top_analogs),
            'reliability': np.mean([a['similarity_score'] for a in top_analogs]),
            'typical_outcome': self._summarize_outcomes(top_analogs),
            'uncertainty_metrics': ensemble_stats['outcome_uncertainty'],
            'common_evolution': ensemble_stats['common_events'],
            'seasonal_context': self._analyze_seasonal_context(top_analogs)
        }
    
    def _get_analogs_for_date(self, query_date: datetime, horizon: str, variable: str) -> Dict[str, Any]:
        """Get analog patterns for a specific historical date."""
        response = requests.get(
            f"{self.base_url}/api/analogs",
            headers=self.headers,
            params={
                'horizon': horizon,
                'variables': variable,
                'query_time': query_date.isoformat() + 'Z',
                'k': 10
            }
        )
        if response.status_code == 200:
            return response.json()
        return None
    
    def _compute_trend_statistics(self, trend_data: List[Dict], variable: str) -> Dict[str, Any]:
        """Compute statistical trends from time series data."""
        if not trend_data:
            return {'error': 'No trend data available'}
        
        dates = [d['date'] for d in trend_data]
        similarities = [d['mean_similarity'] for d in trend_data]
        uncertainties = [d['uncertainty'] for d in trend_data]
        
        return {
            'variable': variable,
            'period_days': len(trend_data),
            'similarity_trend': {
                'mean': np.mean(similarities),
                'std': np.std(similarities),
                'trend_slope': np.polyfit(range(len(similarities)), similarities, 1)[0],
                'min': np.min(similarities),
                'max': np.max(similarities)
            },
            'uncertainty_trend': {
                'mean': np.mean(uncertainties),
                'std': np.std(uncertainties),
                'trend_slope': np.polyfit(range(len(uncertainties)), uncertainties, 1)[0]
            },
            'correlation_similarity_uncertainty': np.corrcoef(similarities, uncertainties)[0,1],
            'data_points': len(trend_data)
        }
    
    def generate_research_report(self, analysis_type: str = "seasonal", **kwargs) -> str:
        """Generate formatted research report."""
        if analysis_type == "seasonal":
            results = self.analyze_seasonal_patterns(kwargs.get('season', 'summer'))
        elif analysis_type == "events":
            results = self.compare_event_types(kwargs.get('events', ['thunderstorm', 'heat_wave']))
        elif analysis_type == "trends":
            results = self.trend_analysis(kwargs.get('variable', 't2m'))
        else:
            raise ValueError("Analysis type must be 'seasonal', 'events', or 'trends'")
        
        # Format as markdown report
        report = f"""# Meteorological Analysis Report

## Analysis Type: {analysis_type.title()}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

## Summary
{self._format_summary(results, analysis_type)}

## Detailed Results
{self._format_detailed_results(results, analysis_type)}

## Methodology
- **Data Source**: Adelaide Weather System Analog Database
- **Search Method**: FAISS-indexed similarity search
- **Distance Metric**: L2 (Euclidean) distance
- **Similarity Threshold**: Patterns with scores >0.6 considered relevant

## Limitations
- Analysis based on available historical patterns in database
- Similarity scores relative to training data distribution
- Regional specificity may limit broader applicability
"""
        return report

# Usage Examples
research_tool = MeteorologicalResearchTool('your-api-token')

# Analyze summer weather patterns
summer_analysis = research_tool.analyze_seasonal_patterns('summer', 2023, k=30)
print("Summer Pattern Analysis:", summer_analysis)

# Compare thunderstorm vs heat wave patterns
event_comparison = research_tool.compare_event_types(['thunderstorm', 'heat_wave', 'cold_front'])
print("Event Comparison:", event_comparison)

# Analyze temperature prediction trends
temp_trends = research_tool.trend_analysis('t2m', horizon='24h', lookback_days=15)
print("Temperature Trend Analysis:", temp_trends)

# Generate comprehensive report
report = research_tool.generate_research_report('seasonal', season='autumn')
with open('meteorological_analysis_report.md', 'w') as f:
    f.write(report)
```

## 📊 Advanced Use Cases

### 1. Real-time Event Monitoring

Set up continuous monitoring for specific weather events:

```python
import asyncio
import websockets
import json

class RealTimeEventMonitor:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.event_thresholds = {
            'extreme_heat': {'temp_threshold': 40, 'similarity_min': 0.75},
            'severe_convection': {'cape_threshold': 2000, 'similarity_min': 0.70},
            'wind_event': {'wind_threshold': 15, 'similarity_min': 0.80}
        }
    
    async def monitor_events(self, interval_minutes: int = 15):
        """Monitor for significant weather events using analog patterns."""
        while True:
            try:
                # Check current conditions against historical patterns
                events = await self.check_for_events()
                
                for event in events:
                    await self.alert_handler(event)
                
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute
    
    async def check_for_events(self) -> List[Dict[str, Any]]:
        """Check for significant weather events."""
        events = []
        
        # Get current analog patterns
        analogs = await self.get_current_analogs()
        
        if not analogs or not analogs.get('top_analogs'):
            return events
        
        # Check each event type
        for event_type, thresholds in self.event_thresholds.items():
            event_detected = self.detect_event(analogs, event_type, thresholds)
            if event_detected:
                events.append(event_detected)
        
        return events
    
    def detect_event(self, analogs: Dict, event_type: str, thresholds: Dict) -> Dict:
        """Detect specific weather event from analog patterns."""
        top_analog = analogs['top_analogs'][0]
        ensemble_stats = analogs['ensemble_stats']
        
        if top_analog['similarity_score'] < thresholds['similarity_min']:
            return None
        
        # Event-specific detection logic
        if event_type == 'extreme_heat':
            temp = ensemble_stats['mean_outcomes'].get('t2m', 0)
            if temp > thresholds['temp_threshold']:
                return {
                    'type': 'extreme_heat',
                    'severity': 'high' if temp > 45 else 'moderate',
                    'temperature': temp,
                    'similarity': top_analog['similarity_score'],
                    'historical_precedent': top_analog['date'],
                    'narrative': top_analog['outcome_narrative']
                }
        
        # Add other event types...
        return None
    
    async def alert_handler(self, event: Dict[str, Any]):
        """Handle weather event alerts."""
        alert_message = self.format_alert(event)
        print(f"🚨 WEATHER ALERT: {alert_message}")
        
        # Send to monitoring systems, dashboards, etc.
        await self.send_alert_notification(event)
    
    def format_alert(self, event: Dict[str, Any]) -> str:
        """Format weather event alert message."""
        event_type = event['type'].replace('_', ' ').title()
        severity = event.get('severity', 'moderate').upper()
        
        return f"{event_type} - {severity} severity detected (similarity: {event['similarity']:.2f})"

# Usage
monitor = RealTimeEventMonitor('your-api-token')
# asyncio.run(monitor.monitor_events(interval_minutes=15))
```

### 2. Climate Analysis Integration

Integrate analog patterns into broader climate analysis:

```python
class ClimateAnalysisIntegration:
    def __init__(self, api_token: str):
        self.api_token = api_token
        
    def analyze_climate_patterns(self, years: List[int], season: str) -> Dict[str, Any]:
        """Analyze multi-year climate patterns using analog search."""
        
        yearly_patterns = {}
        for year in years:
            patterns = self.get_seasonal_patterns(year, season)
            yearly_patterns[year] = patterns
        
        return {
            'multi_year_analysis': yearly_patterns,
            'trends': self.compute_climate_trends(yearly_patterns),
            'anomalies': self.identify_climate_anomalies(yearly_patterns),
            'projections': self.generate_pattern_projections(yearly_patterns)
        }
    
    def correlate_with_climate_indices(self, analog_data: Dict, climate_indices: Dict) -> Dict:
        """Correlate analog pattern characteristics with climate indices (SOI, IOD, etc.)."""
        
        correlations = {}
        for index_name, index_values in climate_indices.items():
            correlation = self.compute_correlation(analog_data, index_values)
            correlations[index_name] = correlation
        
        return {
            'correlations': correlations,
            'significant_relationships': self.identify_significant_correlations(correlations),
            'climate_drivers': self.analyze_climate_drivers(correlations)
        }
```

## 🔍 Troubleshooting

### Common Issues and Solutions

1. **Low Similarity Scores**
   ```python
   # Check if your query parameters are appropriate
   if analogs['top_analogs'][0]['similarity_score'] < 0.5:
       print("Consider adjusting search parameters:")
       print("- Try different horizon (6h, 12h, 24h, 48h)")
       print("- Reduce variable count for broader search") 
       print("- Increase k for more pattern options")
   ```

2. **Empty Results**
   ```python
   # Handle cases with no analog patterns found
   if not analogs.get('top_analogs'):
       print("No patterns found - check:")
       print("- API authentication is valid")
       print("- Query time is within valid range")
       print("- Service health: /health/faiss")
   ```

3. **Performance Optimization**
   ```python
   # Optimize for speed
   optimal_params = {
       'k': 5,  # Fewer patterns for speed
       'horizon': '24h',  # Standard horizon
       'variables': 't2m,msl'  # Minimum viable variables
   }
   ```

### Error Handling Best Practices

```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

class RobustAnalogClient:
    def __init__(self, api_token: str, base_url: str):
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {api_token}'})
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def search_analogs_with_fallback(self, **params):
        """Search analogs with automatic fallback and error handling."""
        try:
            # Primary request
            return self.session.get(f"{self.base_url}/api/analogs", params=params).json()
            
        except requests.exceptions.Timeout:
            # Fallback with reduced parameters
            fallback_params = {k: v for k, v in params.items() if k in ['horizon', 'k']}
            fallback_params['k'] = min(fallback_params.get('k', 10), 5)
            return self.session.get(f"{self.base_url}/api/analogs", params=fallback_params).json()
            
        except requests.exceptions.RequestException as e:
            # Log error and return safe default
            print(f"Analog search failed: {e}")
            return {
                'forecast_horizon': params.get('horizon', '24h'),
                'top_analogs': [],
                'ensemble_stats': {
                    'mean_outcomes': {},
                    'outcome_uncertainty': {},
                    'common_events': []
                }
            }
```

## 🎯 Best Practices Summary

1. **Parameter Selection**
   - Start with `k=10` for general analysis
   - Use relevant variables for your specific use case
   - Match horizon to your application needs

2. **Performance**
   - Cache results for 10-15 minutes
   - Use concurrent requests for multiple queries
   - Implement proper error handling and retries

3. **Data Interpretation**
   - Similarity >0.8 indicates strong pattern match
   - Check ensemble uncertainty for confidence assessment
   - Consider seasonal context in pattern interpretation

4. **Integration**
   - Use correlation IDs for debugging
   - Implement health checks for service monitoring
   - Build graceful fallbacks for service unavailability

5. **Security**
   - Store API tokens securely
   - Use HTTPS in production
   - Implement rate limiting awareness

## 📚 Additional Resources

- [API Reference Documentation](./README.md)
- [Authentication Guide](./authentication.md) 
- [Rate Limiting Policy](./rate-limiting.md)
- [Error Codes Reference](./error-codes.md)
- [Health Monitoring Guide](../RUNBOOK.md)

---

**Need Help?** Check the health endpoint (`/health/faiss`) for service status or review error correlation IDs for debugging support.