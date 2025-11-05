#!/bin/bash

# Adelaide Weather Forecasting System - Health Check Script
set -e

echo "🔍 Running health checks for Adelaide Weather Forecasting System"

# Configuration
API_URL=${API_URL:-"http://localhost:8000"}
UI_URL=${UI_URL:-"http://localhost:3000"}
API_TOKEN=${API_TOKEN:-"dev-token-change-in-production"}
TIMEOUT=${TIMEOUT:-30}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if service is responding
check_url() {
    local url=$1
    local name=$2
    
    if curl -f --max-time $TIMEOUT -s "$url" > /dev/null 2>&1; then
        log_info "$name is responding"
        return 0
    else
        log_error "$name is not responding at $url"
        return 1
    fi
}

# Check API health
check_api_health() {
    echo "🔄 Checking API health..."
    
    if check_url "$API_URL/health" "API Health Endpoint"; then
        # Get detailed health info
        health_response=$(curl -s --max-time $TIMEOUT "$API_URL/health" 2>/dev/null || echo '{}')
        status=$(echo "$health_response" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
        
        if [ "$status" = "healthy" ]; then
            log_info "API status: $status"
        else
            log_warn "API status: $status"
        fi
    else
        return 1
    fi
}

# Check API forecast endpoint
check_api_forecast() {
    echo "🔄 Checking API forecast endpoint..."
    
    forecast_url="$API_URL/forecast?horizon=24h&vars=t2m"
    if curl -f --max-time $TIMEOUT -s -H "Authorization: Bearer $API_TOKEN" "$forecast_url" > /dev/null 2>&1; then
        log_info "Forecast endpoint is working"
        
        # Check if response has expected structure
        response=$(curl -s --max-time $TIMEOUT -H "Authorization: Bearer $API_TOKEN" "$forecast_url" 2>/dev/null || echo '{}')
        t2m_value=$(echo "$response" | jq -r '.variables.t2m.value // null' 2>/dev/null || echo "null")
        
        if [ "$t2m_value" != "null" ]; then
            log_info "Forecast data is available (t2m: ${t2m_value}°C)"
        else
            log_warn "Forecast endpoint responding but no t2m data available"
        fi
    else
        log_error "Forecast endpoint failed"
        return 1
    fi
}

# Check API metrics
check_api_metrics() {
    echo "🔄 Checking API metrics endpoint..."
    
    if check_url "$API_URL/metrics" "Metrics Endpoint"; then
        # Check if prometheus metrics are available
        metrics=$(curl -s --max-time $TIMEOUT "$API_URL/metrics" 2>/dev/null || echo "")
        if echo "$metrics" | grep -q "forecast_requests_total"; then
            log_info "Prometheus metrics are available"
        else
            log_warn "Metrics endpoint responding but no forecast metrics found"
        fi
    else
        return 1
    fi
}

# Check UI
check_ui() {
    echo "🔄 Checking UI..."
    
    if check_url "$UI_URL" "UI Frontend"; then
        log_info "Frontend is serving content"
    else
        return 1
    fi
}

# Main health check
main() {
    echo "🚀 Starting health checks at $(date)"
    echo "   API URL: $API_URL"
    echo "   UI URL: $UI_URL"
    echo ""
    
    failures=0
    
    # API checks
    check_api_health || failures=$((failures + 1))
    check_api_forecast || failures=$((failures + 1))
    check_api_metrics || failures=$((failures + 1))
    
    # UI checks
    check_ui || failures=$((failures + 1))
    
    echo ""
    
    if [ $failures -eq 0 ]; then
        log_info "All health checks passed! 🎉"
        exit 0
    else
        log_error "$failures health check(s) failed"
        exit 1
    fi
}

# Run main function
main "$@"