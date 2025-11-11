#!/usr/bin/env python3
"""
Adelaide Weather Health Monitor
===============================

Comprehensive health monitoring for the Adelaide Weather system.
Monitors all services, validates FAISS indices, and provides detailed reporting.

Usage:
    python validation_scripts/health_monitor.py [--continuous] [--alert-threshold=3]
"""

import os
import sys
import json
import time
import requests
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AdelaideWeatherHealthMonitor:
    """Comprehensive health monitoring for Adelaide Weather system."""
    
    def __init__(self, api_token: Optional[str] = None):
        self.project_root = Path("/home/micha/adelaide-weather-final")
        self.api_token = api_token or self._load_api_token()
        self.base_url = "http://localhost"
        
        # Health check endpoints
        self.endpoints = {
            'nginx': 'http://localhost/health',
            'api': 'http://localhost/api/health',
            'frontend': 'http://localhost',
            'faiss': 'http://localhost/api/health/faiss',
            'prometheus': 'http://localhost:9090/-/healthy',
            'grafana': 'http://localhost:3001/api/health',
            'alertmanager': 'http://localhost:9093/-/healthy'
        }
        
        self.health_history = []
        
    def _load_api_token(self) -> Optional[str]:
        """Load API token from environment file."""
        env_file = self.project_root / ".env.production"
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith('API_TOKEN='):
                            return line.split('=', 1)[1].strip()
            except Exception as e:
                logger.warning(f"Could not load API token: {e}")
        return None
    
    def check_docker_containers(self) -> Dict[str, Dict]:
        """Check status of Docker containers."""
        logger.info("🐳 Checking Docker containers...")
        
        containers = {}
        
        try:
            # Get container status
            result = subprocess.run([
                'docker-compose', '-f', 'docker-compose.production.yml',
                'ps', '--format', 'json'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        container_info = json.loads(line)
                        name = container_info.get('Service', 'unknown')
                        containers[name] = {
                            'status': container_info.get('State', 'unknown'),
                            'ports': container_info.get('Ports', ''),
                            'health': 'unknown'
                        }
            
            # Get health status for each container
            for service in containers:
                try:
                    health_result = subprocess.run([
                        'docker', 'inspect', '--format',
                        '{{.State.Health.Status}}',
                        f"adelaide-weather-{service}"
                    ], capture_output=True, text=True)
                    
                    if health_result.returncode == 0:
                        containers[service]['health'] = health_result.stdout.strip()
                    else:
                        containers[service]['health'] = 'no-healthcheck'
                        
                except Exception as e:
                    logger.warning(f"Could not get health for {service}: {e}")
                    containers[service]['health'] = 'unknown'
                    
        except Exception as e:
            logger.error(f"Failed to check containers: {e}")
            
        return containers
    
    def check_endpoint(self, service: str, url: str, timeout: int = 10) -> Tuple[bool, str, float]:
        """Check a single endpoint for health."""
        start_time = time.time()
        
        try:
            headers = {}
            if self.api_token and 'api' in url:
                headers['Authorization'] = f'Bearer {self.api_token}'
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return True, "OK", response_time
            else:
                return False, f"HTTP {response.status_code}", response_time
                
        except requests.exceptions.ConnectionError:
            return False, "Connection failed", time.time() - start_time
        except requests.exceptions.Timeout:
            return False, "Timeout", time.time() - start_time
        except Exception as e:
            return False, str(e), time.time() - start_time
    
    def check_faiss_indices(self) -> Dict[str, Dict]:
        """Check FAISS indices integrity."""
        logger.info("🧠 Checking FAISS indices...")
        
        indices_dir = self.project_root / "indices"
        indices_status = {}
        
        expected_indices = [
            "faiss_6h_flatip.faiss",
            "faiss_6h_ivfpq.faiss", 
            "faiss_12h_flatip.faiss",
            "faiss_12h_ivfpq.faiss",
            "faiss_24h_flatip.faiss",
            "faiss_24h_ivfpq.faiss",
            "faiss_48h_flatip.faiss",
            "faiss_48h_ivfpq.faiss"
        ]
        
        for index_name in expected_indices:
            index_path = indices_dir / index_name
            
            if index_path.exists():
                size_mb = index_path.stat().st_size / (1024 * 1024)
                modified = datetime.fromtimestamp(index_path.stat().st_mtime)
                
                indices_status[index_name] = {
                    'exists': True,
                    'size_mb': round(size_mb, 2),
                    'modified': modified.isoformat(),
                    'status': 'healthy' if size_mb > 0.1 else 'too_small'
                }
            else:
                indices_status[index_name] = {
                    'exists': False,
                    'status': 'missing'
                }
                
        return indices_status
    
    def check_system_resources(self) -> Dict[str, Dict]:
        """Check system resource usage."""
        logger.info("💻 Checking system resources...")
        
        resources = {}
        
        try:
            # Memory usage
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            total_mem = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1]) // 1024
            available_mem = int([line for line in meminfo.split('\n') if 'MemAvailable' in line][0].split()[1]) // 1024
            
            resources['memory'] = {
                'total_mb': total_mem,
                'available_mb': available_mem,
                'usage_percent': round(((total_mem - available_mem) / total_mem) * 100, 1),
                'status': 'healthy' if available_mem > 2048 else 'low'
            }
            
        except Exception as e:
            logger.warning(f"Could not get memory info: {e}")
            resources['memory'] = {'status': 'unknown'}
        
        try:
            # Disk usage
            import shutil
            total, used, free = shutil.disk_usage(self.project_root)
            
            total_gb = total // (1024**3)
            free_gb = free // (1024**3)
            used_percent = round((used / total) * 100, 1)
            
            resources['disk'] = {
                'total_gb': total_gb,
                'free_gb': free_gb,
                'used_percent': used_percent,
                'status': 'healthy' if free_gb > 5 else 'low'
            }
            
        except Exception as e:
            logger.warning(f"Could not get disk info: {e}")
            resources['disk'] = {'status': 'unknown'}
        
        try:
            # Load average
            with open('/proc/loadavg', 'r') as f:
                load_avg = f.read().split()[0]
            
            cpu_count = os.cpu_count()
            load_percent = round((float(load_avg) / cpu_count) * 100, 1) if cpu_count else 0
            
            resources['cpu'] = {
                'load_avg': float(load_avg),
                'cpu_count': cpu_count,
                'load_percent': load_percent,
                'status': 'healthy' if load_percent < 80 else 'high'
            }
            
        except Exception as e:
            logger.warning(f"Could not get CPU info: {e}")
            resources['cpu'] = {'status': 'unknown'}
            
        return resources
    
    def run_comprehensive_check(self) -> Dict:
        """Run complete health check suite."""
        logger.info("🔍 Running comprehensive health check...")
        
        check_result = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'containers': {},
            'endpoints': {},
            'faiss_indices': {},
            'system_resources': {},
            'summary': {
                'healthy_services': 0,
                'unhealthy_services': 0,
                'total_services': 0
            }
        }
        
        # Check Docker containers
        check_result['containers'] = self.check_docker_containers()
        
        # Check service endpoints
        for service, url in self.endpoints.items():
            is_healthy, message, response_time = self.check_endpoint(service, url)
            
            check_result['endpoints'][service] = {
                'url': url,
                'healthy': is_healthy,
                'message': message,
                'response_time_ms': round(response_time * 1000, 2)
            }
            
            if is_healthy:
                check_result['summary']['healthy_services'] += 1
            else:
                check_result['summary']['unhealthy_services'] += 1
            
            check_result['summary']['total_services'] += 1
        
        # Check FAISS indices
        check_result['faiss_indices'] = self.check_faiss_indices()
        
        # Check system resources
        check_result['system_resources'] = self.check_system_resources()
        
        # Determine overall status
        critical_services = ['nginx', 'api', 'frontend']
        critical_healthy = all(
            check_result['endpoints'].get(service, {}).get('healthy', False)
            for service in critical_services
        )
        
        if critical_healthy and check_result['summary']['unhealthy_services'] == 0:
            check_result['overall_status'] = 'healthy'
        elif critical_healthy:
            check_result['overall_status'] = 'degraded'
        else:
            check_result['overall_status'] = 'unhealthy'
        
        # Add to history
        self.health_history.append(check_result)
        
        return check_result
    
    def print_health_report(self, check_result: Dict):
        """Print formatted health report."""
        status = check_result['overall_status']
        timestamp = check_result['timestamp']
        
        # Status emoji and color
        status_indicators = {
            'healthy': ('🟢', '\033[32m'),
            'degraded': ('🟡', '\033[33m'),
            'unhealthy': ('🔴', '\033[31m'),
            'unknown': ('⚪', '\033[37m')
        }
        
        emoji, color = status_indicators.get(status, ('❓', '\033[0m'))
        reset_color = '\033[0m'
        
        print(f"\n{emoji} ADELAIDE WEATHER HEALTH REPORT {emoji}")
        print("=" * 60)
        print(f"📅 Timestamp: {timestamp}")
        print(f"🎯 Overall Status: {color}{status.upper()}{reset_color}")
        print()
        
        # Service endpoints
        print("🌐 SERVICE ENDPOINTS:")
        for service, info in check_result['endpoints'].items():
            status_icon = "✅" if info['healthy'] else "❌"
            response_time = info['response_time_ms']
            message = info['message']
            
            print(f"  {status_icon} {service:<12} | {response_time:>6.0f}ms | {message}")
        
        # Docker containers
        print("\n🐳 DOCKER CONTAINERS:")
        for service, info in check_result['containers'].items():
            state = info['status']
            health = info['health']
            
            if state == 'running' and health in ['healthy', 'no-healthcheck']:
                status_icon = "✅"
            elif state == 'running':
                status_icon = "⚠️"
            else:
                status_icon = "❌"
            
            print(f"  {status_icon} {service:<12} | {state} | health: {health}")
        
        # FAISS indices status
        healthy_indices = sum(1 for info in check_result['faiss_indices'].values() if info.get('status') == 'healthy')
        total_indices = len(check_result['faiss_indices'])
        
        print(f"\n🧠 FAISS INDICES: {healthy_indices}/{total_indices} healthy")
        
        # System resources
        resources = check_result['system_resources']
        print(f"\n💻 SYSTEM RESOURCES:")
        
        if 'memory' in resources:
            mem = resources['memory']
            if mem.get('status') != 'unknown':
                status_icon = "✅" if mem['status'] == 'healthy' else "⚠️"
                print(f"  {status_icon} Memory: {mem.get('usage_percent', 0)}% used ({mem.get('available_mb', 0):,} MB available)")
        
        if 'disk' in resources:
            disk = resources['disk']
            if disk.get('status') != 'unknown':
                status_icon = "✅" if disk['status'] == 'healthy' else "⚠️"
                print(f"  {status_icon} Disk: {disk.get('used_percent', 0)}% used ({disk.get('free_gb', 0)} GB free)")
        
        if 'cpu' in resources:
            cpu = resources['cpu']
            if cpu.get('status') != 'unknown':
                status_icon = "✅" if cpu['status'] == 'healthy' else "⚠️"
                print(f"  {status_icon} CPU: {cpu.get('load_percent', 0)}% load avg ({cpu.get('load_avg', 0)} on {cpu.get('cpu_count', 0)} cores)")
        
        # Summary
        summary = check_result['summary']
        print(f"\n📊 SUMMARY: {summary['healthy_services']}/{summary['total_services']} services healthy")
        
        print("=" * 60)
        
    def save_health_report(self, check_result: Dict, filename: str = None):
        """Save health report to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_report_{timestamp}.json"
        
        report_path = self.project_root / "validation_scripts" / filename
        
        try:
            with open(report_path, 'w') as f:
                json.dump(check_result, f, indent=2, default=str)
            logger.info(f"💾 Health report saved to: {report_path}")
        except Exception as e:
            logger.error(f"Failed to save health report: {e}")
    
    def monitor_continuously(self, interval: int = 60, alert_threshold: int = 3):
        """Run continuous monitoring with alerting."""
        logger.info(f"🔄 Starting continuous monitoring (interval: {interval}s)")
        
        consecutive_failures = 0
        
        try:
            while True:
                check_result = self.run_comprehensive_check()
                self.print_health_report(check_result)
                
                if check_result['overall_status'] == 'unhealthy':
                    consecutive_failures += 1
                    
                    if consecutive_failures >= alert_threshold:
                        logger.error(f"🚨 ALERT: System unhealthy for {consecutive_failures} consecutive checks!")
                        # Here you could send notifications, emails, etc.
                else:
                    consecutive_failures = 0
                
                # Save periodic reports
                if time.time() % 300 < interval:  # Every 5 minutes
                    self.save_health_report(check_result)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user")

def main():
    parser = argparse.ArgumentParser(description="Adelaide Weather Health Monitor")
    parser.add_argument('--continuous', action='store_true', help='Run continuous monitoring')
    parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in seconds')
    parser.add_argument('--alert-threshold', type=int, default=3, help='Alert after N consecutive failures')
    parser.add_argument('--save-report', action='store_true', help='Save health report to file')
    
    args = parser.parse_args()
    
    monitor = AdelaideWeatherHealthMonitor()
    
    if args.continuous:
        monitor.monitor_continuously(args.interval, args.alert_threshold)
    else:
        # Single health check
        check_result = monitor.run_comprehensive_check()
        monitor.print_health_report(check_result)
        
        if args.save_report:
            monitor.save_health_report(check_result)
        
        # Exit code based on health
        if check_result['overall_status'] == 'healthy':
            sys.exit(0)
        elif check_result['overall_status'] == 'degraded':
            sys.exit(1)
        else:
            sys.exit(2)

if __name__ == "__main__":
    main()