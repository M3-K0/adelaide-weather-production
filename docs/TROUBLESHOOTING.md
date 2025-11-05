# Adelaide Weather Forecasting System - Troubleshooting Guide

## Overview

This comprehensive troubleshooting guide covers common issues, solutions, and diagnostic procedures for the Adelaide Weather Forecasting System. It includes troubleshooting for all major components including the new FAISS health monitoring, environment configuration management, secure credential management, and configuration drift detection.

## 🚨 Quick Diagnostic Commands

### System Health Check
```bash
# Overall system health
curl http://localhost:8000/health

# Detailed health report
curl http://localhost:8000/health/detailed

# FAISS-specific health
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/health/faiss

# Check all dependencies
curl http://localhost:8000/health/dependencies
```

### Deployment Status
```bash
# Check deployment logs
tail -f deploy-{environment}-{timestamp}.log

# Service status
docker-compose ps

# Service logs
docker-compose logs api
docker-compose logs frontend
```

### Configuration Validation
```bash
# Validate environment configuration
python3 -c "from core import EnvironmentConfigManager; EnvironmentConfigManager().load_config()"

# Check credential manager
python3 demo_credential_manager.py

# Check configuration drift
python3 demo_config_drift_detector.py
```

## 🔧 Deployment Issues

### Issue: Deployment Script Fails

#### Symptoms
- `./deploy.sh` exits with error
- Services fail to start
- Health checks timeout

#### Diagnosis
```bash
# Check deployment logs
cat deploy-{environment}-{timestamp}.log

# Check system requirements
./deploy.sh --help

# Verify Docker status
docker info
docker-compose --version
```

#### Solutions

**Docker Issues**
```bash
# Restart Docker daemon
sudo systemctl restart docker

# Clean up Docker resources
docker system prune -f
docker volume prune -f

# Check Docker permissions
sudo usermod -aG docker $USER
# Log out and back in
```

**Configuration Issues**
```bash
# Validate configuration files
python3 -c "
from core.environment_config_manager import EnvironmentConfigManager
try:
    manager = EnvironmentConfigManager(environment='$ENVIRONMENT')
    config = manager.load_config()
    print('✅ Configuration valid')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"
```

**Environment Variable Issues**
```bash
# Check required variables
echo "Environment: $ENVIRONMENT"
echo "API Token: ${API_TOKEN:0:10}..."
echo "Master Key: ${ADELAIDE_WEATHER_MASTER_KEY:+SET}"

# Set missing variables
export ENVIRONMENT="development"
export API_TOKEN="your-secure-token"
export ADELAIDE_WEATHER_MASTER_KEY="your-master-key"
```

### Issue: Services Won't Start

#### Symptoms
- Docker containers exit immediately
- Services show as "unhealthy"
- Port binding errors

#### Diagnosis
```bash
# Check container status
docker-compose ps

# Check container logs
docker-compose logs api --tail=50
docker-compose logs frontend --tail=50

# Check port usage
netstat -tlnp | grep :8000
netstat -tlnp | grep :3000
```

#### Solutions

**Port Conflicts**
```bash
# Kill processes using required ports
sudo lsof -ti:8000 | xargs sudo kill -9
sudo lsof -ti:3000 | xargs sudo kill -9

# Use different ports if needed
export API_PORT=8001
export FRONTEND_PORT=3001
```

**Resource Issues**
```bash
# Check available resources
free -h
df -h

# Clean up Docker resources
docker system prune -f
docker image prune -a -f
```

**Image Build Issues**
```bash
# Rebuild images
docker-compose build --no-cache api
docker-compose build --no-cache frontend

# Pull base images
docker pull python:3.11-slim
docker pull node:18-alpine
```

### Issue: Health Checks Fail

#### Symptoms
- `/health` endpoint returns 503
- Services marked as unhealthy
- Load balancer shows unhealthy targets

#### Diagnosis
```bash
# Test health endpoints
curl -v http://localhost:8000/health
curl -v http://localhost:8000/health/live
curl -v http://localhost:8000/health/ready

# Check service logs
docker-compose logs api | grep -i health
```

#### Solutions

**API Health Issues**
```bash
# Restart API service
docker-compose restart api

# Check API dependencies
curl http://localhost:8000/health/dependencies

# Validate startup system
python3 run_startup_validation.py
```

**Database Connection Issues**
```bash
# Check Redis connectivity (if using Redis)
docker-compose exec redis redis-cli ping

# Test file system access
docker-compose exec api ls -la /app/indices/
docker-compose exec api ls -la /app/embeddings/
```

## 🧠 FAISS Issues

### Issue: FAISS Health Monitoring Fails

#### Symptoms
- `/health/faiss` returns errors
- FAISS queries timing out
- Index loading failures

#### Diagnosis
```bash
# Check FAISS health
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/health/faiss

# Test FAISS integration
python3 test_faiss_monitoring_integration.py

# Check FAISS files
ls -la indices/
ls -la embeddings/
```

#### Solutions

**Missing FAISS Indices**
```bash
# Rebuild FAISS indices
python3 scripts/build_indices.py

# Validate FAISS files
python3 scripts/validate_embeddings.py

# Check permissions
chmod -R 755 indices/
chmod -R 755 embeddings/
```

**FAISS Performance Issues**
```bash
# Check FAISS metrics
curl http://localhost:8000/metrics | grep faiss

# Monitor query performance
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/health/performance

# Restart FAISS monitoring
docker-compose restart api
```

**Memory Issues**
```bash
# Check memory usage
docker stats

# Reduce FAISS parameters
# Edit configs/model.yaml
# Reduce embedding_dim or batch_size
```

### Issue: FAISS Query Errors

#### Symptoms
- Forecast requests failing
- High FAISS error rates
- Query timeout errors

#### Diagnosis
```bash
# Check FAISS error rates
curl http://localhost:8000/metrics | grep faiss_query_errors

# Test individual FAISS queries
python3 -c "
from api.services.faiss_health_monitoring import FAISSHealthMonitor
import asyncio

async def test():
    monitor = FAISSHealthMonitor()
    await monitor.start_monitoring()
    health = await monitor.get_health_summary()
    print(health)

asyncio.run(test())
"
```

#### Solutions

**Index Corruption**
```bash
# Rebuild corrupted indices
rm -rf indices/*.index
python3 scripts/build_indices.py

# Validate rebuilt indices
python3 test_faiss_monitoring_integration.py
```

**Configuration Issues**
```bash
# Check FAISS configuration
cat configs/model.yaml | grep -A10 faiss

# Reset to default FAISS settings
# Edit configs/environments/$ENVIRONMENT/model.yaml
```

## ⚙️ Configuration Issues

### Issue: Environment Configuration Problems

#### Symptoms
- Configuration validation fails
- Wrong environment settings loaded
- Missing configuration values

#### Diagnosis
```bash
# Check environment detection
python3 -c "
from core.environment_config_manager import EnvironmentConfigManager
manager = EnvironmentConfigManager()
print(f'Detected environment: {manager.get_environment().value}')
"

# Check configuration loading
python3 -c "
from core import EnvironmentConfigManager
manager = EnvironmentConfigManager()
try:
    config = manager.load_config()
    metadata = manager.get_metadata()
    print(f'Config loaded successfully')
    print(f'Files loaded: {len(metadata.config_files_loaded)}')
    print(f'Config hash: {metadata.config_hash}')
except Exception as e:
    print(f'Configuration error: {e}')
"
```

#### Solutions

**Environment Detection Issues**
```bash
# Set environment explicitly
export ENVIRONMENT="production"
# or
export ENV="development"
# or
export STAGE="staging"

# Verify environment variables
env | grep -E "(ENVIRONMENT|ENV|STAGE|NODE_ENV)"
```

**Configuration File Issues**
```bash
# Check configuration file syntax
python3 -c "
import yaml
with open('configs/data.yaml') as f:
    data = yaml.safe_load(f)
print('✅ configs/data.yaml syntax valid')
"

# Validate environment-specific configs
ls -la configs/environments/$ENVIRONMENT/
```

**Configuration Override Issues**
```bash
# Check environment variable overrides
env | grep ADELAIDE_

# Test configuration access
python3 -c "
from core import EnvironmentConfigManager
manager = EnvironmentConfigManager()
config = manager.load_config()
print(f'Adelaide lat: {manager.get(\"adelaide.lat\")}')
print(f'Embedding dim: {manager.get(\"encoder.embedding_dim\")}')
"
```

### Issue: Configuration Drift Detection Problems

#### Symptoms
- Drift detector not running
- False positive drift alerts
- Missing drift events

#### Diagnosis
```bash
# Test drift detector
python3 demo_config_drift_detector.py

# Check drift detection manually
python3 -c "
from core.config_drift_detector import ConfigurationDriftDetector
from pathlib import Path

detector = ConfigurationDriftDetector(
    project_root=Path('.'),
    enable_real_time=False
)
detector.start_monitoring()
events = detector.detect_drift()
print(f'Drift events detected: {len(events)}')
for event in events:
    print(f'  - {event.severity.name}: {event.description}')
"
```

#### Solutions

**Drift Detector Not Starting**
```bash
# Check watchdog installation
pip install watchdog

# Check file permissions
ls -la configs/
ls -la docker-compose*.yml
```

**False Positive Alerts**
```bash
# Update baseline after approved changes
python3 -c "
from core.config_drift_detector import ConfigurationDriftDetector
detector = ConfigurationDriftDetector()
detector.update_baseline()
print('Baseline updated')
"

# Resolve known events
python3 -c "
from core.config_drift_detector import ConfigurationDriftDetector
detector = ConfigurationDriftDetector()
# Get event IDs from previous detection
events = detector.detect_drift()
for event in events:
    detector.resolve_drift_event(
        event_id=event.event_id,
        resolution_notes='Approved configuration change'
    )
"
```

## 🔐 Security & Credential Issues

### Issue: Credential Management Problems

#### Symptoms
- Cannot access credentials
- Credential decryption fails
- Master key errors

#### Diagnosis
```bash
# Check master key
echo "Master key status: ${ADELAIDE_WEATHER_MASTER_KEY:+SET}"

# Test credential manager
python3 demo_credential_manager.py

# Check credential storage
ls -la ~/.adelaide-weather/credentials/$ENVIRONMENT/
```

#### Solutions

**Master Key Issues**
```bash
# Set master key
export ADELAIDE_WEATHER_MASTER_KEY="your-secure-master-key"

# Verify key format (should be base64-like string)
echo $ADELAIDE_WEATHER_MASTER_KEY | wc -c  # Should be reasonable length
```

**Credential Storage Issues**
```bash
# Check permissions
ls -la ~/.adelaide-weather/
chmod 700 ~/.adelaide-weather/
chmod -R 600 ~/.adelaide-weather/credentials/

# Reinitialize credential manager
python3 -c "
from core.secure_credential_manager import SecureCredentialManager
manager = SecureCredentialManager(environment='development')
print(manager.health_check())
"
```

**Credential Access Issues**
```bash
# Test credential operations
python3 -c "
from core.secure_credential_manager import SecureCredentialManager, CredentialType, SecurityLevel

manager = SecureCredentialManager(environment='development')

# Store test credential
manager.store_credential(
    credential_id='test_key',
    credential_value='test_value',
    credential_type=CredentialType.API_KEY,
    security_level=SecurityLevel.STANDARD
)

# Retrieve test credential
with manager.secure_context('test_key') as value:
    print(f'Retrieved: {value}')

# Clean up
manager.delete_credential('test_key')
print('Credential test completed successfully')
"
```

### Issue: API Authentication Problems

#### Symptoms
- 401 Unauthorized errors
- Token validation failures
- Rate limiting issues

#### Diagnosis
```bash
# Test API authentication
curl -H "Authorization: Bearer $API_TOKEN" http://localhost:8000/forecast?horizon=6h&vars=t2m

# Check token format
echo "Token: ${API_TOKEN:0:20}..."

# Check rate limiting
curl -v http://localhost:8000/health 2>&1 | grep -i "x-ratelimit"
```

#### Solutions

**Invalid Token Format**
```bash
# Set proper API token
export API_TOKEN="your-secure-alphanumeric-token"

# Token should be 8-128 characters, alphanumeric + limited special chars
```

**Rate Limiting Issues**
```bash
# Check rate limit configuration
grep -r "rate_limit" configs/

# Wait for rate limit reset or increase limits
# Edit environment configuration to increase rate limits
```

## 🌐 Network & Connectivity Issues

### Issue: Service Communication Problems

#### Symptoms
- Services can't communicate
- External API calls fail
- Proxy configuration issues

#### Diagnosis
```bash
# Check network connectivity
docker network ls
docker network inspect adelaide-weather-final_default

# Test internal service communication
docker-compose exec api ping frontend
docker-compose exec frontend ping api

# Check external connectivity
docker-compose exec api curl -I https://google.com
```

#### Solutions

**Internal Network Issues**
```bash
# Recreate network
docker-compose down
docker network prune
docker-compose up -d

# Check service naming
docker-compose ps
```

**External Connectivity Issues**
```bash
# Check DNS resolution
docker-compose exec api nslookup google.com

# Check firewall settings
sudo ufw status
sudo iptables -L
```

**Proxy Configuration Issues**
```bash
# Check Nginx configuration (production)
docker-compose exec nginx nginx -t
docker-compose logs nginx

# Reload Nginx configuration
docker-compose exec nginx nginx -s reload
```

### Issue: Port and Service Access Problems

#### Symptoms
- Cannot access services from host
- Port binding errors
- Service not responding

#### Diagnosis
```bash
# Check port bindings
docker-compose ps
netstat -tlnp | grep -E ":(3000|8000|9090|3001)"

# Test local access
curl -v http://localhost:8000/health
curl -v http://localhost:3000
```

#### Solutions

**Port Conflicts**
```bash
# Find processes using ports
sudo lsof -i :8000
sudo lsof -i :3000

# Kill conflicting processes
sudo kill -9 $(sudo lsof -ti:8000)

# Use alternative ports
docker-compose down
export API_PORT=8001
export FRONTEND_PORT=3001
docker-compose up -d
```

**Service Binding Issues**
```bash
# Check service configuration
docker-compose config

# Restart specific services
docker-compose restart api
docker-compose restart frontend
```

## 📊 Performance Issues

### Issue: Slow Response Times

#### Symptoms
- API responses > 100ms
- High CPU/Memory usage
- FAISS queries slow

#### Diagnosis
```bash
# Check performance metrics
curl http://localhost:8000/health/performance

# Monitor resource usage
docker stats

# Check FAISS performance
curl http://localhost:8000/metrics | grep faiss_query_duration
```

#### Solutions

**Resource Optimization**
```bash
# Increase Docker resources
# Edit Docker Desktop settings or adjust compose file

# Optimize configurations
# Reduce batch sizes in configs/environments/$ENVIRONMENT/model.yaml

# Clean up unused resources
docker system prune -f
docker image prune -a -f
```

**FAISS Optimization**
```bash
# Rebuild indices with optimized parameters
python3 scripts/build_indices.py --optimize

# Check index sizes
ls -lh indices/

# Adjust search parameters
# Edit FAISS configuration for faster but less accurate search
```

### Issue: Memory Issues

#### Symptoms
- Out of memory errors
- Container restarts
- System slowdown

#### Diagnosis
```bash
# Check memory usage
free -h
docker stats --no-stream

# Check container memory limits
docker-compose config | grep -A5 -B5 mem_limit
```

#### Solutions

**Increase Memory Allocation**
```bash
# Adjust Docker Compose memory limits
# Edit docker-compose files to increase memory limits

# Reduce memory usage
# Decrease embedding dimensions in model configuration
# Reduce batch sizes
```

**Memory Leak Investigation**
```bash
# Monitor memory over time
while true; do docker stats --no-stream | grep adelaide; sleep 60; done

# Check application logs for memory issues
docker-compose logs api | grep -i memory
```

## 🔄 Recovery Procedures

### Complete System Recovery

#### When System is Completely Broken
```bash
# 1. Stop all services
docker-compose down -v

# 2. Clean up Docker completely
docker system prune -a -f
docker volume prune -f
docker network prune -f

# 3. Reset configuration to known good state
git status
git checkout -- .
git pull origin main

# 4. Restore from backup if available
if [ -f "backups/$ENVIRONMENT/backup-$(date +%Y%m%d)-*.tar.gz" ]; then
    latest_backup=$(ls -t backups/$ENVIRONMENT/backup-*.tar.gz | head -1)
    tar -xzf "$latest_backup"
    echo "Restored from backup: $latest_backup"
fi

# 5. Rebuild everything
./deploy.sh $ENVIRONMENT --force
```

### Service-Specific Recovery

#### API Service Recovery
```bash
# Restart API only
docker-compose restart api

# Rebuild API if needed
docker-compose build --no-cache api
docker-compose up -d api

# Check API logs
docker-compose logs api --tail=100
```

#### Frontend Service Recovery
```bash
# Restart frontend only
docker-compose restart frontend

# Clear frontend cache and rebuild
docker-compose exec frontend rm -rf .next
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

#### Database/Storage Recovery
```bash
# Reset FAISS indices
rm -rf indices/*.index
python3 scripts/build_indices.py

# Reset credential storage (careful!)
rm -rf ~/.adelaide-weather/credentials/$ENVIRONMENT/
python3 demo_credential_manager.py  # Reinitialize
```

## 📞 Getting Help

### Diagnostic Information to Collect

When reporting issues, please collect:

```bash
# System information
uname -a
docker --version
docker-compose --version
python3 --version

# Service status
docker-compose ps
docker-compose logs --tail=50

# Configuration status
python3 -c "
from core import EnvironmentConfigManager
try:
    manager = EnvironmentConfigManager()
    config = manager.load_config()
    metadata = manager.get_metadata()
    print(f'Environment: {manager.get_environment().value}')
    print(f'Config files: {len(metadata.config_files_loaded)}')
    print(f'Config hash: {metadata.config_hash}')
except Exception as e:
    print(f'Error: {e}')
"

# Health status
curl -s http://localhost:8000/health/detailed | jq '.'
```

### Log Locations

```bash
# Deployment logs
ls -la deploy-*-*.log

# Application logs
docker-compose logs api
docker-compose logs frontend
docker-compose logs nginx  # production only

# System validation logs
cat startup_validation.log

# Configuration logs included in health reports
curl http://localhost:8000/health/detailed
```

### Support Contacts

For issues that cannot be resolved using this guide:

1. **Check existing documentation**:
   - README.md for quick start
   - docs/CONFIGURATION_MANAGEMENT.md for config issues
   - docs/SECURE_CREDENTIAL_MANAGEMENT.md for security issues

2. **Review component-specific documentation**:
   - FAISS_HEALTH_MONITORING_IMPLEMENTATION.md
   - ENVIRONMENT_CONFIG_MANAGER_README.md
   - CONFIG_DRIFT_DETECTOR_README.md
   - CREDENTIAL_MANAGER_IMPLEMENTATION_SUMMARY.md

3. **Submit issues with diagnostic information** collected using the commands above

---

**Adelaide Weather Forecasting System - Troubleshooting Guide**  
*Comprehensive troubleshooting for reliable weather predictions*

**Last Updated**: November 2, 2025  
**Version**: 1.0.0 - Complete System Coverage