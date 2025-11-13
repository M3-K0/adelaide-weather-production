#!/bin/bash
# Adelaide Weather - Automated Rollback System
# Integration script for T-016 Rollback Testing with CI/CD Pipeline

set -euo pipefail

# Configuration
SCRIPT_VERSION="1.0.0"
ENVIRONMENT=${1:-development}
ROLLBACK_REASON=${2:-"Automated rollback testing"}
PROJECT_NAME="adelaide-weather"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="./logs/rollback-${ENVIRONMENT}-${TIMESTAMP}.log"

# RTO Targets (seconds)
declare -A RTO_TARGETS=(
    ["deployment_failure"]=300
    ["performance_degradation"]=180
    ["security_issue"]=120
    ["faiss_corruption"]=240
    ["config_error"]=150
    ["db_migration_failure"]=360
    ["health_check_failure"]=240
)

# Health endpoints
declare -A HEALTH_ENDPOINTS=(
    ["development"]="http://localhost:8000/health"
    ["staging"]="http://localhost:8000/health"
    ["production"]="http://localhost/health"
)

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging functions
log_info() {
    local msg="$1"
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $msg" | tee -a "$LOG_FILE"
}

log_warn() {
    local msg="$1"
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $msg" | tee -a "$LOG_FILE"
}

log_error() {
    local msg="$1"
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $msg" | tee -a "$LOG_FILE"
}

log_success() {
    local msg="$1"
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $msg" | tee -a "$LOG_FILE"
}

log_stage() {
    local msg="$1"
    echo -e "\n${CYAN}=== $msg ===${NC}" | tee -a "$LOG_FILE"
}

# Health check function
check_health() {
    local endpoint="$1"
    local max_attempts="${2:-3}"
    local wait_time="${3:-10}"
    
    for i in $(seq 1 $max_attempts); do
        if curl -f -s "$endpoint" >/dev/null 2>&1; then
            log_success "Health check passed: $endpoint"
            return 0
        fi
        
        if [ $i -lt $max_attempts ]; then
            log_warn "Health check failed (attempt $i/$max_attempts), retrying in ${wait_time}s..."
            sleep $wait_time
        fi
    done
    
    log_error "Health check failed: $endpoint"
    return 1
}

# Measure execution time
measure_time() {
    local start_time="$1"
    local end_time=$(date +%s.%N)
    echo "scale=2; $end_time - $start_time" | bc
}

# Pre-rollback validation
pre_rollback_validation() {
    log_stage "Pre-Rollback Validation"
    
    # Check if backup exists
    local backup_file=".last_backup_${ENVIRONMENT}"
    if [[ ! -f "$backup_file" ]]; then
        log_error "No backup found for rollback (missing $backup_file)"
        return 1
    fi
    
    local backup_path=$(cat "$backup_file")
    if [[ ! -f "$backup_path" ]]; then
        log_error "Backup file not found: $backup_path"
        return 1
    fi
    
    log_success "Backup validation passed: $backup_path"
    
    # Check system requirements
    if ! command -v docker &> /dev/null; then
        log_error "Docker not available"
        return 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        log_error "Docker Compose not available"
        return 1
    fi
    
    # Check emergency recovery script
    if [[ ! -f "./scripts/emergency_recovery.sh" ]]; then
        log_warn "Emergency recovery script not found"
    else
        log_success "Emergency recovery script available"
    fi
    
    log_success "Pre-rollback validation completed"
    return 0
}

# Execute rollback with timing
execute_timed_rollback() {
    log_stage "Executing Timed Rollback"
    
    local start_time=$(date +%s.%N)
    local rollback_success=false
    
    # Execute rollback using deploy.sh
    log_info "Starting rollback execution..."
    if ./deploy.sh --rollback "$ENVIRONMENT" >> "$LOG_FILE" 2>&1; then
        rollback_success=true
        log_success "Deploy script rollback completed"
    else
        log_error "Deploy script rollback failed, attempting emergency recovery"
        
        # Fallback to emergency recovery
        if [[ -f "./scripts/emergency_recovery.sh" ]]; then
            if ./scripts/emergency_recovery.sh full-recovery >> "$LOG_FILE" 2>&1; then
                rollback_success=true
                log_success "Emergency recovery completed"
            else
                log_error "Emergency recovery also failed"
            fi
        fi
    fi
    
    local end_time=$(date +%s.%N)
    local rollback_time=$(measure_time "$start_time")
    
    echo "$rollback_time" > ".rollback_time_${TIMESTAMP}"
    
    if [[ "$rollback_success" == "true" ]]; then
        log_success "Rollback execution completed in ${rollback_time}s"
        return 0
    else
        log_error "Rollback execution failed after ${rollback_time}s"
        return 1
    fi
}

# Post-rollback validation
post_rollback_validation() {
    log_stage "Post-Rollback Validation"
    
    # Wait for services to stabilize
    log_info "Waiting for services to stabilize..."
    sleep 15
    
    local validation_passed=true
    local endpoint="${HEALTH_ENDPOINTS[$ENVIRONMENT]}"
    
    # Health endpoint validation
    if check_health "$endpoint" 5 10; then
        log_success "Health endpoint validation passed"
    else
        log_error "Health endpoint validation failed"
        validation_passed=false
    fi
    
    # Service container validation
    log_info "Checking service containers..."
    if docker compose ps | grep -q "Up"; then
        log_success "Service containers are running"
    else
        log_error "Service containers validation failed"
        validation_passed=false
    fi
    
    # FAISS validation (if available)
    local faiss_endpoint="${endpoint}/faiss"
    if curl -f -s "$faiss_endpoint" >/dev/null 2>&1; then
        log_success "FAISS health validation passed"
    else
        log_warn "FAISS health validation failed or not available"
    fi
    
    # Functional validation using E2E smoke tests
    log_info "Running functional validation..."
    if [[ -f "./test_e2e_smoke.py" ]]; then
        if python3 ./test_e2e_smoke.py --quick >> "$LOG_FILE" 2>&1; then
            log_success "Functional validation passed"
        else
            log_warn "Functional validation had issues"
        fi
    else
        log_warn "E2E smoke test not found, skipping functional validation"
    fi
    
    if [[ "$validation_passed" == "true" ]]; then
        log_success "Post-rollback validation completed successfully"
        return 0
    else
        log_error "Post-rollback validation failed"
        return 1
    fi
}

# RTO compliance check
check_rto_compliance() {
    local scenario="${1:-unknown}"
    local rollback_time_file=".rollback_time_${TIMESTAMP}"
    
    if [[ ! -f "$rollback_time_file" ]]; then
        log_warn "Rollback time not recorded, skipping RTO check"
        return 0
    fi
    
    local rollback_time=$(cat "$rollback_time_file")
    local rto_target="${RTO_TARGETS[$scenario]:-300}"
    
    log_stage "RTO Compliance Check"
    log_info "Scenario: $scenario"
    log_info "Rollback Time: ${rollback_time}s"
    log_info "RTO Target: ${rto_target}s"
    
    if (( $(echo "$rollback_time <= $rto_target" | bc -l) )); then
        log_success "RTO compliance: PASSED (${rollback_time}s <= ${rto_target}s)"
        echo "PASSED" > ".rto_compliance_${TIMESTAMP}"
        return 0
    else
        log_error "RTO compliance: FAILED (${rollback_time}s > ${rto_target}s)"
        echo "FAILED" > ".rto_compliance_${TIMESTAMP}"
        return 1
    fi
}

# Generate rollback report
generate_rollback_report() {
    local scenario="${1:-unknown}"
    local rollback_success="${2:-false}"
    local validation_success="${3:-false}"
    
    log_stage "Generating Rollback Report"
    
    local rollback_time="unknown"
    local rto_compliance="unknown"
    
    if [[ -f ".rollback_time_${TIMESTAMP}" ]]; then
        rollback_time=$(cat ".rollback_time_${TIMESTAMP}")
    fi
    
    if [[ -f ".rto_compliance_${TIMESTAMP}" ]]; then
        rto_compliance=$(cat ".rto_compliance_${TIMESTAMP}")
    fi
    
    local report_file="rollback_report_${TIMESTAMP}.json"
    
    cat > "$report_file" << EOF
{
    "rollback_id": "rollback-${TIMESTAMP}",
    "environment": "${ENVIRONMENT}",
    "scenario": "${scenario}",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "reason": "${ROLLBACK_REASON}",
    "execution": {
        "rollback_success": ${rollback_success},
        "validation_success": ${validation_success},
        "rollback_time_seconds": "${rollback_time}",
        "rto_compliance": "${rto_compliance}"
    },
    "rto_targets": $(echo '{}' | jq '. + {
        "deployment_failure": 300,
        "performance_degradation": 180,
        "security_issue": 120,
        "faiss_corruption": 240,
        "config_error": 150,
        "db_migration_failure": 360,
        "health_check_failure": 240
    }'),
    "validation_results": {
        "health_endpoint": "$(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_ENDPOINTS[$ENVIRONMENT]}" 2>/dev/null || echo "000")",
        "services_running": $(docker compose ps --format json 2>/dev/null | jq 'length' || echo 0),
        "log_file": "${LOG_FILE}"
    },
    "recommendations": [
$(if [[ "$rollback_success" != "true" ]]; then
    echo '        "Investigate rollback execution failures",'
fi)
$(if [[ "$validation_success" != "true" ]]; then
    echo '        "Review post-rollback validation issues",'
fi)
$(if [[ "$rto_compliance" == "FAILED" ]]; then
    echo '        "Optimize rollback procedures to meet RTO targets",'
fi)
        "Monitor system stability for 24 hours",
        "Review rollback triggers and improve automation"
    ]
}
EOF
    
    log_success "Rollback report generated: $report_file"
    
    # Display summary
    echo -e "\n${CYAN}=== ROLLBACK SUMMARY ===${NC}"
    echo "Environment: $ENVIRONMENT"
    echo "Scenario: $scenario"
    echo "Rollback Success: $([ "$rollback_success" == "true" ] && echo "✅ YES" || echo "❌ NO")"
    echo "Validation Success: $([ "$validation_success" == "true" ] && echo "✅ YES" || echo "❌ NO")"
    echo "Rollback Time: ${rollback_time}s"
    echo "RTO Compliance: $rto_compliance"
    echo "Report: $report_file"
    echo "Log: $LOG_FILE"
}

# Simulate failure scenarios for testing
simulate_failure() {
    local scenario="$1"
    
    log_stage "Simulating Failure: $scenario"
    
    case "$scenario" in
        "deployment_failure")
            log_info "Simulating deployment failure..."
            # Stop services to simulate deployment failure
            docker compose down || true
            return 0
            ;;
        "performance_degradation")
            log_info "Simulating performance degradation..."
            # Could set CPU limits or memory constraints
            docker compose exec -T api sh -c 'echo "SLOW_MODE=true" >> /tmp/perf_degrade' 2>/dev/null || true
            return 0
            ;;
        "security_issue")
            log_info "Simulating security issue..."
            # Could modify security configurations
            echo "SECURITY_BREACH_DETECTED=true" > /tmp/security_alert
            return 0
            ;;
        "faiss_corruption")
            log_info "Simulating FAISS corruption..."
            # Backup and corrupt indices
            if [[ -d "./indices" ]]; then
                cp -r ./indices ./indices_backup_sim 2>/dev/null || true
                echo "corrupted" > ./indices/corrupted_index.faiss 2>/dev/null || true
            fi
            return 0
            ;;
        "config_error")
            log_info "Simulating configuration error..."
            # Backup and corrupt config
            if [[ -f "configs/data.yaml" ]]; then
                cp configs/data.yaml configs/data.yaml.sim_backup 2>/dev/null || true
                echo "invalid: yaml: syntax [" > configs/data.yaml 2>/dev/null || true
            fi
            return 0
            ;;
        "health_check_failure")
            log_info "Simulating health check failure..."
            # Stop API service
            docker compose stop api 2>/dev/null || true
            return 0
            ;;
        *)
            log_warn "Unknown failure scenario: $scenario"
            return 1
            ;;
    esac
}

# Cleanup simulation artifacts
cleanup_simulation() {
    log_info "Cleaning up simulation artifacts..."
    
    # Remove temporary files
    rm -f /tmp/perf_degrade /tmp/security_alert
    
    # Restore backups
    if [[ -f "configs/data.yaml.sim_backup" ]]; then
        mv configs/data.yaml.sim_backup configs/data.yaml
        log_info "Restored configuration backup"
    fi
    
    if [[ -d "./indices_backup_sim" ]]; then
        rm -rf ./indices 2>/dev/null || true
        mv ./indices_backup_sim ./indices
        log_info "Restored FAISS indices backup"
    fi
    
    # Clean up timing files
    rm -f ".rollback_time_${TIMESTAMP}" ".rto_compliance_${TIMESTAMP}"
}

# Main execution
main() {
    local action="${1:-help}"
    local scenario="${2:-deployment_failure}"
    
    # Create logs directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    log_stage "Adelaide Weather Rollback Automation v${SCRIPT_VERSION}"
    log_info "Action: $action"
    log_info "Environment: $ENVIRONMENT"
    log_info "Scenario: $scenario"
    
    case "$action" in
        "test")
            # Test rollback with controlled failure
            log_stage "Starting Rollback Test"
            
            # Setup trap for cleanup
            trap cleanup_simulation EXIT
            
            # Simulate failure
            if ! simulate_failure "$scenario"; then
                log_error "Failed to simulate failure scenario"
                exit 1
            fi
            
            # Wait for failure to propagate
            sleep 5
            
            # Execute rollback workflow
            local rollback_success=false
            local validation_success=false
            
            if pre_rollback_validation; then
                if execute_timed_rollback; then
                    rollback_success=true
                    if post_rollback_validation; then
                        validation_success=true
                    fi
                fi
            fi
            
            # Check RTO compliance
            check_rto_compliance "$scenario"
            
            # Generate report
            generate_rollback_report "$scenario" "$rollback_success" "$validation_success"
            
            # Determine exit code
            if [[ "$rollback_success" == "true" && "$validation_success" == "true" ]]; then
                log_success "Rollback test completed successfully"
                exit 0
            else
                log_error "Rollback test failed"
                exit 1
            fi
            ;;
        "execute")
            # Execute actual rollback (production use)
            log_stage "Starting Production Rollback"
            
            local rollback_success=false
            local validation_success=false
            
            if pre_rollback_validation; then
                if execute_timed_rollback; then
                    rollback_success=true
                    if post_rollback_validation; then
                        validation_success=true
                    fi
                fi
            fi
            
            generate_rollback_report "production_rollback" "$rollback_success" "$validation_success"
            
            if [[ "$rollback_success" == "true" && "$validation_success" == "true" ]]; then
                log_success "Production rollback completed successfully"
                exit 0
            else
                log_error "Production rollback failed"
                exit 1
            fi
            ;;
        "validate")
            # Validate rollback capabilities
            log_stage "Validating Rollback Capabilities"
            
            # Check prerequisites
            local validation_issues=()
            
            if [[ ! -f "./deploy.sh" ]]; then
                validation_issues+=("Deploy script missing")
            fi
            
            if [[ ! -f "./scripts/emergency_recovery.sh" ]]; then
                validation_issues+=("Emergency recovery script missing")
            fi
            
            if [[ ! -f "./.github/workflows/rollback-automation.yml" ]]; then
                validation_issues+=("CI/CD rollback workflow missing")
            fi
            
            if ! command -v docker &> /dev/null; then
                validation_issues+=("Docker not available")
            fi
            
            if ! command -v curl &> /dev/null; then
                validation_issues+=("curl not available")
            fi
            
            if [[ ${#validation_issues[@]} -eq 0 ]]; then
                log_success "Rollback capabilities validation passed"
                exit 0
            else
                log_error "Rollback capabilities validation failed:"
                for issue in "${validation_issues[@]}"; do
                    log_error "  - $issue"
                done
                exit 1
            fi
            ;;
        "help"|*)
            cat << EOF
Adelaide Weather Rollback Automation System

Usage: $0 <action> [scenario] [environment]

Actions:
  test <scenario>     Test rollback with controlled failure simulation
  execute             Execute actual rollback (production use)
  validate            Validate rollback capabilities and prerequisites
  help                Show this help message

Scenarios (for test action):
  deployment_failure      Simulate deployment failure
  performance_degradation Simulate performance issues
  security_issue         Simulate security incident
  faiss_corruption       Simulate FAISS index corruption
  config_error           Simulate configuration error
  health_check_failure   Simulate health check failure

Environments:
  development (default)
  staging
  production

Examples:
  $0 test deployment_failure development    # Test deployment failure rollback
  $0 test security_issue production        # Test emergency security rollback
  $0 execute production                     # Execute production rollback
  $0 validate                              # Validate rollback capabilities

RTO Targets:
  - Deployment Failure: 300s (5 minutes)
  - Performance Degradation: 180s (3 minutes)  
  - Security Issue: 120s (2 minutes)
  - FAISS Corruption: 240s (4 minutes)
  - Configuration Error: 150s (2.5 minutes)
  - Database Migration Failure: 360s (6 minutes)
  - Health Check Failure: 240s (4 minutes)

Exit Codes:
  0 - Success
  1 - Failure
  2 - Validation issues
EOF
            exit 0
            ;;
    esac
}

# Execute main function with all arguments
main "$@"