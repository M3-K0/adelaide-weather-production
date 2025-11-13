#!/bin/bash

# Adelaide Weather Forecasting System - Advanced Deployment Script
# Usage: ./deploy.sh [environment] [options]
# Environment: development | staging | production
# Options: --force, --no-health-check, --rollback, --monitoring

set -euo pipefail

# Script configuration
SCRIPT_VERSION="2.0.0"
ENVIRONMENT=${1:-development}
PROJECT_NAME="adelaide-weather"
DEPLOYMENT_TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DEPLOY_DIR=$(pwd)
LOG_FILE="${DEPLOY_DIR}/deploy-${ENVIRONMENT}-${DEPLOYMENT_TIMESTAMP}.log"

# Environment-specific settings
declare -A COMPOSE_FILES=(
    ["development"]="docker-compose.yml:docker-compose.dev.yml"
    ["staging"]="docker-compose.staging.yml"
    ["production"]="docker-compose.production.yml"
)

declare -A HEALTH_ENDPOINTS=(
    ["development"]="http://localhost:8000/health"
    ["staging"]="http://localhost:8000/health" 
    ["production"]="http://localhost/health"
)

declare -A FRONTEND_ENDPOINTS=(
    ["development"]="http://localhost:3000"
    ["staging"]="http://localhost:3000"
    ["production"]="http://localhost"
)

# Global variables
FORCE_DEPLOY=false
SKIP_HEALTH_CHECK=false
ROLLBACK_MODE=false
ENABLE_MONITORING=false
BACKUP_CREATED=false
DEPLOYMENT_SUCCESS=false

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Enhanced logging functions
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

log_debug() {
    local msg="$1"
    echo -e "${CYAN}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') $msg" | tee -a "$LOG_FILE"
}

log_stage() {
    local msg="$1"
    echo -e "\n${MAGENTA}=== $msg ===${NC}" | tee -a "$LOG_FILE"
}

# Argument parsing
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                FORCE_DEPLOY=true
                log_info "Force deployment enabled"
                shift
                ;;
            --no-health-check)
                SKIP_HEALTH_CHECK=true
                log_warn "Health checks disabled"
                shift
                ;;
            --rollback)
                ROLLBACK_MODE=true
                log_info "Rollback mode enabled"
                shift
                ;;
            --monitoring)
                ENABLE_MONITORING=true
                log_info "Monitoring stack enabled"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                if [[ "$1" =~ ^(development|staging|production)$ ]]; then
                    ENVIRONMENT="$1"
                else
                    log_error "Unknown argument: $1"
                    show_help
                    exit 1
                fi
                shift
                ;;
        esac
    done
}

show_help() {
    cat << EOF
Adelaide Weather Forecasting System - Deployment Script v${SCRIPT_VERSION}

Usage: $0 [environment] [options]

Environments:
  development  - Local development with hot reload and debug features
  staging      - Production-like environment for integration testing  
  production   - Full production deployment with monitoring

Options:
  --force            Force deployment without confirmation prompts
  --no-health-check  Skip post-deployment health verification
  --rollback         Rollback to previous deployment
  --monitoring       Enable monitoring stack (Prometheus/Grafana)
  -h, --help         Show this help message

Examples:
  $0 development              # Deploy to development
  $0 staging --monitoring     # Deploy staging with monitoring
  $0 production --force       # Force production deployment
  $0 --rollback production    # Rollback production deployment

EOF
}

# Environment validation
validate_environment() {
    if [[ ! "${ENVIRONMENT}" =~ ^(development|staging|production)$ ]]; then
        log_error "Invalid environment: ${ENVIRONMENT}"
        log_info "Valid environments: development, staging, production"
        exit 1
    fi
    
    log_info "Deploying to environment: ${ENVIRONMENT}"
}

# System requirements validation
check_system_requirements() {
    log_stage "System Requirements Check"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    log_info "Docker version: ${docker_version}"
    
    # Check Docker Compose
    local compose_cmd=""
    if command -v docker-compose &> /dev/null; then
        compose_cmd="docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        compose_cmd="docker compose"
    else
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    local compose_version=$(${compose_cmd} --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    log_info "Docker Compose version: ${compose_version}"
    
    # Set global compose command
    COMPOSE_CMD="${compose_cmd}"
    
    # Check available resources
    local available_memory=$(free -m | awk 'NR==2{printf "%.1f", $7/1024}')
    local available_disk=$(df -h . | awk 'NR==2{print $4}')
    
    log_info "Available memory: ${available_memory}GB"
    log_info "Available disk: ${available_disk}"
    
    # Environment-specific resource checks
    if [[ "$ENVIRONMENT" == "production" ]]; then
        if (( $(echo "${available_memory} < 4.0" | bc -l) )); then
            log_warn "Production deployment recommended with at least 4GB available memory"
        fi
    fi
    
    log_success "System requirements check passed"
}

# Environment configuration validation
validate_environment_config() {
    log_stage "Environment Configuration Validation"
    
    # Check environment configuration files
    local config_dir="configs/environments/${ENVIRONMENT}"
    if [[ ! -d "$config_dir" ]]; then
        log_error "Environment configuration directory not found: $config_dir"
        exit 1
    fi
    
    # Validate using Environment Config Manager
    log_info "Validating environment configuration using Environment Config Manager..."
    if ! python3 -c "
import sys, os
sys.path.append('.')
from core.environment_config_manager import EnvironmentConfigManager
try:
    manager = EnvironmentConfigManager(environment='${ENVIRONMENT}')
    config = manager.load_config()
    print(f'✅ Configuration validation passed for {manager.get_environment().value}')
    print(f'📊 Configuration hash: {manager.get_metadata().config_hash}')
except Exception as e:
    print(f'❌ Configuration validation failed: {e}')
    sys.exit(1)
" 2>&1 | tee -a "$LOG_FILE"; then
        log_error "Environment configuration validation failed"
        exit 1
    fi
    
    log_success "Environment configuration validation passed"
}

# Secure credential validation
validate_credentials() {
    log_stage "Credential Validation"
    
    # Environment-specific credential requirements
    case "$ENVIRONMENT" in
        development)
            log_info "Development environment - minimal credential requirements"
            ;;
        staging)
            log_info "Staging environment - validating staging credentials..."
            ;;
        production)
            log_info "Production environment - validating production credentials..."
            
            # Check required environment variables
            local required_vars=("API_TOKEN")
            for var in "${required_vars[@]}"; do
                if [[ -z "${!var:-}" ]]; then
                    log_error "Required environment variable not set: $var"
                    exit 1
                fi
            done
            
            # Additional production credential checks
            if [[ -z "${GRAFANA_PASSWORD:-}" ]]; then
                log_warn "GRAFANA_PASSWORD not set, using default"
            fi
            ;;
    esac
    
    log_success "Credential validation completed"
}

# Docker Compose file validation
validate_compose_files() {
    log_stage "Docker Compose Configuration Validation"
    
    local compose_files_str="${COMPOSE_FILES[$ENVIRONMENT]}"
    IFS=':' read -ra compose_files_array <<< "$compose_files_str"
    
    for compose_file in "${compose_files_array[@]}"; do
        if [[ ! -f "$compose_file" ]]; then
            log_error "Docker Compose file not found: $compose_file"
            exit 1
        fi
        
        log_info "Validating compose file: $compose_file"
        
        # Validate compose file syntax
        if ! ${COMPOSE_CMD} -f "$compose_file" config >/dev/null 2>&1; then
            log_error "Docker Compose file validation failed: $compose_file"
            exit 1
        fi
    done
    
    log_success "Docker Compose configuration validation passed"
}

# Create deployment backup
create_backup() {
    if [[ "$ROLLBACK_MODE" == "true" ]]; then
        return 0
    fi
    
    log_stage "Creating Deployment Backup"
    
    local backup_dir="backups/${ENVIRONMENT}"
    mkdir -p "$backup_dir"
    
    # Create backup of current running state
    local backup_file="${backup_dir}/backup-${DEPLOYMENT_TIMESTAMP}.tar.gz"
    
    # Save current container states
    ${COMPOSE_CMD} -f "${COMPOSE_FILES[$ENVIRONMENT]//://}" -p "$PROJECT_NAME" ps --format json > "${backup_dir}/containers-${DEPLOYMENT_TIMESTAMP}.json" 2>/dev/null || true
    
    # Create configuration backup
    tar -czf "$backup_file" \
        configs/ \
        "${COMPOSE_FILES[$ENVIRONMENT]//://}" \
        .env* \
        2>/dev/null || true
    
    if [[ -f "$backup_file" ]]; then
        log_success "Backup created: $backup_file"
        BACKUP_CREATED=true
        echo "$backup_file" > ".last_backup_${ENVIRONMENT}"
    else
        log_warn "Backup creation skipped or failed"
    fi
}

# Deployment confirmation
confirm_deployment() {
    if [[ "$FORCE_DEPLOY" == "true" ]] || [[ "$ROLLBACK_MODE" == "true" ]]; then
        return 0
    fi
    
    echo -e "\n${YELLOW}=== DEPLOYMENT CONFIRMATION ===${NC}"
    echo "Environment: ${ENVIRONMENT}"
    echo "Timestamp: ${DEPLOYMENT_TIMESTAMP}"
    echo "Compose files: ${COMPOSE_FILES[$ENVIRONMENT]}"
    echo "Monitoring: ${ENABLE_MONITORING}"
    echo "Log file: ${LOG_FILE}"
    echo ""
    
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled by user"
        exit 0
    fi
}

# Handle rollback
perform_rollback() {
    log_stage "Performing Rollback"
    
    local last_backup_file=".last_backup_${ENVIRONMENT}"
    if [[ ! -f "$last_backup_file" ]]; then
        log_error "No backup found for rollback"
        exit 1
    fi
    
    local backup_path=$(cat "$last_backup_file")
    if [[ ! -f "$backup_path" ]]; then
        log_error "Backup file not found: $backup_path"
        exit 1
    fi
    
    log_info "Rolling back to: $backup_path"
    
    # Stop current services
    stop_services
    
    # Restore from backup
    tar -xzf "$backup_path" 2>/dev/null || true
    
    # Start services with backup configuration
    start_services
    
    log_success "Rollback completed"
    exit 0
}

# Stop running services
stop_services() {
    log_stage "Stopping Services"
    
    local compose_files_str="${COMPOSE_FILES[$ENVIRONMENT]}"
    IFS=':' read -ra compose_files_array <<< "$compose_files_str"
    
    local compose_args=""
    for compose_file in "${compose_files_array[@]}"; do
        compose_args="$compose_args -f $compose_file"
    done
    
    log_info "Stopping existing containers..."
    ${COMPOSE_CMD} $compose_args -p "$PROJECT_NAME" down --remove-orphans 2>&1 | tee -a "$LOG_FILE" || true
    
    # Clean up old images for production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_info "Cleaning up unused Docker resources..."
        docker system prune -f 2>&1 | tee -a "$LOG_FILE" || true
    fi
    
    log_success "Services stopped"
}

# Start services
start_services() {
    log_stage "Starting Services"
    
    local compose_files_str="${COMPOSE_FILES[$ENVIRONMENT]}"
    IFS=':' read -ra compose_files_array <<< "$compose_files_str"
    
    local compose_args=""
    for compose_file in "${compose_files_array[@]}"; do
        compose_args="$compose_args -f $compose_file"
    done
    
    # Add monitoring profile if enabled
    local profile_args=""
    if [[ "$ENABLE_MONITORING" == "true" ]]; then
        profile_args="--profile monitoring"
    fi
    
    # Set environment variables
    export ENVIRONMENT
    export DEPLOYMENT_TIMESTAMP
    
    log_info "Building and starting services..."
    ${COMPOSE_CMD} $compose_args -p "$PROJECT_NAME" up -d --build $profile_args 2>&1 | tee -a "$LOG_FILE"
    
    log_success "Services started"
}

# Wait for services to be ready
wait_for_services() {
    if [[ "$SKIP_HEALTH_CHECK" == "true" ]]; then
        log_warn "Skipping service readiness check"
        return 0
    fi
    
    log_stage "Waiting for Services to be Ready"
    
    local max_attempts=60
    local attempt=1
    local all_healthy=false
    
    while [[ $attempt -le $max_attempts ]] && [[ "$all_healthy" == "false" ]]; do
        log_info "Health check attempt $attempt/$max_attempts..."
        
        # Get service status
        local compose_files_str="${COMPOSE_FILES[$ENVIRONMENT]}"
        IFS=':' read -ra compose_files_array <<< "$compose_files_str"
        
        local compose_args=""
        for compose_file in "${compose_files_array[@]}"; do
            compose_args="$compose_args -f $compose_file"
        done
        
        local service_status=$(${COMPOSE_CMD} $compose_args -p "$PROJECT_NAME" ps --format json 2>/dev/null | jq -r '.[].Health // "unknown"' 2>/dev/null || echo "unknown")
        
        # Check if any services are unhealthy or starting
        if echo "$service_status" | grep -q "starting\|unhealthy"; then
            log_info "Services still starting/unhealthy..."
            sleep 10
            ((attempt++))
        else
            all_healthy=true
        fi
    done
    
    if [[ "$all_healthy" == "false" ]]; then
        log_error "Services failed to become healthy within timeout"
        
        # Show service status for debugging
        ${COMPOSE_CMD} $compose_args -p "$PROJECT_NAME" ps 2>&1 | tee -a "$LOG_FILE"
        
        # Show recent logs
        log_info "Recent service logs:"
        ${COMPOSE_CMD} $compose_args -p "$PROJECT_NAME" logs --tail=20 2>&1 | tee -a "$LOG_FILE"
        
        return 1
    fi
    
    log_success "All services are healthy"
}

# Comprehensive health verification
verify_deployment() {
    if [[ "$SKIP_HEALTH_CHECK" == "true" ]]; then
        log_warn "Skipping deployment verification"
        return 0
    fi
    
    log_stage "Deployment Verification"
    
    local verification_passed=true
    
    # API Health Check
    log_info "Checking API health..."
    local api_endpoint="${HEALTH_ENDPOINTS[$ENVIRONMENT]}"
    local api_response=$(curl -s -w "%{http_code}" -o /tmp/api_health.json "$api_endpoint" 2>/dev/null || echo "000")
    
    if [[ "$api_response" == "200" ]]; then
        log_success "API health check passed"
        local api_status=$(jq -r '.status // "unknown"' /tmp/api_health.json 2>/dev/null || echo "unknown")
        log_info "API status: $api_status"
    else
        log_error "API health check failed (HTTP: $api_response)"
        verification_passed=false
    fi
    
    # Frontend Health Check
    log_info "Checking frontend health..."
    local frontend_endpoint="${FRONTEND_ENDPOINTS[$ENVIRONMENT]}"
    local frontend_response=$(curl -s -w "%{http_code}" -o /dev/null "$frontend_endpoint" 2>/dev/null || echo "000")
    
    if [[ "$frontend_response" == "200" ]]; then
        log_success "Frontend health check passed"
    else
        log_error "Frontend health check failed (HTTP: $frontend_response)"
        verification_passed=false
    fi
    
    # Run startup validation system
    log_info "Running comprehensive system validation..."
    if python3 -c "
import sys
sys.path.append('.')
from core.startup_validation_system import ExpertValidatedStartupSystem
try:
    validator = ExpertValidatedStartupSystem(environment='${ENVIRONMENT}')
    results = validator.run_validation()
    if results['overall_status'] == 'pass':
        print('✅ System validation passed')
    else:
        print('❌ System validation failed')
        sys.exit(1)
except Exception as e:
    print(f'⚠️ System validation error: {e}')
    sys.exit(1)
" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "System validation passed"
    else
        log_error "System validation failed"
        verification_passed=false
    fi
    
    # Show running services
    log_info "Current service status:"
    local compose_files_str="${COMPOSE_FILES[$ENVIRONMENT]}"
    IFS=':' read -ra compose_files_array <<< "$compose_files_str"
    
    local compose_args=""
    for compose_file in "${compose_files_array[@]}"; do
        compose_args="$compose_args -f $compose_file"
    done
    
    ${COMPOSE_CMD} $compose_args -p "$PROJECT_NAME" ps 2>&1 | tee -a "$LOG_FILE"
    
    if [[ "$verification_passed" == "true" ]]; then
        DEPLOYMENT_SUCCESS=true
        log_success "Deployment verification completed successfully"
        show_service_urls
    else
        log_error "Deployment verification failed"
        return 1
    fi
}

# Show service URLs
show_service_urls() {
    log_stage "Service URLs"
    
    case "$ENVIRONMENT" in
        development)
            log_info "Frontend: http://localhost:3000"
            log_info "API: http://localhost:8000"
            log_info "API Health: http://localhost:8000/health"
            log_info "API Docs: http://localhost:8000/docs"
            log_info "API Metrics: http://localhost:8000/metrics"
            
            if [[ "$ENABLE_MONITORING" == "true" ]]; then
                log_info "Prometheus: http://localhost:9090"
                log_info "Grafana: http://localhost:3001 (admin/admin)"
            fi
            ;;
        staging)
            log_info "Frontend: http://localhost:3000"
            log_info "API: http://localhost:8000"
            log_info "API Health: http://localhost:8000/health"
            log_info "API Docs: http://localhost:8000/docs"
            ;;
        production)
            log_info "Frontend: http://localhost"
            log_info "API: http://localhost/api"
            log_info "Health: http://localhost/health"
            log_info "Metrics: http://localhost/metrics"
            log_info "Prometheus: http://localhost:9090"
            log_info "Grafana: http://localhost:3001"
            ;;
    esac
}

# Cleanup on exit
cleanup() {
    local exit_code=$?
    
    if [[ "$exit_code" -ne 0 ]] && [[ "$DEPLOYMENT_SUCCESS" == "false" ]]; then
        log_error "Deployment failed with exit code: $exit_code"
        
        if [[ "$BACKUP_CREATED" == "true" ]] && [[ "$FORCE_DEPLOY" == "false" ]]; then
            echo ""
            read -p "Would you like to rollback to the previous state? (y/N): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                ROLLBACK_MODE=true
                perform_rollback
            fi
        fi
    fi
    
    # Clean up temporary files
    rm -f /tmp/api_health.json
    
    log_info "Deployment script completed"
    log_info "Log file: $LOG_FILE"
}

# Main execution function
main() {
    log_stage "Adelaide Weather Forecasting System Deployment v${SCRIPT_VERSION}"
    
    # Parse arguments
    parse_arguments "$@"
    
    # Handle rollback mode
    if [[ "$ROLLBACK_MODE" == "true" ]]; then
        perform_rollback
        return 0
    fi
    
    # Validation phase
    validate_environment
    check_system_requirements
    validate_environment_config
    validate_credentials
    validate_compose_files
    
    # Deployment phase
    create_backup
    confirm_deployment
    stop_services
    start_services
    wait_for_services
    verify_deployment
    
    log_success "🚀 Deployment completed successfully!"
    
    # Show management commands
    echo -e "\n${CYAN}=== MANAGEMENT COMMANDS ===${NC}"
    echo "View logs:  ${COMPOSE_CMD} -f ${COMPOSE_FILES[$ENVIRONMENT]//://} -p $PROJECT_NAME logs -f"
    echo "Stop:       ${COMPOSE_CMD} -f ${COMPOSE_FILES[$ENVIRONMENT]//://} -p $PROJECT_NAME down"
    echo "Status:     ${COMPOSE_CMD} -f ${COMPOSE_FILES[$ENVIRONMENT]//://} -p $PROJECT_NAME ps"
    echo "Restart:    ./deploy.sh $ENVIRONMENT"
    echo ""
}

# Set up signal handlers and cleanup
trap cleanup EXIT INT TERM

# Initialize log file
mkdir -p "$(dirname "$LOG_FILE")"
echo "# Adelaide Weather Deployment Log - $(date)" > "$LOG_FILE"

# Run main function with all arguments
main "$@"