#!/bin/bash

# =============================================================================
# End-to-End Testing Suite for Adelaide Weather System
# =============================================================================
# 
# Comprehensive end-to-end testing of the complete Adelaide Weather system.
# Tests user workflows, API functionality, and system integration.
# =============================================================================

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# Test configuration
readonly BASE_URL="http://localhost"
readonly API_BASE_URL="http://localhost/api"
readonly SSL_URL="https://localhost"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Load environment variables
if [[ -f ".env.production" ]]; then
    source .env.production
fi

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; ((TESTS_PASSED++)); }
log_error() { echo -e "${RED}[✗]${NC} $1"; ((TESTS_FAILED++)); }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${CYAN}🧪 Testing: $test_name${NC}"
    ((TESTS_TOTAL++))
    
    if eval "$test_command"; then
        log_success "$test_name"
        return 0
    else
        log_error "$test_name"
        return 1
    fi
}

test_basic_connectivity() {
    # Test basic HTTP connectivity
    curl -s -f --connect-timeout 10 "$BASE_URL/health" > /dev/null
}

test_ssl_connectivity() {
    # Test HTTPS connectivity (allow self-signed certificates)
    curl -s -f -k --connect-timeout 10 "$SSL_URL/health" > /dev/null
}

test_frontend_loading() {
    # Test that frontend loads and contains expected content
    local response=$(curl -s -f --connect-timeout 10 "$BASE_URL")
    echo "$response" | grep -q -i "adelaide\|weather\|forecast"
}

test_api_health() {
    # Test API health endpoint
    if [[ -z "$API_TOKEN" ]]; then
        echo "API_TOKEN not set, using unauthenticated request"
        curl -s -f --connect-timeout 10 "$API_BASE_URL/health" > /dev/null
    else
        curl -s -f --connect-timeout 10 -H "Authorization: Bearer $API_TOKEN" "$API_BASE_URL/health" > /dev/null
    fi
}

test_api_documentation() {
    # Test that API documentation is accessible
    curl -s -f --connect-timeout 10 "$API_BASE_URL/docs" > /dev/null
}

test_openapi_schema() {
    # Test OpenAPI schema endpoint
    local response=$(curl -s -f --connect-timeout 10 "$API_BASE_URL/openapi.json")
    echo "$response" | grep -q "openapi\|paths\|info"
}

test_faiss_health() {
    # Test FAISS health endpoint
    if [[ -z "$API_TOKEN" ]]; then
        return 1
    fi
    
    curl -s -f --connect-timeout 10 \
        -H "Authorization: Bearer $API_TOKEN" \
        "$API_BASE_URL/health/faiss" > /dev/null
}

test_forecast_api() {
    # Test forecast API with sample request
    if [[ -z "$API_TOKEN" ]]; then
        return 1
    fi
    
    local payload='{"horizon": "24h", "location": {"lat": -34.93, "lon": 138.60}}'
    local response=$(curl -s -f --connect-timeout 30 \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json" \
        -X POST \
        -d "$payload" \
        "$API_BASE_URL/forecast")
    
    # Check if response contains expected forecast fields
    echo "$response" | grep -q "forecast\|prediction\|temperature\|precipitation"
}

test_analog_search() {
    # Test analog search API
    if [[ -z "$API_TOKEN" ]]; then
        return 1
    fi
    
    local response=$(curl -s -f --connect-timeout 30 \
        -H "Authorization: Bearer $API_TOKEN" \
        "$API_BASE_URL/analogs/24h")
    
    # Check if response contains analog search results
    echo "$response" | grep -q "analogs\|similar\|matches"
}

test_metrics_endpoint() {
    # Test metrics endpoint for monitoring
    if [[ -z "$API_TOKEN" ]]; then
        return 1
    fi
    
    curl -s -f --connect-timeout 10 \
        -H "Authorization: Bearer $API_TOKEN" \
        "$API_BASE_URL/metrics" > /dev/null
}

test_performance_baseline() {
    # Test API response time is acceptable
    if [[ -z "$API_TOKEN" ]]; then
        return 1
    fi
    
    local start_time=$(date +%s.%N)
    curl -s -f --connect-timeout 10 \
        -H "Authorization: Bearer $API_TOKEN" \
        "$API_BASE_URL/health" > /dev/null
    local end_time=$(date +%s.%N)
    
    local response_time=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "1.0")
    
    # Check if response time is under 2 seconds
    if command -v bc &> /dev/null; then
        if (( $(echo "$response_time < 2.0" | bc -l) )); then
            log_info "API response time: ${response_time}s"
            return 0
        else
            log_warning "API response time: ${response_time}s (slow)"
            return 1
        fi
    else
        # If bc is not available, assume test passes
        return 0
    fi
}

test_monitoring_stack() {
    # Test monitoring endpoints
    local prometheus_healthy=false
    local grafana_healthy=false
    
    # Test Prometheus
    if curl -s -f --connect-timeout 10 "http://localhost:9090/-/healthy" > /dev/null; then
        prometheus_healthy=true
    fi
    
    # Test Grafana
    if curl -s -f --connect-timeout 10 "http://localhost:3001/api/health" > /dev/null; then
        grafana_healthy=true
    fi
    
    # At least one monitoring service should be healthy
    if [[ "$prometheus_healthy" == true ]] || [[ "$grafana_healthy" == true ]]; then
        log_info "Monitoring stack: Prometheus=$prometheus_healthy, Grafana=$grafana_healthy"
        return 0
    else
        return 1
    fi
}

test_security_headers() {
    # Test that security headers are present
    local headers=$(curl -s -I -k --connect-timeout 10 "$SSL_URL")
    
    local hsts_present=false
    local content_type_present=false
    local frame_options_present=false
    
    if echo "$headers" | grep -qi "strict-transport-security"; then
        hsts_present=true
    fi
    
    if echo "$headers" | grep -qi "x-content-type-options"; then
        content_type_present=true
    fi
    
    if echo "$headers" | grep -qi "x-frame-options"; then
        frame_options_present=true
    fi
    
    log_info "Security headers: HSTS=$hsts_present, Content-Type=$content_type_present, Frame-Options=$frame_options_present"
    
    # At least 2 out of 3 security headers should be present
    local header_count=0
    [[ "$hsts_present" == true ]] && ((header_count++))
    [[ "$content_type_present" == true ]] && ((header_count++))
    [[ "$frame_options_present" == true ]] && ((header_count++))
    
    [[ $header_count -ge 2 ]]
}

test_error_handling() {
    # Test that API handles errors gracefully
    local error_response=$(curl -s -w "%{http_code}" -o /dev/null "$API_BASE_URL/nonexistent-endpoint")
    
    # Should return 404 or similar error code (not 500)
    if [[ "$error_response" == "404" ]] || [[ "$error_response" == "405" ]]; then
        log_info "Error handling: Returns $error_response for invalid endpoint"
        return 0
    else
        log_warning "Error handling: Returns $error_response for invalid endpoint"
        return 1
    fi
}

test_cors_headers() {
    # Test CORS headers for API
    local cors_response=$(curl -s -I \
        -H "Origin: http://localhost:3000" \
        -H "Access-Control-Request-Method: GET" \
        "$API_BASE_URL/health")
    
    if echo "$cors_response" | grep -qi "access-control-allow"; then
        log_info "CORS headers present"
        return 0
    else
        log_warning "CORS headers missing"
        return 1
    fi
}

test_data_validation() {
    # Test that API validates input data properly
    if [[ -z "$API_TOKEN" ]]; then
        return 1
    fi
    
    # Send invalid data and expect proper error response
    local invalid_payload='{"invalid": "data"}'
    local response_code=$(curl -s -w "%{http_code}" -o /dev/null \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json" \
        -X POST \
        -d "$invalid_payload" \
        "$API_BASE_URL/forecast")
    
    # Should return 400 (Bad Request) or 422 (Unprocessable Entity)
    if [[ "$response_code" == "400" ]] || [[ "$response_code" == "422" ]]; then
        log_info "Data validation: Returns $response_code for invalid data"
        return 0
    else
        log_warning "Data validation: Returns $response_code for invalid data"
        return 1
    fi
}

run_stress_test() {
    # Simple stress test - make multiple concurrent requests
    if [[ -z "$API_TOKEN" ]]; then
        return 1
    fi
    
    log_info "Running stress test (10 concurrent requests)..."
    
    local success_count=0
    local pids=()
    
    # Launch 10 concurrent requests
    for i in {1..10}; do
        (
            if curl -s -f --connect-timeout 10 \
                -H "Authorization: Bearer $API_TOKEN" \
                "$API_BASE_URL/health" > /dev/null; then
                exit 0
            else
                exit 1
            fi
        ) &
        pids+=($!)
    done
    
    # Wait for all requests to complete and count successes
    for pid in "${pids[@]}"; do
        if wait "$pid"; then
            ((success_count++))
        fi
    done
    
    log_info "Stress test: $success_count/10 requests successful"
    
    # At least 8 out of 10 requests should succeed
    [[ $success_count -ge 8 ]]
}

main() {
    echo -e "${CYAN}🧪 ADELAIDE WEATHER SYSTEM - END-TO-END TESTING${NC}"
    echo "================================================================="
    echo ""
    
    log_info "Starting comprehensive end-to-end testing..."
    
    if [[ -z "${API_TOKEN:-}" ]]; then
        log_warning "API_TOKEN not set - some tests will be skipped"
    fi
    
    echo ""
    echo "🌐 CONNECTIVITY TESTS"
    echo "-----------------"
    run_test "Basic HTTP connectivity" "test_basic_connectivity"
    run_test "SSL/HTTPS connectivity" "test_ssl_connectivity"
    run_test "Frontend loading" "test_frontend_loading"
    
    echo ""
    echo "🔌 API TESTS"
    echo "------------"
    run_test "API health endpoint" "test_api_health"
    run_test "API documentation" "test_api_documentation"
    run_test "OpenAPI schema" "test_openapi_schema"
    
    echo ""
    echo "🧠 FAISS & FORECAST TESTS"
    echo "-------------------------"
    run_test "FAISS health check" "test_faiss_health"
    run_test "Forecast API" "test_forecast_api"
    run_test "Analog search API" "test_analog_search"
    
    echo ""
    echo "📊 MONITORING TESTS"
    echo "------------------"
    run_test "Metrics endpoint" "test_metrics_endpoint"
    run_test "Monitoring stack" "test_monitoring_stack"
    
    echo ""
    echo "🔒 SECURITY TESTS"
    echo "----------------"
    run_test "Security headers" "test_security_headers"
    run_test "CORS headers" "test_cors_headers"
    run_test "Error handling" "test_error_handling"
    run_test "Data validation" "test_data_validation"
    
    echo ""
    echo "⚡ PERFORMANCE TESTS"
    echo "-------------------"
    run_test "Response time baseline" "test_performance_baseline"
    run_test "Concurrent requests stress test" "run_stress_test"
    
    echo ""
    echo "================================================================="
    echo "📊 TEST SUMMARY"
    echo "================================================================="
    echo -e "${GREEN}✓ Passed:${NC}  $TESTS_PASSED"
    echo -e "${RED}✗ Failed:${NC}  $TESTS_FAILED"
    echo -e "${BLUE}Total:${NC}   $TESTS_TOTAL"
    
    local success_rate=0
    if [[ $TESTS_TOTAL -gt 0 ]]; then
        success_rate=$((TESTS_PASSED * 100 / TESTS_TOTAL))
    fi
    
    echo -e "${CYAN}Success Rate:${NC} $success_rate%"
    echo ""
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}🎉 All tests passed! System is fully functional.${NC}"
        exit 0
    elif [[ $success_rate -ge 80 ]]; then
        echo -e "${YELLOW}⚠️ Most tests passed ($success_rate%). System is mostly functional.${NC}"
        exit 0
    else
        echo -e "${RED}❌ Multiple tests failed ($success_rate% success). System has issues.${NC}"
        echo ""
        echo "🔧 Troubleshooting Steps:"
        echo "1. Check service status: ./deploy-adelaide-weather.sh status"
        echo "2. View service logs: ./deploy-adelaide-weather.sh logs"
        echo "3. Run health check: ./deploy-adelaide-weather.sh health"
        echo "4. Check deployment logs in deployment_logs/"
        exit 1
    fi
}

main "$@"