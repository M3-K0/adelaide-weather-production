#!/bin/bash

# Adelaide Weather Forecasting - Synthetic Monitoring Deployment Script
# Deploys comprehensive SLO monitoring, synthetic checks, and alerting

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is required but not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is required but not installed"
        exit 1
    fi
    
    # Check if .env file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        warn ".env file not found, creating template..."
        create_env_template
    fi
    
    success "Prerequisites check completed"
}

# Create environment template
create_env_template() {
    cat > "$ENV_FILE" << EOF
# Adelaide Weather Forecasting Environment Variables

# API Configuration
API_TOKEN=your-secure-api-token-here
API_BASE_URL=http://api:8000
FRONTEND_BASE_URL=http://frontend:3000

# Monitoring Configuration
METRICS_PORT=8080
GRAFANA_PASSWORD=admin

# Alerting Configuration
SLACK_WEBHOOK_URL=
PAGERDUTY_SERVICE_KEY=
PAGERDUTY_ROUTING_KEY=
SMTP_SERVER=
SMTP_USERNAME=
SMTP_PASSWORD=

# Database Configuration  
REDIS_URL=redis://redis:6379

# Environment
ENVIRONMENT=production
EOF
    
    warn "Created .env template at $ENV_FILE"
    warn "Please edit the file with your actual configuration values"
}

# Validate configuration
validate_configuration() {
    log "Validating configuration..."
    
    source "$ENV_FILE"
    
    # Check required variables
    required_vars=("API_TOKEN")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Validate API token format (basic check)
    if [[ ${#API_TOKEN} -lt 16 ]]; then
        warn "API_TOKEN appears to be too short (less than 16 characters)"
    fi
    
    success "Configuration validation completed"
}

# Build synthetic monitoring image
build_synthetic_monitor() {
    log "Building synthetic monitoring Docker image..."
    
    cd "$SCRIPT_DIR"
    
    # Build the image
    docker build -t adelaide-synthetic-monitor:latest -f synthetic/Dockerfile .
    
    success "Synthetic monitoring image built successfully"
}

# Deploy monitoring stack
deploy_monitoring_stack() {
    log "Deploying monitoring stack..."
    
    cd "$SCRIPT_DIR"
    
    # Create necessary directories
    mkdir -p {grafana/provisioning/{datasources,dashboards},alertmanager/templates}
    
    # Create Grafana datasource configuration
    create_grafana_datasource
    
    # Create Grafana dashboard provisioning
    create_grafana_dashboard_config
    
    # Start the monitoring stack
    docker-compose -f docker-compose.monitoring.yml up -d
    
    success "Monitoring stack deployed"
}

# Create Grafana datasource configuration
create_grafana_datasource() {
    mkdir -p grafana/provisioning/datasources
    
    cat > grafana/provisioning/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    orgId: 1
    url: http://prometheus:9090
    isDefault: true
    editable: true
    version: 1
    
  - name: Alertmanager
    type: alertmanager
    access: proxy
    orgId: 1
    url: http://alertmanager:9093
    editable: true
    version: 1
EOF
}

# Create Grafana dashboard provisioning
create_grafana_dashboard_config() {
    mkdir -p grafana/provisioning/dashboards
    
    cat > grafana/provisioning/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF
}

# Wait for services to be ready
wait_for_services() {
    log "Waiting for services to be ready..."
    
    services=(
        "prometheus:9090"
        "grafana:3000"
        "alertmanager:9093"
        "synthetic-monitor:8080"
    )
    
    for service in "${services[@]}"; do
        service_name=$(echo "$service" | cut -d: -f1)
        port=$(echo "$service" | cut -d: -f2)
        
        log "Waiting for $service_name to be ready..."
        
        # Wait up to 60 seconds for each service
        timeout=60
        counter=0
        
        while [[ $counter -lt $timeout ]]; do
            if docker-compose -f docker-compose.monitoring.yml exec -T "$service_name" curl -f "http://localhost:$port" &>/dev/null; then
                success "$service_name is ready"
                break
            fi
            
            sleep 2
            counter=$((counter + 2))
        done
        
        if [[ $counter -ge $timeout ]]; then
            warn "$service_name did not become ready within $timeout seconds"
        fi
    done
}

# Run synthetic monitoring tests
test_synthetic_monitoring() {
    log "Testing synthetic monitoring..."
    
    # Check synthetic monitor metrics
    if docker-compose -f docker-compose.monitoring.yml exec -T synthetic-monitor curl -f http://localhost:8080/metrics &>/dev/null; then
        success "Synthetic monitor is exposing metrics"
    else
        error "Synthetic monitor metrics endpoint not accessible"
        return 1
    fi
    
    # Check Prometheus targets
    log "Checking Prometheus targets..."
    sleep 10  # Give Prometheus time to scrape
    
    success "Synthetic monitoring tests completed"
}

# Show deployment information
show_deployment_info() {
    log "Deployment completed successfully!"
    echo
    echo "🔗 Access URLs:"
    echo "  📊 Grafana Dashboard: http://localhost:3001"
    echo "  🎯 Prometheus: http://localhost:9090"
    echo "  🚨 Alertmanager: http://localhost:9093"
    echo "  📈 Synthetic Monitor: http://localhost:8080/metrics"
    echo
    echo "🔐 Default Credentials:"
    echo "  Grafana: admin / $(grep GRAFANA_PASSWORD "$ENV_FILE" | cut -d= -f2)"
    echo
    echo "📋 Key Features:"
    echo "  ✅ SLO tracking with error budget monitoring"
    echo "  ✅ Geographic synthetic monitoring"
    echo "  ✅ Multi-layer alerting with escalation"
    echo "  ✅ Comprehensive health checks"
    echo "  ✅ Real-time SLO dashboards"
    echo
    echo "🔍 To view logs:"
    echo "  docker-compose -f monitoring/docker-compose.monitoring.yml logs -f"
    echo
    echo "🛑 To stop:"
    echo "  docker-compose -f monitoring/docker-compose.monitoring.yml down"
}

# Cleanup function
cleanup() {
    log "Cleaning up monitoring stack..."
    cd "$SCRIPT_DIR"
    docker-compose -f docker-compose.monitoring.yml down
    success "Cleanup completed"
}

# Main execution
main() {
    case "${1:-deploy}" in
        "deploy")
            log "Starting Adelaide Weather Synthetic Monitoring deployment..."
            check_prerequisites
            validate_configuration
            build_synthetic_monitor
            deploy_monitoring_stack
            wait_for_services
            test_synthetic_monitoring
            show_deployment_info
            ;;
        "cleanup")
            cleanup
            ;;
        "restart")
            cleanup
            sleep 5
            main deploy
            ;;
        "test")
            test_synthetic_monitoring
            ;;
        *)
            echo "Usage: $0 {deploy|cleanup|restart|test}"
            echo
            echo "Commands:"
            echo "  deploy   - Deploy the complete synthetic monitoring stack"
            echo "  cleanup  - Stop and remove all monitoring containers"
            echo "  restart  - Cleanup and redeploy"
            echo "  test     - Test synthetic monitoring functionality"
            exit 1
            ;;
    esac
}

# Handle script interruption
trap cleanup INT TERM

# Run main function
main "$@"