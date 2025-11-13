#!/bin/bash

# =============================================================================
# Adelaide Weather Forecasting System - Production Deployment Script
# =============================================================================
#
# This script deploys the Adelaide Weather system in production mode with:
# - Zero mock data (only real FAISS indices)
# - Comprehensive health checks and monitoring
# - Proper service dependency ordering
# - Security and performance optimization
#
# Usage: ./deploy-production.sh [command]
# Commands:
#   deploy    - Deploy the production stack
#   stop      - Stop all services
#   restart   - Restart the stack
#   status    - Check service status
#   logs      - View service logs
#   health    - Run health checks
#   cleanup   - Clean up resources
#
# =============================================================================

set -euo pipefail

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
ENV_FILE=".env.production"
PROJECT_NAME="adelaide-weather"

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if files exist
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file not found: $ENV_FILE"
        exit 1
    fi
    
    # Check FAISS indices
    if [[ ! -d "indices" ]]; then
        log_error "FAISS indices directory not found"
        exit 1
    fi
    
    local index_count=$(find indices -name "*.faiss" | wc -l)
    if [[ $index_count -lt 8 ]]; then
        log_warning "Expected 8 FAISS indices, found $index_count"
    fi
    
    log_success "Prerequisites check passed"
}

# Set build metadata
set_build_metadata() {
    log_info "Setting build metadata..."
    
    # Set build date
    export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Set version (from git tag or default)
    if git rev-parse --git-dir > /dev/null 2>&1; then
        export VCS_REF=$(git rev-parse --short HEAD)
        export VERSION=$(git describe --tags --always 2>/dev/null || echo "1.0.0")
    else
        export VCS_REF="unknown"
        export VERSION="1.0.0"
    fi
    
    log_info "Build Date: $BUILD_DATE"
    log_info "Version: $VERSION"
    log_info "VCS Ref: $VCS_REF"
}

# Create required directories
create_directories() {
    log_info "Creating required directories..."
    
    mkdir -p logs/{api,frontend,nginx}
    mkdir -p monitoring/alertmanager
    
    # Set proper permissions
    chmod 755 logs/{api,frontend,nginx}
    
    log_success "Directories created"
}

# Validate environment configuration
validate_environment() {
    log_info "Validating environment configuration..."
    
    # Source the environment file
    if [[ -f "$ENV_FILE" ]]; then
        source "$ENV_FILE"
    fi
    
    # Check required variables
    if [[ -z "${API_TOKEN:-}" ]]; then
        log_error "API_TOKEN is not set in $ENV_FILE"
        exit 1
    fi
    
    # Warn about default values
    if [[ "${GRAFANA_PASSWORD:-}" == "secure-admin-password" ]]; then
        log_warning "Using default Grafana password - change this for production"
    fi
    
    if [[ "${API_TOKEN:-}" == "demo-token-12345" ]]; then
        log_warning "Using demo API token - change this for production"
    fi
    
    log_success "Environment validation passed"
}

# Deploy the production stack
deploy() {
    log_info "Deploying Adelaide Weather production stack..."
    
    check_prerequisites
    set_build_metadata
    create_directories
    validate_environment
    
    # Pull latest images
    log_info "Pulling latest base images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
    
    # Build and deploy services
    log_info "Building and starting services..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    check_health
    
    log_success "Production deployment completed!"
    log_info "Access URLs:"
    log_info "  • Application: http://localhost"
    log_info "  • Grafana: http://localhost:3001 (admin / ${GRAFANA_PASSWORD:-admin})"
    log_info "  • Prometheus: http://localhost:9090"
    log_info "  • AlertManager: http://localhost:9093"
    log_info "  • API Health: http://localhost/api/health"
}

# Stop all services
stop() {
    log_info "Stopping Adelaide Weather services..."
    
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
    
    log_success "Services stopped"
}

# Restart services
restart() {
    log_info "Restarting Adelaide Weather services..."
    
    stop
    sleep 5
    deploy
}

# Check service status
status() {
    log_info "Checking service status..."
    
    echo ""
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
    echo ""
    
    # Check Docker resource usage
    log_info "Resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# View service logs
logs() {
    local service="${1:-}"
    
    if [[ -n "$service" ]]; then
        log_info "Viewing logs for service: $service"
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f "$service"
    else
        log_info "Viewing logs for all services..."
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f
    fi
}

# Run comprehensive health checks
check_health() {
    log_info "Running health checks..."
    
    # Check service health status
    local unhealthy_services=0
    
    while read -r container; do
        if [[ -n "$container" ]]; then
            local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
            
            case "$health_status" in
                "healthy")
                    log_success "$container: healthy"
                    ;;
                "unhealthy")
                    log_error "$container: unhealthy"
                    ((unhealthy_services++))
                    ;;
                "starting")
                    log_warning "$container: starting"
                    ;;
                *)
                    log_warning "$container: $health_status"
                    ;;
            esac
        fi
    done < <(docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps -q)
    
    echo ""
    
    # Test API endpoints
    log_info "Testing API endpoints..."
    
    # Source environment for API token
    source "$ENV_FILE" 2>/dev/null || true
    
    # Test health endpoint
    if curl -s -f -H "Authorization: Bearer ${API_TOKEN}" http://localhost/api/health > /dev/null; then
        log_success "API health endpoint: OK"
    else
        log_error "API health endpoint: FAILED"
        ((unhealthy_services++))
    fi
    
    # Test FAISS health
    if curl -s -f -H "Authorization: Bearer ${API_TOKEN}" http://localhost/api/health/faiss > /dev/null; then
        log_success "FAISS health endpoint: OK"
    else
        log_error "FAISS health endpoint: FAILED"
        ((unhealthy_services++))
    fi
    
    # Test frontend
    if curl -s -f http://localhost > /dev/null; then
        log_success "Frontend endpoint: OK"
    else
        log_error "Frontend endpoint: FAILED"
        ((unhealthy_services++))
    fi
    
    # Test monitoring endpoints
    if curl -s -f http://localhost:9090/-/healthy > /dev/null; then
        log_success "Prometheus endpoint: OK"
    else
        log_warning "Prometheus endpoint: FAILED"
    fi
    
    if curl -s -f http://localhost:3001/api/health > /dev/null; then
        log_success "Grafana endpoint: OK"
    else
        log_warning "Grafana endpoint: FAILED"
    fi
    
    # Summary
    echo ""
    if [[ $unhealthy_services -eq 0 ]]; then
        log_success "All critical health checks passed!"
    else
        log_error "$unhealthy_services critical services are unhealthy"
        return 1
    fi
}

# Clean up resources
cleanup() {
    log_info "Cleaning up Adelaide Weather resources..."
    
    # Stop and remove containers
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down -v --remove-orphans
    
    # Remove unused images
    log_info "Removing unused Docker images..."
    docker image prune -f
    
    # Clean up log files (ask for confirmation)
    read -p "Remove log files? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf logs/*
        log_success "Log files removed"
    fi
    
    log_success "Cleanup completed"
}

# Main command dispatcher
main() {
    local command="${1:-deploy}"
    
    case "$command" in
        "deploy")
            deploy
            ;;
        "stop")
            stop
            ;;
        "restart")
            restart
            ;;
        "status")
            status
            ;;
        "logs")
            logs "${2:-}"
            ;;
        "health")
            check_health
            ;;
        "cleanup")
            cleanup
            ;;
        *)
            echo "Usage: $0 {deploy|stop|restart|status|logs|health|cleanup}"
            echo ""
            echo "Commands:"
            echo "  deploy    - Deploy the production stack"
            echo "  stop      - Stop all services"
            echo "  restart   - Restart the stack"
            echo "  status    - Check service status"
            echo "  logs      - View service logs (optionally specify service name)"
            echo "  health    - Run health checks"
            echo "  cleanup   - Clean up resources"
            echo ""
            echo "Examples:"
            echo "  $0 deploy"
            echo "  $0 logs api"
            echo "  $0 health"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"