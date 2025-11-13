#!/bin/bash

# Rollback Procedures Script for Adelaide Weather Forecast
# Comprehensive rollback automation with safety checks and validation

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NAMESPACE="${NAMESPACE:-adelaide-weather-production}"
TIMEOUT="${ROLLBACK_TIMEOUT:-600}"  # 10 minutes

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
Rollback Procedures for Adelaide Weather Forecast

Usage: $0 [OPTIONS] [ROLLBACK_TYPE]

ROLLBACK_TYPE:
    application     Rollback application deployment (default)
    traffic         Rollback traffic routing only
    database        Rollback database migrations
    full            Full system rollback (application + database)
    emergency       Emergency rollback (fastest path)

OPTIONS:
    --target-version <version>    Specific version to rollback to
    --environment <env>           Environment (staging|production) [default: production]
    --namespace <ns>              Kubernetes namespace [default: adelaide-weather-production]
    --timeout <seconds>           Rollback timeout [default: 600]
    --reason <reason>             Reason for rollback (for audit logs)
    --dry-run                     Simulate rollback without making changes
    --force                       Skip confirmation prompts
    --list-versions               List available versions for rollback
    --health-check                Perform health check after rollback
    --notify                      Send notifications after rollback
    --help                        Show this help message

EXAMPLES:
    $0 application --target-version v1.2.3
    $0 traffic --force
    $0 emergency --reason "Critical security issue"
    $0 full --target-version v1.2.2 --notify
    $0 --list-versions

ENVIRONMENT VARIABLES:
    NAMESPACE               Kubernetes namespace
    ROLLBACK_TIMEOUT        Rollback timeout in seconds
    SLACK_WEBHOOK_URL       Slack webhook for notifications
    PAGERDUTY_SERVICE_KEY   PagerDuty service key
EOF
}

# Parse command line arguments
parse_args() {
    ROLLBACK_TYPE="application"
    TARGET_VERSION=""
    ENVIRONMENT="production"
    REASON=""
    DRY_RUN=false
    FORCE=false
    LIST_VERSIONS=false
    HEALTH_CHECK=true
    NOTIFY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            application|traffic|database|full|emergency)
                ROLLBACK_TYPE="$1"
                shift
                ;;
            --target-version)
                TARGET_VERSION="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --reason)
                REASON="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --list-versions)
                LIST_VERSIONS=true
                shift
                ;;
            --health-check)
                HEALTH_CHECK=true
                shift
                ;;
            --notify)
                NOTIFY=true
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
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites for rollback..."
    
    # Check required tools
    local required_tools=("kubectl" "helm" "jq" "curl")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is required but not installed"
            exit 1
        fi
    done
    
    # Check kubectl connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace '$NAMESPACE' does not exist"
        exit 1
    fi
    
    log_success "Prerequisites validated"
}

# List available versions for rollback
list_available_versions() {
    log_info "Available versions for rollback:"
    
    echo
    echo "=== Helm Release History ==="
    helm history adelaide-weather -n "$NAMESPACE" 2>/dev/null || {
        log_warning "No Helm release history found for adelaide-weather"
    }
    
    echo
    echo "=== Available Blue-Green Environments ==="
    local blue_exists=$(kubectl get deployment adelaide-weather-api-blue -n "$NAMESPACE" 2>/dev/null && echo "true" || echo "false")
    local green_exists=$(kubectl get deployment adelaide-weather-api-green -n "$NAMESPACE" 2>/dev/null && echo "true" || echo "false")
    local current_active=$(kubectl get service adelaide-weather-active -n "$NAMESPACE" \
        -o jsonpath='{.spec.selector.deployment}' 2>/dev/null || echo "unknown")
    
    echo "Blue environment: $([ "$blue_exists" = "true" ] && echo "Available" || echo "Not deployed")"
    echo "Green environment: $([ "$green_exists" = "true" ] && echo "Available" || echo "Not deployed")"
    echo "Currently active: $current_active"
    
    if [[ "$blue_exists" = "true" ]]; then
        echo
        echo "Blue Environment Details:"
        kubectl get deployment adelaide-weather-api-blue -n "$NAMESPACE" \
            -o jsonpath='{.metadata.labels.version}' 2>/dev/null && echo
    fi
    
    if [[ "$green_exists" = "true" ]]; then
        echo
        echo "Green Environment Details:"
        kubectl get deployment adelaide-weather-api-green -n "$NAMESPACE" \
            -o jsonpath='{.metadata.labels.version}' 2>/dev/null && echo
    fi
    
    echo
    echo "=== Recent Container Image Tags ==="
    kubectl get deployments -n "$NAMESPACE" -l app=adelaide-weather \
        -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.spec.template.spec.containers[0].image}{"\n"}{end}' 2>/dev/null || {
        log_warning "No deployments found"
    }
}

# Get current deployment state
get_current_state() {
    log_info "Getting current deployment state..."
    
    CURRENT_ACTIVE=$(kubectl get service adelaide-weather-active -n "$NAMESPACE" \
        -o jsonpath='{.spec.selector.deployment}' 2>/dev/null || echo "unknown")
    
    if [[ "$CURRENT_ACTIVE" = "blue" ]]; then
        CURRENT_ENV="blue"
        TARGET_ENV="green"
    elif [[ "$CURRENT_ACTIVE" = "green" ]]; then
        CURRENT_ENV="green"
        TARGET_ENV="blue"
    else
        log_warning "Cannot determine current active environment, defaulting to blue/green"
        CURRENT_ENV="blue"
        TARGET_ENV="green"
    fi
    
    log_info "Current active environment: $CURRENT_ENV"
    log_info "Target rollback environment: $TARGET_ENV"
    
    export CURRENT_ENV TARGET_ENV CURRENT_ACTIVE
}

# Create rollback backup
create_rollback_backup() {
    log_info "Creating pre-rollback backup..."
    
    local backup_dir="$PROJECT_ROOT/backups/rollback-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup current state
    kubectl get all -n "$NAMESPACE" -l app=adelaide-weather -o yaml > \
        "$backup_dir/current-state.yaml" 2>/dev/null || true
    
    # Backup active service
    kubectl get service adelaide-weather-active -n "$NAMESPACE" -o yaml > \
        "$backup_dir/active-service.yaml" 2>/dev/null || true
    
    # Create rollback metadata
    cat > "$backup_dir/rollback-metadata.json" << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "environment": "$ENVIRONMENT",
    "namespace": "$NAMESPACE",
    "rollback_type": "$ROLLBACK_TYPE",
    "target_version": "$TARGET_VERSION",
    "reason": "$REASON",
    "initiated_by": "${USER:-unknown}",
    "current_active": "$CURRENT_ACTIVE"
}
EOF
    
    log_success "Backup created at $backup_dir"
    echo "$backup_dir" > /tmp/rollback-backup-path
}

# Application rollback
rollback_application() {
    log_info "Performing application rollback..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would perform application rollback"
        return 0
    fi
    
    local rollback_target=""
    
    if [[ -n "$TARGET_VERSION" ]]; then
        # Rollback to specific version using Helm
        log_info "Rolling back to version: $TARGET_VERSION"
        
        if ! helm rollback adelaide-weather "$TARGET_VERSION" -n "$NAMESPACE" --wait --timeout="${TIMEOUT}s"; then
            log_error "Helm rollback failed"
            return 1
        fi
    else
        # Blue-green rollback
        log_info "Performing blue-green rollback to $TARGET_ENV"
        
        # Check if target environment exists and is healthy
        if ! kubectl get deployment "adelaide-weather-api-$TARGET_ENV" -n "$NAMESPACE" &> /dev/null; then
            log_error "Target environment $TARGET_ENV does not exist"
            return 1
        fi
        
        # Scale up target environment
        local target_replicas=3
        kubectl scale deployment "adelaide-weather-api-$TARGET_ENV" \
            --replicas=$target_replicas -n "$NAMESPACE"
        kubectl scale deployment "adelaide-weather-frontend-$TARGET_ENV" \
            --replicas=$target_replicas -n "$NAMESPACE"
        
        # Wait for target environment to be ready
        if ! kubectl rollout status "deployment/adelaide-weather-api-$TARGET_ENV" -n "$NAMESPACE" --timeout="${TIMEOUT}s"; then
            log_error "Target environment failed to become ready"
            return 1
        fi
        
        if ! kubectl rollout status "deployment/adelaide-weather-frontend-$TARGET_ENV" -n "$NAMESPACE" --timeout="${TIMEOUT}s"; then
            log_error "Target environment failed to become ready"
            return 1
        fi
    fi
    
    log_success "Application rollback completed"
}

# Traffic rollback
rollback_traffic() {
    log_info "Performing traffic rollback..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would switch traffic to $TARGET_ENV"
        return 0
    fi
    
    # Confirmation prompt unless forced
    if [[ "$FORCE" == "false" ]]; then
        echo
        log_warning "About to switch traffic from $CURRENT_ENV to $TARGET_ENV"
        read -p "Continue with traffic rollback? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log_info "Traffic rollback cancelled by user"
            return 1
        fi
    fi
    
    # Switch traffic to target environment
    kubectl patch service adelaide-weather-active -n "$NAMESPACE" \
        -p "{\"spec\":{\"selector\":{\"deployment\":\"$TARGET_ENV\"}}}"
    
    log_success "Traffic switched to $TARGET_ENV environment"
    
    # Wait for DNS propagation
    log_info "Waiting for DNS propagation..."
    sleep 30
}

# Database rollback
rollback_database() {
    log_info "Performing database rollback..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would perform database rollback"
        return 0
    fi
    
    log_warning "Database rollback is a dangerous operation"
    
    if [[ "$FORCE" == "false" ]]; then
        echo
        read -p "Are you sure you want to rollback the database? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log_info "Database rollback cancelled by user"
            return 1
        fi
    fi
    
    # Database rollback logic would go here
    # This would typically involve:
    # 1. Creating a database backup
    # 2. Running migration rollback scripts
    # 3. Validating database integrity
    
    log_warning "Database rollback functionality not implemented - manual intervention required"
    log_info "Please follow the database rollback procedures in the runbook"
}

# Emergency rollback
emergency_rollback() {
    log_info "Performing EMERGENCY rollback..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would perform emergency rollback"
        return 0
    fi
    
    # Skip all confirmations in emergency mode
    log_warning "Emergency rollback initiated - skipping confirmations"
    
    # Immediate traffic switch to previous environment
    log_info "Switching traffic immediately to $TARGET_ENV"
    kubectl patch service adelaide-weather-active -n "$NAMESPACE" \
        -p "{\"spec\":{\"selector\":{\"deployment\":\"$TARGET_ENV\"}}}"
    
    # Scale up target environment aggressively
    kubectl scale deployment "adelaide-weather-api-$TARGET_ENV" \
        --replicas=5 -n "$NAMESPACE" 2>/dev/null || true
    kubectl scale deployment "adelaide-weather-frontend-$TARGET_ENV" \
        --replicas=5 -n "$NAMESPACE" 2>/dev/null || true
    
    log_success "Emergency rollback completed"
}

# Health check after rollback
perform_health_check() {
    if [[ "$HEALTH_CHECK" == "false" ]]; then
        return 0
    fi
    
    log_info "Performing post-rollback health check..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would perform health check"
        return 0
    fi
    
    local health_url="https://adelaide-weather.com/api/health"
    local retry_count=0
    local max_retries=20
    
    while [[ $retry_count -lt $max_retries ]]; do
        if curl -f -s "$health_url" > /dev/null; then
            log_success "Health check passed"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        log_info "Health check attempt $retry_count/$max_retries..."
        sleep 15
    done
    
    log_error "Health check failed after rollback"
    return 1
}

# Send notifications
send_notifications() {
    if [[ "$NOTIFY" == "false" ]]; then
        return 0
    fi
    
    log_info "Sending rollback notifications..."
    
    local status_emoji="⚠️"
    local status_message="Rollback completed"
    
    # Send Slack notification if webhook is configured
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{
                \"text\": \"$status_emoji Adelaide Weather Forecast Rollback\",
                \"attachments\": [{
                    \"color\": \"warning\",
                    \"fields\": [
                        {\"title\": \"Environment\", \"value\": \"$ENVIRONMENT\", \"short\": true},
                        {\"title\": \"Type\", \"value\": \"$ROLLBACK_TYPE\", \"short\": true},
                        {\"title\": \"Target Version\", \"value\": \"${TARGET_VERSION:-N/A}\", \"short\": true},
                        {\"title\": \"Reason\", \"value\": \"${REASON:-Manual rollback}\", \"short\": true},
                        {\"title\": \"Initiated By\", \"value\": \"${USER:-unknown}\", \"short\": true},
                        {\"title\": \"Timestamp\", \"value\": \"$(date)\", \"short\": true}
                    ]
                }]
            }" 2>/dev/null || log_warning "Failed to send Slack notification"
    fi
    
    log_success "Notifications sent"
}

# Log rollback event
log_rollback_event() {
    log_info "Logging rollback event..."
    
    local log_file="$PROJECT_ROOT/logs/rollback.log"
    mkdir -p "$(dirname "$log_file")"
    
    local log_entry=$(cat << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "event": "rollback",
    "environment": "$ENVIRONMENT",
    "namespace": "$NAMESPACE",
    "rollback_type": "$ROLLBACK_TYPE",
    "target_version": "$TARGET_VERSION",
    "reason": "$REASON",
    "initiated_by": "${USER:-unknown}",
    "status": "completed",
    "duration": "${SECONDS:-0}s"
}
EOF
    )
    
    echo "$log_entry" >> "$log_file"
    log_success "Rollback event logged"
}

# Main rollback function
main_rollback() {
    local start_time=$SECONDS
    
    log_info "Starting $ROLLBACK_TYPE rollback..."
    
    # Create backup
    create_rollback_backup
    
    # Perform rollback based on type
    case "$ROLLBACK_TYPE" in
        application)
            rollback_application
            ;;
        traffic)
            rollback_traffic
            ;;
        database)
            rollback_database
            ;;
        full)
            rollback_application
            rollback_traffic
            rollback_database
            ;;
        emergency)
            emergency_rollback
            ;;
        *)
            log_error "Unknown rollback type: $ROLLBACK_TYPE"
            exit 1
            ;;
    esac
    
    # Perform health check
    if ! perform_health_check; then
        log_error "Post-rollback health check failed"
        exit 1
    fi
    
    # Send notifications
    send_notifications
    
    # Log the event
    log_rollback_event
    
    local duration=$((SECONDS - start_time))
    log_success "$ROLLBACK_TYPE rollback completed successfully in ${duration}s"
}

# Main script execution
main() {
    parse_args "$@"
    
    if [[ "$LIST_VERSIONS" == "true" ]]; then
        list_available_versions
        exit 0
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Running in DRY RUN mode - no changes will be made"
    fi
    
    validate_prerequisites
    get_current_state
    
    # Perform the rollback
    main_rollback
}

# Execute main function with all arguments
main "$@"