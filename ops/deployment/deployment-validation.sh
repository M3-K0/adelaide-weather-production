#!/bin/bash

# Deployment Validation Script for Adelaide Weather Forecast
# Comprehensive validation of deployments across all environments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TIMEOUT="${VALIDATION_TIMEOUT:-300}"  # 5 minutes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage function
usage() {
    cat << EOF
Deployment Validation for Adelaide Weather Forecast

Usage: $0 [OPTIONS] [VALIDATION_TYPE]

VALIDATION_TYPE:
    health          Basic health checks (default)
    performance     Performance validation
    security        Security validation
    integration     Integration tests
    full            Complete validation suite
    smoke           Quick smoke tests

OPTIONS:
    --environment <env>       Environment to validate (staging|production)
    --namespace <ns>          Kubernetes namespace
    --url <url>              Base URL for testing (auto-detected if not provided)
    --timeout <seconds>       Validation timeout [default: 300]
    --load-test              Include load testing
    --report-file <file>     Generate validation report
    --json-output            Output results in JSON format
    --verbose                Verbose output
    --help                   Show this help message

EXAMPLES:
    $0 health --environment production
    $0 performance --url https://adelaide-weather.com --load-test
    $0 full --environment staging --report-file validation-report.json
    $0 smoke --namespace adelaide-weather-staging

ENVIRONMENT VARIABLES:
    VALIDATION_TIMEOUT       Validation timeout in seconds
    API_BASE_URL            Base URL for API testing
    LOAD_TEST_DURATION      Load test duration in seconds
EOF
}

# Parse command line arguments
parse_args() {
    VALIDATION_TYPE="health"
    ENVIRONMENT=""
    NAMESPACE=""
    BASE_URL=""
    LOAD_TEST=false
    REPORT_FILE=""
    JSON_OUTPUT=false
    VERBOSE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            health|performance|security|integration|full|smoke)
                VALIDATION_TYPE="$1"
                shift
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --url)
                BASE_URL="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --load-test)
                LOAD_TEST=true
                shift
                ;;
            --report-file)
                REPORT_FILE="$2"
                shift 2
                ;;
            --json-output)
                JSON_OUTPUT=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown argument: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Set default namespace based on environment
    if [[ -z "$NAMESPACE" && -n "$ENVIRONMENT" ]]; then
        NAMESPACE="adelaide-weather-$ENVIRONMENT"
    fi
}

# Initialize validation results
init_results() {
    declare -g VALIDATION_RESULTS=()
    declare -g VALIDATION_START_TIME=$(date +%s)
    declare -g TOTAL_TESTS=0
    declare -g PASSED_TESTS=0
    declare -g FAILED_TESTS=0
    declare -g WARNING_TESTS=0
}

# Add test result
add_result() {
    local test_name="$1"
    local status="$2"  # PASS, FAIL, WARNING
    local message="$3"
    local details="${4:-}"
    
    VALIDATION_RESULTS+=("{
        \"test_name\": \"$test_name\",
        \"status\": \"$status\",
        \"message\": \"$message\",
        \"details\": \"$details\",
        \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
    }")
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    case "$status" in
        PASS)
            PASSED_TESTS=$((PASSED_TESTS + 1))
            if [[ "$VERBOSE" == "true" || "$JSON_OUTPUT" == "false" ]]; then
                log_success "$test_name: $message"
            fi
            ;;
        FAIL)
            FAILED_TESTS=$((FAILED_TESTS + 1))
            log_error "$test_name: $message"
            if [[ -n "$details" ]]; then
                log_error "Details: $details"
            fi
            ;;
        WARNING)
            WARNING_TESTS=$((WARNING_TESTS + 1))
            log_warning "$test_name: $message"
            if [[ -n "$details" ]]; then
                log_warning "Details: $details"
            fi
            ;;
    esac
}

# Detect environment configuration
detect_environment() {
    log_info "Detecting environment configuration..."
    
    if [[ -z "$NAMESPACE" ]]; then
        NAMESPACE="default"
        log_warning "No namespace specified, using default"
    fi
    
    if [[ -z "$BASE_URL" ]]; then
        # Try to detect from ingress
        local ingress_host
        ingress_host=$(kubectl get ingress -n "$NAMESPACE" \
            -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
        
        if [[ -n "$ingress_host" ]]; then
            BASE_URL="https://$ingress_host"
            log_info "Detected base URL: $BASE_URL"
        else
            log_warning "Could not auto-detect base URL"
        fi
    fi
    
    log_info "Environment: ${ENVIRONMENT:-auto-detected}"
    log_info "Namespace: $NAMESPACE"
    log_info "Base URL: ${BASE_URL:-not specified}"
}

# Kubernetes connectivity validation
validate_k8s_connectivity() {
    log_info "Validating Kubernetes connectivity..."
    
    if kubectl cluster-info &> /dev/null; then
        add_result "k8s_connectivity" "PASS" "Kubernetes cluster is accessible"
    else
        add_result "k8s_connectivity" "FAIL" "Cannot connect to Kubernetes cluster"
        return 1
    fi
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        add_result "namespace_exists" "PASS" "Namespace '$NAMESPACE' exists"
    else
        add_result "namespace_exists" "FAIL" "Namespace '$NAMESPACE' does not exist"
        return 1
    fi
}

# Deployment health validation
validate_deployment_health() {
    log_info "Validating deployment health..."
    
    local deployments
    deployments=$(kubectl get deployments -n "$NAMESPACE" -l app=adelaide-weather \
        --no-headers 2>/dev/null | wc -l)
    
    if [[ "$deployments" -eq 0 ]]; then
        add_result "deployments_exist" "FAIL" "No Adelaide Weather deployments found"
        return 1
    fi
    
    add_result "deployments_exist" "PASS" "Found $deployments Adelaide Weather deployments"
    
    # Check each deployment
    while IFS= read -r deployment; do
        local name ready_replicas desired_replicas
        name=$(echo "$deployment" | awk '{print $1}')
        ready_replicas=$(echo "$deployment" | awk '{print $2}' | cut -d'/' -f1)
        desired_replicas=$(echo "$deployment" | awk '{print $2}' | cut -d'/' -f2)
        
        if [[ "$ready_replicas" -eq "$desired_replicas" && "$ready_replicas" -gt 0 ]]; then
            add_result "deployment_$name" "PASS" "All replicas ready ($ready_replicas/$desired_replicas)"
        else
            add_result "deployment_$name" "FAIL" "Not all replicas ready ($ready_replicas/$desired_replicas)"
        fi
    done < <(kubectl get deployments -n "$NAMESPACE" -l app=adelaide-weather --no-headers 2>/dev/null)
}

# Pod health validation
validate_pod_health() {
    log_info "Validating pod health..."
    
    local running_pods not_running_pods
    running_pods=$(kubectl get pods -n "$NAMESPACE" -l app=adelaide-weather \
        --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
    not_running_pods=$(kubectl get pods -n "$NAMESPACE" -l app=adelaide-weather \
        --field-selector=status.phase!=Running --no-headers 2>/dev/null | wc -l)
    
    if [[ "$running_pods" -gt 0 && "$not_running_pods" -eq 0 ]]; then
        add_result "pod_health" "PASS" "$running_pods pods running, $not_running_pods not running"
    elif [[ "$running_pods" -gt 0 && "$not_running_pods" -gt 0 ]]; then
        add_result "pod_health" "WARNING" "$running_pods pods running, $not_running_pods not running"
    else
        add_result "pod_health" "FAIL" "No pods are running"
    fi
    
    # Check for restart counts
    local high_restart_pods
    high_restart_pods=$(kubectl get pods -n "$NAMESPACE" -l app=adelaide-weather \
        --no-headers 2>/dev/null | awk '$4 > 5 {print $1}' || echo "")
    
    if [[ -n "$high_restart_pods" ]]; then
        add_result "pod_restarts" "WARNING" "Pods with high restart counts found" "$high_restart_pods"
    else
        add_result "pod_restarts" "PASS" "No pods with excessive restarts"
    fi
}

# Service validation
validate_services() {
    log_info "Validating services..."
    
    local services
    services=$(kubectl get services -n "$NAMESPACE" -l app=adelaide-weather \
        --no-headers 2>/dev/null | wc -l)
    
    if [[ "$services" -gt 0 ]]; then
        add_result "services_exist" "PASS" "Found $services Adelaide Weather services"
    else
        add_result "services_exist" "FAIL" "No Adelaide Weather services found"
        return 1
    fi
    
    # Check service endpoints
    while IFS= read -r service; do
        local name endpoints
        name=$(echo "$service" | awk '{print $1}')
        endpoints=$(kubectl get endpoints "$name" -n "$NAMESPACE" \
            -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null | wc -w)
        
        if [[ "$endpoints" -gt 0 ]]; then
            add_result "service_$name" "PASS" "Service has $endpoints endpoints"
        else
            add_result "service_$name" "FAIL" "Service has no endpoints"
        fi
    done < <(kubectl get services -n "$NAMESPACE" -l app=adelaide-weather --no-headers 2>/dev/null)
}

# Ingress validation
validate_ingress() {
    log_info "Validating ingress..."
    
    local ingresses
    ingresses=$(kubectl get ingress -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    
    if [[ "$ingresses" -eq 0 ]]; then
        add_result "ingress_exists" "WARNING" "No ingress found"
        return 0
    fi
    
    add_result "ingress_exists" "PASS" "Found $ingresses ingress(es)"
    
    # Check ingress status
    local ingress_ready=0
    while IFS= read -r ingress; do
        local name address
        name=$(echo "$ingress" | awk '{print $1}')
        address=$(echo "$ingress" | awk '{print $4}')
        
        if [[ -n "$address" && "$address" != "<none>" ]]; then
            add_result "ingress_$name" "PASS" "Ingress has address: $address"
            ingress_ready=$((ingress_ready + 1))
        else
            add_result "ingress_$name" "FAIL" "Ingress has no address"
        fi
    done < <(kubectl get ingress -n "$NAMESPACE" --no-headers 2>/dev/null)
}

# Application health checks
validate_application_health() {
    log_info "Validating application health..."
    
    if [[ -z "$BASE_URL" ]]; then
        add_result "app_health" "WARNING" "No base URL available for health check"
        return 0
    fi
    
    # API health check
    local api_url="$BASE_URL/api/health"
    if curl -f -s --max-time 10 "$api_url" > /dev/null 2>&1; then
        add_result "api_health" "PASS" "API health check successful"
    else
        add_result "api_health" "FAIL" "API health check failed"
    fi
    
    # Frontend health check
    local frontend_response
    frontend_response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$BASE_URL" 2>/dev/null || echo "000")
    
    if [[ "$frontend_response" == "200" ]]; then
        add_result "frontend_health" "PASS" "Frontend responding (HTTP $frontend_response)"
    else
        add_result "frontend_health" "FAIL" "Frontend not responding (HTTP $frontend_response)"
    fi
}

# Database connectivity validation
validate_database_connectivity() {
    log_info "Validating database connectivity..."
    
    if [[ -z "$BASE_URL" ]]; then
        add_result "db_connectivity" "WARNING" "No base URL available for database check"
        return 0
    fi
    
    local db_health_url="$BASE_URL/api/health/database"
    local response
    response=$(curl -s --max-time 10 "$db_health_url" 2>/dev/null || echo "")
    
    if echo "$response" | grep -q "healthy"; then
        add_result "db_connectivity" "PASS" "Database connectivity check successful"
    else
        add_result "db_connectivity" "FAIL" "Database connectivity check failed"
    fi
}

# Redis connectivity validation
validate_redis_connectivity() {
    log_info "Validating Redis connectivity..."
    
    if [[ -z "$BASE_URL" ]]; then
        add_result "redis_connectivity" "WARNING" "No base URL available for Redis check"
        return 0
    fi
    
    local redis_health_url="$BASE_URL/api/health/redis"
    local response
    response=$(curl -s --max-time 10 "$redis_health_url" 2>/dev/null || echo "")
    
    if echo "$response" | grep -q "healthy"; then
        add_result "redis_connectivity" "PASS" "Redis connectivity check successful"
    else
        add_result "redis_connectivity" "FAIL" "Redis connectivity check failed"
    fi
}

# Performance validation
validate_performance() {
    log_info "Validating performance..."
    
    if [[ -z "$BASE_URL" ]]; then
        add_result "performance" "WARNING" "No base URL available for performance testing"
        return 0
    fi
    
    # Response time test
    local api_url="$BASE_URL/api/health"
    local response_time
    response_time=$(curl -o /dev/null -s -w '%{time_total}' --max-time 30 "$api_url" 2>/dev/null || echo "30")
    
    # Convert to milliseconds
    local response_time_ms
    response_time_ms=$(echo "$response_time * 1000" | bc 2>/dev/null || echo "30000")
    
    if (( $(echo "$response_time < 1.0" | bc -l 2>/dev/null || echo 0) )); then
        add_result "response_time" "PASS" "API response time: ${response_time_ms}ms"
    elif (( $(echo "$response_time < 2.0" | bc -l 2>/dev/null || echo 0) )); then
        add_result "response_time" "WARNING" "API response time: ${response_time_ms}ms (acceptable but slow)"
    else
        add_result "response_time" "FAIL" "API response time: ${response_time_ms}ms (too slow)"
    fi
}

# Security validation
validate_security() {
    log_info "Validating security..."
    
    # Check for security policies
    local psp_count
    psp_count=$(kubectl get podsecuritypolicy 2>/dev/null | grep -c adelaide-weather || echo "0")
    
    if [[ "$psp_count" -gt 0 ]]; then
        add_result "pod_security_policy" "PASS" "Pod Security Policy found"
    else
        add_result "pod_security_policy" "WARNING" "No Pod Security Policy found"
    fi
    
    # Check network policies
    local netpol_count
    netpol_count=$(kubectl get networkpolicy -n "$NAMESPACE" 2>/dev/null | grep -c adelaide-weather || echo "0")
    
    if [[ "$netpol_count" -gt 0 ]]; then
        add_result "network_policy" "PASS" "Network Policy found"
    else
        add_result "network_policy" "WARNING" "No Network Policy found"
    fi
    
    # Check for non-root containers
    local non_root_violations
    non_root_violations=$(kubectl get pods -n "$NAMESPACE" -l app=adelaide-weather \
        -o jsonpath='{range .items[*]}{.spec.securityContext.runAsUser}{"\n"}{end}' 2>/dev/null | \
        grep -c "^0$" || echo "0")
    
    if [[ "$non_root_violations" -eq 0 ]]; then
        add_result "non_root_containers" "PASS" "All containers running as non-root"
    else
        add_result "non_root_containers" "FAIL" "$non_root_violations containers running as root"
    fi
}

# Integration tests
run_integration_tests() {
    log_info "Running integration tests..."
    
    if [[ -z "$BASE_URL" ]]; then
        add_result "integration_tests" "WARNING" "No base URL available for integration testing"
        return 0
    fi
    
    # Test API endpoints
    local api_endpoints=("health" "forecast" "metrics")
    local passed_endpoints=0
    
    for endpoint in "${api_endpoints[@]}"; do
        local url="$BASE_URL/api/$endpoint"
        if curl -f -s --max-time 10 "$url" > /dev/null 2>&1; then
            passed_endpoints=$((passed_endpoints + 1))
        fi
    done
    
    if [[ "$passed_endpoints" -eq "${#api_endpoints[@]}" ]]; then
        add_result "api_endpoints" "PASS" "All API endpoints responding"
    elif [[ "$passed_endpoints" -gt 0 ]]; then
        add_result "api_endpoints" "WARNING" "$passed_endpoints/${#api_endpoints[@]} API endpoints responding"
    else
        add_result "api_endpoints" "FAIL" "No API endpoints responding"
    fi
}

# Load testing
run_load_test() {
    if [[ "$LOAD_TEST" == "false" ]]; then
        return 0
    fi
    
    log_info "Running load test..."
    
    if [[ -z "$BASE_URL" ]]; then
        add_result "load_test" "WARNING" "No base URL available for load testing"
        return 0
    fi
    
    # Simple load test using curl
    local duration="${LOAD_TEST_DURATION:-60}"
    local concurrent_requests=10
    local success_count=0
    local total_requests=0
    
    log_info "Running $duration second load test with $concurrent_requests concurrent requests..."
    
    # Run load test in background
    local end_time=$(($(date +%s) + duration))
    while [[ $(date +%s) -lt $end_time ]]; do
        for ((i=1; i<=concurrent_requests; i++)); do
            if curl -f -s --max-time 5 "$BASE_URL/api/health" > /dev/null 2>&1; then
                success_count=$((success_count + 1))
            fi
            total_requests=$((total_requests + 1))
        done
        sleep 1
    done
    
    local success_rate=0
    if [[ "$total_requests" -gt 0 ]]; then
        success_rate=$((success_count * 100 / total_requests))
    fi
    
    if [[ "$success_rate" -ge 95 ]]; then
        add_result "load_test" "PASS" "Load test passed: $success_rate% success rate ($success_count/$total_requests)"
    elif [[ "$success_rate" -ge 90 ]]; then
        add_result "load_test" "WARNING" "Load test warning: $success_rate% success rate ($success_count/$total_requests)"
    else
        add_result "load_test" "FAIL" "Load test failed: $success_rate% success rate ($success_count/$total_requests)"
    fi
}

# Generate validation report
generate_report() {
    local end_time=$(date +%s)
    local duration=$((end_time - VALIDATION_START_TIME))
    
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        # Generate JSON report
        cat << EOF
{
    "validation_summary": {
        "environment": "$ENVIRONMENT",
        "namespace": "$NAMESPACE",
        "base_url": "$BASE_URL",
        "validation_type": "$VALIDATION_TYPE",
        "start_time": "$(date -d @$VALIDATION_START_TIME -u +%Y-%m-%dT%H:%M:%SZ)",
        "end_time": "$(date -d @$end_time -u +%Y-%m-%dT%H:%M:%SZ)",
        "duration_seconds": $duration,
        "total_tests": $TOTAL_TESTS,
        "passed_tests": $PASSED_TESTS,
        "failed_tests": $FAILED_TESTS,
        "warning_tests": $WARNING_TESTS,
        "success_rate": $(( TOTAL_TESTS > 0 ? PASSED_TESTS * 100 / TOTAL_TESTS : 0 ))
    },
    "test_results": [
        $(IFS=','; echo "${VALIDATION_RESULTS[*]}")
    ]
}
EOF
    else
        # Generate human-readable report
        echo
        echo "==============================================="
        echo "         DEPLOYMENT VALIDATION REPORT"
        echo "==============================================="
        echo "Environment: $ENVIRONMENT"
        echo "Namespace: $NAMESPACE"
        echo "Base URL: $BASE_URL"
        echo "Validation Type: $VALIDATION_TYPE"
        echo "Duration: ${duration}s"
        echo
        echo "==============================================="
        echo "                   SUMMARY"
        echo "==============================================="
        echo "Total Tests: $TOTAL_TESTS"
        echo "Passed: $PASSED_TESTS"
        echo "Failed: $FAILED_TESTS"
        echo "Warnings: $WARNING_TESTS"
        echo "Success Rate: $(( TOTAL_TESTS > 0 ? PASSED_TESTS * 100 / TOTAL_TESTS : 0 ))%"
        echo
        
        if [[ "$FAILED_TESTS" -gt 0 ]]; then
            echo "❌ VALIDATION FAILED"
        elif [[ "$WARNING_TESTS" -gt 0 ]]; then
            echo "⚠️  VALIDATION PASSED WITH WARNINGS"
        else
            echo "✅ VALIDATION PASSED"
        fi
        echo "==============================================="
    fi
}

# Save report to file
save_report() {
    if [[ -n "$REPORT_FILE" ]]; then
        generate_report > "$REPORT_FILE"
        log_success "Validation report saved to $REPORT_FILE"
    fi
}

# Main validation function
main_validation() {
    case "$VALIDATION_TYPE" in
        health)
            validate_k8s_connectivity
            validate_deployment_health
            validate_pod_health
            validate_services
            validate_ingress
            validate_application_health
            ;;
        performance)
            validate_k8s_connectivity
            validate_application_health
            validate_performance
            run_load_test
            ;;
        security)
            validate_k8s_connectivity
            validate_security
            ;;
        integration)
            validate_k8s_connectivity
            validate_application_health
            validate_database_connectivity
            validate_redis_connectivity
            run_integration_tests
            ;;
        smoke)
            validate_k8s_connectivity
            validate_deployment_health
            validate_application_health
            ;;
        full)
            validate_k8s_connectivity
            validate_deployment_health
            validate_pod_health
            validate_services
            validate_ingress
            validate_application_health
            validate_database_connectivity
            validate_redis_connectivity
            validate_performance
            validate_security
            run_integration_tests
            run_load_test
            ;;
        *)
            log_error "Unknown validation type: $VALIDATION_TYPE"
            exit 1
            ;;
    esac
}

# Main script execution
main() {
    parse_args "$@"
    init_results
    detect_environment
    
    log_info "Starting $VALIDATION_TYPE validation..."
    
    main_validation
    
    save_report
    
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        generate_report
    fi
    
    # Exit with appropriate code
    if [[ "$FAILED_TESTS" -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

# Execute main function with all arguments
main "$@"