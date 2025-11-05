#!/bin/bash
# Adelaide Weather - Enhanced Deployment Script with Rollback Testing
# Extends deploy.sh with comprehensive rollback testing capabilities

set -euo pipefail

# Script configuration
SCRIPT_VERSION="2.1.0-rollback"
ENVIRONMENT=${1:-development}
PROJECT_NAME="adelaide-weather"
DEPLOYMENT_TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DEPLOY_DIR=$(pwd)
LOG_FILE="${DEPLOY_DIR}/deploy-rollback-${ENVIRONMENT}-${DEPLOYMENT_TIMESTAMP}.log"

# Enhanced rollback configuration
ROLLBACK_TESTING_ENABLED=false
ENABLE_RTO_MONITORING=false
ROLLBACK_VALIDATION_TIMEOUT=300  # 5 minutes

# Source original deploy.sh functions (if needed)
if [[ -f "./deploy.sh" ]]; then
    # Extract functions from original deploy.sh
    source <(grep -A 1000 "^log_info()" ./deploy.sh | head -n -1)
fi

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Enhanced logging functions
log_rollback() {
    local msg="$1"
    echo -e "${MAGENTA}[ROLLBACK]${NC} $(date '+%Y-%m-%d %H:%M:%S') $msg" | tee -a "$LOG_FILE"
}

log_rto() {
    local msg="$1"
    echo -e "${CYAN}[RTO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $msg" | tee -a "$LOG_FILE"
}

log_test() {
    local msg="$1"
    echo -e "${YELLOW}[TEST]${NC} $(date '+%Y-%m-%d %H:%M:%S') $msg" | tee -a "$LOG_FILE"
}

# Enhanced argument parsing
parse_enhanced_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --test-rollback)
                ROLLBACK_TESTING_ENABLED=true
                log_test "Rollback testing enabled"
                shift
                ;;
            --rto-monitoring)
                ENABLE_RTO_MONITORING=true
                log_rto "RTO monitoring enabled"
                shift
                ;;
            --rollback-timeout)
                ROLLBACK_VALIDATION_TIMEOUT="$2"
                log_rollback "Rollback validation timeout set to ${ROLLBACK_VALIDATION_TIMEOUT}s"
                shift 2
                ;;
            --help-rollback)
                show_enhanced_help
                exit 0
                ;;
            *)
                # Pass through to original argument parser
                shift
                ;;
        esac
    done
}

show_enhanced_help() {
    cat << EOF
Adelaide Weather Forecasting System - Enhanced Deployment Script v${SCRIPT_VERSION}

ROLLBACK TESTING ENHANCEMENTS:

Rollback Options:
  --test-rollback        Enable comprehensive rollback testing
  --rto-monitoring       Enable Recovery Time Objective monitoring
  --rollback-timeout N   Set rollback validation timeout (default: 300s)

Rollback Testing Features:
  - Controlled failure simulation
  - Automated rollback execution
  - RTO compliance measurement
  - Post-rollback validation
  - Integration with CI/CD pipeline

Usage Examples:
  $0 development --test-rollback                    # Test rollback capabilities
  $0 staging --test-rollback --rto-monitoring      # Test with RTO tracking
  $0 production --rollback                         # Execute production rollback

RTO Targets by Scenario:
  - Deployment Failure: 300s
  - Performance Issues: 180s
  - Security Incidents: 120s
  - FAISS Corruption: 240s
  - Config Errors: 150s
  - Health Failures: 240s

For complete rollback testing, see:
  ./scripts/rollback_automation.sh
  python3 test_rollback_comprehensive.py

EOF
}

# Enhanced backup creation with metadata
create_enhanced_backup() {
    log_rollback "Creating enhanced deployment backup..."
    
    local backup_dir="backups/${ENVIRONMENT}"
    mkdir -p "$backup_dir"
    
    local backup_file="${backup_dir}/backup-${DEPLOYMENT_TIMESTAMP}.tar.gz"
    local metadata_file="${backup_dir}/backup-${DEPLOYMENT_TIMESTAMP}.json"
    
    # Capture pre-deployment state
    local pre_deployment_state=$(cat << EOF
{
    "backup_id": "backup-${DEPLOYMENT_TIMESTAMP}",
    "environment": "${ENVIRONMENT}",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "script_version": "${SCRIPT_VERSION}",
    "deployment_type": "enhanced_with_rollback",
    "system_state": {
        "docker_version": "$(docker --version 2>/dev/null || echo "unknown")",
        "compose_version": "$(docker-compose --version 2>/dev/null || docker compose version 2>/dev/null || echo "unknown")",
        "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo "unknown")",
        "running_containers": $(docker ps --format json 2>/dev/null | jq -s '.' || echo "[]")
    },
    "health_status": $(curl -s "${API_BASE_URL:-http://localhost:8000}/health" 2>/dev/null || echo '{"status": "unknown"}'),
    "backup_components": [
        "configurations",
        "docker_compose_files",
        "environment_files",
        "container_states",
        "system_metadata"
    ]
}
EOF
    )
    
    # Save metadata
    echo "$pre_deployment_state" | jq . > "$metadata_file" 2>/dev/null || echo "$pre_deployment_state" > "$metadata_file"
    
    # Create enhanced backup
    tar -czf "$backup_file" \
        configs/ \
        docker-compose*.yml \
        .env* \
        "$metadata_file" \
        2>/dev/null || true
    
    if [[ -f "$backup_file" ]]; then
        log_rollback "Enhanced backup created: $backup_file"
        log_rollback "Backup metadata: $metadata_file"
        BACKUP_CREATED=true
        echo "$backup_file" > ".last_backup_${ENVIRONMENT}"
        echo "$metadata_file" > ".last_backup_metadata_${ENVIRONMENT}"
        return 0
    else
        log_error "Enhanced backup creation failed"
        return 1
    fi
}

# RTO-monitored rollback execution
execute_rto_monitored_rollback() {
    local scenario="${1:-manual_rollback}"
    
    log_rollback "Starting RTO-monitored rollback for scenario: $scenario"
    
    local start_time=$(date +%s.%N)
    local rollback_success=false
    
    # Execute original rollback with monitoring
    if [[ -f "./scripts/rollback_automation.sh" ]]; then
        log_rollback "Using enhanced rollback automation"
        if ./scripts/rollback_automation.sh execute "$ENVIRONMENT"; then
            rollback_success=true
        fi
    else
        log_rollback "Using basic deploy.sh rollback"
        if ./deploy.sh --rollback "$ENVIRONMENT"; then
            rollback_success=true
        fi
    fi
    
    local end_time=$(date +%s.%N)
    local rollback_duration=$(echo "scale=2; $end_time - $start_time" | bc)
    
    # Log RTO metrics
    log_rto "Rollback duration: ${rollback_duration}s"
    
    # Determine RTO target based on scenario
    local rto_target=300  # Default 5 minutes
    case "$scenario" in
        "security_incident") rto_target=120 ;;
        "performance_issue") rto_target=180 ;;
        "faiss_corruption") rto_target=240 ;;
        "config_error") rto_target=150 ;;
    esac
    
    log_rto "RTO target for $scenario: ${rto_target}s"
    
    if (( $(echo "$rollback_duration <= $rto_target" | bc -l) )); then
        log_rto "✅ RTO compliance: PASSED"
    else
        log_rto "❌ RTO compliance: FAILED (${rollback_duration}s > ${rto_target}s)"
    fi
    
    # Save RTO metrics
    echo "$rollback_duration" > ".rollback_duration_${DEPLOYMENT_TIMESTAMP}"
    echo "$rto_target" > ".rollback_rto_target_${DEPLOYMENT_TIMESTAMP}"
    
    return $([[ "$rollback_success" == "true" ]] && echo 0 || echo 1)
}

# Comprehensive post-rollback validation
validate_rollback_success() {
    log_rollback "Starting comprehensive post-rollback validation..."
    
    local validation_timeout="${ROLLBACK_VALIDATION_TIMEOUT}"
    local validation_start=$(date +%s)
    local validation_passed=true
    
    # Wait for services to stabilize
    log_rollback "Waiting for services to stabilize (15s)..."
    sleep 15
    
    # Health endpoint validation with retry
    log_rollback "Validating health endpoints..."
    local health_attempts=0
    local max_health_attempts=10
    local health_success=false
    
    while [[ $health_attempts -lt $max_health_attempts ]]; do
        local current_time=$(date +%s)
        if [[ $((current_time - validation_start)) -gt $validation_timeout ]]; then
            log_error "Rollback validation timeout exceeded"
            validation_passed=false
            break
        fi
        
        if curl -f -s "${API_BASE_URL:-http://localhost:8000}/health" >/dev/null 2>&1; then
            log_rollback "✅ Health endpoint validation passed"
            health_success=true
            break
        fi
        
        health_attempts=$((health_attempts + 1))
        log_rollback "Health check attempt $health_attempts/$max_health_attempts failed, retrying..."
        sleep 10
    done
    
    if [[ "$health_success" != "true" ]]; then
        log_error "Health endpoint validation failed after $max_health_attempts attempts"
        validation_passed=false
    fi
    
    # Service container validation
    log_rollback "Validating service containers..."
    if docker compose ps | grep -q "Up"; then
        log_rollback "✅ Service containers validation passed"
    else
        log_error "Service containers validation failed"
        validation_passed=false
    fi
    
    # Functional validation with E2E tests
    if [[ -f "./test_e2e_smoke.py" ]]; then
        log_rollback "Running functional validation with E2E tests..."
        if python3 ./test_e2e_smoke.py --quick >> "$LOG_FILE" 2>&1; then
            log_rollback "✅ Functional validation passed"
        else
            log_error "Functional validation failed"
            validation_passed=false
        fi
    fi
    
    # FAISS-specific validation
    if curl -f -s "${API_BASE_URL:-http://localhost:8000}/health/faiss" >/dev/null 2>&1; then
        log_rollback "✅ FAISS validation passed"
    else
        log_rollback "⚠️ FAISS validation failed or not available"
    fi
    
    local validation_duration=$(($(date +%s) - validation_start))
    log_rollback "Validation completed in ${validation_duration}s"
    
    if [[ "$validation_passed" == "true" ]]; then
        log_rollback "✅ Comprehensive rollback validation PASSED"
        return 0
    else
        log_rollback "❌ Comprehensive rollback validation FAILED"
        return 1
    fi
}

# Rollback testing workflow
execute_rollback_testing() {
    log_test "Starting rollback testing workflow..."
    
    # Available test scenarios
    local test_scenarios=(
        "deployment_failure"
        "performance_degradation"
        "config_error"
        "health_check_failure"
    )
    
    local total_tests=${#test_scenarios[@]}
    local passed_tests=0
    local test_results=()
    
    log_test "Will execute $total_tests rollback test scenarios"
    
    for scenario in "${test_scenarios[@]}"; do
        log_test "Testing rollback scenario: $scenario"
        
        # Use comprehensive test suite if available
        if [[ -f "./test_rollback_comprehensive.py" ]]; then
            log_test "Using comprehensive rollback test suite"
            if python3 ./test_rollback_comprehensive.py --environment "$ENVIRONMENT" --scenario "$scenario" >> "$LOG_FILE" 2>&1; then
                log_test "✅ Scenario $scenario PASSED"
                passed_tests=$((passed_tests + 1))
                test_results+=("$scenario:PASSED")
            else
                log_test "❌ Scenario $scenario FAILED"
                test_results+=("$scenario:FAILED")
            fi
        else
            # Fallback to automation script
            if [[ -f "./scripts/rollback_automation.sh" ]]; then
                log_test "Using rollback automation script"
                if ./scripts/rollback_automation.sh test "$scenario" "$ENVIRONMENT" >> "$LOG_FILE" 2>&1; then
                    log_test "✅ Scenario $scenario PASSED"
                    passed_tests=$((passed_tests + 1))
                    test_results+=("$scenario:PASSED")
                else
                    log_test "❌ Scenario $scenario FAILED"
                    test_results+=("$scenario:FAILED")
                fi
            else
                log_test "⚠️ No rollback testing tools available, skipping $scenario"
                test_results+=("$scenario:SKIPPED")
            fi
        fi
        
        # Brief pause between tests
        sleep 5
    done
    
    # Generate testing summary
    local success_rate=$((passed_tests * 100 / total_tests))
    
    log_test "=== ROLLBACK TESTING SUMMARY ==="
    log_test "Total Tests: $total_tests"
    log_test "Passed: $passed_tests"
    log_test "Success Rate: ${success_rate}%"
    
    for result in "${test_results[@]}"; do
        IFS=':' read -r scenario status <<< "$result"
        case "$status" in
            "PASSED") log_test "✅ $scenario: PASSED" ;;
            "FAILED") log_test "❌ $scenario: FAILED" ;;
            "SKIPPED") log_test "⚠️ $scenario: SKIPPED" ;;
        esac
    done
    
    # Save test results
    local test_report_file="rollback_test_summary_${DEPLOYMENT_TIMESTAMP}.json"
    cat > "$test_report_file" << EOF
{
    "test_run_id": "rollback-test-${DEPLOYMENT_TIMESTAMP}",
    "environment": "${ENVIRONMENT}",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "total_tests": $total_tests,
    "passed_tests": $passed_tests,
    "success_rate": $success_rate,
    "test_results": [
$(for result in "${test_results[@]}"; do
    IFS=':' read -r scenario status <<< "$result"
    echo "        {\"scenario\": \"$scenario\", \"status\": \"$status\"},"
done | sed '$ s/,$//')
    ],
    "log_file": "${LOG_FILE}"
}
EOF
    
    log_test "Test summary saved: $test_report_file"
    
    # Return success if 80% or more tests passed
    return $([[ $success_rate -ge 80 ]] && echo 0 || echo 1)
}

# Enhanced deployment with rollback testing
enhanced_deployment_workflow() {
    log_stage "Enhanced Deployment Workflow with Rollback Testing"
    
    # Pre-deployment rollback capability validation
    if [[ "$ROLLBACK_TESTING_ENABLED" == "true" ]]; then
        log_test "Validating rollback capabilities before deployment..."
        if [[ -f "./scripts/rollback_automation.sh" ]]; then
            if ./scripts/rollback_automation.sh validate; then
                log_test "✅ Rollback capabilities validated"
            else
                log_error "❌ Rollback capabilities validation failed"
                return 1
            fi
        fi
    fi
    
    # Enhanced backup creation
    if ! create_enhanced_backup; then
        log_error "Enhanced backup creation failed"
        return 1
    fi
    
    # Execute standard deployment (delegating to original deploy.sh)
    log_info "Executing standard deployment workflow..."
    if ./deploy.sh "$ENVIRONMENT" --force >> "$LOG_FILE" 2>&1; then
        log_success "Standard deployment completed successfully"
        DEPLOYMENT_SUCCESS=true
    else
        log_error "Standard deployment failed"
        
        # Automatic rollback on deployment failure
        if [[ "$ENABLE_RTO_MONITORING" == "true" ]]; then
            log_rollback "Initiating automatic rollback due to deployment failure..."
            execute_rto_monitored_rollback "deployment_failure"
        fi
        return 1
    fi
    
    # Post-deployment rollback testing
    if [[ "$ROLLBACK_TESTING_ENABLED" == "true" && "$DEPLOYMENT_SUCCESS" == "true" ]]; then
        log_test "Starting post-deployment rollback testing..."
        if execute_rollback_testing; then
            log_test "✅ Post-deployment rollback testing completed successfully"
        else
            log_test "⚠️ Some rollback tests failed - review required"
        fi
    fi
    
    return 0
}

# Enhanced cleanup with rollback artifacts
enhanced_cleanup() {
    local exit_code=$?
    
    log_info "Enhanced cleanup with rollback artifacts..."
    
    # Clean up temporary test files
    rm -f ".rollback_duration_${DEPLOYMENT_TIMESTAMP}"
    rm -f ".rollback_rto_target_${DEPLOYMENT_TIMESTAMP}"
    
    # Original cleanup
    if command -v cleanup >/dev/null 2>&1; then
        cleanup
    fi
    
    log_info "Enhanced deployment script completed with exit code: $exit_code"
    
    # Show rollback information
    if [[ -f ".last_backup_${ENVIRONMENT}" ]]; then
        local backup_file=$(cat ".last_backup_${ENVIRONMENT}")
        echo -e "\n${CYAN}=== ROLLBACK INFORMATION ===${NC}"
        echo "Latest backup: $backup_file"
        echo "Rollback command: ./deploy.sh --rollback $ENVIRONMENT"
        echo "Enhanced rollback: ./scripts/rollback_automation.sh execute $ENVIRONMENT"
        echo "Test rollback: ./scripts/rollback_automation.sh test <scenario> $ENVIRONMENT"
        echo ""
    fi
}

# Main enhanced execution
main_enhanced() {
    log_stage "Adelaide Weather Enhanced Deployment v${SCRIPT_VERSION}"
    
    # Parse enhanced arguments first
    parse_enhanced_arguments "$@"
    
    # Handle rollback mode (delegated to original deploy.sh)
    if [[ "${1:-}" == "--rollback" ]]; then
        if [[ "$ENABLE_RTO_MONITORING" == "true" ]]; then
            execute_rto_monitored_rollback "manual_rollback"
        else
            ./deploy.sh --rollback "$ENVIRONMENT"
        fi
        return $?
    fi
    
    # Execute enhanced deployment workflow
    enhanced_deployment_workflow
    
    local workflow_exit_code=$?
    
    if [[ $workflow_exit_code -eq 0 ]]; then
        log_success "🚀 Enhanced deployment completed successfully!"
        
        # Show enhanced management commands
        echo -e "\n${CYAN}=== ENHANCED MANAGEMENT COMMANDS ===${NC}"
        echo "Standard commands:"
        echo "  View logs:    docker compose logs -f"
        echo "  Stop:         docker compose down"
        echo "  Status:       docker compose ps"
        echo ""
        echo "Rollback commands:"
        echo "  Quick rollback:    ./deploy.sh --rollback $ENVIRONMENT"
        echo "  Enhanced rollback: ./scripts/rollback_automation.sh execute $ENVIRONMENT"
        echo "  Test rollback:     ./scripts/rollback_automation.sh test <scenario> $ENVIRONMENT"
        echo "  Validate rollback: ./scripts/rollback_automation.sh validate"
        echo ""
        echo "Testing commands:"
        echo "  Comprehensive rollback tests: python3 test_rollback_comprehensive.py"
        echo "  E2E smoke tests:              python3 test_e2e_smoke.py"
        echo ""
    else
        log_error "Enhanced deployment workflow failed"
    fi
    
    return $workflow_exit_code
}

# Set up enhanced signal handlers and cleanup
trap enhanced_cleanup EXIT INT TERM

# Initialize enhanced log file
mkdir -p "$(dirname "$LOG_FILE")"
echo "# Adelaide Weather Enhanced Deployment Log - $(date)" > "$LOG_FILE"

# Run enhanced main function with all arguments
main_enhanced "$@"