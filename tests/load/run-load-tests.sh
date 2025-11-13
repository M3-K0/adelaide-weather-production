#!/bin/bash

#===============================================================================
# Adelaide Weather API - Comprehensive Load Testing Suite
# 
# This script orchestrates the complete load testing and benchmarking framework
# including progressive load phases, geographic distribution, and capacity analysis.
#
# Usage: ./run-load-tests.sh [environment] [test-suite] [options]
#
# Examples:
#   ./run-load-tests.sh development baseline
#   ./run-load-tests.sh staging full-suite --parallel
#   ./run-load-tests.sh production smoke-test --duration=300
#===============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="$SCRIPT_DIR/reports"
CONFIGS_DIR="$SCRIPT_DIR/configs"
UTILS_DIR="$SCRIPT_DIR/utils"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
ENVIRONMENT="${1:-development}"
TEST_SUITE="${2:-baseline}"
PARALLEL_EXECUTION=false
DURATION=""
USERS=""
MONITORING_ENABLED=true
GENERATE_REPORT=true
CLEANUP_AFTER=true

# Parse command line options
shift 2 2>/dev/null || true
while [[ $# -gt 0 ]]; do
  case $1 in
    --parallel)
      PARALLEL_EXECUTION=true
      shift
      ;;
    --duration=*)
      DURATION="${1#*=}"
      shift
      ;;
    --users=*)
      USERS="${1#*=}"
      shift
      ;;
    --no-monitoring)
      MONITORING_ENABLED=false
      shift
      ;;
    --no-report)
      GENERATE_REPORT=false
      shift
      ;;
    --no-cleanup)
      CLEANUP_AFTER=false
      shift
      ;;
    --help)
      show_help
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      show_help
      exit 1
      ;;
  esac
done

#===============================================================================
# Helper Functions
#===============================================================================

show_help() {
  cat << EOF
Adelaide Weather API - Load Testing Suite

Usage: $0 [environment] [test-suite] [options]

Environments:
  development    Local development environment (default)
  staging        Staging environment  
  production     Production environment (limited tests)
  cloud-scale    Multi-region cloud testing

Test Suites:
  baseline       Basic load test (10 users, 5 minutes)
  smoke-test     Quick validation (5 users, 2 minutes)
  target-load    Expected peak load (50 users, 10 minutes)
  stress-test    High load testing (100 users, 5 minutes)
  spike-test     Traffic spike simulation (200 users, 3 minutes)
  capacity-test  Progressive capacity analysis
  endurance-test Long-running stability test (30 minutes)
  full-suite     Complete test suite (all scenarios)
  geographic     Multi-region load distribution
  mixed-workload Realistic usage patterns

Options:
  --parallel           Execute tests in parallel where possible
  --duration=SECONDS   Override test duration
  --users=COUNT        Override user count
  --no-monitoring      Disable monitoring integration
  --no-report          Skip report generation
  --no-cleanup         Skip cleanup after tests
  --help              Show this help message

Examples:
  $0 development baseline
  $0 staging target-load --duration=600
  $0 production smoke-test --users=5
  $0 development full-suite --parallel
  $0 cloud-scale geographic --monitoring
EOF
}

log() {
  echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

error() {
  echo -e "${RED}[ERROR]${NC} $*" >&2
}

warning() {
  echo -e "${YELLOW}[WARNING]${NC} $*"
}

info() {
  echo -e "${BLUE}[INFO]${NC} $*"
}

#===============================================================================
# Environment Validation
#===============================================================================

validate_environment() {
  log "Validating test environment: $ENVIRONMENT"
  
  # Check if environment configuration exists
  local env_config="$CONFIGS_DIR/load-test-environments.json"
  if [[ ! -f "$env_config" ]]; then
    error "Environment configuration not found: $env_config"
    exit 1
  fi
  
  # Validate required tools
  local required_tools=("curl" "jq")
  local optional_tools=("k6" "artillery" "docker")
  
  for tool in "${required_tools[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
      error "Required tool not found: $tool"
      exit 1
    fi
  done
  
  for tool in "${optional_tools[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
      warning "Optional tool not found: $tool"
    fi
  done
  
  # Load environment configuration
  if ! ENV_CONFIG=$(jq -r ".environments.$ENVIRONMENT" "$env_config" 2>/dev/null); then
    error "Environment '$ENVIRONMENT' not found in configuration"
    exit 1
  fi
  
  if [[ "$ENV_CONFIG" == "null" ]]; then
    error "Environment '$ENVIRONMENT' not configured"
    exit 1
  fi
  
  # Extract environment endpoints
  API_BASE=$(echo "$ENV_CONFIG" | jq -r '.endpoints.api_base')
  FRONTEND_BASE=$(echo "$ENV_CONFIG" | jq -r '.endpoints.frontend_base')
  API_TOKEN=$(echo "$ENV_CONFIG" | jq -r '.authentication.api_token')
  
  # Handle environment variables in token
  if [[ "$API_TOKEN" =~ \$\{.*\} ]]; then
    local token_var=$(echo "$API_TOKEN" | sed 's/.*{\(.*\)}.*/\1/')
    API_TOKEN="${!token_var:-$API_TOKEN}"
  fi
  
  info "API Base: $API_BASE"
  info "Frontend Base: $FRONTEND_BASE"
  info "Token configured: ${API_TOKEN:0:10}..."
}

#===============================================================================
# System Health Checks
#===============================================================================

check_system_health() {
  log "Performing system health checks..."
  
  # API health check
  local health_response
  if health_response=$(curl -s -f "$API_BASE/health" 2>/dev/null); then
    local ready=$(echo "$health_response" | jq -r '.ready // false')
    if [[ "$ready" == "true" ]]; then
      info "✅ API health check passed"
    else
      error "❌ API not ready: $health_response"
      exit 1
    fi
  else
    error "❌ API health check failed - server not responding"
    exit 1
  fi
  
  # Frontend health check (if applicable)
  if [[ "$FRONTEND_BASE" != "null" ]] && [[ -n "$FRONTEND_BASE" ]]; then
    if curl -s -f "$FRONTEND_BASE/" -o /dev/null 2>/dev/null; then
      info "✅ Frontend health check passed"
    else
      warning "⚠️  Frontend health check failed"
    fi
  fi
  
  # Authentication test
  local auth_response
  if auth_response=$(curl -s -H "Authorization: Bearer $API_TOKEN" "$API_BASE/forecast?horizon=6h&vars=t2m" 2>/dev/null); then
    local status=$(echo "$auth_response" | jq -r '.error.code // 200')
    if [[ "$status" == "200" ]] || [[ "$status" == "null" ]]; then
      info "✅ Authentication test passed"
    else
      error "❌ Authentication test failed: $status"
      exit 1
    fi
  else
    error "❌ Authentication test failed"
    exit 1
  fi
}

#===============================================================================
# Test Data Generation
#===============================================================================

prepare_test_data() {
  log "Preparing test data..."
  
  local test_data_dir="$REPORTS_DIR/test-data"
  mkdir -p "$test_data_dir"
  
  # Generate CSV test data using helper utilities
  if [[ -f "$UTILS_DIR/load-test-helpers.js" ]]; then
    node "$UTILS_DIR/load-test-helpers.js" generate-data "$test_data_dir" 1000
  else
    warning "Test data generator not found, creating minimal test data"
    
    # Create minimal CSV files
    cat > "$test_data_dir/variables.csv" << EOF
horizon,variables
6h,t2m
12h,t2m,u10,v10
24h,t2m,u10,v10,msl
48h,t2m,u10,v10,msl,cape
EOF
    
    cat > "$test_data_dir/tokens.csv" << EOF
token
$API_TOKEN
EOF
  fi
  
  info "✅ Test data prepared"
}

#===============================================================================
# Monitoring Setup
#===============================================================================

setup_monitoring() {
  if [[ "$MONITORING_ENABLED" == "false" ]]; then
    info "Monitoring disabled, skipping setup"
    return 0
  fi
  
  log "Setting up monitoring..."
  
  # Check if Prometheus is available
  local prometheus_url=$(echo "$ENV_CONFIG" | jq -r '.monitoring.prometheus_url // "http://localhost:9090"')
  if curl -s -f "$prometheus_url/api/v1/status/config" -o /dev/null 2>/dev/null; then
    info "✅ Prometheus monitoring available at $prometheus_url"
    export PROMETHEUS_URL="$prometheus_url"
  else
    warning "⚠️  Prometheus not available, metrics collection limited"
  fi
  
  # Check if Grafana is available
  local grafana_url=$(echo "$ENV_CONFIG" | jq -r '.monitoring.grafana_url // "http://localhost:3001"')
  if curl -s -f "$grafana_url/api/health" -o /dev/null 2>/dev/null; then
    info "✅ Grafana dashboard available at $grafana_url"
  else
    warning "⚠️  Grafana not available, dashboard visualization limited"
  fi
}

#===============================================================================
# Test Suite Execution
#===============================================================================

execute_test_suite() {
  log "Executing test suite: $TEST_SUITE"
  
  local timestamp=$(date +%Y%m%d_%H%M%S)
  local results_dir="$REPORTS_DIR/run_$timestamp"
  mkdir -p "$results_dir"
  
  case "$TEST_SUITE" in
    "baseline")
      run_baseline_test "$results_dir"
      ;;
    "smoke-test")
      run_smoke_test "$results_dir"
      ;;
    "target-load")
      run_target_load_test "$results_dir"
      ;;
    "stress-test")
      run_stress_test "$results_dir"
      ;;
    "spike-test")
      run_spike_test "$results_dir"
      ;;
    "capacity-test")
      run_capacity_test "$results_dir"
      ;;
    "endurance-test")
      run_endurance_test "$results_dir"
      ;;
    "full-suite")
      run_full_suite "$results_dir"
      ;;
    "geographic")
      run_geographic_test "$results_dir"
      ;;
    "mixed-workload")
      run_mixed_workload_test "$results_dir"
      ;;
    *)
      error "Unknown test suite: $TEST_SUITE"
      exit 1
      ;;
  esac
  
  # Store test metadata
  cat > "$results_dir/test-metadata.json" << EOF
{
  "test_suite": "$TEST_SUITE",
  "environment": "$ENVIRONMENT",
  "timestamp": "$timestamp",
  "duration": "$DURATION",
  "users": "$USERS",
  "parallel_execution": $PARALLEL_EXECUTION,
  "monitoring_enabled": $MONITORING_ENABLED,
  "api_base": "$API_BASE",
  "frontend_base": "$FRONTEND_BASE"
}
EOF
  
  export RESULTS_DIR="$results_dir"
}

run_baseline_test() {
  local results_dir="$1"
  info "Running baseline load test (10 users, 5 minutes)"
  
  # Use Artillery for baseline test
  if command -v artillery &> /dev/null; then
    local config="$SCRIPT_DIR/artillery/api-load-scenarios.yml"
    local output="$results_dir/baseline-artillery-results.json"
    
    # Override configuration for baseline
    export ARTILLERY_ENVIRONMENT="development"
    export ARTILLERY_PHASES='[{"duration": 60, "arrivalRate": 2}, {"duration": 300, "arrivalRate": 2}]'
    
    artillery run "$config" --output "$output" \
      --environment development \
      || error "Artillery baseline test failed"
      
    info "✅ Baseline test completed"
  else
    error "Artillery not available for baseline test"
    return 1
  fi
}

run_target_load_test() {
  local results_dir="$1"
  info "Running target load test (50 users, 10 minutes)"
  
  # Use K6 for target load test
  if command -v k6 &> /dev/null; then
    local script="$SCRIPT_DIR/k6/complex-user-journeys.js"
    local output="$results_dir/target-load-k6-results.json"
    
    K6_USERS="${USERS:-50}" \
    K6_DURATION="${DURATION:-600}" \
    API_BASE="$API_BASE" \
    FRONTEND_BASE="$FRONTEND_BASE" \
    API_TOKEN="$API_TOKEN" \
    k6 run --out json="$output" "$script" \
      || error "K6 target load test failed"
      
    info "✅ Target load test completed"
  else
    error "K6 not available for target load test"
    return 1
  fi
}

run_capacity_test() {
  local results_dir="$1"
  info "Running capacity analysis test"
  
  # Use capacity planning script
  if [[ -f "$SCRIPT_DIR/scripts/capacity-planning.js" ]]; then
    node "$SCRIPT_DIR/scripts/capacity-planning.js" \
      --base_url="$API_BASE" \
      --frontend_url="$FRONTEND_BASE" \
      --api_token="$API_TOKEN" \
      --report_dir="$results_dir" \
      --monitoring_enabled="$MONITORING_ENABLED" \
      || error "Capacity planning test failed"
      
    info "✅ Capacity analysis completed"
  else
    error "Capacity planning script not found"
    return 1
  fi
}

run_geographic_test() {
  local results_dir="$1"
  info "Running geographic load distribution test"
  
  # Use geographic load simulation script
  if [[ -f "$SCRIPT_DIR/scripts/geographic-load-simulation.js" ]]; then
    node "$SCRIPT_DIR/scripts/geographic-load-simulation.js" \
      --base_url="$API_BASE" \
      --frontend_url="$FRONTEND_BASE" \
      --api_token="$API_TOKEN" \
      --total_users="${USERS:-100}" \
      --test_duration="${DURATION:-600}" \
      --report_dir="$results_dir" \
      --concurrent_regions=true \
      || error "Geographic load test failed"
      
    info "✅ Geographic load test completed"
  else
    error "Geographic load simulation script not found"
    return 1
  fi
}

run_full_suite() {
  local results_dir="$1"
  info "Running full test suite"
  
  if [[ "$PARALLEL_EXECUTION" == "true" ]]; then
    info "Executing tests in parallel"
    
    # Run multiple test types in parallel
    (run_baseline_test "$results_dir/baseline" &)
    (run_target_load_test "$results_dir/target-load" &)
    (run_stress_test "$results_dir/stress" &)
    
    # Wait for all background jobs
    wait
  else
    info "Executing tests sequentially"
    
    # Run tests sequentially with cool-down periods
    run_baseline_test "$results_dir/baseline"
    sleep 60
    
    run_target_load_test "$results_dir/target-load"
    sleep 60
    
    run_stress_test "$results_dir/stress"
    sleep 60
    
    run_capacity_test "$results_dir/capacity"
  fi
  
  info "✅ Full test suite completed"
}

run_smoke_test() {
  local results_dir="$1"
  info "Running smoke test (5 users, 2 minutes)"
  
  # Quick validation test
  K6_USERS="${USERS:-5}" \
  K6_DURATION="${DURATION:-120}" \
  API_BASE="$API_BASE" \
  API_TOKEN="$API_TOKEN" \
  k6 run --quiet --out json="$results_dir/smoke-test-results.json" - << 'EOF'
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: parseInt(__ENV.K6_USERS) || 5,
  duration: (parseInt(__ENV.K6_DURATION) || 120) + 's',
};

export default function() {
  const response = http.get(__ENV.API_BASE + '/health');
  check(response, {
    'health check status is 200': (r) => r.status === 200,
  });
  
  const forecast = http.get(__ENV.API_BASE + '/forecast?horizon=6h&vars=t2m', {
    headers: { 'Authorization': 'Bearer ' + __ENV.API_TOKEN },
  });
  check(forecast, {
    'forecast status is 200': (r) => r.status === 200,
  });
}
EOF

  info "✅ Smoke test completed"
}

run_stress_test() {
  local results_dir="$1"
  info "Running stress test (100 users, 5 minutes)"
  
  # Use artillery for stress testing
  local stress_config="$results_dir/stress-test-config.yml"
  
  cat > "$stress_config" << EOF
config:
  target: '$API_BASE'
  phases:
    - duration: 60
      arrivalRate: 5
    - duration: 300
      arrivalRate: 20
    - duration: 60
      arrivalRate: 0
  http:
    timeout: 30
    
scenarios:
  - name: stress_scenario
    weight: 100
    flow:
      - get:
          url: "/forecast"
          headers:
            Authorization: "Bearer $API_TOKEN"
          qs:
            horizon: "24h"
            vars: "t2m,u10,v10,msl"
          expect:
            - statusCode: 200
      - think: 1
EOF

  artillery run "$stress_config" --output "$results_dir/stress-test-results.json" \
    || error "Stress test failed"
    
  info "✅ Stress test completed"
}

run_spike_test() {
  local results_dir="$1"
  info "Running spike test (200 users, 3 minutes)"
  
  # Quick spike to test system resilience
  K6_USERS="${USERS:-200}" \
  K6_DURATION="${DURATION:-180}" \
  API_BASE="$API_BASE" \
  API_TOKEN="$API_TOKEN" \
  k6 run --out json="$results_dir/spike-test-results.json" - << 'EOF'
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: parseInt(__ENV.K6_USERS) || 200 },
    { duration: '120s', target: parseInt(__ENV.K6_USERS) || 200 },
    { duration: '30s', target: 0 },
  ],
};

export default function() {
  const response = http.get(__ENV.API_BASE + '/forecast?horizon=6h&vars=t2m,u10,v10', {
    headers: { 'Authorization': 'Bearer ' + __ENV.API_TOKEN },
  });
  
  check(response, {
    'spike test response': (r) => r.status === 200 || r.status === 429,
  });
}
EOF

  info "✅ Spike test completed"
}

run_endurance_test() {
  local results_dir="$1"
  info "Running endurance test (30 minutes sustained load)"
  
  # Long-running stability test
  K6_USERS="${USERS:-25}" \
  K6_DURATION="${DURATION:-1800}" \
  API_BASE="$API_BASE" \
  API_TOKEN="$API_TOKEN" \
  k6 run --out json="$results_dir/endurance-test-results.json" - << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: parseInt(__ENV.K6_USERS) || 25 },
    { duration: '26m', target: parseInt(__ENV.K6_USERS) || 25 },
    { duration: '2m', target: 0 },
  ],
};

export default function() {
  const response = http.get(__ENV.API_BASE + '/forecast?horizon=24h&vars=t2m,u10,v10,msl', {
    headers: { 'Authorization': 'Bearer ' + __ENV.API_TOKEN },
  });
  
  check(response, {
    'endurance test response': (r) => r.status === 200,
  });
  
  sleep(Math.random() * 3 + 2); // 2-5 second think time
}
EOF

  info "✅ Endurance test completed"
}

run_mixed_workload_test() {
  local results_dir="$1"
  info "Running mixed workload test (realistic usage patterns)"
  
  # Use complex user journeys script
  if [[ -f "$SCRIPT_DIR/k6/complex-user-journeys.js" ]]; then
    K6_USERS="${USERS:-75}" \
    K6_DURATION="${DURATION:-900}" \
    API_BASE="$API_BASE" \
    FRONTEND_BASE="$FRONTEND_BASE" \
    API_TOKEN="$API_TOKEN" \
    k6 run --out json="$results_dir/mixed-workload-results.json" \
      "$SCRIPT_DIR/k6/complex-user-journeys.js" \
      || error "Mixed workload test failed"
      
    info "✅ Mixed workload test completed"
  else
    error "Complex user journeys script not found"
    return 1
  fi
}

#===============================================================================
# Results Analysis and Reporting
#===============================================================================

analyze_results() {
  if [[ "$GENERATE_REPORT" == "false" ]]; then
    info "Report generation disabled, skipping analysis"
    return 0
  fi
  
  log "Analyzing test results..."
  
  local results_dir="$RESULTS_DIR"
  
  # Find all result files
  local result_files=($(find "$results_dir" -name "*results.json" -type f))
  
  if [[ ${#result_files[@]} -eq 0 ]]; then
    warning "No result files found for analysis"
    return 0
  fi
  
  # Analyze each result file
  for result_file in "${result_files[@]}"; do
    local base_name=$(basename "$result_file" .json)
    local analysis_file="$results_dir/${base_name}-analysis.json"
    
    if [[ -f "$UTILS_DIR/load-test-helpers.js" ]]; then
      node "$UTILS_DIR/load-test-helpers.js" analyze-results "$result_file" k6 > "$analysis_file" 2>/dev/null || {
        warning "Failed to analyze $result_file"
        continue
      }
      info "✅ Analyzed: $base_name"
    fi
  done
  
  # Generate summary report
  generate_summary_report "$results_dir"
}

generate_summary_report() {
  local results_dir="$1"
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  
  log "Generating summary report..."
  
  cat > "$results_dir/load-test-summary.md" << EOF
# Load Test Summary Report

**Test Suite**: $TEST_SUITE  
**Environment**: $ENVIRONMENT  
**Execution Time**: $timestamp  
**Parallel Execution**: $PARALLEL_EXECUTION  

## Test Configuration
- **API Base**: $API_BASE
- **Frontend Base**: $FRONTEND_BASE
- **Duration Override**: ${DURATION:-Default}
- **Users Override**: ${USERS:-Default}
- **Monitoring**: $MONITORING_ENABLED

## Results Overview

$(if [[ -f "$results_dir"/*analysis.json ]]; then
  echo "### Performance Metrics"
  for analysis in "$results_dir"/*analysis.json; do
    if [[ -f "$analysis" ]]; then
      local test_name=$(basename "$analysis" -analysis.json)
      echo "#### $test_name"
      
      local summary=$(jq -r '.summary // empty' "$analysis" 2>/dev/null)
      if [[ -n "$summary" ]]; then
        echo "- **Total Requests**: $(echo "$summary" | jq -r '.total_requests // "N/A"')"
        echo "- **Error Rate**: $(echo "$summary" | jq -r '.error_rate // "N/A"')%"
        echo "- **Avg Response Time**: $(echo "$summary" | jq -r '.avg_response_time // "N/A"')ms"
        echo "- **P95 Response Time**: $(echo "$summary" | jq -r '.p95_response_time // "N/A"')ms"
        echo "- **Throughput**: $(echo "$summary" | jq -r '.throughput // "N/A"') req/s"
        echo ""
      fi
    fi
  done
else
  echo "No detailed analysis available"
fi)

## Files Generated
$(find "$results_dir" -type f -name "*.json" -o -name "*.md" | sed 's|^|  - |')

## Next Steps
1. Review detailed analysis files for performance insights
2. Compare results against baseline and SLA thresholds
3. Identify performance bottlenecks and optimization opportunities
4. Plan capacity scaling based on load test findings

---
*Report generated by Adelaide Weather API Load Testing Suite*
EOF

  info "✅ Summary report generated: $results_dir/load-test-summary.md"
}

#===============================================================================
# Cleanup and Finalization
#===============================================================================

cleanup() {
  if [[ "$CLEANUP_AFTER" == "false" ]]; then
    info "Cleanup disabled, skipping"
    return 0
  fi
  
  log "Performing cleanup..."
  
  # Clean up temporary files
  local temp_files=(
    "$REPORTS_DIR/test-data/variables.csv"
    "$REPORTS_DIR/test-data/tokens.csv"
    "$REPORTS_DIR/test-data/user-profiles.csv"
  )
  
  for temp_file in "${temp_files[@]}"; do
    if [[ -f "$temp_file" ]]; then
      rm -f "$temp_file"
    fi
  done
  
  # Compress large result files
  find "$REPORTS_DIR" -name "*results.json" -size +10M -exec gzip {} \; 2>/dev/null || true
  
  info "✅ Cleanup completed"
}

#===============================================================================
# Main Execution Flow
#===============================================================================

main() {
  local start_time=$(date +%s)
  
  echo -e "${BLUE}"
  cat << "EOF"
    ╔═══════════════════════════════════════════════════════════════╗
    ║                Adelaide Weather API                           ║
    ║             Load Testing & Benchmarking Suite                ║
    ║                                                               ║
    ║  Progressive Load Testing • Geographic Distribution           ║
    ║  Capacity Planning • Performance Benchmarking                ║
    ╚═══════════════════════════════════════════════════════════════╝
EOF
  echo -e "${NC}"
  
  log "Starting load testing suite"
  info "Environment: $ENVIRONMENT"
  info "Test Suite: $TEST_SUITE"
  info "Parallel Execution: $PARALLEL_EXECUTION"
  
  # Create reports directory
  mkdir -p "$REPORTS_DIR"
  
  # Main execution flow
  validate_environment
  check_system_health
  prepare_test_data
  setup_monitoring
  execute_test_suite
  analyze_results
  cleanup
  
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))
  
  log "Load testing completed successfully in ${duration}s"
  info "Results available in: $RESULTS_DIR"
  
  if [[ "$GENERATE_REPORT" == "true" ]]; then
    info "Summary report: $RESULTS_DIR/load-test-summary.md"
  fi
  
  # Show next steps
  echo -e "\n${GREEN}Next Steps:${NC}"
  echo "  1. Review test results in $RESULTS_DIR"
  echo "  2. Compare against baseline performance metrics"
  echo "  3. Analyze capacity planning recommendations"
  echo "  4. Update monitoring dashboards with new thresholds"
  echo "  5. Plan infrastructure scaling based on findings"
}

#===============================================================================
# Error Handling and Cleanup
#===============================================================================

# Trap errors and cleanup
trap 'error "Test execution interrupted"; cleanup; exit 1' INT TERM
trap 'if [[ $? -ne 0 ]]; then error "Test execution failed"; fi' EXIT

# Run main function
main "$@"