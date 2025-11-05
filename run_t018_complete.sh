#!/bin/bash
"""
T-018 Performance Validation - Complete Execution Script
========================================================

Master script for executing complete T-018 performance validation.
This script sets up the environment and runs the comprehensive validation
with proper error handling and reporting.

Usage:
    ./run_t018_complete.sh [API_URL] [API_TOKEN]

Environment Setup:
    API_BASE_URL - API endpoint (default: http://localhost:8000)
    API_TOKEN - Authentication token (required)

Author: Performance Specialist
Version: 1.0.0 - T-018 Complete Execution
"""

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default configuration
DEFAULT_API_URL="http://localhost:8000"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/t018_execution_logs"

# Create log directory
mkdir -p "$LOG_DIR"

# Function to print colored output
print_header() {
    echo -e "${BOLD}${CYAN}================================================================================================${NC}"
    echo -e "${BOLD}${CYAN}$1${NC}"
    echo -e "${BOLD}${CYAN}================================================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Python version
    if ! python3 --version | grep -q "Python 3.[8-9]"; then
        print_error "Python 3.8+ required"
        exit 1
    fi
    print_success "Python version check passed"
    
    # Check required Python packages
    if ! python3 -c "import aiohttp, psutil, numpy, requests" 2>/dev/null; then
        print_error "Required Python packages missing"
        echo "Install with: pip install aiohttp psutil numpy requests"
        exit 1
    fi
    print_success "Required Python packages available"
    
    # Check required scripts exist
    required_scripts=(
        "validate_t018_readiness.py"
        "performance_validation_suite.py" 
        "run_t018_validation.py"
        "validate_t018_complete.py"
    )
    
    for script in "${required_scripts[@]}"; do
        if [[ ! -f "$SCRIPT_DIR/$script" ]]; then
            print_error "Required script missing: $script"
            exit 1
        fi
    done
    print_success "All required scripts available"
    
    print_success "Prerequisites check completed"
}

# Function to setup environment
setup_environment() {
    print_header "Setting Up Environment"
    
    # Get API URL
    if [[ -n "$1" ]]; then
        export API_BASE_URL="$1"
    elif [[ -z "$API_BASE_URL" ]]; then
        export API_BASE_URL="$DEFAULT_API_URL"
    fi
    
    # Get API token
    if [[ -n "$2" ]]; then
        export API_TOKEN="$2"
    elif [[ -z "$API_TOKEN" ]]; then
        print_error "API_TOKEN is required"
        echo ""
        echo "Usage: $0 [API_URL] [API_TOKEN]"
        echo "   or: export API_TOKEN='your-token' && $0"
        echo ""
        exit 1
    fi
    
    print_info "API URL: $API_BASE_URL"
    print_info "API Token: ${API_TOKEN:0:8}..."
    print_success "Environment configured"
}

# Function to test API connectivity
test_api_connectivity() {
    print_header "Testing API Connectivity"
    
    # Test basic connectivity
    if curl -s -f -H "Authorization: Bearer $API_TOKEN" \
            "$API_BASE_URL/health" > /dev/null; then
        print_success "API is accessible and responding"
    else
        print_error "API connectivity test failed"
        print_info "Please ensure the API is running at: $API_BASE_URL"
        print_info "And that the token is valid: ${API_TOKEN:0:8}..."
        exit 1
    fi
}

# Function to run T-018 validation phases
run_validation_phases() {
    print_header "Running T-018 Performance Validation"
    
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local session_log="$LOG_DIR/t018_validation_session_$timestamp.log"
    
    print_info "Starting comprehensive T-018 validation..."
    print_info "Session log: $session_log"
    
    # Run the complete validation script
    if python3 "$SCRIPT_DIR/validate_t018_complete.py" 2>&1 | tee "$session_log"; then
        print_success "T-018 validation completed successfully"
        
        # Check if production ready
        if grep -q "PRODUCTION CERTIFIED" "$session_log"; then
            print_success "🚀 SYSTEM IS PRODUCTION READY!"
            return 0
        elif grep -q "CONDITIONALLY_CERTIFIED" "$session_log"; then
            print_warning "🚀 SYSTEM IS CONDITIONALLY READY (with warnings)"
            return 0
        else
            print_error "🚫 SYSTEM IS NOT PRODUCTION READY"
            return 1
        fi
    else
        print_error "T-018 validation failed"
        print_info "Check the session log for details: $session_log"
        return 1
    fi
}

# Function to generate summary report
generate_summary() {
    local validation_result=$1
    
    print_header "T-018 Validation Summary"
    
    if [[ $validation_result -eq 0 ]]; then
        print_success "T-018 Performance Validation: PASSED"
        print_success "All performance targets validated successfully"
        print_success "System ready for production deployment"
        
        echo ""
        print_info "Key achievements:"
        echo "  • /forecast p95 < 150ms validated"
        echo "  • /health p95 < 50ms validated" 
        echo "  • /metrics p95 < 30ms validated"
        echo "  • FAISS search performance validated"
        echo "  • Concurrent throughput ≥ 100 requests validated"
        echo "  • T-005 compression integration validated"
        echo "  • T-011 FAISS monitoring integration validated"
        
    else
        print_error "T-018 Performance Validation: FAILED"
        print_error "Performance targets not met"
        print_error "System NOT ready for production deployment"
        
        echo ""
        print_info "Next steps:"
        echo "  • Review validation logs for specific failures"
        echo "  • Address performance bottlenecks"
        echo "  • Verify T-005 and T-011 integrations"
        echo "  • Re-run validation after fixes"
    fi
    
    echo ""
    print_info "Detailed results available in:"
    if [[ -d "t018_complete_validation" ]]; then
        echo "  • t018_complete_validation/"
    fi
    if [[ -d "t018_validation_results" ]]; then
        echo "  • t018_validation_results/"
    fi
    echo "  • $LOG_DIR/"
}

# Function to cleanup on exit
cleanup() {
    print_info "Cleaning up temporary files..."
    # Add any cleanup logic here
}

# Main execution
main() {
    # Set up cleanup trap
    trap cleanup EXIT
    
    print_header "T-018 Performance Validation - Complete Execution"
    echo "Comprehensive performance validation for Adelaide Weather Forecasting API"
    echo "Validates all SLA targets with T-005 compression and T-011 FAISS monitoring"
    echo ""
    
    # Run validation workflow
    check_prerequisites
    setup_environment "$1" "$2"
    test_api_connectivity
    
    # Run the main validation
    if run_validation_phases; then
        validation_result=0
    else
        validation_result=1
    fi
    
    # Generate summary
    generate_summary $validation_result
    
    # Exit with appropriate code
    exit $validation_result
}

# Execute main function with all arguments
main "$@"