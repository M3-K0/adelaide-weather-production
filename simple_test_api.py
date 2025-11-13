#!/usr/bin/env python3
"""
Simple HTTP server for load testing
===================================

Ultra-simple HTTP server that responds to weather API requests
for load testing purposes.
"""

import http.server
import socketserver
import json
import time
import random
import urllib.parse
from datetime import datetime

class WeatherAPIHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        start_time = time.time()
        
        # Parse URL
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Add realistic delay
        delay = random.uniform(0.01, 0.05)  # 10-50ms
        time.sleep(delay)
        
        if path == '/health':
            self._handle_health()
        elif path == '/forecast':
            self._handle_forecast(query_params)
        elif path == '/metrics':
            self._handle_metrics()
        elif path == '/':
            self._handle_root()
        else:
            self._send_404()
    
    def _handle_health(self):
        """Health check endpoint"""
        response = {
            "status": "healthy",
            "ready": True,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {
                "analog_search": "healthy",
                "forecast_generator": "healthy"
            }
        }
        self._send_json(response)
    
    def _handle_forecast(self, params):
        """Forecast endpoint with mock data"""
        # Validate horizon
        horizon = params.get('horizon', [''])[0]
        if horizon not in ['6h', '12h', '24h', '48h']:
            self._send_error(400, "Invalid horizon")
            return
        
        # Validate variables
        vars_str = params.get('vars', ['t2m'])[0]
        variables = [v.strip() for v in vars_str.split(',')]
        
        # Generate mock forecast
        forecast_data = {}
        for var in variables:
            if var == 't2m':
                value = random.uniform(280, 310)
            elif var in ['u10', 'v10']:
                value = random.uniform(-20, 20)
            elif var == 'msl':
                value = random.uniform(980, 1030)
            elif var == 'cape':
                value = random.uniform(0, 4000)
            else:
                value = random.uniform(-50, 50)
            
            forecast_data[var] = {
                'value': round(value, 3),
                'confidence_interval': {
                    'lower': round(value - 5, 3),
                    'upper': round(value + 5, 3)
                }
            }
        
        response = {
            "forecast": forecast_data,
            "metadata": {
                "horizon": horizon,
                "variables": variables,
                "forecast_time": datetime.now().isoformat(),
                "analog_search": {
                    "search_time_ms": round(random.uniform(5, 25), 2),
                    "total_candidates": 50000,
                    "k_neighbors": 25
                }
            },
            "performance": {
                "total_time_ms": round(random.uniform(15, 60), 2)
            }
        }
        
        self._send_json(response)
    
    def _handle_metrics(self):
        """Simple metrics endpoint"""
        metrics = f"""# HELP api_requests_total Total number of API requests
# TYPE api_requests_total counter
api_requests_total {random.randint(100, 1000)}

# HELP api_response_time_ms Response time in milliseconds
# TYPE api_response_time_ms histogram
api_response_time_ms_avg {random.uniform(20, 80):.2f}
"""
        self._send_text(metrics)
    
    def _handle_root(self):
        """Root endpoint"""
        response = {
            "message": "Adelaide Weather Load Test API",
            "version": "1.0.0",
            "endpoints": ["/health", "/forecast", "/metrics"]
        }
        self._send_json(response)
    
    def _send_json(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _send_text(self, text):
        """Send text response"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(text.encode())
    
    def _send_404(self):
        """Send 404 response"""
        self.send_response(404)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def _send_error(self, code, message):
        """Send error response"""
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())
    
    def log_message(self, format, *args):
        """Suppress request logging"""
        pass

def main():
    PORT = 8002
    
    print(f"🚀 Starting Simple Weather API Server on port {PORT}")
    print(f"📡 Endpoints available:")
    print(f"   Health: http://localhost:{PORT}/health")
    print(f"   Forecast: http://localhost:{PORT}/forecast?horizon=24h&vars=t2m,u10,v10")
    print(f"   Metrics: http://localhost:{PORT}/metrics")
    print()
    
    with socketserver.TCPServer(("", PORT), WeatherAPIHandler) as httpd:
        print(f"✅ Server running on http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    main()