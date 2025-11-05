#!/bin/bash
# Adelaide Weather E2E Smoke Test Runner
# ====================================
# 
# Comprehensive smoke test runner for the Adelaide Weather Forecasting System.
# This script validates the complete critical path including:
# - Authentication flow
# - Nginx proxy integration
# - FAISS search integration
# - Metrics export
# - Performance validation
#
# Usage:
#   ./run_smoke_tests.sh [options]
#
# Options:
#   --skip-setup     Skip docker-compose setup (use existing services)
#   --cleanup-only   Only cleanup existing services and exit
#   --verbose        Enable verbose output
#   --timeout NUM    Set custom timeout in seconds (default: 300)
#
# Exit Codes:
#   0 - All tests passed
#   1 - Some tests failed
#   2 - Setup/infrastructure failure
#   130 - User interrupted

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}"
SMOKE_TEST_SCRIPT="${PROJECT_DIR}/test_e2e_smoke.py"
RESULTS_FILE="${PROJECT_DIR}/e2e_smoke_test_results.json"
LOG_FILE="${PROJECT_DIR}/smoke_test_run.log"

# Default values
SKIP_SETUP=false
CLEANUP_ONLY=false
VERBOSE=false
TIMEOUT=300
TEST_TOKEN="test-e2e-smoke-token-12345"

# Trap to ensure cleanup on exit
cleanup() {
    if [[ "${CLEANUP_ONLY}" == "true" || "${1:-}" == "EXIT" ]]; then
        echo -e "${YELLOW}🧹 Cleaning up test environment...${NC}"
        cd "${PROJECT_DIR}"
        docker-compose down --remove-orphans 2>/dev/null || true
        echo -e "${GREEN}✅ Cleanup complete${NC}"
    fi
}
trap cleanup EXIT

print_header() {
    echo -e "\n${BOLD}${CYAN}$(printf '=%.0s' {1..80})${NC}"
    echo -e "${BOLD}${CYAN}$(printf '%*s' $(((80+${#1})/2)) "$1")${NC}"
    echo -e "${BOLD}${CYAN}$(printf '=%.0s' {1..80})${NC}\n"
}

print_usage() {
    cat << EOF
Adelaide Weather E2E Smoke Test Runner

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --skip-setup        Skip docker-compose setup (use existing services)
    --cleanup-only      Only cleanup existing services and exit
    --verbose           Enable verbose output
    --timeout NUM       Set custom timeout in seconds (default: 300)
    --help             Show this help message

DESCRIPTION:
    Runs comprehensive E2E smoke tests for the Adelaide Weather system.
    Tests validate the complete request flow: Browser → Nginx → FastAPI → FAISS → Response

TEST SCENARIOS:
    1. 401 without token - Verify unauthorized access rejection
    2. 200 with token for /health - Verify authenticated health endpoint
    3. 200 with token for /forecast - Verify forecast with real FAISS data
    4. 200 for /metrics - Verify Prometheus metrics export
    5. Proxy validation - Verify Nginx integration works correctly

EXIT CODES:
    0   All tests passed
    1   Some tests failed
    2   Setup/infrastructure failure
    130 User interrupted

EXAMPLES:
    $0                          # Run full test suite with setup
    $0 --skip-setup             # Run tests against existing services
    $0 --cleanup-only           # Just cleanup existing services
    $0 --verbose --timeout 600  # Verbose mode with 10 minute timeout

EOF
}

log() {
    local level="$1"
    shift
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "${LOG_FILE}"
}

check_dependencies() {
    log "INFO" "🔍 Checking dependencies..."
    
    local missing_deps=()
    
    # Check required commands
    for cmd in docker docker-compose python3; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done
    
    # Check Python modules
    if ! python3 -c "import requests" 2>/dev/null; then
        missing_deps+=("python3-requests")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log "ERROR" "❌ Missing dependencies: ${missing_deps[*]}"
        echo -e "${RED}Please install missing dependencies:${NC}"
        echo -e "${YELLOW}  sudo apt-get update${NC}"
        echo -e "${YELLOW}  sudo apt-get install -y docker.io docker-compose python3 python3-pip${NC}"
        echo -e "${YELLOW}  pip3 install requests${NC}"
        exit 2
    fi
    
    log "INFO" "✅ All dependencies available"
}

check_docker() {
    log "INFO" "🐳 Checking Docker status..."
    
    if ! docker info &> /dev/null; then
        log "ERROR" "❌ Docker daemon not running"
        echo -e "${RED}Please start Docker daemon:${NC}"
        echo -e "${YELLOW}  sudo systemctl start docker${NC}"
        exit 2
    fi
    
    log "INFO" "✅ Docker is running"
}

setup_environment() {
    if [[ "${SKIP_SETUP}" == "true" ]]; then
        log "INFO" "⏭️ Skipping docker-compose setup as requested"
        return 0
    fi
    
    log "INFO" "🚀 Setting up test environment..."
    
    cd "${PROJECT_DIR}"
    
    # Export test token for docker-compose
    export API_TOKEN="${TEST_TOKEN}"
    
    # Check if services are already running
    if docker-compose ps --services --filter "status=running" | grep -q "api"; then
        log "INFO" "📋 Services already running, stopping them first..."
        docker-compose down --remove-orphans 2>/dev/null || true
        sleep 2
    fi
    
    # Start services
    log "INFO" "🏗️ Starting Adelaide Weather services..."
    if [[ "${VERBOSE}" == "true" ]]; then
        docker-compose up -d
    else
        docker-compose up -d 2>&1 | tee -a "${LOG_FILE}" | grep -E "(Starting|Created|Started|ERROR|WARNING)" || true
    fi
    
    if [[ $? -ne 0 ]]; then
        log "ERROR" "❌ Failed to start services"
        return 1
    fi
    
    log "INFO" "✅ Services started successfully"
    
    # Wait for services to be ready
    log "INFO" "⏳ Waiting for services to be ready..."
    
    local wait_count=0
    local max_wait=60
    
    while [[ $wait_count -lt $max_wait ]]; do
        if curl -s -f http://localhost/health >/dev/null 2>&1; then
            log "INFO" "✅ Services are ready"
            sleep 5  # Additional settling time
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((wait_count++))
    done
    
    log "ERROR" "❌ Services did not become ready within ${max_wait} attempts"
    
    # Show service logs for debugging
    echo -e "\n${YELLOW}Service logs for debugging:${NC}"
    docker-compose logs --tail=20
    
    return 1
}

run_smoke_tests() {
    log "INFO" "🧪 Running E2E smoke tests..."
    
    if [[ ! -f "${SMOKE_TEST_SCRIPT}" ]]; then
        log "ERROR" "❌ Smoke test script not found: ${SMOKE_TEST_SCRIPT}"
        return 1
    fi
    
    # Run the Python smoke test script
    cd "${PROJECT_DIR}"
    
    local python_cmd="python3"
    if command -v python &> /dev/null; then
        python_cmd="python"
    fi
    
    log "INFO" "🐍 Executing smoke tests with ${python_cmd}..."
    
    if [[ "${VERBOSE}" == "true" ]]; then
        timeout "${TIMEOUT}" "${python_cmd}" "${SMOKE_TEST_SCRIPT}"
    else
        timeout "${TIMEOUT}" "${python_cmd}" "${SMOKE_TEST_SCRIPT}" 2>&1 | tee -a "${LOG_FILE}"
    fi
    
    local test_exit_code=$?
    
    if [[ $test_exit_code -eq 0 ]]; then
        log "INFO" "✅ All smoke tests passed"
    elif [[ $test_exit_code -eq 130 ]]; then
        log "WARN" "⚠️ Tests interrupted by user"
        return 130
    elif [[ $test_exit_code -eq 124 ]]; then
        log "ERROR" "❌ Tests timed out after ${TIMEOUT} seconds"
        return 1
    else
        log "ERROR" "❌ Some smoke tests failed (exit code: $test_exit_code)"
        return 1
    fi
    
    return 0
}

display_results() {
    if [[ -f "${RESULTS_FILE}" ]]; then
        log "INFO" "📊 Test results summary:"
        
        if command -v jq &> /dev/null; then
            # Pretty format with jq if available
            echo -e "\n${BOLD}Test Results:${NC}"
            jq -r '.test_results[] | "  \(.name): \(if .passed then "✅ PASS" else "❌ FAIL" end) (\(.response_time_ms // 0 | round)ms)"' "${RESULTS_FILE}"
            
            echo -e "\n${BOLD}Summary:${NC}"
            jq -r '"  Total Tests: \(.total_tests)"' "${RESULTS_FILE}"
            jq -r '"  Passed: \(.passed_tests)"' "${RESULTS_FILE}"
            jq -r '"  Failed: \(.failed_tests)"' "${RESULTS_FILE}"
            jq -r '"  Success Rate: \(.success_rate | round)%"' "${RESULTS_FILE}"
            jq -r '"  Avg Response Time: \(.avg_response_time_ms | round)ms"' "${RESULTS_FILE}"
            jq -r '"  Critical Path: \(if .critical_path_passing then "✅ PASSING" else "❌ FAILING" end)"' "${RESULTS_FILE}"
        else
            # Basic format without jq
            echo -e "\n${YELLOW}📄 Results saved to: ${RESULTS_FILE}${NC}"
            echo -e "${BLUE}Use 'cat ${RESULTS_FILE} | python3 -m json.tool' for formatted output${NC}"
        fi
    else
        log "WARN" "⚠️ Results file not found: ${RESULTS_FILE}"
    fi
}

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-setup)
                SKIP_SETUP=true
                shift
                ;;
            --cleanup-only)
                CLEANUP_ONLY=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --help)
                print_usage
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Unknown option: $1${NC}"
                print_usage
                exit 2
                ;;
        esac
    done
    
    # Handle cleanup-only mode
    if [[ "${CLEANUP_ONLY}" == "true" ]]; then
        cleanup EXIT
        exit 0
    fi
    
    # Create log file
    mkdir -p "$(dirname "${LOG_FILE}")"
    echo "# Adelaide Weather E2E Smoke Test Log - $(date)" > "${LOG_FILE}"
    
    print_header "Adelaide Weather E2E Smoke Test Suite"
    
    log "INFO" "🎯 Starting smoke test run..."
    log "INFO" "📋 Configuration:"
    log "INFO" "   • Project Directory: ${PROJECT_DIR}"
    log "INFO" "   • Skip Setup: ${SKIP_SETUP}"
    log "INFO" "   • Verbose: ${VERBOSE}"
    log "INFO" "   • Timeout: ${TIMEOUT}s"
    log "INFO" "   • Test Token: ${TEST_TOKEN:0:8}..."
    
    # Pre-flight checks
    check_dependencies
    check_docker
    
    # Setup environment
    if ! setup_environment; then
        log "ERROR" "❌ Environment setup failed"
        exit 2
    fi
    
    # Run tests
    local test_result=0
    if ! run_smoke_tests; then
        test_result=$?
    fi
    
    # Display results
    display_results
    
    # Final status
    if [[ $test_result -eq 0 ]]; then
        print_header "🎉 ALL SMOKE TESTS PASSED"
        echo -e "${GREEN}${BOLD}✅ System is ready for CI/CD pipeline integration${NC}"
        echo -e "${BLUE}📄 Detailed results: ${RESULTS_FILE}${NC}"
        echo -e "${BLUE}📄 Test log: ${LOG_FILE}${NC}"
    elif [[ $test_result -eq 130 ]]; then
        print_header "⚠️ TESTS INTERRUPTED"
        echo -e "${YELLOW}${BOLD}Tests were interrupted by user${NC}"
    else
        print_header "❌ SMOKE TESTS FAILED"
        echo -e "${RED}${BOLD}System is NOT ready for production deployment${NC}"
        echo -e "${YELLOW}Please address failed tests before proceeding${NC}"
        echo -e "${BLUE}📄 Detailed results: ${RESULTS_FILE}${NC}"
        echo -e "${BLUE}📄 Test log: ${LOG_FILE}${NC}"
    fi
    
    log "INFO" "🏁 Smoke test run completed with exit code: $test_result"
    exit $test_result
}

# Run main function with all arguments
main "$@"