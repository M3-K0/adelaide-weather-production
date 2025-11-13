#!/bin/bash

# Adelaide Weather Deployment Test Script
# Tests the deployment script functionality without actually deploying

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

test_count=0
pass_count=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    ((test_count++))
    log_info "Running test: $test_name"
    
    if eval "$test_command" >/dev/null 2>&1; then
        log_success "$test_name"
        ((pass_count++))
    else
        log_error "$test_name"
    fi
}

echo "=== Adelaide Weather Deployment Script Tests ==="
echo ""

# Test 1: Script exists and is executable
run_test "Deployment script exists and is executable" "test -x ./deploy.sh"

# Test 2: Help functionality
run_test "Help functionality works" "./deploy.sh --help"

# Test 3: Environment validation
run_test "Invalid environment rejection" "! ./deploy.sh invalid_env --no-health-check 2>/dev/null"

# Test 4: Required files exist
run_test "Docker Compose files exist" "test -f docker-compose.yml && test -f docker-compose.production.yml && test -f docker-compose.staging.yml"

# Test 5: Environment config directories exist
run_test "Environment config directories exist" "test -d configs/environments/development && test -d configs/environments/staging && test -d configs/environments/production"

# Test 6: Configuration files exist
run_test "Configuration files exist" "test -f configs/environments/development/data.yaml && test -f configs/environments/staging/data.yaml && test -f configs/environments/production/data.yaml"

# Test 7: Core system files exist
run_test "Core system files exist" "test -f core/environment_config_manager.py && test -f core/secure_credential_manager.py"

# Test 8: API files exist
run_test "API files exist" "test -f api/main.py && test -f api/health_checks.py"

# Test 9: Frontend files exist
run_test "Frontend files exist" "test -f frontend/package.json"

# Test 10: Environment configuration validation
run_test "Environment config validation (development)" "python3 -c '
import sys; sys.path.append(\".\")
from core.environment_config_manager import EnvironmentConfigManager
manager = EnvironmentConfigManager(environment=\"development\")
config = manager.load_config()
'"

run_test "Environment config validation (staging)" "python3 -c '
import sys; sys.path.append(\".\")
from core.environment_config_manager import EnvironmentConfigManager
manager = EnvironmentConfigManager(environment=\"staging\")
config = manager.load_config()
'"

run_test "Environment config validation (production)" "python3 -c '
import sys; sys.path.append(\".\")
from core.environment_config_manager import EnvironmentConfigManager
manager = EnvironmentConfigManager(environment=\"production\")
config = manager.load_config()
'"

# Test 11: Docker Compose syntax validation
if command -v docker-compose >/dev/null 2>&1; then
    run_test "Development compose syntax" "docker-compose -f docker-compose.yml -f docker-compose.dev.yml config >/dev/null"
    run_test "Staging compose syntax" "docker-compose -f docker-compose.staging.yml config >/dev/null"
    run_test "Production compose syntax" "docker-compose -f docker-compose.production.yml config >/dev/null"
elif docker compose version >/dev/null 2>&1; then
    run_test "Development compose syntax" "docker compose -f docker-compose.yml -f docker-compose.dev.yml config >/dev/null"
    run_test "Staging compose syntax" "docker compose -f docker-compose.staging.yml config >/dev/null"
    run_test "Production compose syntax" "docker compose -f docker-compose.production.yml config >/dev/null"
else
    log_warn "Docker Compose not found - skipping syntax validation tests"
fi

# Summary
echo ""
echo "=== Test Results ==="
echo "Tests run: $test_count"
echo "Tests passed: $pass_count"
echo "Tests failed: $((test_count - pass_count))"

if [[ $pass_count -eq $test_count ]]; then
    log_success "All tests passed! Deployment script is ready for use."
    exit 0
else
    log_error "Some tests failed. Please review the issues above."
    exit 1
fi