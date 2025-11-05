#!/usr/bin/env python3
"""
Setup deployment monitoring for post-deployment validation.
This script configures enhanced monitoring and alerting after a deployment.
"""

import os
import sys
import time
import argparse
import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class DeploymentMonitor:
    """Monitor deployment health and setup enhanced alerting."""
    
    def __init__(self, environment: str, duration_minutes: int = 30):
        self.environment = environment
        self.duration_minutes = duration_minutes
        self.cloudwatch = boto3.client('cloudwatch')
        self.sns = boto3.client('sns')
        
        # Environment-specific configuration
        self.config = self._get_environment_config()
        
    def _get_environment_config(self) -> Dict:
        """Get environment-specific configuration."""
        configs = {
            'dev': {
                'cluster_name': 'weather-forecast-dev-cluster',
                'api_service': 'weather-forecast-dev-api',
                'frontend_service': 'weather-forecast-dev-frontend',
                'alb_arn_suffix': None,  # Will be determined dynamically
                'sns_topic': None
            },
            'staging': {
                'cluster_name': 'weather-forecast-staging-cluster',
                'api_service': 'weather-forecast-staging-api',
                'frontend_service': 'weather-forecast-staging-frontend',
                'alb_arn_suffix': None,
                'sns_topic': None
            },
            'prod': {
                'cluster_name': 'weather-forecast-prod-cluster',
                'api_service': 'weather-forecast-prod-api',
                'frontend_service': 'weather-forecast-prod-frontend',
                'alb_arn_suffix': None,
                'sns_topic': None
            }
        }
        
        if self.environment not in configs:
            raise ValueError(f"Unknown environment: {self.environment}")
            
        return configs[self.environment]
    
    def setup_enhanced_monitoring(self):
        """Setup enhanced monitoring for the deployment period."""
        print(f"Setting up enhanced monitoring for {self.environment} environment...")
        
        # Create temporary high-frequency alarms
        self._create_deployment_alarms()
        
        # Setup deployment dashboard
        self._create_deployment_dashboard()
        
        # Send notification about monitoring setup
        self._send_monitoring_notification()
        
        print(f"Enhanced monitoring active for {self.duration_minutes} minutes")
        
    def _create_deployment_alarms(self):
        """Create temporary deployment-specific alarms."""
        alarms = [
            {
                'name': f'{self.environment}-deployment-high-errors',
                'metric_name': 'HTTPCode_Target_5XX_Count',
                'namespace': 'AWS/ApplicationELB',
                'threshold': 5,
                'comparison': 'GreaterThanThreshold',
                'period': 60,  # 1 minute
                'evaluation_periods': 2,
                'description': 'High error rate during deployment window'
            },
            {
                'name': f'{self.environment}-deployment-high-latency',
                'metric_name': 'TargetResponseTime',
                'namespace': 'AWS/ApplicationELB',
                'threshold': 5.0,
                'comparison': 'GreaterThanThreshold',
                'period': 60,
                'evaluation_periods': 3,
                'description': 'High response time during deployment window'
            },
            {
                'name': f'{self.environment}-deployment-unhealthy-targets',
                'metric_name': 'UnHealthyHostCount',
                'namespace': 'AWS/ApplicationELB',
                'threshold': 0,
                'comparison': 'GreaterThanThreshold',
                'period': 60,
                'evaluation_periods': 1,
                'description': 'Unhealthy targets detected during deployment'
            },
            {
                'name': f'{self.environment}-deployment-cpu-spike',
                'metric_name': 'CPUUtilization',
                'namespace': 'AWS/ECS',
                'threshold': 90,
                'comparison': 'GreaterThanThreshold',
                'period': 60,
                'evaluation_periods': 2,
                'description': 'CPU spike during deployment window'
            }
        ]
        
        for alarm_config in alarms:
            try:
                self._create_alarm(alarm_config)
                print(f"Created alarm: {alarm_config['name']}")
            except Exception as e:
                print(f"Failed to create alarm {alarm_config['name']}: {e}")
    
    def _create_alarm(self, config: Dict):
        """Create a CloudWatch alarm."""
        dimensions = []
        
        if config['namespace'] == 'AWS/ApplicationELB':
            # Get ALB ARN suffix (would need to be configured or discovered)
            pass
        elif config['namespace'] == 'AWS/ECS':
            dimensions = [
                {'Name': 'ServiceName', 'Value': self.config['api_service']},
                {'Name': 'ClusterName', 'Value': self.config['cluster_name']}
            ]
        
        self.cloudwatch.put_metric_alarm(
            AlarmName=config['name'],
            ComparisonOperator=config['comparison'],
            EvaluationPeriods=config['evaluation_periods'],
            MetricName=config['metric_name'],
            Namespace=config['namespace'],
            Period=config['period'],
            Statistic='Average',
            Threshold=config['threshold'],
            ActionsEnabled=True,
            AlarmActions=[],  # Would include SNS topic ARN
            AlarmDescription=config['description'],
            Dimensions=dimensions,
            Unit='None'
        )
    
    def _create_deployment_dashboard(self):
        """Create a temporary dashboard for deployment monitoring."""
        dashboard_name = f"Deployment-{self.environment}-{int(time.time())}"
        
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            ["AWS/ApplicationELB", "RequestCount"],
                            ["AWS/ApplicationELB", "TargetResponseTime"],
                            ["AWS/ApplicationELB", "HTTPCode_Target_2XX_Count"],
                            ["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count"],
                            ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count"]
                        ],
                        "period": 60,
                        "stat": "Sum",
                        "region": "us-east-1",
                        "title": "Load Balancer Metrics"
                    }
                },
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            ["AWS/ECS", "CPUUtilization", "ServiceName", self.config['api_service']],
                            ["AWS/ECS", "MemoryUtilization", "ServiceName", self.config['api_service']]
                        ],
                        "period": 60,
                        "stat": "Average",
                        "region": "us-east-1",
                        "title": "ECS Service Metrics"
                    }
                }
            ]
        }
        
        try:
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            print(f"Created deployment dashboard: {dashboard_name}")
        except Exception as e:
            print(f"Failed to create dashboard: {e}")
    
    def _send_monitoring_notification(self):
        """Send notification about monitoring setup."""
        message = f"""
Deployment Monitoring Active

Environment: {self.environment}
Duration: {self.duration_minutes} minutes
Started: {datetime.now().isoformat()}

Enhanced monitoring includes:
- High-frequency error rate monitoring
- Response time tracking
- Target health monitoring
- Resource utilization alerts

The monitoring will automatically scale back after the specified duration.
"""
        
        print("Monitoring notification:")
        print(message)
        
        # Would send to SNS topic if configured
        # self.sns.publish(TopicArn=topic_arn, Message=message)
    
    def monitor_deployment(self):
        """Monitor deployment for the specified duration."""
        start_time = time.time()
        end_time = start_time + (self.duration_minutes * 60)
        
        print(f"Monitoring deployment for {self.duration_minutes} minutes...")
        
        while time.time() < end_time:
            remaining = int((end_time - time.time()) / 60)
            print(f"Monitoring active - {remaining} minutes remaining")
            
            # Check deployment health
            self._check_deployment_health()
            
            # Wait before next check
            time.sleep(60)  # Check every minute
        
        print("Monitoring period completed")
        self._cleanup_monitoring()
    
    def _check_deployment_health(self):
        """Check current deployment health."""
        try:
            # Get recent metrics
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=5)
            
            # Check error rate
            error_metrics = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ApplicationELB',
                MetricName='HTTPCode_Target_5XX_Count',
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            if error_metrics['Datapoints']:
                latest_errors = error_metrics['Datapoints'][-1]['Sum']
                if latest_errors > 10:
                    print(f"WARNING: High error count detected: {latest_errors}")
            
            # Check response time
            latency_metrics = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ApplicationELB',
                MetricName='TargetResponseTime',
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            if latency_metrics['Datapoints']:
                latest_latency = latency_metrics['Datapoints'][-1]['Average']
                if latest_latency > 5.0:
                    print(f"WARNING: High response time detected: {latest_latency:.2f}s")
            
        except Exception as e:
            print(f"Error checking deployment health: {e}")
    
    def _cleanup_monitoring(self):
        """Clean up temporary monitoring resources."""
        print("Cleaning up deployment monitoring...")
        
        # Delete temporary alarms
        alarm_names = [
            f'{self.environment}-deployment-high-errors',
            f'{self.environment}-deployment-high-latency',
            f'{self.environment}-deployment-unhealthy-targets',
            f'{self.environment}-deployment-cpu-spike'
        ]
        
        for alarm_name in alarm_names:
            try:
                self.cloudwatch.delete_alarms(AlarmNames=[alarm_name])
                print(f"Deleted alarm: {alarm_name}")
            except Exception as e:
                print(f"Failed to delete alarm {alarm_name}: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Setup deployment monitoring')
    parser.add_argument('--environment', '-e', required=True,
                       choices=['dev', 'staging', 'prod'],
                       help='Environment to monitor')
    parser.add_argument('--duration', '-d', default='30m',
                       help='Monitoring duration (e.g., 30m, 1h)')
    
    args = parser.parse_args()
    
    # Parse duration
    duration_str = args.duration.lower()
    if duration_str.endswith('m'):
        duration_minutes = int(duration_str[:-1])
    elif duration_str.endswith('h'):
        duration_minutes = int(duration_str[:-1]) * 60
    else:
        duration_minutes = int(duration_str)
    
    # Create and run monitor
    monitor = DeploymentMonitor(args.environment, duration_minutes)
    monitor.setup_enhanced_monitoring()
    
    if '--monitor' in sys.argv:
        monitor.monitor_deployment()


if __name__ == '__main__':
    main()