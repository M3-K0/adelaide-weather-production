# Integration Guide

This guide shows how to integrate the Adelaide Weather Forecasting API into real-world applications with production-ready patterns and best practices.

## Table of Contents

- [Integration Patterns](#integration-patterns)
- [Architecture Examples](#architecture-examples)
- [Real-Time Applications](#real-time-applications)
- [Batch Processing](#batch-processing)
- [Monitoring & Alerting](#monitoring--alerting)
- [Caching Strategies](#caching-strategies)
- [Error Handling](#error-handling)
- [Performance Optimization](#performance-optimization)

## Integration Patterns

### 1. Direct API Integration

Simple integration for applications that need real-time weather data.

```python
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class WeatherService:
    """Production weather service with async support."""
    
    def __init__(self, api_token: str, base_url: str = None):
        self.api_token = api_token
        self.base_url = base_url or "https://api.adelaideweather.example.com"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {self.api_token}',
                'Accept': 'application/json',
                'User-Agent': 'YourApp/1.0.0'
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_current_conditions(self) -> Dict:
        """Get current weather conditions (6h forecast)."""
        async with self.session.get(
            f"{self.base_url}/forecast",
            params={'horizon': '6h', 'vars': 't2m,u10,v10,msl'}
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    async def get_daily_forecast(self) -> Dict:
        """Get daily forecast with risk assessment."""
        async with self.session.get(
            f"{self.base_url}/forecast",
            params={'horizon': '24h', 'vars': 't2m,u10,v10,msl,cape,tp6h'}
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    async def get_extended_outlook(self) -> Dict:
        """Get extended 48h outlook."""
        async with self.session.get(
            f"{self.base_url}/forecast",
            params={'horizon': '48h', 'vars': 't2m,msl,tp6h'}
        ) as response:
            response.raise_for_status()
            return await response.json()

# Usage example
async def main():
    async with WeatherService('your_token_here') as weather:
        current = await weather.get_current_conditions()
        daily = await weather.get_daily_forecast()
        
        print(f"Current temp: {current['variables']['t2m']['value']}°C")
        print(f"Risk level: {daily['risk_assessment']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Background Service Integration

For applications that need continuous weather monitoring.

```python
import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Callable, Optional
import aioredis

@dataclass
class WeatherAlert:
    alert_type: str
    severity: str
    message: str
    timestamp: datetime
    forecast_data: dict

class WeatherMonitorService:
    """Background service for continuous weather monitoring."""
    
    def __init__(self, weather_service: WeatherService, 
                 redis_url: str = "redis://localhost:6379"):
        self.weather_service = weather_service
        self.redis_url = redis_url
        self.redis = None
        self.alert_callbacks: List[Callable] = []
        self.running = False
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
    
    def add_alert_callback(self, callback: Callable[[WeatherAlert], None]):
        """Add callback for weather alerts."""
        self.alert_callbacks.append(callback)
    
    async def start(self):
        """Start the monitoring service."""
        self.redis = await aioredis.from_url(self.redis_url)
        self.running = True
        
        # Start monitoring tasks
        await asyncio.gather(
            self.monitor_current_conditions(),
            self.monitor_severe_weather(),
            self.update_daily_forecasts(),
        )
    
    async def stop(self):
        """Stop the monitoring service."""
        self.running = False
        if self.redis:
            await self.redis.close()
    
    async def monitor_current_conditions(self):
        """Monitor current conditions every 10 minutes."""
        while self.running:
            try:
                forecast = await self.weather_service.get_current_conditions()
                
                # Cache current conditions
                await self.redis.setex(
                    'weather:current',
                    300,  # 5 minute TTL
                    json.dumps(forecast)
                )
                
                # Check for temperature alerts
                temp = forecast['variables']['t2m']['value']
                if temp > 40:  # Extreme heat
                    await self.send_alert(WeatherAlert(
                        alert_type='extreme_heat',
                        severity='high',
                        message=f'Extreme temperature: {temp}°C',
                        timestamp=datetime.now(),
                        forecast_data=forecast
                    ))
                
                await asyncio.sleep(600)  # 10 minutes
                
            except Exception as e:
                self.logger.error(f"Error monitoring conditions: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute
    
    async def monitor_severe_weather(self):
        """Monitor for severe weather conditions every 30 minutes."""
        while self.running:
            try:
                forecast = await self.weather_service.get_daily_forecast()
                risks = forecast['risk_assessment']
                
                # Check for high-risk conditions
                high_risks = [
                    risk_type for risk_type, level in risks.items()
                    if level in ['high', 'extreme']
                ]
                
                if high_risks:
                    await self.send_alert(WeatherAlert(
                        alert_type='severe_weather',
                        severity='high',
                        message=f'High risk conditions: {", ".join(high_risks)}',
                        timestamp=datetime.now(),
                        forecast_data=forecast
                    ))
                
                await asyncio.sleep(1800)  # 30 minutes
                
            except Exception as e:
                self.logger.error(f"Error monitoring severe weather: {e}")
                await asyncio.sleep(300)  # Retry in 5 minutes
    
    async def update_daily_forecasts(self):
        """Update daily forecasts every 6 hours."""
        while self.running:
            try:
                daily = await self.weather_service.get_daily_forecast()
                extended = await self.weather_service.get_extended_outlook()
                
                # Cache forecasts
                await self.redis.setex(
                    'weather:daily',
                    21600,  # 6 hour TTL
                    json.dumps(daily)
                )
                
                await self.redis.setex(
                    'weather:extended',
                    43200,  # 12 hour TTL
                    json.dumps(extended)
                )
                
                await asyncio.sleep(21600)  # 6 hours
                
            except Exception as e:
                self.logger.error(f"Error updating forecasts: {e}")
                await asyncio.sleep(1800)  # Retry in 30 minutes
    
    async def send_alert(self, alert: WeatherAlert):
        """Send alert to all registered callbacks."""
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
```

### 3. REST API Gateway Integration

For microservices architectures with API gateways.

```javascript
// Express.js middleware for weather data
const express = require('express');
const NodeCache = require('node-cache');
const AdelaideWeatherClient = require('./lib/weather-client');

class WeatherMiddleware {
    constructor(apiToken, cacheOptions = {}) {
        this.client = new AdelaideWeatherClient(apiToken);
        this.cache = new NodeCache({
            stdTTL: cacheOptions.defaultTTL || 300, // 5 minutes
            checkperiod: 60,
            useClones: false
        });
        
        // Bind methods
        this.getCurrentWeather = this.getCurrentWeather.bind(this);
        this.getDailyForecast = this.getDailyForecast.bind(this);
        this.getExtendedForecast = this.getExtendedForecast.bind(this);
    }
    
    // Middleware for current weather
    async getCurrentWeather(req, res, next) {
        try {
            const cacheKey = 'current_weather';
            let weather = this.cache.get(cacheKey);
            
            if (!weather) {
                weather = await this.client.getForecast({
                    horizon: '6h',
                    variables: ['t2m', 'u10', 'v10', 'msl']
                });
                
                // Cache for 5 minutes
                this.cache.set(cacheKey, weather, 300);
            }
            
            // Add to request context
            req.currentWeather = weather;
            next();
            
        } catch (error) {
            console.error('Weather middleware error:', error);
            req.currentWeather = null;
            next(); // Continue without weather data
        }
    }
    
    // Middleware for daily forecast
    async getDailyForecast(req, res, next) {
        try {
            const cacheKey = 'daily_forecast';
            let forecast = this.cache.get(cacheKey);
            
            if (!forecast) {
                forecast = await this.client.getForecast({
                    horizon: '24h',
                    variables: ['t2m', 'u10', 'v10', 'msl', 'cape', 'tp6h']
                });
                
                // Cache for 30 minutes
                this.cache.set(cacheKey, forecast, 1800);
            }
            
            req.dailyForecast = forecast;
            next();
            
        } catch (error) {
            console.error('Forecast middleware error:', error);
            req.dailyForecast = null;
            next();
        }
    }
    
    // API endpoint handler
    createWeatherRoutes() {
        const router = express.Router();
        
        // Current conditions endpoint
        router.get('/current', this.getCurrentWeather, (req, res) => {
            if (!req.currentWeather) {
                return res.status(503).json({
                    error: 'Weather data temporarily unavailable'
                });
            }
            
            const weather = req.currentWeather;
            res.json({
                temperature: weather.variables.t2m.value,
                temperatureRange: {
                    min: weather.variables.t2m.p05,
                    max: weather.variables.t2m.p95
                },
                wind: {
                    speed: weather.wind10m?.speed,
                    direction: weather.wind10m?.direction
                },
                pressure: weather.variables.msl.value,
                confidence: weather.variables.t2m.confidence,
                narrative: weather.narrative,
                lastUpdated: weather.generated_at
            });
        });
        
        // Daily forecast endpoint
        router.get('/daily', this.getDailyForecast, (req, res) => {
            if (!req.dailyForecast) {
                return res.status(503).json({
                    error: 'Forecast data temporarily unavailable'
                });
            }
            
            const forecast = req.dailyForecast;
            res.json({
                forecast: {
                    temperature: forecast.variables.t2m.value,
                    precipitation: forecast.variables.tp6h.value,
                    stormRisk: forecast.variables.cape.value
                },
                risks: forecast.risk_assessment,
                confidence: forecast.confidence_explanation,
                analogs: forecast.analogs_summary,
                narrative: forecast.narrative,
                lastUpdated: forecast.generated_at
            });
        });
        
        // Health check endpoint
        router.get('/health', async (req, res) => {
            try {
                const health = await this.client.getHealth();
                res.json({
                    status: health.ready ? 'healthy' : 'degraded',
                    uptime: health.uptime_seconds,
                    version: health.model.version
                });
            } catch (error) {
                res.status(503).json({
                    status: 'unhealthy',
                    error: error.message
                });
            }
        });
        
        return router;
    }
}

// Usage in Express app
const app = express();
const weatherMiddleware = new WeatherMiddleware(process.env.WEATHER_API_TOKEN);

// Mount weather routes
app.use('/api/weather', weatherMiddleware.createWeatherRoutes());

// Example protected route that includes weather context
app.get('/dashboard', 
    weatherMiddleware.getCurrentWeather,
    weatherMiddleware.getDailyForecast,
    (req, res) => {
        res.json({
            user: req.user,
            currentWeather: req.currentWeather,
            dailyForecast: req.dailyForecast,
            recommendations: generateRecommendations(req.currentWeather, req.dailyForecast)
        });
    }
);

function generateRecommendations(current, daily) {
    const recommendations = [];
    
    if (current?.variables.t2m.value > 35) {
        recommendations.push({
            type: 'heat_warning',
            message: 'High temperature expected. Stay hydrated and avoid prolonged sun exposure.',
            priority: 'high'
        });
    }
    
    if (daily?.risk_assessment.thunderstorm === 'high') {
        recommendations.push({
            type: 'storm_warning',
            message: 'Severe thunderstorms possible. Secure outdoor items and avoid travel if possible.',
            priority: 'high'
        });
    }
    
    return recommendations;
}
```

## Architecture Examples

### 1. Microservices Architecture

```yaml
# docker-compose.yml
version: '3.8'

services:
  weather-service:
    build: ./weather-service
    environment:
      - WEATHER_API_TOKEN=${WEATHER_API_TOKEN}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    networks:
      - backend

  api-gateway:
    build: ./api-gateway
    ports:
      - "8080:8080"
    environment:
      - WEATHER_SERVICE_URL=http://weather-service:3000
    depends_on:
      - weather-service
    networks:
      - backend
      - frontend

  redis:
    image: redis:6-alpine
    networks:
      - backend

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - monitoring

networks:
  frontend:
  backend:
  monitoring:
```

### 2. Event-Driven Architecture

```python
import asyncio
import json
from typing import Dict, Any
import nats
from nats.aio.client import Client as NATS

class WeatherEventPublisher:
    """Publishes weather events to NATS streaming."""
    
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        self.nats_url = nats_url
        self.nc: NATS = None
    
    async def connect(self):
        self.nc = await nats.connect(self.nats_url)
    
    async def disconnect(self):
        if self.nc:
            await self.nc.close()
    
    async def publish_weather_update(self, forecast_data: Dict[str, Any]):
        """Publish weather forecast update event."""
        event = {
            'event_type': 'weather.forecast.updated',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'horizon': forecast_data['horizon'],
                'temperature': forecast_data['variables']['t2m']['value'],
                'confidence': forecast_data['variables']['t2m']['confidence'],
                'risks': forecast_data['risk_assessment'],
                'generated_at': forecast_data['generated_at']
            }
        }
        
        await self.nc.publish('weather.updates', json.dumps(event).encode())
    
    async def publish_weather_alert(self, alert: WeatherAlert):
        """Publish weather alert event."""
        event = {
            'event_type': 'weather.alert.triggered',
            'timestamp': alert.timestamp.isoformat(),
            'data': {
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'message': alert.message,
                'forecast_data': alert.forecast_data
            }
        }
        
        await self.nc.publish('weather.alerts', json.dumps(event).encode())

# Event consumer example
class WeatherEventConsumer:
    """Consumes weather events and triggers actions."""
    
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        self.nats_url = nats_url
        self.nc: NATS = None
    
    async def start_consuming(self):
        self.nc = await nats.connect(self.nats_url)
        
        # Subscribe to weather updates
        await self.nc.subscribe('weather.updates', cb=self.handle_weather_update)
        await self.nc.subscribe('weather.alerts', cb=self.handle_weather_alert)
    
    async def handle_weather_update(self, msg):
        """Handle weather forecast updates."""
        try:
            event = json.loads(msg.data.decode())
            
            # Update database
            await self.update_weather_database(event['data'])
            
            # Notify subscribed clients via WebSocket
            await self.notify_websocket_clients(event)
            
            # Update cache
            await self.update_cache(event['data'])
            
        except Exception as e:
            print(f"Error handling weather update: {e}")
    
    async def handle_weather_alert(self, msg):
        """Handle weather alerts."""
        try:
            event = json.loads(msg.data.decode())
            alert_data = event['data']
            
            # Send push notifications
            await self.send_push_notifications(alert_data)
            
            # Log alert
            await self.log_alert(alert_data)
            
            # Trigger automated responses
            await self.trigger_automated_responses(alert_data)
            
        except Exception as e:
            print(f"Error handling weather alert: {e}")
```

## Real-Time Applications

### WebSocket Integration

```javascript
// Real-time weather updates via WebSocket
const WebSocket = require('ws');
const EventEmitter = require('events');

class WeatherWebSocketServer extends EventEmitter {
    constructor(port = 8081) {
        super();
        this.wss = new WebSocket.Server({ port });
        this.clients = new Set();
        this.lastWeatherData = null;
        
        this.setupWebSocketServer();
        this.startWeatherUpdates();
    }
    
    setupWebSocketServer() {
        this.wss.on('connection', (ws, req) => {
            console.log('New WebSocket connection');
            this.clients.add(ws);
            
            // Send latest weather data immediately
            if (this.lastWeatherData) {
                ws.send(JSON.stringify({
                    type: 'weather_update',
                    data: this.lastWeatherData
                }));
            }
            
            ws.on('message', (message) => {
                try {
                    const data = JSON.parse(message);
                    this.handleClientMessage(ws, data);
                } catch (error) {
                    console.error('Invalid message from client:', error);
                }
            });
            
            ws.on('close', () => {
                this.clients.delete(ws);
                console.log('WebSocket connection closed');
            });
            
            ws.on('error', (error) => {
                console.error('WebSocket error:', error);
                this.clients.delete(ws);
            });
        });
    }
    
    handleClientMessage(ws, data) {
        switch (data.type) {
            case 'subscribe_location':
                // In a real app, you might filter updates by location
                ws.location = data.location;
                break;
            case 'request_forecast':
                this.sendForecastToClient(ws, data.horizon);
                break;
        }
    }
    
    async sendForecastToClient(ws, horizon = '24h') {
        try {
            const forecast = await this.weatherClient.getForecast({
                horizon: horizon,
                variables: ['t2m', 'u10', 'v10', 'msl', 'cape']
            });
            
            ws.send(JSON.stringify({
                type: 'forecast_response',
                data: forecast
            }));
        } catch (error) {
            ws.send(JSON.stringify({
                type: 'error',
                message: 'Failed to fetch forecast'
            }));
        }
    }
    
    broadcastWeatherUpdate(weatherData) {
        this.lastWeatherData = weatherData;
        
        const message = JSON.stringify({
            type: 'weather_update',
            timestamp: new Date().toISOString(),
            data: weatherData
        });
        
        this.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(message);
            }
        });
    }
    
    broadcastAlert(alert) {
        const message = JSON.stringify({
            type: 'weather_alert',
            timestamp: new Date().toISOString(),
            data: alert
        });
        
        this.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(message);
            }
        });
    }
    
    startWeatherUpdates() {
        // Update weather every 10 minutes
        setInterval(async () => {
            try {
                const weather = await this.weatherClient.getForecast({
                    horizon: '6h',
                    variables: ['t2m', 'u10', 'v10', 'msl']
                });
                
                this.broadcastWeatherUpdate(weather);
                
                // Check for alerts
                this.checkForAlerts(weather);
                
            } catch (error) {
                console.error('Error updating weather:', error);
            }
        }, 600000); // 10 minutes
    }
    
    checkForAlerts(weather) {
        const temp = weather.variables.t2m.value;
        const risks = weather.risk_assessment;
        
        // Temperature alerts
        if (temp > 40) {
            this.broadcastAlert({
                type: 'extreme_heat',
                severity: 'high',
                message: `Extreme temperature: ${temp.toFixed(1)}°C`,
                temperature: temp
            });
        }
        
        // Risk alerts
        Object.entries(risks).forEach(([riskType, level]) => {
            if (level === 'high' || level === 'extreme') {
                this.broadcastAlert({
                    type: 'severe_weather',
                    severity: level,
                    message: `${riskType.replace('_', ' ')} risk is ${level}`,
                    riskType: riskType,
                    level: level
                });
            }
        });
    }
}

// Client-side JavaScript for real-time updates
class WeatherWebSocketClient {
    constructor(url = 'ws://localhost:8081') {
        this.url = url;
        this.ws = null;
        this.reconnectInterval = 5000;
        this.callbacks = new Map();
        
        this.connect();
    }
    
    connect() {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
            console.log('Connected to weather WebSocket');
            this.emit('connected');
        };
        
        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
        this.ws.onclose = () => {
            console.log('Weather WebSocket connection closed');
            this.emit('disconnected');
            
            // Reconnect after delay
            setTimeout(() => this.connect(), this.reconnectInterval);
        };
        
        this.ws.onerror = (error) => {
            console.error('Weather WebSocket error:', error);
            this.emit('error', error);
        };
    }
    
    handleMessage(message) {
        switch (message.type) {
            case 'weather_update':
                this.emit('weather_update', message.data);
                break;
            case 'weather_alert':
                this.emit('weather_alert', message.data);
                break;
            case 'forecast_response':
                this.emit('forecast_response', message.data);
                break;
            case 'error':
                this.emit('error', new Error(message.message));
                break;
        }
    }
    
    on(event, callback) {
        if (!this.callbacks.has(event)) {
            this.callbacks.set(event, []);
        }
        this.callbacks.get(event).push(callback);
    }
    
    emit(event, data) {
        const callbacks = this.callbacks.get(event) || [];
        callbacks.forEach(callback => callback(data));
    }
    
    requestForecast(horizon = '24h') {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'request_forecast',
                horizon: horizon
            }));
        }
    }
    
    subscribeToLocation(location) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'subscribe_location',
                location: location
            }));
        }
    }
}
```

## Batch Processing

For applications that need to process weather data in batches.

```python
import asyncio
import csv
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

class WeatherBatchProcessor:
    """Batch process weather forecasts for multiple locations/times."""
    
    def __init__(self, weather_service: WeatherService, max_workers: int = 5):
        self.weather_service = weather_service
        self.max_workers = max_workers
        self.results = []
    
    async def process_forecast_batch(self, requests: List[Dict]) -> List[Dict]:
        """Process multiple forecast requests concurrently."""
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_single_request(request):
            async with semaphore:
                try:
                    forecast = await self.weather_service.get_forecast(request)
                    return {
                        'request': request,
                        'forecast': forecast,
                        'status': 'success',
                        'timestamp': datetime.now().isoformat()
                    }
                except Exception as e:
                    return {
                        'request': request,
                        'error': str(e),
                        'status': 'error',
                        'timestamp': datetime.now().isoformat()
                    }
        
        tasks = [process_single_request(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    def generate_forecast_timeline(self, 
                                 start_date: datetime, 
                                 end_date: datetime,
                                 interval_hours: int = 6) -> List[Dict]:
        """Generate forecast requests for a timeline."""
        requests = []
        current_date = start_date
        
        while current_date <= end_date:
            # For historical analysis, you might vary the horizon
            horizon = '24h'  # or determine based on your needs
            
            requests.append({
                'horizon': horizon,
                'variables': ['t2m', 'u10', 'v10', 'msl', 'cape', 'tp6h'],
                'reference_time': current_date.isoformat()
            })
            
            current_date += timedelta(hours=interval_hours)
        
        return requests
    
    async def export_to_csv(self, results: List[Dict], filename: str):
        """Export batch results to CSV."""
        rows = []
        
        for result in results:
            if result['status'] == 'success':
                forecast = result['forecast']
                base_row = {
                    'timestamp': result['timestamp'],
                    'horizon': forecast['horizon'],
                    'generated_at': forecast['generated_at'],
                    'narrative': forecast['narrative'],
                    'confidence_explanation': forecast['confidence_explanation'],
                    'latency_ms': forecast['latency_ms']
                }
                
                # Add variable data
                for var_name, var_data in forecast['variables'].items():
                    base_row.update({
                        f'{var_name}_value': var_data['value'],
                        f'{var_name}_p05': var_data['p05'],
                        f'{var_name}_p95': var_data['p95'],
                        f'{var_name}_confidence': var_data['confidence'],
                        f'{var_name}_analog_count': var_data['analog_count']
                    })
                
                # Add risk assessment
                for risk_type, level in forecast['risk_assessment'].items():
                    base_row[f'risk_{risk_type}'] = level
                
                # Add wind data if available
                if forecast.get('wind10m', {}).get('available'):
                    wind = forecast['wind10m']
                    base_row.update({
                        'wind_speed': wind['speed'],
                        'wind_direction': wind['direction'],
                        'wind_gust': wind.get('gust')
                    })
                
                rows.append(base_row)
            else:
                # Add error row
                rows.append({
                    'timestamp': result['timestamp'],
                    'error': result['error'],
                    'status': 'error'
                })
        
        # Write to CSV
        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(filename, index=False)
            print(f"Exported {len(rows)} records to {filename}")

# Usage example
async def main():
    async with WeatherService('your_token_here') as weather:
        processor = WeatherBatchProcessor(weather, max_workers=3)
        
        # Generate requests for the past week
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        requests = processor.generate_forecast_timeline(
            start_date, end_date, interval_hours=6
        )
        
        print(f"Processing {len(requests)} forecast requests...")
        results = await processor.process_forecast_batch(requests)
        
        # Export results
        await processor.export_to_csv(results, 'weather_batch_results.csv')
        
        # Print summary
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = len(results) - successful
        
        print(f"Batch processing complete:")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Monitoring & Alerting

### Prometheus Metrics Integration

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

class WeatherMetrics:
    """Prometheus metrics for weather API integration."""
    
    def __init__(self):
        # Request metrics
        self.request_total = Counter(
            'weather_api_requests_total',
            'Total weather API requests',
            ['method', 'endpoint', 'status']
        )
        
        self.request_duration = Histogram(
            'weather_api_request_duration_seconds',
            'Weather API request duration',
            ['method', 'endpoint']
        )
        
        # Data quality metrics
        self.forecast_confidence = Gauge(
            'weather_forecast_confidence',
            'Average forecast confidence',
            ['horizon', 'variable']
        )
        
        self.api_latency = Gauge(
            'weather_api_latency_ms',
            'API response latency in milliseconds'
        )
        
        # Alert metrics
        self.active_alerts = Gauge(
            'weather_active_alerts_total',
            'Number of active weather alerts',
            ['severity', 'type']
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'weather_cache_hits_total',
            'Weather data cache hits'
        )
        
        self.cache_misses = Counter(
            'weather_cache_misses_total',
            'Weather data cache misses'
        )
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record API request metrics."""
        self.request_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        self.request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def update_forecast_quality(self, forecast_data: Dict):
        """Update forecast quality metrics."""
        horizon = forecast_data['horizon']
        
        for var_name, var_data in forecast_data['variables'].items():
            if var_data['available']:
                self.forecast_confidence.labels(
                    horizon=horizon,
                    variable=var_name
                ).set(var_data['confidence'])
        
        self.api_latency.set(forecast_data['latency_ms'])
    
    def record_alert(self, alert_type: str, severity: str, active: bool):
        """Record alert metrics."""
        if active:
            self.active_alerts.labels(severity=severity, type=alert_type).inc()
        else:
            self.active_alerts.labels(severity=severity, type=alert_type).dec()
    
    def record_cache_hit(self):
        """Record cache hit."""
        self.cache_hits.inc()
    
    def record_cache_miss(self):
        """Record cache miss."""
        self.cache_misses.inc()

# Instrumented weather service
class InstrumentedWeatherService:
    """Weather service with Prometheus metrics."""
    
    def __init__(self, weather_service: WeatherService):
        self.weather_service = weather_service
        self.metrics = WeatherMetrics()
        
        # Start Prometheus metrics server
        start_http_server(8000)
    
    async def get_forecast(self, request: Dict) -> Dict:
        """Get forecast with metrics recording."""
        start_time = time.time()
        
        try:
            forecast = await self.weather_service.get_forecast(request)
            
            # Record successful request
            duration = time.time() - start_time
            self.metrics.record_request(
                method='GET',
                endpoint='/forecast',
                status=200,
                duration=duration
            )
            
            # Update quality metrics
            self.metrics.update_forecast_quality(forecast)
            
            return forecast
            
        except Exception as e:
            # Record failed request
            duration = time.time() - start_time
            status = getattr(e, 'status_code', 500)
            
            self.metrics.record_request(
                method='GET',
                endpoint='/forecast',
                status=status,
                duration=duration
            )
            
            raise
```

### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "id": null,
    "title": "Weather API Integration Dashboard",
    "tags": ["weather", "api"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "API Request Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(weather_api_requests_total[5m])",
            "legendFormat": "{{endpoint}} - {{status}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(weather_api_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(weather_api_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Forecast Confidence",
        "type": "graph",
        "targets": [
          {
            "expr": "weather_forecast_confidence",
            "legendFormat": "{{horizon}} - {{variable}}"
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "Active Weather Alerts",
        "type": "stat",
        "targets": [
          {
            "expr": "sum by (severity) (weather_active_alerts_total)",
            "legendFormat": "{{severity}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
      },
      {
        "id": 5,
        "title": "Cache Hit Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(weather_cache_hits_total[5m]) / (rate(weather_cache_hits_total[5m]) + rate(weather_cache_misses_total[5m]))",
            "legendFormat": "Hit Rate"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

This integration guide provides comprehensive examples for integrating the Adelaide Weather Forecasting API into production applications. Choose the patterns that best fit your architecture and requirements.

## Summary

The integration guide covers:

1. **Direct API Integration** - Simple async/await patterns
2. **Background Services** - Continuous monitoring with Redis caching
3. **REST API Gateways** - Express.js middleware patterns
4. **Microservices** - Docker Compose architecture
5. **Event-Driven** - NATS messaging for scalable architectures
6. **Real-Time** - WebSocket integration for live updates
7. **Batch Processing** - Concurrent request processing with CSV export
8. **Monitoring** - Prometheus metrics and Grafana dashboards

Each pattern includes production-ready code with proper error handling, logging, caching, and monitoring capabilities.