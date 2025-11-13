#!/bin/bash
# =============================================================================
# QUALITY GATES EXECUTION SCRIPT
# =============================================================================
# Runs all quality gates locally to validate code before CI/CD pipeline
# 
# This script mimics the CI/CD pipeline quality gates and can be used for:
# - Pre-commit validation
# - Local development testing
# - Quality assurance before pushing code
#
# Author: Design Systems Architect
# Version: 1.0.0 - CI1 Implementation
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.11"
NODE_VERSION="18"
COVERAGE_THRESHOLD=90
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Function to print colored output
print_step() {
    echo -e "${BLUE}🔍 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_critical() {
    echo -e "${RED}🚨 CRITICAL: $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate environment
validate_environment() {
    print_step "Validating environment..."
    
    # Check Python version
    if ! command_exists python; then
        print_error "Python not found"
        exit 1
    fi
    
    python_version=$(python --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
    if [[ "$python_version" != "3.11" ]]; then
        print_warning "Expected Python 3.11, found $python_version"
    fi
    
    # Check Node version
    if ! command_exists node; then
        print_error "Node.js not found"
        exit 1
    fi
    
    node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ "$node_version" != "18" ]]; then
        print_warning "Expected Node.js 18, found $node_version"
    fi
    
    print_success "Environment validation passed"
}

# Function to install Python dependencies
install_python_deps() {
    print_step "Installing Python dependencies..."
    
    cd "$PROJECT_ROOT"
    
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install black isort flake8 mypy bandit safety pytest-cov pytest-xdist
    
    print_success "Python dependencies installed"
}

# Function to install Node dependencies
install_node_deps() {
    print_step "Installing Node.js dependencies..."
    
    cd "$PROJECT_ROOT/frontend"
    npm ci
    
    print_success "Node.js dependencies installed"
}

# Function to run Python quality gates
run_python_quality_gates() {
    print_step "Running Python quality gates..."
    
    cd "$PROJECT_ROOT"
    
    # Code formatting check
    print_step "Checking code formatting with Black..."
    if ! black --check --diff .; then
        print_error "Black formatting check failed"
        echo "Run: black ."
        return 1
    fi
    print_success "Black formatting check passed"
    
    # Import sorting check
    print_step "Checking import sorting with isort..."
    if ! isort --check-only --diff .; then
        print_error "isort check failed"
        echo "Run: isort ."
        return 1
    fi
    print_success "isort check passed"
    
    # Linting
    print_step "Running flake8 linting..."
    if ! flake8 . --count --statistics; then
        print_error "flake8 linting failed"
        return 1
    fi
    print_success "flake8 linting passed"
    
    # Type checking
    print_step "Running mypy type checking..."
    if ! mypy . --ignore-missing-imports; then
        print_error "mypy type checking failed"
        return 1
    fi
    print_success "mypy type checking passed"
    
    return 0
}

# Function to run security scanning
run_security_scanning() {
    print_step "Running security scanning..."
    
    cd "$PROJECT_ROOT"
    
    # Bandit security scanning
    print_step "Running Bandit security scan..."
    bandit -r . -f json -o bandit-report.json -c pyproject.toml || true
    
    if [ -f "bandit-report.json" ]; then
        high_count=$(jq '.results[] | select(.issue_severity == "HIGH") | length' bandit-report.json 2>/dev/null | wc -l || echo "0")
        medium_count=$(jq '.results[] | select(.issue_severity == "MEDIUM") | length' bandit-report.json 2>/dev/null | wc -l || echo "0")
        
        if [ "$high_count" -gt 0 ] || [ "$medium_count" -gt 0 ]; then
            print_error "Bandit found HIGH/MEDIUM severity security issues"
            echo "HIGH issues: $high_count"
            echo "MEDIUM issues: $medium_count"
            if command_exists jq; then
                jq '.results[] | select(.issue_severity == "HIGH" or .issue_severity == "MEDIUM")' bandit-report.json
            fi
            return 1
        fi
    fi
    print_success "Bandit security scan passed"
    
    # Safety dependency check
    print_step "Running Safety dependency check..."
    if ! safety check --json --output safety-report.json; then
        if [ -f "safety-report.json" ]; then
            print_error "Safety found vulnerabilities:"
            cat safety-report.json
            return 1
        fi
    fi
    print_success "Safety dependency check passed"
    
    return 0
}

# Function to run Frontend quality gates
run_frontend_quality_gates() {
    print_step "Running Frontend quality gates..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # ESLint
    print_step "Running ESLint..."
    if ! npm run lint; then
        print_error "ESLint failed"
        return 1
    fi
    print_success "ESLint passed"
    
    # TypeScript check
    print_step "Running TypeScript check..."
    if ! npm run type-check; then
        print_error "TypeScript check failed"
        return 1
    fi
    print_success "TypeScript check passed"
    
    # Prettier formatting check
    print_step "Running Prettier check..."
    if ! npm run format:check; then
        print_error "Prettier formatting check failed"
        echo "Run: npm run format"
        return 1
    fi
    print_success "Prettier formatting check passed"
    
    # Security audit
    print_step "Running npm security audit..."
    if ! npm audit --audit-level=high; then
        print_error "npm audit found high/critical vulnerabilities"
        return 1
    fi
    print_success "npm security audit passed"
    
    return 0
}

# Function to run test coverage enforcement
run_test_coverage() {
    print_step "Running test coverage enforcement..."
    
    cd "$PROJECT_ROOT"
    
    # Run tests with coverage
    print_step "Running tests with coverage..."
    if ! pytest --cov=api --cov=core --cov-report=xml --cov-report=term-missing \
        --cov-fail-under=$COVERAGE_THRESHOLD --maxfail=1; then
        print_error "Test coverage below $COVERAGE_THRESHOLD% threshold"
        return 1
    fi
    
    print_success "Test coverage meets requirement"
    return 0
}

# Function to run Frontend testing
run_frontend_tests() {
    print_step "Running Frontend test suite..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # Unit tests
    print_step "Running Frontend unit tests..."
    if ! npm run test:coverage; then
        print_error "Frontend unit tests failed"
        return 1
    fi
    print_success "Frontend unit tests passed"
    
    # Integration tests
    print_step "Running Frontend integration tests..."
    if ! npm run test:integration; then
        print_error "Frontend integration tests failed"
        return 1
    fi
    print_success "Frontend integration tests passed"
    
    # All CI tests
    print_step "Running Frontend CI test suite..."
    if ! npm run ci:all; then
        print_error "Frontend CI test suite failed"
        return 1
    fi
    print_success "Frontend CI test suite passed"
    
    return 0
}

# Function to validate monitoring gates
run_monitoring_validation() {
    print_step "Running monitoring gates validation..."
    
    cd "$PROJECT_ROOT"
    
    # Check if validation script exists
    if [ ! -f "scripts/validate_monitoring_gates.py" ]; then
        print_warning "Monitoring gates validation script not found, skipping..."
        return 0
    fi
    
    # Run monitoring validation with local endpoints
    if ! python scripts/validate_monitoring_gates.py \
        --api-url "http://localhost:8000" \
        --prometheus-url "http://localhost:9090" \
        --output "local_monitoring_gates_results.json"; then
        print_warning "Monitoring gates validation failed (non-blocking for local runs)"
        return 0  # Non-blocking for local execution
    fi
    
    print_success "Monitoring gates validation passed"
    return 0
}

# Function to generate summary
generate_summary() {
    local exit_code=$1
    
    echo ""
    echo "=================================================================="
    echo "                    QUALITY GATES SUMMARY"
    echo "=================================================================="
    
    if [ $exit_code -eq 0 ]; then
        print_success "ALL QUALITY GATES PASSED"
        echo "🎉 Code is ready for CI/CD pipeline"
        echo ""
        echo "Next steps:"
        echo "  1. Commit your changes"
        echo "  2. Push to your branch"
        echo "  3. Create a pull request"
    else
        print_error "QUALITY GATES FAILED"
        echo "🚫 Fix the issues above before pushing"
        echo ""
        echo "Common fixes:"
        echo "  - Run: black . (format code)"
        echo "  - Run: isort . (sort imports)"  
        echo "  - Run: npm run format (format frontend)"
        echo "  - Fix linting/type errors"
        echo "  - Add tests to increase coverage"
    fi
    
    echo "=================================================================="
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help              Show this help message"
    echo "  --skip-deps         Skip dependency installation"
    echo "  --skip-python       Skip Python quality gates"
    echo "  --skip-frontend     Skip Frontend quality gates"
    echo "  --skip-tests        Skip test execution"
    echo "  --skip-security     Skip security scanning"
    echo "  --skip-monitoring   Skip monitoring validation"
    echo "  --fast             Skip non-essential checks"
    echo ""
    echo "Examples:"
    echo "  $0                  # Run all quality gates"
    echo "  $0 --fast           # Quick validation"
    echo "  $0 --skip-frontend  # Backend only"
}

# Main execution function
main() {
    # Parse command line arguments
    SKIP_DEPS=false
    SKIP_PYTHON=false
    SKIP_FRONTEND=false
    SKIP_TESTS=false
    SKIP_SECURITY=false
    SKIP_MONITORING=false
    FAST_MODE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_usage
                exit 0
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            --skip-python)
                SKIP_PYTHON=true
                shift
                ;;
            --skip-frontend)
                SKIP_FRONTEND=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-security)
                SKIP_SECURITY=true
                shift
                ;;
            --skip-monitoring)
                SKIP_MONITORING=true
                shift
                ;;
            --fast)
                FAST_MODE=true
                SKIP_SECURITY=true
                SKIP_MONITORING=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    echo "=================================================================="
    echo "               ADELAIDE WEATHER QUALITY GATES"
    echo "=================================================================="
    echo ""
    
    # Track overall success
    overall_success=true
    
    # Environment validation
    validate_environment || overall_success=false
    
    # Dependency installation
    if [ "$SKIP_DEPS" = false ]; then
        install_python_deps || overall_success=false
        if [ "$SKIP_FRONTEND" = false ]; then
            install_node_deps || overall_success=false
        fi
    fi
    
    # Python quality gates
    if [ "$SKIP_PYTHON" = false ]; then
        run_python_quality_gates || overall_success=false
    fi
    
    # Security scanning
    if [ "$SKIP_SECURITY" = false ]; then
        run_security_scanning || overall_success=false
    fi
    
    # Frontend quality gates
    if [ "$SKIP_FRONTEND" = false ]; then
        run_frontend_quality_gates || overall_success=false
    fi
    
    # Test execution
    if [ "$SKIP_TESTS" = false ]; then
        run_test_coverage || overall_success=false
        if [ "$SKIP_FRONTEND" = false ]; then
            run_frontend_tests || overall_success=false
        fi
    fi
    
    # Monitoring validation
    if [ "$SKIP_MONITORING" = false ]; then
        run_monitoring_validation  # Non-blocking for local runs
    fi
    
    # Generate summary
    if [ "$overall_success" = true ]; then
        generate_summary 0
        exit 0
    else
        generate_summary 1
        exit 1
    fi
}

# Run main function with all arguments
main "$@"