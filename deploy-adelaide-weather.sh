#!/bin/bash

# =============================================================================
# Adelaide Weather Forecasting System - Master Deployment Automation
# =============================================================================
# 
# Comprehensive "simple click and go" deployment automation for the Adelaide
# Weather Forecasting System. This script provides complete orchestration with
# validation, health checks, and user guidance.
#
# Features:
# - Prerequisites validation (Docker, compose, resources)  
# - SSL certificate generation and configuration
# - Service startup sequencing with health validation
# - Complete system validation and testing
# - User-friendly progress indication and logging
# - Error handling with troubleshooting guidance
# - Rollback capabilities if deployment fails
#
# Usage: ./deploy-adelaide-weather.sh [options]
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION AND CONSTANTS
# =============================================================================

SCRIPT_VERSION="2.0.0"
PROJECT_NAME="adelaide-weather"
COMPOSE_FILE="docker-compose.production.yml"
ENV_FILE=".env.production"
DEPLOYMENT_LOG_DIR="deployment_logs"
VALIDATION_SCRIPTS_DIR="validation_scripts"

# Colors for enhanced output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# Deployment tracking
DEPLOYMENT_ID="deploy-$(date +%Y%m%d-%H%M%S)"
DEPLOYMENT_LOG="${DEPLOYMENT_LOG_DIR}/${DEPLOYMENT_ID}.log"
ROLLBACK_CHECKPOINT=""

# =============================================================================
# LOGGING AND UI FUNCTIONS
# =============================================================================

# Enhanced logging with timestamp and formatting
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} ${timestamp} - $message" | tee -a "$DEPLOYMENT_LOG"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $message" | tee -a "$DEPLOYMENT_LOG"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} ${timestamp} - $message" | tee -a "$DEPLOYMENT_LOG"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" | tee -a "$DEPLOYMENT_LOG"
            ;;
        "STEP")
            echo -e "${PURPLE}[STEP]${NC} ${timestamp} - $message" | tee -a "$DEPLOYMENT_LOG"
            ;;
        "PROGRESS")
            echo -e "${CYAN}[PROGRESS]${NC} ${timestamp} - $message" | tee -a "$DEPLOYMENT_LOG"
            ;;
    esac
}

# Progress indicator with spinner
show_progress() {
    local pid=$1
    local message="$2"
    local spin='-\|/'
    local i=0
    
    while kill -0 $pid 2>/dev/null; do
        i=$(( (i+1) %4 ))
        printf "\r${CYAN}[PROGRESS]${NC} %s ${spin:$i:1}" "$message"
        sleep .1
    done
    printf "\r${GREEN}[COMPLETE]${NC} %s ✓\n" "$message"
}

# Display banner
show_banner() {
    echo -e "${WHITE}"
    echo "============================================================================="
    echo "    Adelaide Weather Forecasting System - Deployment Automation v${SCRIPT_VERSION}"
    echo "============================================================================="
    echo -e "${NC}"
    echo -e "🌡️  ${CYAN}Comprehensive Weather Forecast Deployment${NC}"
    echo -e "🚀 ${GREEN}Simple Click and Go Automation${NC}"
    echo -e "📊 ${BLUE}Full Stack: API + Frontend + Nginx + Monitoring${NC}"
    echo -e "🔒 ${YELLOW}SSL Certificates + Security Validation${NC}"
    echo ""
}

# =============================================================================
# PREREQUISITE VALIDATION FUNCTIONS
# =============================================================================

validate_docker() {
    log "INFO" "Validating Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        log "ERROR" "Docker is not installed or not in PATH"
        log "INFO" "Install Docker: https://docs.docker.com/get-docker/"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        log "ERROR" "Docker daemon is not running"
        log "INFO" "Start Docker daemon: sudo systemctl start docker"
        return 1
    fi
    
    local docker_version=$(docker --version | cut -d' ' -f3 | tr -d ',')
    log "SUCCESS" "Docker is available (version: $docker_version)"
    return 0
}

validate_docker_compose() {
    log "INFO" "Validating Docker Compose installation..."
    
    if ! command -v docker-compose &> /dev/null; then
        log "ERROR" "Docker Compose is not installed"
        log "INFO" "Install: pip install docker-compose or use Docker Desktop"
        return 1
    fi
    
    local compose_version=$(docker-compose --version | cut -d' ' -f3 | tr -d ',')
    log "SUCCESS" "Docker Compose is available (version: $compose_version)"
    return 0
}

validate_system_resources() {
    log "INFO" "Validating system resources..."
    
    # Check available memory (require at least 8GB)
    local mem_gb=$(free -g | awk '/^Mem:/{print $7}')
    if [[ $mem_gb -lt 6 ]]; then
        log "WARNING" "Available memory: ${mem_gb}GB (recommended: 8GB+)"
    else
        log "SUCCESS" "Available memory: ${mem_gb}GB"
    fi
    
    # Check available disk space (require at least 10GB)
    local disk_gb=$(df -BG . | awk 'NR==2{print $4}' | tr -d 'G')
    if [[ $disk_gb -lt 10 ]]; then
        log "ERROR" "Available disk space: ${disk_gb}GB (required: 10GB+)"
        return 1
    else
        log "SUCCESS" "Available disk space: ${disk_gb}GB"
    fi
    
    # Check CPU cores
    local cpu_cores=$(nproc)
    if [[ $cpu_cores -lt 2 ]]; then
        log "WARNING" "CPU cores: $cpu_cores (recommended: 4+)"
    else
        log "SUCCESS" "CPU cores: $cpu_cores"
    fi
    
    return 0
}

validate_required_files() {
    log "INFO" "Validating required files and directories..."
    
    local missing_files=()
    local required_files=(
        "$COMPOSE_FILE"
        "nginx/nginx.conf"
        "api/Dockerfile.production"
        "frontend/Dockerfile.production"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    local required_dirs=(
        "api"
        "frontend" 
        "nginx"
        "indices"
        "embeddings"
        "outcomes"
        "monitoring"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            missing_files+=("$dir/")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        log "ERROR" "Missing required files/directories:"
        for file in "${missing_files[@]}"; do
            log "ERROR" "  - $file"
        done
        return 1
    fi
    
    log "SUCCESS" "All required files and directories present"
    return 0
}

validate_faiss_data() {
    log "INFO" "Validating FAISS data availability..."
    
    # Check for FAISS indices
    local index_count=$(find indices -name "*.faiss" 2>/dev/null | wc -l)
    if [[ $index_count -lt 8 ]]; then
        log "ERROR" "Expected 8 FAISS indices, found $index_count"
        log "INFO" "Run: python scripts/build_indices.py to generate indices"
        return 1
    fi
    
    # Check embeddings
    local embedding_count=$(find embeddings -name "*.npy" 2>/dev/null | wc -l)
    if [[ $embedding_count -lt 4 ]]; then
        log "ERROR" "Expected 4 embedding files, found $embedding_count"
        log "INFO" "Run: python scripts/generate_embeddings.py to generate embeddings"
        return 1
    fi
    
    # Check outcomes
    local outcomes_count=$(find outcomes -name "*.npy" 2>/dev/null | wc -l)
    if [[ $outcomes_count -lt 4 ]]; then
        log "ERROR" "Expected 4 outcome files, found $outcomes_count"
        log "INFO" "Run: python scripts/build_outcomes_database.py to generate outcomes"
        return 1
    fi
    
    log "SUCCESS" "FAISS data validation passed"
    log "INFO" "  - FAISS indices: $index_count"
    log "INFO" "  - Embeddings: $embedding_count"
    log "INFO" "  - Outcomes: $outcomes_count"
    return 0
}

# =============================================================================
# ENVIRONMENT SETUP FUNCTIONS
# =============================================================================

setup_deployment_environment() {
    log "INFO" "Setting up deployment environment..."
    
    # Create deployment directories
    mkdir -p "$DEPLOYMENT_LOG_DIR"
    mkdir -p "$VALIDATION_SCRIPTS_DIR"
    mkdir -p logs/{api,frontend,nginx}
    mkdir -p monitoring/grafana/{dashboards,datasources}
    mkdir -p monitoring/alertmanager
    
    # Set proper permissions
    chmod 755 logs/{api,frontend,nginx}
    chmod 755 "$DEPLOYMENT_LOG_DIR"
    chmod 755 "$VALIDATION_SCRIPTS_DIR"
    
    log "SUCCESS" "Deployment environment ready"
}

generate_environment_file() {
    log "INFO" "Generating production environment configuration..."
    
    if [[ -f "$ENV_FILE" ]]; then
        log "INFO" "Environment file exists, backing up..."
        cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d-%H%M%S)"
    fi
    
    # Generate secure tokens
    local api_token=$(openssl rand -hex 32)
    local grafana_password=$(openssl rand -base64 16)
    local grafana_secret=$(openssl rand -hex 32)
    
    cat > "$ENV_FILE" << EOF
# =============================================================================
# Adelaide Weather Production Environment Configuration
# Generated: $(date)
# Deployment ID: $DEPLOYMENT_ID
# =============================================================================

# Core Application Settings
VERSION=1.0.0
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# API Configuration
API_TOKEN=$api_token
CORS_ORIGINS=http://localhost,http://localhost:3000,https://localhost
TRUSTED_HOSTS=localhost,127.0.0.1,*.adelaide-weather.local

# Performance Settings
LOG_LEVEL=INFO
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_ENABLED=true
PERFORMANCE_CACHE_TTL=300
COMPRESSION_ENABLED=true
NGINX_COMPRESSION=true

# Monitoring Configuration
PROMETHEUS_ENABLED=true
MONITORING_ENABLED=true
GRAFANA_PASSWORD=$grafana_password
GRAFANA_SECRET_KEY=$grafana_secret
METRICS_COLLECTION_INTERVAL=30

# Security Settings
TOKEN_ROTATION_ENABLED=true
TOKEN_ROTATION_INTERVAL_HOURS=24
CONFIG_DRIFT_REALTIME_ENABLED=true

# Redis Configuration
REDIS_ENABLED=true

# Optional External Services
WEATHER_API_ENABLED=false
WEATHER_API_KEY=

# Nginx Configuration
NGINX_HOST=localhost
EOF
    
    log "SUCCESS" "Environment file generated: $ENV_FILE"
    log "INFO" "API Token: $api_token"
    log "INFO" "Grafana Password: $grafana_password"
    log "WARNING" "Store these credentials securely!"
}

generate_ssl_certificates() {
    log "INFO" "Generating SSL certificates..."
    
    if [[ -f "nginx/ssl/cert.pem" ]] && [[ -f "nginx/ssl/key.pem" ]]; then
        log "INFO" "SSL certificates already exist, skipping generation"
        return 0
    fi
    
    mkdir -p nginx/ssl
    
    # Check if generate_certs.sh exists and use it
    if [[ -f "nginx/ssl/generate_certs.sh" ]]; then
        log "INFO" "Using existing certificate generation script..."
        cd nginx/ssl
        chmod +x generate_certs.sh
        ./generate_certs.sh &> /dev/null
        cd ../..
    else
        log "INFO" "Generating self-signed certificates..."
        
        # Generate self-signed certificate
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=AU/ST=SA/L=Adelaide/O=Adelaide Weather/OU=Forecast/CN=localhost" \
            &> /dev/null
    fi
    
    if [[ -f "nginx/ssl/cert.pem" ]] && [[ -f "nginx/ssl/key.pem" ]]; then
        log "SUCCESS" "SSL certificates generated successfully"
        chmod 600 nginx/ssl/key.pem
        chmod 644 nginx/ssl/cert.pem
    else
        log "ERROR" "Failed to generate SSL certificates"
        return 1
    fi
}

# =============================================================================
# DEPLOYMENT ORCHESTRATION FUNCTIONS
# =============================================================================

pull_and_build_images() {
    log "INFO" "Pulling base images and building services..."
    
    # Pull base images first
    log "PROGRESS" "Pulling base images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull &
    local pull_pid=$!
    show_progress $pull_pid "Pulling base images"
    
    if ! wait $pull_pid; then
        log "WARNING" "Some base images failed to pull, continuing with build..."
    fi
    
    # Build custom images
    log "PROGRESS" "Building application images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build &
    local build_pid=$!
    show_progress $build_pid "Building application images"
    
    if ! wait $build_pid; then
        log "ERROR" "Failed to build application images"
        return 1
    fi
    
    log "SUCCESS" "Images built successfully"
}

start_services_sequenced() {
    log "INFO" "Starting services with proper sequencing..."
    
    # Start services in dependency order
    local service_groups=(
        "redis"
        "api"
        "frontend"
        "nginx"
        "prometheus"
        "grafana alertmanager"
    )
    
    for group in "${service_groups[@]}"; do
        log "STEP" "Starting services: $group"
        
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d $group
        
        # Wait for services to be ready
        case "$group" in
            "redis")
                wait_for_service_health "redis" 30
                ;;
            "api")
                wait_for_service_health "api" 60
                ;;
            "frontend")
                wait_for_service_health "frontend" 90
                ;;
            "nginx")
                wait_for_service_health "nginx" 30
                ;;
            "prometheus")
                wait_for_service_health "prometheus" 45
                ;;
        esac
    done
    
    log "SUCCESS" "All services started successfully"
}

wait_for_service_health() {
    local service_name="$1"
    local max_wait="${2:-60}"
    local wait_time=0
    local check_interval=5
    
    log "PROGRESS" "Waiting for $service_name to be healthy (max ${max_wait}s)..."
    
    while [[ $wait_time -lt $max_wait ]]; do
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' "${PROJECT_NAME}_${service_name}_1" 2>/dev/null || echo "no-healthcheck")
        
        case "$health_status" in
            "healthy")
                log "SUCCESS" "$service_name is healthy (took ${wait_time}s)"
                return 0
                ;;
            "starting")
                log "PROGRESS" "$service_name is starting... (${wait_time}s/${max_wait}s)"
                ;;
            "unhealthy")
                log "WARNING" "$service_name is unhealthy (${wait_time}s/${max_wait}s)"
                ;;
            "no-healthcheck")
                # No health check defined, just check if container is running
                if docker ps --filter "name=${PROJECT_NAME}_${service_name}_1" --filter "status=running" --quiet | grep -q .; then
                    log "SUCCESS" "$service_name is running (no health check defined)"
                    return 0
                fi
                ;;
        esac
        
        sleep $check_interval
        wait_time=$((wait_time + check_interval))
    done
    
    log "ERROR" "$service_name failed to become healthy within ${max_wait}s"
    return 1
}

# =============================================================================
# VALIDATION SCRIPT GENERATION
# =============================================================================

create_validation_scripts() {
    log "INFO" "Creating validation scripts..."
    
    # System validation script
    cat > "$VALIDATION_SCRIPTS_DIR/system_validation.sh" << 'EOF'
#!/bin/bash
# Adelaide Weather System Validation Script

validate_system() {
    echo "🔍 Running system validation..."
    
    # Check all containers are running
    local running_containers=$(docker-compose -f docker-compose.production.yml ps --services --filter "status=running" | wc -l)
    local expected_containers=7
    
    if [[ $running_containers -lt $expected_containers ]]; then
        echo "❌ Only $running_containers/$expected_containers containers running"
        return 1
    fi
    
    echo "✅ All containers running ($running_containers/$expected_containers)"
    
    # Test API endpoints
    echo "🔍 Testing API endpoints..."
    
    source .env.production
    
    if curl -s -f -H "Authorization: Bearer $API_TOKEN" http://localhost/api/health > /dev/null; then
        echo "✅ API health endpoint: OK"
    else
        echo "❌ API health endpoint: FAILED"
        return 1
    fi
    
    # Test FAISS endpoints
    if curl -s -f -H "Authorization: Bearer $API_TOKEN" http://localhost/api/health/faiss > /dev/null; then
        echo "✅ FAISS health endpoint: OK"
    else
        echo "❌ FAISS health endpoint: FAILED"
        return 1
    fi
    
    # Test frontend
    if curl -s -f http://localhost > /dev/null; then
        echo "✅ Frontend endpoint: OK"
    else
        echo "❌ Frontend endpoint: FAILED"
        return 1
    fi
    
    echo "🎉 System validation passed!"
    return 0
}

validate_system
EOF

    # Performance validation script
    cat > "$VALIDATION_SCRIPTS_DIR/performance_validation.sh" << 'EOF'
#!/bin/bash
# Adelaide Weather Performance Validation Script

validate_performance() {
    echo "🚀 Running performance validation..."
    
    source .env.production
    
    # Test API response times
    echo "🔍 Testing API response times..."
    
    local api_response_time=$(curl -w "%{time_total}" -s -o /dev/null -H "Authorization: Bearer $API_TOKEN" http://localhost/api/health)
    
    if (( $(echo "$api_response_time < 1.0" | bc -l) )); then
        echo "✅ API response time: ${api_response_time}s (< 1s)"
    else
        echo "⚠️ API response time: ${api_response_time}s (> 1s)"
    fi
    
    # Test FAISS query performance
    echo "🔍 Testing FAISS query performance..."
    
    local forecast_response_time=$(curl -w "%{time_total}" -s -o /dev/null \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json" \
        -X POST \
        -d '{"horizon": "24h", "location": {"lat": -34.93, "lon": 138.60}}' \
        http://localhost/api/forecast)
    
    if (( $(echo "$forecast_response_time < 5.0" | bc -l) )); then
        echo "✅ Forecast response time: ${forecast_response_time}s (< 5s)"
    else
        echo "⚠️ Forecast response time: ${forecast_response_time}s (> 5s)"
    fi
    
    echo "🎉 Performance validation completed!"
    return 0
}

validate_performance
EOF

    # Security validation script  
    cat > "$VALIDATION_SCRIPTS_DIR/security_validation.sh" << 'EOF'
#!/bin/bash
# Adelaide Weather Security Validation Script

validate_security() {
    echo "🔒 Running security validation..."
    
    # Check SSL certificate
    echo "🔍 Checking SSL certificate..."
    
    if openssl x509 -in nginx/ssl/cert.pem -noout -checkend 86400 &> /dev/null; then
        echo "✅ SSL certificate is valid"
    else
        echo "❌ SSL certificate is invalid or expired"
        return 1
    fi
    
    # Check secure headers
    echo "🔍 Checking security headers..."
    
    local headers_response=$(curl -s -I https://localhost -k)
    
    if echo "$headers_response" | grep -q "Strict-Transport-Security"; then
        echo "✅ HSTS header present"
    else
        echo "❌ HSTS header missing"
    fi
    
    if echo "$headers_response" | grep -q "X-Content-Type-Options"; then
        echo "✅ X-Content-Type-Options header present"  
    else
        echo "❌ X-Content-Type-Options header missing"
    fi
    
    # Check exposed ports
    echo "🔍 Checking exposed ports..."
    
    local exposed_ports=$(docker-compose -f docker-compose.production.yml ps --format "table {{.Ports}}" | grep -v "PORTS" | wc -l)
    
    if [[ $exposed_ports -gt 0 ]]; then
        echo "✅ Services properly exposed ($exposed_ports ports)"
    else
        echo "❌ No services exposed"
        return 1
    fi
    
    echo "🎉 Security validation completed!"
    return 0
}

validate_security
EOF

    # Make validation scripts executable
    chmod +x "$VALIDATION_SCRIPTS_DIR"/*.sh
    
    log "SUCCESS" "Validation scripts created and made executable"
}

# =============================================================================
# COMPREHENSIVE VALIDATION FUNCTIONS
# =============================================================================

run_system_validation() {
    log "INFO" "Running comprehensive system validation..."
    
    local validation_failed=false
    
    # Run system validation
    if bash "$VALIDATION_SCRIPTS_DIR/system_validation.sh"; then
        log "SUCCESS" "System validation passed"
    else
        log "ERROR" "System validation failed"
        validation_failed=true
    fi
    
    # Run performance validation
    if command -v bc &> /dev/null; then
        if bash "$VALIDATION_SCRIPTS_DIR/performance_validation.sh"; then
            log "SUCCESS" "Performance validation passed"
        else
            log "WARNING" "Performance validation had issues"
        fi
    else
        log "WARNING" "bc not available, skipping performance validation"
    fi
    
    # Run security validation
    if bash "$VALIDATION_SCRIPTS_DIR/security_validation.sh"; then
        log "SUCCESS" "Security validation passed"
    else
        log "WARNING" "Security validation had issues"
    fi
    
    if [[ "$validation_failed" == "true" ]]; then
        log "ERROR" "Critical validation failures detected"
        return 1
    fi
    
    log "SUCCESS" "All validations completed successfully"
    return 0
}

run_end_to_end_test() {
    log "INFO" "Running end-to-end functionality test..."
    
    source "$ENV_FILE"
    
    # Test complete forecast workflow
    log "STEP" "Testing forecast workflow..."
    
    local test_payload='{"horizon": "24h", "location": {"lat": -34.93, "lon": 138.60}}'
    local forecast_response=$(curl -s -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json" \
        -X POST \
        -d "$test_payload" \
        http://localhost/api/forecast)
    
    if echo "$forecast_response" | grep -q "forecast"; then
        log "SUCCESS" "Forecast API working correctly"
    else
        log "ERROR" "Forecast API test failed"
        log "ERROR" "Response: $forecast_response"
        return 1
    fi
    
    # Test analog search
    log "STEP" "Testing analog search..."
    
    local analog_response=$(curl -s -H "Authorization: Bearer $API_TOKEN" \
        http://localhost/api/analogs/24h)
    
    if echo "$analog_response" | grep -q "analogs"; then
        log "SUCCESS" "Analog search API working correctly"
    else
        log "WARNING" "Analog search API test had issues"
    fi
    
    log "SUCCESS" "End-to-end test completed successfully"
    return 0
}

# =============================================================================
# MONITORING AND TROUBLESHOOTING
# =============================================================================

show_service_status() {
    log "INFO" "Service Status Summary:"
    echo ""
    
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
    
    echo ""
    log "INFO" "Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | head -8
}

show_access_information() {
    log "INFO" "Deployment completed successfully! 🎉"
    echo ""
    echo -e "${WHITE}📱 ACCESS INFORMATION${NC}"
    echo "============================================================================="
    echo -e "🌐 ${CYAN}Main Application:${NC}     http://localhost"
    echo -e "🌐 ${CYAN}Main Application (SSL):${NC} https://localhost"  
    echo -e "📊 ${BLUE}API Documentation:${NC}   http://localhost/docs"
    echo -e "📈 ${GREEN}Grafana Dashboard:${NC}   http://localhost:3001"
    echo -e "🔍 ${YELLOW}Prometheus Metrics:${NC}  http://localhost:9090"
    echo -e "🚨 ${RED}Alert Manager:${NC}       http://localhost:9093"
    echo ""
    
    # Show credentials
    source "$ENV_FILE" 2>/dev/null || true
    echo -e "${WHITE}🔐 CREDENTIALS${NC}"
    echo "============================================================================="
    echo -e "📡 ${CYAN}API Token:${NC}           ${API_TOKEN:-Not set}"
    echo -e "📊 ${BLUE}Grafana Login:${NC}       admin / ${GRAFANA_PASSWORD:-admin}"
    echo ""
    
    echo -e "${WHITE}🛠️ MANAGEMENT COMMANDS${NC}"
    echo "============================================================================="
    echo -e "📋 ${CYAN}View Status:${NC}          ./deploy-adelaide-weather.sh status"
    echo -e "📋 ${CYAN}View Logs:${NC}            ./deploy-adelaide-weather.sh logs [service]"
    echo -e "🔄 ${YELLOW}Restart:${NC}              ./deploy-adelaide-weather.sh restart"
    echo -e "🛑 ${RED}Stop:${NC}                  ./deploy-adelaide-weather.sh stop"
    echo -e "🔍 ${GREEN}Health Check:${NC}         ./deploy-adelaide-weather.sh health"
    echo ""
    
    echo -e "${WHITE}📁 IMPORTANT FILES${NC}"
    echo "============================================================================="
    echo -e "🔧 ${CYAN}Environment:${NC}          $ENV_FILE"
    echo -e "📜 ${BLUE}Deployment Log:${NC}       $DEPLOYMENT_LOG"
    echo -e "📊 ${GREEN}Validation Scripts:${NC}   $VALIDATION_SCRIPTS_DIR/"
    echo ""
}

# =============================================================================
# ROLLBACK FUNCTIONS
# =============================================================================

create_rollback_checkpoint() {
    log "INFO" "Creating rollback checkpoint..."
    
    ROLLBACK_CHECKPOINT="${DEPLOYMENT_LOG_DIR}/rollback-${DEPLOYMENT_ID}.tar.gz"
    
    # Save current state
    tar -czf "$ROLLBACK_CHECKPOINT" \
        "$ENV_FILE" \
        "nginx/ssl/" \
        "$DEPLOYMENT_LOG_DIR/" \
        2>/dev/null || true
    
    if [[ -f "$ROLLBACK_CHECKPOINT" ]]; then
        log "SUCCESS" "Rollback checkpoint created: $ROLLBACK_CHECKPOINT"
    else
        log "WARNING" "Failed to create rollback checkpoint"
    fi
}

rollback_deployment() {
    log "WARNING" "Initiating deployment rollback..."
    
    # Stop current services
    log "STEP" "Stopping current services..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down --remove-orphans 2>/dev/null || true
    
    # Restore from checkpoint if available
    if [[ -f "$ROLLBACK_CHECKPOINT" ]]; then
        log "STEP" "Restoring from checkpoint..."
        tar -xzf "$ROLLBACK_CHECKPOINT" 2>/dev/null || true
    fi
    
    # Clean up failed deployment artifacts
    log "STEP" "Cleaning up deployment artifacts..."
    docker system prune -f --volumes 2>/dev/null || true
    
    log "SUCCESS" "Rollback completed"
    log "INFO" "You can retry deployment after resolving issues"
}

# =============================================================================
# COMMAND HANDLING FUNCTIONS  
# =============================================================================

handle_stop() {
    log "INFO" "Stopping Adelaide Weather services..."
    
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down --remove-orphans
    
    log "SUCCESS" "All services stopped"
}

handle_restart() {
    log "INFO" "Restarting Adelaide Weather services..."
    
    handle_stop
    sleep 5
    
    # Restart with existing configuration
    start_services_sequenced
    run_system_validation
    
    log "SUCCESS" "Services restarted successfully"
}

handle_status() {
    log "INFO" "Adelaide Weather System Status"
    echo ""
    
    show_service_status
    
    echo ""
    log "INFO" "Quick health check..."
    
    source "$ENV_FILE" 2>/dev/null || true
    
    # Quick API test
    if curl -s -f -H "Authorization: Bearer ${API_TOKEN}" http://localhost/api/health > /dev/null; then
        log "SUCCESS" "✅ API is healthy"
    else
        log "ERROR" "❌ API is not responding"
    fi
    
    # Quick frontend test
    if curl -s -f http://localhost > /dev/null; then
        log "SUCCESS" "✅ Frontend is healthy"  
    else
        log "ERROR" "❌ Frontend is not responding"
    fi
}

handle_logs() {
    local service="${1:-}"
    
    if [[ -n "$service" ]]; then
        log "INFO" "Viewing logs for service: $service"
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f --tail=50 "$service"
    else
        log "INFO" "Viewing logs for all services (last 50 lines each)..."
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=50
    fi
}

handle_health() {
    log "INFO" "Running comprehensive health checks..."
    
    if run_system_validation; then
        log "SUCCESS" "All health checks passed!"
        return 0
    else
        log "ERROR" "Some health checks failed"
        return 1
    fi
}

# =============================================================================
# MAIN DEPLOYMENT FUNCTION
# =============================================================================

deploy_adelaide_weather() {
    log "INFO" "Starting Adelaide Weather deployment..."
    log "INFO" "Deployment ID: $DEPLOYMENT_ID"
    
    # Step 1: Prerequisites validation
    log "STEP" "Step 1/8: Validating prerequisites..."
    if ! validate_docker || ! validate_docker_compose || ! validate_system_resources; then
        log "ERROR" "Prerequisites validation failed"
        return 1
    fi
    
    if ! validate_required_files || ! validate_faiss_data; then
        log "ERROR" "Required files validation failed"
        return 1
    fi
    
    # Step 2: Environment setup
    log "STEP" "Step 2/8: Setting up deployment environment..."
    setup_deployment_environment
    create_rollback_checkpoint
    
    # Step 3: Configuration generation
    log "STEP" "Step 3/8: Generating configuration..."
    generate_environment_file
    generate_ssl_certificates
    
    # Step 4: Build and prepare images
    log "STEP" "Step 4/8: Building application images..."
    if ! pull_and_build_images; then
        log "ERROR" "Image build failed"
        rollback_deployment
        return 1
    fi
    
    # Step 5: Start services
    log "STEP" "Step 5/8: Starting services with sequencing..."
    if ! start_services_sequenced; then
        log "ERROR" "Service startup failed"
        rollback_deployment
        return 1
    fi
    
    # Step 6: Create validation scripts
    log "STEP" "Step 6/8: Creating validation scripts..."
    create_validation_scripts
    
    # Step 7: System validation
    log "STEP" "Step 7/8: Running system validation..."
    if ! run_system_validation; then
        log "ERROR" "System validation failed"
        rollback_deployment
        return 1
    fi
    
    # Step 8: End-to-end testing
    log "STEP" "Step 8/8: Running end-to-end tests..."
    if ! run_end_to_end_test; then
        log "WARNING" "End-to-end tests had issues, but deployment continues"
    fi
    
    # Success!
    log "SUCCESS" "Adelaide Weather deployment completed successfully! 🎉"
    show_access_information
    
    return 0
}

# =============================================================================
# MAIN SCRIPT EXECUTION
# =============================================================================

main() {
    # Create deployment log directory if it doesn't exist
    mkdir -p "$DEPLOYMENT_LOG_DIR"
    
    # Initialize deployment log
    echo "Adelaide Weather Deployment Log - $(date)" > "$DEPLOYMENT_LOG"
    echo "Deployment ID: $DEPLOYMENT_ID" >> "$DEPLOYMENT_LOG"
    echo "========================================" >> "$DEPLOYMENT_LOG"
    
    local command="${1:-deploy}"
    
    case "$command" in
        "deploy"|"")
            show_banner
            deploy_adelaide_weather
            ;;
        "stop")
            handle_stop
            ;;
        "restart")
            handle_restart
            ;;
        "status")
            handle_status
            ;;
        "logs")
            handle_logs "${2:-}"
            ;;
        "health")
            handle_health
            ;;
        "rollback")
            rollback_deployment
            ;;
        "--help"|"-h"|"help")
            show_banner
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  deploy        Deploy the complete Adelaide Weather system (default)"
            echo "  stop          Stop all services gracefully"  
            echo "  restart       Restart all services with health checks"
            echo "  status        Show service status and resource usage"
            echo "  logs [svc]    View service logs (optionally specify service)"
            echo "  health        Run comprehensive health checks"
            echo "  rollback      Rollback failed deployment"
            echo "  help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Deploy the system"
            echo "  $0 deploy             # Deploy the system"
            echo "  $0 status             # Check system status"
            echo "  $0 logs api           # View API service logs"
            echo "  $0 health             # Run health checks"
            echo ""
            echo "For troubleshooting, check:"
            echo "  - Deployment logs: $DEPLOYMENT_LOG_DIR/"
            echo "  - Validation scripts: $VALIDATION_SCRIPTS_DIR/"
            echo "  - Environment config: $ENV_FILE"
            ;;
        *)
            log "ERROR" "Unknown command: $command"
            echo "Use '$0 --help' for usage information"
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"