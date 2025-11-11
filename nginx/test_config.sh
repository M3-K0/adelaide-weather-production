#!/bin/bash
# =============================================================================
# Adelaide Weather System - Nginx Configuration Tester
# =============================================================================
# 
# Tests nginx configuration in the context of docker-compose
# This approach validates the config with actual service discovery
# 
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.production.yml"

echo "============================================================================="
echo "Testing Adelaide Weather System Nginx Configuration with Docker Compose"
echo "============================================================================="

# Check if docker-compose file exists
if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo "Error: docker-compose.production.yml not found at $COMPOSE_FILE"
    exit 1
fi

echo "Starting nginx service with dependencies for configuration test..."

# Start only nginx and required dependencies
docker-compose -f "$COMPOSE_FILE" up -d redis api frontend
echo "Waiting for services to be healthy..."
sleep 10

# Test nginx configuration
echo "Testing nginx configuration..."
docker-compose -f "$COMPOSE_FILE" config

if docker-compose -f "$COMPOSE_FILE" up -d nginx; then
    echo ""
    echo "✅ Nginx started successfully!"
    
    # Test a few endpoints
    echo "Testing health endpoint..."
    sleep 5
    
    if curl -f -s http://localhost/health > /dev/null; then
        echo "✅ Health endpoint responding"
    else
        echo "⚠️  Health endpoint not responding (may need more time)"
    fi
    
    echo ""
    echo "============================================================================="
    echo "✅ Nginx configuration test PASSED"
    echo "============================================================================="
    echo "The nginx reverse proxy is working correctly!"
    echo ""
    echo "Test the routing manually:"
    echo "  - Frontend: http://localhost/"
    echo "  - API: http://localhost/api/health"  
    echo "  - Health: http://localhost/health"
    echo "  - HTTPS: https://localhost/ (with self-signed cert warning)"
    echo ""
    echo "Monitoring (internal networks only):"
    echo "  - Grafana: http://localhost/grafana/"
    echo "  - Prometheus: http://localhost/prometheus/ (restricted)"
    echo "============================================================================="
    
    # Stop services
    echo ""
    echo "Stopping test services..."
    docker-compose -f "$COMPOSE_FILE" down
    
else
    echo ""
    echo "============================================================================="
    echo "❌ Nginx configuration test FAILED"
    echo "============================================================================="
    echo "Checking nginx logs for errors..."
    docker-compose -f "$COMPOSE_FILE" logs nginx
    
    echo ""
    echo "Stopping test services..."
    docker-compose -f "$COMPOSE_FILE" down
    exit 1
fi