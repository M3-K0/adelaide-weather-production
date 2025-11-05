#!/bin/bash

# Blue-Green Deployment Automation Script for Adelaide Weather Forecast
# This script manages the blue-green deployment process with comprehensive validation

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NAMESPACE="${NAMESPACE:-adelaide-weather-production}"
HELM_CHART_PATH="${PROJECT_ROOT}/helm/adelaide-weather-forecast"
TIMEOUT="${DEPLOYMENT_TIMEOUT:-1200}"  # 20 minutes
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-300}"  # 5 minutes

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
Blue-Green Deployment Automation

Usage: $0 [OPTIONS] --image-tag <tag>

OPTIONS:
    --image-tag <tag>        Docker image tag to deploy (required)
    --environment <env>      Environment (staging|production) [default: production]
    --namespace <ns>         Kubernetes namespace [default: adelaide-weather-production]
    --timeout <seconds>      Deployment timeout [default: 1200]
    --health-timeout <sec>   Health check timeout [default: 300]
    --dry-run               Simulate deployment without making changes
    --force                 Skip safety checks and confirmations
    --rollback-only         Only perform rollback operation
    --cleanup               Cleanup old environment after successful deployment
    --help                  Show this help message

EXAMPLES:
    $0 --image-tag v1.2.3
    $0 --image-tag latest --environment staging --dry-run
    $0 --rollback-only
    $0 --image-tag v1.2.3 --force --cleanup

ENVIRONMENT VARIABLES:
    NAMESPACE               Kubernetes namespace
    DEPLOYMENT_TIMEOUT      Deployment timeout in seconds
    HEALTH_CHECK_TIMEOUT    Health check timeout in seconds
    AWS_REGION              AWS region for EKS cluster
    EKS_CLUSTER_NAME        EKS cluster name
EOF
}

# Parse command line arguments
parse_args() {
    IMAGE_TAG=""
    ENVIRONMENT="production"
    DRY_RUN=false
    FORCE=false
    ROLLBACK_ONLY=false
    CLEANUP=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --image-tag)
                IMAGE_TAG="$2"
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
            --health-timeout)
                HEALTH_CHECK_TIMEOUT="$2"
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
            --rollback-only)
                ROLLBACK_ONLY=true
                shift
                ;;
            --cleanup)
                CLEANUP=true
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
    
    if [[ "$ROLLBACK_ONLY" == "false" && -z "$IMAGE_TAG" ]]; then
        log_error "Image tag is required unless using --rollback-only"
        usage
        exit 1
    fi
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check required tools
    local required_tools=("kubectl" "helm" "aws" "jq" "curl")
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
    
    # Validate Helm chart
    if [[ ! -d "$HELM_CHART_PATH" ]]; then
        log_error "Helm chart not found at $HELM_CHART_PATH"
        exit 1
    fi
    
    log_success "Prerequisites validated"
}

# Determine current and target environments
determine_environments() {
    log_info "Determining current and target environments..."
    
    # Get current active environment
    CURRENT_ENV=$(kubectl get service adelaide-weather-active -n "$NAMESPACE" \
        -o jsonpath='{.spec.selector.deployment}' 2>/dev/null || echo "blue")
    
    # Determine target environment
    if [[ "$CURRENT_ENV" == "blue" ]]; then
        TARGET_ENV="green"
    else
        TARGET_ENV="blue"
    fi
    
    log_info "Current environment: $CURRENT_ENV"
    log_info "Target environment: $TARGET_ENV"
    
    export CURRENT_ENV TARGET_ENV
}

# Create deployment backup
create_backup() {
    log_info "Creating deployment backup..."
    
    local backup_dir="$PROJECT_ROOT/backups/$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup current service configuration
    kubectl get service adelaide-weather-active -n "$NAMESPACE" -o yaml > \
        "$backup_dir/active-service.yaml" 2>/dev/null || true
    
    # Backup current deployment configuration
    kubectl get deployment -n "$NAMESPACE" -l app=adelaide-weather -o yaml > \
        "$backup_dir/deployments.yaml" 2>/dev/null || true
    
    # Backup ingress configuration
    kubectl get ingress -n "$NAMESPACE" -o yaml > \
        "$backup_dir/ingress.yaml" 2>/dev/null || true
    
    log_success "Backup created at $backup_dir"
    echo "$backup_dir" > /tmp/deployment-backup-path
}

# Generate Helm values for target environment
generate_helm_values() {
    log_info "Generating Helm values for $TARGET_ENV environment..."
    
    local values_file="/tmp/production-values-$TARGET_ENV.yaml"
    
    cat > "$values_file" << EOF
environment: $ENVIRONMENT

image:
  api:
    repository: ghcr.io/adelaide-weather/api
    tag: $IMAGE_TAG
    pullPolicy: Always
  frontend:
    repository: ghcr.io/adelaide-weather/frontend
    tag: $IMAGE_TAG
    pullPolicy: Always

deployment:
  suffix: $TARGET_ENV
  
replicaCount:
  api: 3
  frontend: 3
  
resources:
  api:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1000m"
  frontend:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "1Gi"
      cpu: "500m"

service:
  type: ClusterIP
  api:
    port: 8000
  frontend:
    port: 3000

ingress:
  enabled: true
  className: "alb"
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
  hosts:
    - host: adelaide-weather.com
      paths:
        - path: /api
          pathType: Prefix
          service: api
        - path: /
          pathType: Prefix
          service: frontend

monitoring:
  enabled: true
  prometheus:
    scrape: true

autoscaling:
  enabled: true
  api:
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80
  frontend:
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80

podDisruptionBudget:
  enabled: true
  api:
    minAvailable: 2
  frontend:
    minAvailable: 2

security:
  podSecurityPolicy:
    enabled: true
  networkPolicy:
    enabled: true
EOF
    
    echo "$values_file"
}

# Deploy to target environment
deploy_to_target() {
    local values_file="$1"
    
    log_info "Deploying to $TARGET_ENV environment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would deploy with the following command:"
        echo "helm upgrade --install adelaide-weather-$TARGET_ENV $HELM_CHART_PATH \\"
        echo "  --namespace $NAMESPACE \\"
        echo "  --values $values_file \\"
        echo "  --wait --timeout=${TIMEOUT}s"
        return 0
    fi
    
    # Deploy using Helm
    if ! helm upgrade --install "adelaide-weather-$TARGET_ENV" "$HELM_CHART_PATH" \
        --namespace "$NAMESPACE" \
        --create-namespace \
        --values "$values_file" \
        --set deployment.strategy.type=RollingUpdate \
        --set deployment.strategy.rollingUpdate.maxUnavailable=0 \
        --set deployment.strategy.rollingUpdate.maxSurge=50% \
        --wait --timeout="${TIMEOUT}s" \
        --history-max=5; then
        
        log_error "Deployment to $TARGET_ENV failed"
        return 1
    fi
    
    log_success "Deployment to $TARGET_ENV completed"
}

# Validate deployment health
validate_deployment_health() {
    log_info "Validating $TARGET_ENV environment health..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would validate deployment health"
        return 0
    fi
    
    # Wait for deployments to be ready
    local deployments=("adelaide-weather-api-$TARGET_ENV" "adelaide-weather-frontend-$TARGET_ENV")
    
    for deployment in "${deployments[@]}"; do
        log_info "Waiting for deployment $deployment..."
        if ! kubectl rollout status "deployment/$deployment" -n "$NAMESPACE" --timeout="${HEALTH_CHECK_TIMEOUT}s"; then
            log_error "Deployment $deployment failed to become ready"
            return 1
        fi
    done
    
    # Check pod health
    local ready_pods=$(kubectl get pods -n "$NAMESPACE" -l deployment="$TARGET_ENV" \
        --field-selector=status.phase=Running --no-headers | wc -l)
    local total_pods=$(kubectl get pods -n "$NAMESPACE" -l deployment="$TARGET_ENV" --no-headers | wc -l)
    
    log_info "Ready pods in $TARGET_ENV: $ready_pods/$total_pods"
    
    if [[ "$ready_pods" -lt "$total_pods" ]]; then
        log_error "Not all pods are ready in $TARGET_ENV environment"
        kubectl describe pods -n "$NAMESPACE" -l deployment="$TARGET_ENV" | head -50
        return 1
    fi
    
    # Test application health
    local ingress_host
    ingress_host=$(kubectl get ingress "adelaide-weather-ingress-$TARGET_ENV" -n "$NAMESPACE" \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
    
    if [[ -n "$ingress_host" ]]; then
        log_info "Testing application health at https://$ingress_host"
        
        local retry_count=0
        local max_retries=30
        
        while [[ $retry_count -lt $max_retries ]]; do
            if curl -f -s "https://$ingress_host/api/health" > /dev/null; then
                log_success "Application health check passed"
                break
            fi
            
            retry_count=$((retry_count + 1))
            log_info "Health check attempt $retry_count/$max_retries..."
            sleep 10
        done
        
        if [[ $retry_count -eq $max_retries ]]; then
            log_error "Application health check failed after $max_retries attempts"
            return 1
        fi
    else
        log_warning "Could not determine ingress host for health check"
    fi
    
    log_success "$TARGET_ENV environment health validation passed"
}

# Switch traffic to target environment
switch_traffic() {
    log_info "Switching traffic to $TARGET_ENV environment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would switch traffic from $CURRENT_ENV to $TARGET_ENV"
        return 0
    fi
    
    # Confirmation prompt unless forced
    if [[ "$FORCE" == "false" ]]; then
        echo
        log_warning "About to switch production traffic from $CURRENT_ENV to $TARGET_ENV"
        read -p "Continue? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log_info "Traffic switch cancelled by user"
            return 1
        fi
    fi
    
    # Update active service selector
    kubectl patch service adelaide-weather-active -n "$NAMESPACE" \
        -p "{\"spec\":{\"selector\":{\"deployment\":\"$TARGET_ENV\"}}}"
    
    log_success "Traffic switched to $TARGET_ENV environment"
    
    # Wait for DNS propagation
    log_info "Waiting for DNS propagation and connection draining..."
    sleep 60
    
    # Monitor post-switch health
    log_info "Monitoring post-switch health..."
    local health_checks=0
    local max_health_checks=10
    
    while [[ $health_checks -lt $max_health_checks ]]; do
        if curl -f -s "https://adelaide-weather.com/api/health" > /dev/null; then
            health_checks=$((health_checks + 1))
            log_info "Health check $health_checks/$max_health_checks: OK"
        else
            log_error "Post-switch health check failed - initiating emergency rollback"
            emergency_rollback
            return 1
        fi
        sleep 10
    done
    
    log_success "Post-switch monitoring completed successfully"
}

# Emergency rollback function
emergency_rollback() {
    log_error "Performing emergency rollback to $CURRENT_ENV"
    
    kubectl patch service adelaide-weather-active -n "$NAMESPACE" \
        -p "{\"spec\":{\"selector\":{\"deployment\":\"$CURRENT_ENV\"}}}"
    
    log_success "Emergency rollback completed"
}

# Cleanup old environment
cleanup_old_environment() {
    if [[ "$CLEANUP" == "false" ]]; then
        log_info "Skipping cleanup (use --cleanup to enable)"
        return 0
    fi
    
    log_info "Cleaning up $CURRENT_ENV environment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would cleanup $CURRENT_ENV environment"
        return 0
    fi
    
    # Scale down old environment (don't delete for emergency rollback capability)
    kubectl scale deployment "adelaide-weather-api-$CURRENT_ENV" \
        --replicas=0 -n "$NAMESPACE" 2>/dev/null || true
    kubectl scale deployment "adelaide-weather-frontend-$CURRENT_ENV" \
        --replicas=0 -n "$NAMESPACE" 2>/dev/null || true
    
    log_success "$CURRENT_ENV environment scaled down"
}

# Rollback to previous environment
rollback() {
    log_info "Rolling back to $CURRENT_ENV environment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would rollback to $CURRENT_ENV"
        return 0
    fi
    
    # Scale up previous environment
    local target_replicas=3
    kubectl scale deployment "adelaide-weather-api-$CURRENT_ENV" \
        --replicas=$target_replicas -n "$NAMESPACE"
    kubectl scale deployment "adelaide-weather-frontend-$CURRENT_ENV" \
        --replicas=$target_replicas -n "$NAMESPACE"
    
    # Wait for previous environment to be ready
    kubectl rollout status "deployment/adelaide-weather-api-$CURRENT_ENV" -n "$NAMESPACE"
    kubectl rollout status "deployment/adelaide-weather-frontend-$CURRENT_ENV" -n "$NAMESPACE"
    
    # Switch traffic back
    kubectl patch service adelaide-weather-active -n "$NAMESPACE" \
        -p "{\"spec\":{\"selector\":{\"deployment\":\"$CURRENT_ENV\"}}}"
    
    log_success "Rollback completed"
}

# Main deployment function
main_deployment() {
    log_info "Starting blue-green deployment for image tag: $IMAGE_TAG"
    
    # Create backup
    create_backup
    
    # Generate Helm values
    local values_file
    values_file=$(generate_helm_values)
    
    # Deploy to target environment
    if ! deploy_to_target "$values_file"; then
        log_error "Deployment failed"
        exit 1
    fi
    
    # Validate deployment health
    if ! validate_deployment_health; then
        log_error "Health validation failed"
        log_info "Rolling back to $CURRENT_ENV..."
        rollback
        exit 1
    fi
    
    # Switch traffic
    if ! switch_traffic; then
        log_error "Traffic switch failed"
        exit 1
    fi
    
    # Cleanup old environment
    cleanup_old_environment
    
    log_success "Blue-green deployment completed successfully!"
    log_info "Active environment: $TARGET_ENV"
    log_info "Image tag: $IMAGE_TAG"
}

# Main script execution
main() {
    parse_args "$@"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Running in DRY RUN mode - no changes will be made"
    fi
    
    validate_prerequisites
    determine_environments
    
    if [[ "$ROLLBACK_ONLY" == "true" ]]; then
        rollback
    else
        main_deployment
    fi
}

# Execute main function with all arguments
main "$@"