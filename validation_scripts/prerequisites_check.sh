#!/bin/bash

# =============================================================================
# Prerequisites Validation Script for Adelaide Weather System
# =============================================================================
# 
# Comprehensive validation of system prerequisites before deployment.
# This script checks all requirements and provides detailed feedback.
# =============================================================================

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; ((CHECKS_PASSED++)); }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; ((CHECKS_WARNING++)); }
log_error() { echo -e "${RED}[✗]${NC} $1"; ((CHECKS_FAILED++)); }

check_docker() {
    echo "🐳 Checking Docker..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        echo "   Install: https://docs.docker.com/get-docker/"
        return 1
    fi
    
    local docker_version=$(docker --version 2>/dev/null | cut -d' ' -f3 | tr -d ',')
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        echo "   Start: sudo systemctl start docker"
        return 1
    fi
    
    # Check Docker version (require 20.0+)
    local major_version=$(echo "$docker_version" | cut -d'.' -f1)
    if [[ $major_version -lt 20 ]]; then
        log_warning "Docker version $docker_version is old (recommend 20.0+)"
    else
        log_success "Docker $docker_version is running"
    fi
    
    # Check Docker memory limit
    local docker_mem_gb=$(docker info --format '{{.MemTotal}}' 2>/dev/null | awk '{print int($1/1024/1024/1024)}')
    if [[ $docker_mem_gb -lt 4 ]]; then
        log_warning "Docker memory limit: ${docker_mem_gb}GB (recommend 8GB+)"
    else
        log_success "Docker memory: ${docker_mem_gb}GB"
    fi
}

check_docker_compose() {
    echo "🚀 Checking Docker Compose..."
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        echo "   Install: pip install docker-compose"
        return 1
    fi
    
    local compose_version=$(docker-compose --version 2>/dev/null | cut -d' ' -f3 | tr -d ',')
    local major_version=$(echo "$compose_version" | cut -d'.' -f1)
    
    if [[ $major_version -lt 2 ]]; then
        log_warning "Docker Compose v$compose_version (recommend v2.0+)"
    else
        log_success "Docker Compose v$compose_version"
    fi
    
    # Test Docker Compose functionality
    if docker-compose --help &> /dev/null; then
        log_success "Docker Compose is functional"
    else
        log_error "Docker Compose is not functional"
        return 1
    fi
}

check_system_resources() {
    echo "💻 Checking System Resources..."
    
    # Memory check
    local total_mem_gb=$(free -g | awk '/^Mem:/{print $2}')
    local available_mem_gb=$(free -g | awk '/^Mem:/{print $7}')
    
    if [[ $available_mem_gb -lt 6 ]]; then
        log_error "Available memory: ${available_mem_gb}GB (require 6GB+)"
        log_info "   Total memory: ${total_mem_gb}GB"
    elif [[ $available_mem_gb -lt 8 ]]; then
        log_warning "Available memory: ${available_mem_gb}GB (recommend 8GB+)"
    else
        log_success "Available memory: ${available_mem_gb}GB"
    fi
    
    # Disk space check
    local available_disk_gb=$(df -BG . | awk 'NR==2{print $4}' | tr -d 'G')
    
    if [[ $available_disk_gb -lt 10 ]]; then
        log_error "Available disk: ${available_disk_gb}GB (require 10GB+)"
    elif [[ $available_disk_gb -lt 20 ]]; then
        log_warning "Available disk: ${available_disk_gb}GB (recommend 20GB+)"
    else
        log_success "Available disk: ${available_disk_gb}GB"
    fi
    
    # CPU cores check
    local cpu_cores=$(nproc)
    
    if [[ $cpu_cores -lt 2 ]]; then
        log_error "CPU cores: $cpu_cores (require 2+)"
    elif [[ $cpu_cores -lt 4 ]]; then
        log_warning "CPU cores: $cpu_cores (recommend 4+)"
    else
        log_success "CPU cores: $cpu_cores"
    fi
    
    # Load average check
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | xargs)
    local load_threshold=$(echo "$cpu_cores * 0.8" | bc -l 2>/dev/null || echo "$cpu_cores")
    
    if command -v bc &> /dev/null; then
        if (( $(echo "$load_avg > $load_threshold" | bc -l) )); then
            log_warning "High system load: $load_avg (cores: $cpu_cores)"
        else
            log_success "System load: $load_avg (cores: $cpu_cores)"
        fi
    else
        log_info "System load: $load_avg (install 'bc' for threshold checking)"
    fi
}

check_required_ports() {
    echo "🔌 Checking Required Ports..."
    
    local required_ports=(80 443 3000 3001 6379 8000 9090 9093)
    local ports_in_use=()
    
    for port in "${required_ports[@]}"; do
        if ss -tuln | grep -q ":$port "; then
            ports_in_use+=($port)
        fi
    done
    
    if [[ ${#ports_in_use[@]} -gt 0 ]]; then
        log_warning "Ports already in use: ${ports_in_use[*]}"
        log_info "   Stop services using these ports or deployment may fail"
    else
        log_success "All required ports (${required_ports[*]}) are available"
    fi
}

check_network_connectivity() {
    echo "🌐 Checking Network Connectivity..."
    
    # Check internet connectivity for Docker Hub
    if curl -s --connect-timeout 5 --max-time 10 https://registry-1.docker.io/v2/ &> /dev/null; then
        log_success "Docker Hub connectivity: OK"
    else
        log_warning "Docker Hub connectivity: FAILED (may affect image pulling)"
    fi
    
    # Check if behind corporate firewall
    if curl -s --connect-timeout 5 --max-time 10 https://github.com &> /dev/null; then
        log_success "GitHub connectivity: OK"
    else
        log_warning "GitHub connectivity: FAILED (may be behind firewall)"
    fi
    
    # Check DNS resolution
    if nslookup docker.io &> /dev/null; then
        log_success "DNS resolution: OK"
    else
        log_warning "DNS resolution: Issues detected"
    fi
}

check_required_tools() {
    echo "🛠️ Checking Required Tools..."
    
    local required_tools=(
        "curl:HTTP client for testing"
        "openssl:SSL certificate generation"
        "git:Version control (optional)"
        "jq:JSON processing (optional)"
    )
    
    local optional_tools=(
        "bc:Numeric calculations"
        "htop:System monitoring"
        "tree:Directory visualization"
    )
    
    for tool_desc in "${required_tools[@]}"; do
        local tool=$(echo "$tool_desc" | cut -d':' -f1)
        local desc=$(echo "$tool_desc" | cut -d':' -f2)
        
        if command -v "$tool" &> /dev/null; then
            log_success "$tool: Available ($desc)"
        else
            if [[ "$tool" == "git" ]] || [[ "$tool" == "jq" ]]; then
                log_warning "$tool: Missing ($desc) - optional"
            else
                log_error "$tool: Missing ($desc) - install required"
            fi
        fi
    done
    
    for tool_desc in "${optional_tools[@]}"; do
        local tool=$(echo "$tool_desc" | cut -d':' -f1)
        local desc=$(echo "$tool_desc" | cut -d':' -f2)
        
        if command -v "$tool" &> /dev/null; then
            log_success "$tool: Available ($desc)"
        else
            log_info "$tool: Not available ($desc) - optional"
        fi
    done
}

check_file_structure() {
    echo "📁 Checking File Structure..."
    
    local project_root="/home/micha/adelaide-weather-final"
    
    if [[ ! -d "$project_root" ]]; then
        log_error "Project root directory not found: $project_root"
        return 1
    fi
    
    cd "$project_root" || exit 1
    
    local required_files=(
        "docker-compose.production.yml:Main orchestration file"
        "nginx/nginx.conf:Nginx configuration"
        "api/Dockerfile.production:API container definition"
        "frontend/Dockerfile.production:Frontend container definition"
    )
    
    local required_dirs=(
        "api:API service code"
        "frontend:Frontend application"
        "nginx:Nginx configuration"
        "monitoring:Monitoring configuration"
        "indices:FAISS indices"
        "embeddings:ML embeddings"
        "outcomes:Forecast outcomes"
    )
    
    for file_desc in "${required_files[@]}"; do
        local file=$(echo "$file_desc" | cut -d':' -f1)
        local desc=$(echo "$file_desc" | cut -d':' -f2)
        
        if [[ -f "$file" ]]; then
            local size_kb=$(du -k "$file" | cut -f1)
            log_success "$file: Present (${size_kb}KB - $desc)"
        else
            log_error "$file: Missing ($desc)"
        fi
    done
    
    for dir_desc in "${required_dirs[@]}"; do
        local dir=$(echo "$dir_desc" | cut -d':' -f1)
        local desc=$(echo "$dir_desc" | cut -d':' -f2)
        
        if [[ -d "$dir" ]]; then
            local file_count=$(find "$dir" -type f 2>/dev/null | wc -l)
            log_success "$dir/: Present (${file_count} files - $desc)"
        else
            log_error "$dir/: Missing ($desc)"
        fi
    done
}

check_faiss_data() {
    echo "🧠 Checking FAISS Data..."
    
    # Check FAISS indices
    local index_count=$(find indices -name "*.faiss" 2>/dev/null | wc -l)
    local expected_indices=8
    
    if [[ $index_count -eq $expected_indices ]]; then
        log_success "FAISS indices: $index_count/$expected_indices present"
        
        # Show index sizes
        local total_index_size_mb=0
        while IFS= read -r -d '' index_file; do
            local size_mb=$(du -m "$index_file" | cut -f1)
            total_index_size_mb=$((total_index_size_mb + size_mb))
        done < <(find indices -name "*.faiss" -print0 2>/dev/null)
        
        log_info "   Total index size: ${total_index_size_mb}MB"
        
    elif [[ $index_count -gt 0 ]]; then
        log_warning "FAISS indices: $index_count/$expected_indices present (some missing)"
    else
        log_error "FAISS indices: None found (run: python scripts/build_indices.py)"
    fi
    
    # Check embeddings
    local embedding_count=$(find embeddings -name "*.npy" 2>/dev/null | wc -l)
    local expected_embeddings=4
    
    if [[ $embedding_count -eq $expected_embeddings ]]; then
        log_success "Embeddings: $embedding_count/$expected_embeddings present"
    elif [[ $embedding_count -gt 0 ]]; then
        log_warning "Embeddings: $embedding_count/$expected_embeddings present (some missing)"
    else
        log_error "Embeddings: None found (run: python scripts/generate_embeddings.py)"
    fi
    
    # Check outcomes
    local outcomes_count=$(find outcomes -name "*.npy" 2>/dev/null | wc -l)
    local expected_outcomes=4
    
    if [[ $outcomes_count -eq $expected_outcomes ]]; then
        log_success "Outcomes: $outcomes_count/$expected_outcomes present"
    elif [[ $outcomes_count -gt 0 ]]; then
        log_warning "Outcomes: $outcomes_count/$expected_outcomes present (some missing)"
    else
        log_error "Outcomes: None found (run: python scripts/build_outcomes_database.py)"
    fi
}

main() {
    echo "🔍 ADELAIDE WEATHER SYSTEM - PREREQUISITES CHECK"
    echo "================================================================="
    echo ""
    
    check_docker
    echo ""
    
    check_docker_compose
    echo ""
    
    check_system_resources
    echo ""
    
    check_required_ports
    echo ""
    
    check_network_connectivity
    echo ""
    
    check_required_tools
    echo ""
    
    check_file_structure
    echo ""
    
    check_faiss_data
    echo ""
    
    # Summary
    echo "================================================================="
    echo "📊 PREREQUISITES CHECK SUMMARY"
    echo "================================================================="
    echo -e "${GREEN}✓ Passed:${NC}   $CHECKS_PASSED"
    echo -e "${YELLOW}! Warnings:${NC} $CHECKS_WARNING"
    echo -e "${RED}✗ Failed:${NC}   $CHECKS_FAILED"
    echo ""
    
    if [[ $CHECKS_FAILED -eq 0 ]]; then
        if [[ $CHECKS_WARNING -eq 0 ]]; then
            echo -e "${GREEN}🎉 All prerequisites met! Ready for deployment.${NC}"
            exit 0
        else
            echo -e "${YELLOW}⚠️ Prerequisites mostly met with warnings. Deployment should work.${NC}"
            exit 0
        fi
    else
        echo -e "${RED}❌ Critical prerequisites missing. Fix issues before deployment.${NC}"
        echo ""
        echo "🛠️ Next Steps:"
        echo "1. Address all failed checks above"
        echo "2. Re-run this script to verify fixes"
        echo "3. Proceed with: ./deploy-adelaide-weather.sh"
        exit 1
    fi
}

main "$@"