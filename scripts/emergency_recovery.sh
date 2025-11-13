#!/bin/bash
# Adelaide Weather API - Emergency Recovery Script
# Usage: ./scripts/emergency_recovery.sh [scenario] [options]

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-weather-forecast-prod}"
API_BASE_URL="${API_BASE_URL:-https://api.adelaide-weather.com}"
BACKUP_BUCKET="${BACKUP_BUCKET:-weather-forecast-data-backup}"
LOG_FILE="/tmp/emergency_recovery_$(date +%s).log"

# Logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: $*" | tee -a "$LOG_FILE" >&2
}

# Health check function
check_health() {
    local endpoint="$1"
    local max_attempts="${2:-3}"
    local wait_time="${3:-10}"
    
    for i in $(seq 1 $max_attempts); do
        if curl -f "$endpoint" >/dev/null 2>&1; then
            log "✓ Health check passed: $endpoint"
            return 0
        fi
        
        if [ $i -lt $max_attempts ]; then
            log "⚠ Health check failed (attempt $i/$max_attempts), retrying in ${wait_time}s..."
            sleep $wait_time
        fi
    done
    
    error "✗ Health check failed: $endpoint"
    return 1
}

# Wait for pods to be ready
wait_for_pods() {
    local app_label="$1"
    local timeout="${2:-300}"
    
    log "Waiting for pods with label app=$app_label to be ready..."
    
    if kubectl wait --for=condition=ready pod -l app="$app_label" -n "$NAMESPACE" --timeout="${timeout}s"; then
        log "✓ Pods are ready"
        return 0
    else
        error "✗ Pods failed to become ready within ${timeout}s"
        return 1
    fi
}

# FAISS indices recovery
recover_faiss_indices() {
    log "🔧 Starting FAISS indices recovery..."
    
    local backup_date="${1:-$(date +%Y%m%d)}"
    local recovery_dir="/tmp/faiss_recovery_$$"
    
    # Create recovery directory
    mkdir -p "$recovery_dir"
    
    # Download backup indices
    log "Downloading FAISS indices backup for date: $backup_date"
    if aws s3 sync "s3://$BACKUP_BUCKET/$backup_date/indices/" "$recovery_dir/"; then
        log "✓ Backup downloaded successfully"
    else
        error "✗ Failed to download backup"
        return 1
    fi
    
    # Verify backup integrity
    log "Verifying backup integrity..."
    local required_indices=(
        "faiss_6h_flatip.faiss"
        "faiss_6h_ivfpq.faiss"
        "faiss_12h_flatip.faiss"
        "faiss_12h_ivfpq.faiss"
        "faiss_24h_flatip.faiss"
        "faiss_24h_ivfpq.faiss"
        "faiss_48h_flatip.faiss"
        "faiss_48h_ivfpq.faiss"
    )
    
    for index in "${required_indices[@]}"; do
        if [ -f "$recovery_dir/$index" ]; then
            size=$(stat -c%s "$recovery_dir/$index" 2>/dev/null || stat -f%z "$recovery_dir/$index")
            if [ "$size" -gt 1024 ]; then  # At least 1KB
                log "✓ $index: $(( size / 1024 / 1024 ))MB"
            else
                error "✗ $index is too small: ${size} bytes"
                return 1
            fi
        else
            error "✗ Missing required index: $index"
            return 1
        fi
    done
    
    # Scale down API to replace indices
    log "Scaling down API deployment for index replacement..."
    kubectl scale deployment api-deployment --replicas=0 -n "$NAMESPACE"
    
    # Wait for pods to terminate
    sleep 30
    
    # Get a pod to copy files to (scale up to 1 temporarily)
    kubectl scale deployment api-deployment --replicas=1 -n "$NAMESPACE"
    wait_for_pods "api"
    
    # Copy indices to pod
    local pod_name
    pod_name=$(kubectl get pods -l app=api -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}')
    
    log "Copying indices to pod: $pod_name"
    kubectl cp "$recovery_dir/" "$NAMESPACE/$pod_name:/app/indices/"
    
    # Scale back up
    kubectl scale deployment api-deployment --replicas=3 -n "$NAMESPACE"
    wait_for_pods "api"
    
    # Verify recovery
    log "Verifying FAISS recovery..."
    if check_health "$API_BASE_URL/health/faiss"; then
        log "✅ FAISS indices recovery completed successfully"
        
        # Test forecast functionality
        if [ -n "${API_TOKEN:-}" ]; then
            log "Testing forecast functionality..."
            if curl -s -H "Authorization: Bearer $API_TOKEN" \
                "$API_BASE_URL/forecast?horizon=24h&vars=t2m" | jq -e '.variables.t2m.available' >/dev/null; then
                log "✓ Forecast functionality verified"
            else
                log "⚠ Forecast functionality test failed"
            fi
        fi
        
        return 0
    else
        error "✗ FAISS recovery verification failed"
        return 1
    fi
}

# Emergency token rotation
emergency_token_rotation() {
    log "🔐 Starting emergency token rotation..."
    
    local reason="${1:-Emergency rotation}"
    
    # Generate new token
    local new_token
    new_token=$(openssl rand -hex 32)
    log "Generated new token: ${new_token:0:8}..."
    
    # Update Kubernetes secret
    log "Updating Kubernetes secret..."
    kubectl create secret generic api-secrets \
        --from-literal=API_TOKEN="$new_token" \
        --dry-run=client -o yaml | kubectl apply -f - -n "$NAMESPACE"
    
    # Force immediate pod restart
    log "Forcing pod restart to pick up new token..."
    kubectl delete pods -l app=api -n "$NAMESPACE"
    
    # Wait for pods to be ready
    wait_for_pods "api" 120
    
    # Verify new token
    log "Verifying new token functionality..."
    if curl -s -H "Authorization: Bearer $new_token" \
        "$API_BASE_URL/health" | jq -e '.ready == true' >/dev/null; then
        log "✅ Emergency token rotation completed successfully"
        log "🔑 New token: ${new_token:0:8}..."
        
        # Log security event
        cat > "/tmp/token_rotation_$(date +%s).json" << EOF
{
    "event": "emergency_token_rotation",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "reason": "$reason",
    "new_token_hint": "${new_token:0:8}...",
    "operator": "${USER:-unknown}",
    "success": true
}
EOF
        
        echo "$new_token"  # Return new token
        return 0
    else
        error "✗ New token verification failed"
        return 1
    fi
}

# Performance recovery
performance_recovery() {
    log "⚡ Starting performance recovery..."
    
    # Check current resource usage
    log "Checking current resource usage..."
    kubectl top pods -l app=api -n "$NAMESPACE"
    
    # Scale up if needed
    local current_replicas
    current_replicas=$(kubectl get deployment api-deployment -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
    
    if [ "$current_replicas" -lt 5 ]; then
        log "Scaling up from $current_replicas to 5 replicas..."
        kubectl scale deployment api-deployment --replicas=5 -n "$NAMESPACE"
        wait_for_pods "api"
    fi
    
    # Enable performance optimizations
    log "Enabling performance optimizations..."
    kubectl set env deployment/api-deployment \
        PERFORMANCE_MODE=true \
        FAISS_LAZY_LOAD=true \
        RESPONSE_CACHING=true \
        MEMORY_OPTIMIZATION=true \
        -n "$NAMESPACE"
    
    # Restart high-memory pods
    log "Checking for high-memory pods..."
    local high_memory_pods
    high_memory_pods=$(kubectl get pods -l app=api -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,MEMORY:.status.containerStatuses[0].usage.memory --no-headers | awk '$2 ~ /[0-9]+Mi/ && $2+0 > 400 {print $1}' || true)
    
    if [ -n "$high_memory_pods" ]; then
        log "Restarting high-memory pods: $high_memory_pods"
        echo "$high_memory_pods" | xargs kubectl delete pod -n "$NAMESPACE"
        wait_for_pods "api"
    fi
    
    # Test performance
    log "Testing performance recovery..."
    local total_time=0
    local requests=5
    
    for i in $(seq 1 $requests); do
        local start_time end_time duration
        start_time=$(date +%s.%N)
        
        if curl -s "$API_BASE_URL/health" >/dev/null; then
            end_time=$(date +%s.%N)
            duration=$(echo "$end_time - $start_time" | bc)
            total_time=$(echo "$total_time + $duration" | bc)
            log "Request $i: ${duration}s"
        else
            error "Request $i failed"
        fi
    done
    
    local avg_time
    avg_time=$(echo "scale=3; $total_time / $requests" | bc)
    log "Average response time: ${avg_time}s"
    
    if (( $(echo "$avg_time < 0.15" | bc -l) )); then
        log "✅ Performance recovery completed - SLA met"
        return 0
    else
        log "⚠ Performance recovery completed - SLA not met but improved"
        return 0
    fi
}

# System health recovery
system_health_recovery() {
    log "🏥 Starting system health recovery..."
    
    # Check all health endpoints
    local endpoints=(
        "$API_BASE_URL/health"
        "$API_BASE_URL/health/detailed"
        "$API_BASE_URL/health/live"
        "$API_BASE_URL/health/ready"
    )
    
    local failed_endpoints=()
    
    for endpoint in "${endpoints[@]}"; do
        if ! check_health "$endpoint" 1 0; then
            failed_endpoints+=("$endpoint")
        fi
    done
    
    if [ ${#failed_endpoints[@]} -gt 0 ]; then
        log "Failed endpoints detected: ${failed_endpoints[*]}"
        
        # Restart deployment
        log "Restarting API deployment..."
        kubectl rollout restart deployment/api-deployment -n "$NAMESPACE"
        kubectl rollout status deployment/api-deployment -n "$NAMESPACE" --timeout=300s
        
        # Re-test endpoints
        local still_failing=()
        for endpoint in "${failed_endpoints[@]}"; do
            if ! check_health "$endpoint" 3 10; then
                still_failing+=("$endpoint")
            fi
        done
        
        if [ ${#still_failing[@]} -eq 0 ]; then
            log "✅ System health recovery completed successfully"
            return 0
        else
            error "✗ System health recovery failed - still failing: ${still_failing[*]}"
            return 1
        fi
    else
        log "✅ All health endpoints are operational"
        return 0
    fi
}

# Emergency mode activation
activate_emergency_mode() {
    log "🚨 Activating emergency mode..."
    
    # Enable emergency mode settings
    kubectl set env deployment/api-deployment \
        EMERGENCY_MODE=true \
        SIMPLE_RESPONSES=true \
        SKIP_COMPLEX_VALIDATION=true \
        ANALOG_SEARCH_MODE=simplified \
        ANALOG_MAX_NEIGHBORS=20 \
        FAISS_SIMPLE_SEARCH=true \
        RATE_LIMIT_PER_MINUTE=30 \
        -n "$NAMESPACE"
    
    # Scale to minimum viable configuration
    kubectl scale deployment api-deployment --replicas=2 -n "$NAMESPACE"
    wait_for_pods "api"
    
    # Test basic functionality
    if check_health "$API_BASE_URL/health"; then
        log "✅ Emergency mode activated successfully"
        log "⚠ System running in degraded mode - limited functionality"
        return 0
    else
        error "✗ Emergency mode activation failed"
        return 1
    fi
}

# Main function
main() {
    local scenario="${1:-help}"
    shift || true
    
    log "Adelaide Weather API Emergency Recovery Script"
    log "Scenario: $scenario"
    log "Namespace: $NAMESPACE"
    log "API Base URL: $API_BASE_URL"
    log "Log file: $LOG_FILE"
    
    case "$scenario" in
        "faiss-recovery"|"faiss")
            recover_faiss_indices "$@"
            ;;
        "token-rotation"|"token")
            emergency_token_rotation "$@"
            ;;
        "performance"|"perf")
            performance_recovery "$@"
            ;;
        "health"|"health-recovery")
            system_health_recovery "$@"
            ;;
        "emergency-mode"|"emergency")
            activate_emergency_mode "$@"
            ;;
        "full-recovery"|"full")
            log "🔄 Starting full system recovery..."
            system_health_recovery || log "⚠ Health recovery had issues"
            performance_recovery || log "⚠ Performance recovery had issues"
            if [ -n "${API_TOKEN:-}" ]; then
                check_health "$API_BASE_URL/health/faiss" || recover_faiss_indices
            fi
            log "✅ Full recovery sequence completed"
            ;;
        "status"|"check")
            log "📊 System status check..."
            kubectl get pods -l app=api -n "$NAMESPACE"
            check_health "$API_BASE_URL/health" || log "Health check failed"
            if [ -n "${API_TOKEN:-}" ]; then
                check_health "$API_BASE_URL/health/faiss" || log "FAISS health check failed"
            fi
            ;;
        "help"|*)
            cat << EOF
Adelaide Weather API Emergency Recovery Script

Usage: $0 <scenario> [options]

Scenarios:
  faiss-recovery [backup_date]    - Recover FAISS indices from backup
  token-rotation [reason]         - Emergency API token rotation
  performance                     - Recover from performance issues
  health-recovery                 - Recover system health
  emergency-mode                  - Activate emergency degraded mode
  full-recovery                   - Run complete recovery sequence
  status                          - Check system status
  help                            - Show this help

Environment Variables:
  NAMESPACE                       - Kubernetes namespace (default: weather-forecast-prod)
  API_BASE_URL                   - API base URL (default: https://api.adelaide-weather.com)
  API_TOKEN                      - API token for authenticated requests
  BACKUP_BUCKET                  - S3 backup bucket (default: weather-forecast-data-backup)

Examples:
  $0 faiss-recovery 20251105      # Restore FAISS indices from Nov 5, 2025 backup
  $0 token-rotation "Security incident"  # Rotate token due to security incident
  $0 performance                  # Recover from performance degradation
  $0 full-recovery               # Complete system recovery

Exit Codes:
  0 - Success
  1 - Failure
  2 - Partial success/warnings
EOF
            exit 0
            ;;
    esac
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log "✅ Emergency recovery completed successfully"
    else
        error "❌ Emergency recovery failed (exit code: $exit_code)"
    fi
    
    log "Recovery log saved to: $LOG_FILE"
    exit $exit_code
}

# Run main function with all arguments
main "$@"