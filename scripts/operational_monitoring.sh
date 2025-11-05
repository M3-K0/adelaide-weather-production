#!/bin/bash
# Adelaide Weather API - Operational Monitoring Script
# Comprehensive health and performance monitoring for operations team

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-weather-forecast-prod}"
API_BASE_URL="${API_BASE_URL:-https://api.adelaide-weather.com}"
MONITORING_INTERVAL="${MONITORING_INTERVAL:-60}"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Thresholds
RESPONSE_TIME_THRESHOLD=${RESPONSE_TIME_THRESHOLD:-0.15}  # 150ms SLA
ERROR_RATE_THRESHOLD=${ERROR_RATE_THRESHOLD:-0.01}        # 1% error rate
MEMORY_THRESHOLD=${MEMORY_THRESHOLD:-400}                 # 400MB memory warning
CPU_THRESHOLD=${CPU_THRESHOLD:-70}                        # 70% CPU warning

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*"
}

# Send alert function
send_alert() {
    local severity="$1"
    local message="$2"
    local details="${3:-}"
    
    if [ -n "$ALERT_WEBHOOK_URL" ]; then
        local alert_data
        alert_data=$(cat << EOF
{
    "severity": "$severity",
    "service": "adelaide-weather-api",
    "message": "$message",
    "details": "$details",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "source": "operational_monitoring"
}
EOF
)
        
        curl -s -X POST "$ALERT_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "$alert_data" || log_warn "Failed to send alert"
    fi
}

# Health check function
check_endpoint_health() {
    local endpoint="$1"
    local description="$2"
    local expected_status="${3:-200}"
    local timeout="${4:-10}"
    
    local response_code response_time start_time end_time
    
    start_time=$(date +%s.%N)
    response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$timeout" "$endpoint" || echo "000")
    end_time=$(date +%s.%N)
    
    response_time=$(echo "$end_time - $start_time" | bc)
    
    if [ "$response_code" = "$expected_status" ]; then
        if (( $(echo "$response_time < $RESPONSE_TIME_THRESHOLD" | bc -l) )); then
            log_success "$description: ${response_code} (${response_time}s)"
        else
            log_warn "$description: ${response_code} (${response_time}s - SLOW)"
            send_alert "warning" "$description response time ${response_time}s exceeds ${RESPONSE_TIME_THRESHOLD}s threshold"
        fi
        return 0
    else
        log_error "$description: ${response_code} (${response_time}s - FAILED)"
        send_alert "high" "$description failed with status $response_code"
        return 1
    fi
}

# Authenticated endpoint check
check_authenticated_endpoint() {
    local endpoint="$1"
    local description="$2"
    
    if [ -z "${API_TOKEN:-}" ]; then
        log_warn "$description: SKIPPED (no API_TOKEN provided)"
        return 0
    fi
    
    local response_code response_time start_time end_time
    
    start_time=$(date +%s.%N)
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $API_TOKEN" \
        --max-time 15 "$endpoint" || echo "000")
    end_time=$(date +%s.%N)
    
    response_time=$(echo "$end_time - $start_time" | bc)
    
    if [ "$response_code" = "200" ]; then
        if (( $(echo "$response_time < $RESPONSE_TIME_THRESHOLD" | bc -l) )); then
            log_success "$description: ${response_code} (${response_time}s)"
        else
            log_warn "$description: ${response_code} (${response_time}s - SLOW)"
        fi
        return 0
    else
        log_error "$description: ${response_code} (${response_time}s - FAILED)"
        send_alert "high" "$description failed with status $response_code"
        return 1
    fi
}

# Kubernetes resource monitoring
check_kubernetes_resources() {
    log_info "Checking Kubernetes resources..."
    
    # Pod status
    local pod_count ready_count
    pod_count=$(kubectl get pods -l app=api -n "$NAMESPACE" --no-headers | wc -l)
    ready_count=$(kubectl get pods -l app=api -n "$NAMESPACE" --no-headers | grep "Running.*1/1" | wc -l)
    
    if [ "$ready_count" -eq "$pod_count" ] && [ "$pod_count" -gt 0 ]; then
        log_success "Pods: $ready_count/$pod_count ready"
    else
        log_error "Pods: $ready_count/$pod_count ready"
        send_alert "high" "Pod readiness issue: $ready_count/$pod_count pods ready"
        
        # Show problematic pods
        kubectl get pods -l app=api -n "$NAMESPACE" | grep -v "Running.*1/1" || true
    fi
    
    # Resource usage
    if kubectl top pods -l app=api -n "$NAMESPACE" --no-headers >/dev/null 2>&1; then
        log_info "Resource usage:"
        
        kubectl get pods -l app=api -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' | \
        while read -r pod; do
            local usage
            usage=$(kubectl top pod "$pod" -n "$NAMESPACE" --no-headers 2>/dev/null || echo "$pod 0m 0Mi")
            
            local cpu_usage memory_usage
            cpu_usage=$(echo "$usage" | awk '{print $2}' | sed 's/m//')
            memory_usage=$(echo "$usage" | awk '{print $3}' | sed 's/Mi//')
            
            if [ "$memory_usage" -gt "$MEMORY_THRESHOLD" ]; then
                log_warn "  $pod: CPU ${cpu_usage}m, Memory ${memory_usage}Mi (HIGH MEMORY)"
                send_alert "warning" "High memory usage on pod $pod: ${memory_usage}Mi"
            elif [ "$cpu_usage" -gt "$((CPU_THRESHOLD * 10))" ]; then  # Convert percentage to milliCPU
                log_warn "  $pod: CPU ${cpu_usage}m, Memory ${memory_usage}Mi (HIGH CPU)"
                send_alert "warning" "High CPU usage on pod $pod: ${cpu_usage}m"
            else
                log_success "  $pod: CPU ${cpu_usage}m, Memory ${memory_usage}Mi"
            fi
        done
    else
        log_warn "Resource usage metrics not available"
    fi
    
    # Deployment status
    local desired_replicas current_replicas
    desired_replicas=$(kubectl get deployment api-deployment -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
    current_replicas=$(kubectl get deployment api-deployment -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
    
    if [ "${current_replicas:-0}" -eq "$desired_replicas" ]; then
        log_success "Deployment: $current_replicas/$desired_replicas replicas ready"
    else
        log_error "Deployment: ${current_replicas:-0}/$desired_replicas replicas ready"
        send_alert "high" "Deployment scaling issue: ${current_replicas:-0}/$desired_replicas replicas ready"
    fi
}

# Performance testing
check_performance() {
    log_info "Performance testing..."
    
    local total_time=0
    local successful_requests=0
    local failed_requests=0
    local test_requests=5
    
    for i in $(seq 1 $test_requests); do
        local start_time end_time duration response_code
        
        start_time=$(date +%s.%N)
        if [ -n "${API_TOKEN:-}" ]; then
            response_code=$(curl -s -o /dev/null -w "%{http_code}" \
                -H "Authorization: Bearer $API_TOKEN" \
                --max-time 10 \
                "$API_BASE_URL/forecast?horizon=24h&vars=t2m" || echo "000")
        else
            response_code=$(curl -s -o /dev/null -w "%{http_code}" \
                --max-time 10 \
                "$API_BASE_URL/health" || echo "000")
        fi
        end_time=$(date +%s.%N)
        
        duration=$(echo "$end_time - $start_time" | bc)
        
        if [ "$response_code" = "200" ]; then
            ((successful_requests++))
            total_time=$(echo "$total_time + $duration" | bc)
        else
            ((failed_requests++))
        fi
    done
    
    # Calculate metrics
    local success_rate avg_response_time
    success_rate=$(echo "scale=3; $successful_requests * 100 / $test_requests" | bc)
    
    if [ "$successful_requests" -gt 0 ]; then
        avg_response_time=$(echo "scale=3; $total_time / $successful_requests" | bc)
    else
        avg_response_time="N/A"
    fi
    
    # Report results
    if [ "$successful_requests" -eq "$test_requests" ]; then
        if (( $(echo "$avg_response_time < $RESPONSE_TIME_THRESHOLD" | bc -l) )); then
            log_success "Performance: ${success_rate}% success, avg ${avg_response_time}s"
        else
            log_warn "Performance: ${success_rate}% success, avg ${avg_response_time}s (SLOW)"
            send_alert "warning" "Performance degradation: average response time ${avg_response_time}s"
        fi
    else
        log_error "Performance: ${success_rate}% success, avg ${avg_response_time}s"
        local error_rate
        error_rate=$(echo "scale=3; $failed_requests * 100 / $test_requests" | bc)
        send_alert "high" "High error rate detected: ${error_rate}% ($failed_requests/$test_requests failed)"
    fi
}

# FAISS health monitoring
check_faiss_health() {
    log_info "Checking FAISS health..."
    
    if [ -z "${API_TOKEN:-}" ]; then
        log_warn "FAISS health check: SKIPPED (no API_TOKEN provided)"
        return 0
    fi
    
    local faiss_response
    faiss_response=$(curl -s -H "Authorization: Bearer $API_TOKEN" \
        --max-time 20 \
        "$API_BASE_URL/health/faiss" || echo '{"error": "request_failed"}')
    
    if echo "$faiss_response" | jq -e '.status' >/dev/null 2>&1; then
        local faiss_status
        faiss_status=$(echo "$faiss_response" | jq -r '.status')
        
        case "$faiss_status" in
            "healthy")
                log_success "FAISS status: $faiss_status"
                ;;
            "degraded")
                log_warn "FAISS status: $faiss_status"
                send_alert "warning" "FAISS system in degraded state"
                ;;
            *)
                log_error "FAISS status: $faiss_status"
                send_alert "high" "FAISS system unhealthy: $faiss_status"
                ;;
        esac
        
        # Check index health if available
        if echo "$faiss_response" | jq -e '.indices' >/dev/null 2>&1; then
            local indices_info
            indices_info=$(echo "$faiss_response" | jq -r '.indices | to_entries[] | "\(.key): \(.value.vectors // "unknown") vectors"')
            log_info "FAISS indices:"
            echo "$indices_info" | while read -r line; do
                log_info "  $line"
            done
        fi
    else
        log_error "FAISS health check failed"
        send_alert "high" "FAISS health endpoint unreachable"
    fi
}

# Security monitoring
check_security_status() {
    log_info "Checking security status..."
    
    # Check for recent authentication failures
    local auth_failures
    auth_failures=$(kubectl logs -l app=api --tail=100 -n "$NAMESPACE" 2>/dev/null | \
        grep "authentication_attempt.*success.*false" | wc -l || echo "0")
    
    if [ "$auth_failures" -gt 10 ]; then
        log_warn "Security: $auth_failures recent authentication failures"
        send_alert "warning" "Elevated authentication failures: $auth_failures in recent logs"
    else
        log_success "Security: $auth_failures recent authentication failures"
    fi
    
    # Check for security violations
    local security_violations
    security_violations=$(kubectl logs -l app=api --tail=100 -n "$NAMESPACE" 2>/dev/null | \
        grep "security_violation" | wc -l || echo "0")
    
    if [ "$security_violations" -gt 0 ]; then
        log_warn "Security: $security_violations security violations detected"
        send_alert "high" "Security violations detected: $security_violations in recent logs"
    else
        log_success "Security: No recent security violations"
    fi
}

# Configuration drift monitoring
check_configuration_drift() {
    log_info "Checking configuration drift..."
    
    # Check if config drift detector is available
    if kubectl get pods -l app=api -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}' >/dev/null 2>&1; then
        local pod_name
        pod_name=$(kubectl get pods -l app=api -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}')
        
        local drift_status
        drift_status=$(kubectl exec "$pod_name" -n "$NAMESPACE" -- python3 -c "
try:
    from core.config_drift_detector import ConfigurationDriftDetector
    detector = ConfigurationDriftDetector()
    report = detector.run_comprehensive_drift_scan()
    
    critical = report.get('critical_issues', 0)
    high = report.get('high_priority_issues', 0)
    
    if critical > 0:
        print(f'CRITICAL:{critical}')
        exit(2)
    elif high > 0:
        print(f'HIGH:{high}')
        exit(1)
    else:
        print('OK:0')
        exit(0)
except Exception as e:
    print(f'ERROR:{e}')
    exit(3)
" 2>/dev/null || echo "ERROR:check_failed")
        
        case "$drift_status" in
            "OK:"*)
                log_success "Configuration: No drift detected"
                ;;
            "HIGH:"*)
                local high_issues
                high_issues=$(echo "$drift_status" | cut -d: -f2)
                log_warn "Configuration: $high_issues high priority drift issues"
                send_alert "warning" "Configuration drift detected: $high_issues high priority issues"
                ;;
            "CRITICAL:"*)
                local critical_issues
                critical_issues=$(echo "$drift_status" | cut -d: -f2)
                log_error "Configuration: $critical_issues critical drift issues"
                send_alert "critical" "Critical configuration drift: $critical_issues issues detected"
                ;;
            *)
                log_warn "Configuration: Drift check failed or unavailable"
                ;;
        esac
    else
        log_warn "Configuration: No pods available for drift checking"
    fi
}

# Comprehensive monitoring check
run_comprehensive_check() {
    log_info "=== Adelaide Weather API Operational Monitoring ==="
    log_info "Timestamp: $(date)"
    log_info "Namespace: $NAMESPACE"
    log_info "API Base URL: $API_BASE_URL"
    echo
    
    local overall_health=0
    
    # Basic health checks
    log_info "=== Basic Health Checks ==="
    check_endpoint_health "$API_BASE_URL/health" "API Health" || ((overall_health++))
    check_endpoint_health "$API_BASE_URL/health/live" "Liveness" || ((overall_health++))
    check_endpoint_health "$API_BASE_URL/health/ready" "Readiness" || ((overall_health++))
    echo
    
    # Authenticated endpoints
    log_info "=== Authenticated Endpoints ==="
    check_authenticated_endpoint "$API_BASE_URL/health/detailed" "Detailed Health" || ((overall_health++))
    check_authenticated_endpoint "$API_BASE_URL/metrics" "Metrics Endpoint" || ((overall_health++))
    echo
    
    # Kubernetes resources
    log_info "=== Kubernetes Resources ==="
    check_kubernetes_resources || ((overall_health++))
    echo
    
    # Performance testing
    log_info "=== Performance Testing ==="
    check_performance || ((overall_health++))
    echo
    
    # FAISS health
    log_info "=== FAISS Health ==="
    check_faiss_health || ((overall_health++))
    echo
    
    # Security monitoring
    log_info "=== Security Monitoring ==="
    check_security_status || ((overall_health++))
    echo
    
    # Configuration drift
    log_info "=== Configuration Monitoring ==="
    check_configuration_drift || ((overall_health++))
    echo
    
    # Overall status
    log_info "=== Overall Status ==="
    if [ "$overall_health" -eq 0 ]; then
        log_success "Overall system health: HEALTHY"
    elif [ "$overall_health" -le 2 ]; then
        log_warn "Overall system health: DEGRADED ($overall_health issues)"
        send_alert "warning" "System health degraded: $overall_health issues detected"
    else
        log_error "Overall system health: UNHEALTHY ($overall_health issues)"
        send_alert "critical" "System unhealthy: $overall_health issues detected"
    fi
    
    return $overall_health
}

# Continuous monitoring mode
continuous_monitoring() {
    log_info "Starting continuous monitoring (interval: ${MONITORING_INTERVAL}s)"
    log_info "Press Ctrl+C to stop"
    
    while true; do
        run_comprehensive_check
        echo
        log_info "Next check in ${MONITORING_INTERVAL}s..."
        sleep "$MONITORING_INTERVAL"
        echo "----------------------------------------"
    done
}

# Quick status check
quick_status() {
    log_info "=== Quick Status Check ==="
    
    # Health check
    if check_endpoint_health "$API_BASE_URL/health" "API Health" >/dev/null 2>&1; then
        echo -e "Health: ${GREEN}✓ OK${NC}"
    else
        echo -e "Health: ${RED}✗ FAILED${NC}"
    fi
    
    # Pod status
    local pod_count ready_count
    pod_count=$(kubectl get pods -l app=api -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l || echo "0")
    ready_count=$(kubectl get pods -l app=api -n "$NAMESPACE" --no-headers 2>/dev/null | grep "Running.*1/1" | wc -l || echo "0")
    
    if [ "$ready_count" -eq "$pod_count" ] && [ "$pod_count" -gt 0 ]; then
        echo -e "Pods: ${GREEN}✓ $ready_count/$pod_count ready${NC}"
    else
        echo -e "Pods: ${RED}✗ $ready_count/$pod_count ready${NC}"
    fi
    
    # Performance check
    local start_time end_time duration
    start_time=$(date +%s.%N)
    if curl -s --max-time 5 "$API_BASE_URL/health" >/dev/null 2>&1; then
        end_time=$(date +%s.%N)
        duration=$(echo "$end_time - $start_time" | bc)
        
        if (( $(echo "$duration < $RESPONSE_TIME_THRESHOLD" | bc -l) )); then
            echo -e "Performance: ${GREEN}✓ ${duration}s${NC}"
        else
            echo -e "Performance: ${YELLOW}⚠ ${duration}s (slow)${NC}"
        fi
    else
        echo -e "Performance: ${RED}✗ Failed${NC}"
    fi
}

# Main function
main() {
    local command="${1:-check}"
    
    case "$command" in
        "check"|"full")
            run_comprehensive_check
            ;;
        "continuous"|"monitor")
            continuous_monitoring
            ;;
        "quick"|"status")
            quick_status
            ;;
        "performance"|"perf")
            log_info "=== Performance Check ==="
            check_performance
            ;;
        "faiss")
            log_info "=== FAISS Health Check ==="
            check_faiss_health
            ;;
        "security")
            log_info "=== Security Check ==="
            check_security_status
            ;;
        "resources"|"k8s")
            log_info "=== Kubernetes Resources ==="
            check_kubernetes_resources
            ;;
        "help"|*)
            cat << EOF
Adelaide Weather API Operational Monitoring

Usage: $0 <command>

Commands:
  check, full       - Run comprehensive health check (default)
  continuous        - Run continuous monitoring
  quick, status     - Quick status overview
  performance       - Performance testing only
  faiss            - FAISS health check only
  security         - Security monitoring only
  resources, k8s   - Kubernetes resources only
  help             - Show this help

Environment Variables:
  NAMESPACE                    - Kubernetes namespace (default: weather-forecast-prod)
  API_BASE_URL                - API base URL (default: https://api.adelaide-weather.com)
  API_TOKEN                   - API token for authenticated requests
  MONITORING_INTERVAL         - Continuous monitoring interval in seconds (default: 60)
  ALERT_WEBHOOK_URL          - Webhook URL for alerts
  RESPONSE_TIME_THRESHOLD     - Response time threshold in seconds (default: 0.15)
  ERROR_RATE_THRESHOLD       - Error rate threshold (default: 0.01)
  MEMORY_THRESHOLD           - Memory threshold in MB (default: 400)
  CPU_THRESHOLD              - CPU threshold percentage (default: 70)

Examples:
  $0 check                    # Full health check
  $0 continuous              # Continuous monitoring every 60s
  $0 quick                   # Quick status check
  MONITORING_INTERVAL=30 $0 continuous  # Monitor every 30s
EOF
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'log_info "Monitoring stopped by user"; exit 0' INT

# Run main function
main "$@"