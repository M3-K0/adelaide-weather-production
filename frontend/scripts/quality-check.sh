#!/bin/bash

# Quality Check Script
# This script runs comprehensive quality checks locally before committing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to run a command and capture its result
run_check() {
    local check_name="$1"
    local command="$2"
    
    print_status "Running $check_name..."
    
    if eval "$command"; then
        print_success "$check_name passed"
        return 0
    else
        print_error "$check_name failed"
        return 1
    fi
}

# Main quality check function
main() {
    local failed_checks=0
    
    echo "🚀 Starting Quality Checks for Adelaide Weather Frontend"
    echo "=================================================="
    
    # Check if we're in the right directory
    if [[ ! -f "package.json" ]]; then
        print_error "package.json not found. Please run this script from the frontend directory."
        exit 1
    fi
    
    # Install dependencies if node_modules doesn't exist
    if [[ ! -d "node_modules" ]]; then
        print_status "Installing dependencies..."
        npm ci
    fi
    
    # 1. TypeScript Type Check
    if ! run_check "TypeScript Type Check" "npm run type-check"; then
        ((failed_checks++))
    fi
    
    # 2. ESLint Check
    if ! run_check "ESLint" "npm run lint"; then
        ((failed_checks++))
    fi
    
    # 3. Prettier Format Check
    if ! run_check "Prettier Format Check" "npm run format:check"; then
        ((failed_checks++))
    fi
    
    # 4. Unit Tests
    if ! run_check "Unit Tests" "npm run test"; then
        ((failed_checks++))
    fi
    
    # 5. Test Coverage
    if ! run_check "Test Coverage" "npm run test:coverage"; then
        ((failed_checks++))
    fi
    
    # 6. Build Check
    if ! run_check "Build Check" "npm run build"; then
        ((failed_checks++))
    fi
    
    # 7. Security Audit
    if ! run_check "Security Audit" "npm audit --audit-level=moderate"; then
        print_warning "Security audit found issues. Please review and fix if necessary."
    fi
    
    # 8. Bundle Size Analysis (non-blocking)
    print_status "Analyzing bundle size..."
    if command -v npx &> /dev/null; then
        npx bundlesize || print_warning "Bundle size check failed (non-blocking)"
    else
        print_warning "npx not available, skipping bundle size check"
    fi
    
    # Summary
    echo ""
    echo "=================================================="
    if [[ $failed_checks -eq 0 ]]; then
        print_success "All quality checks passed! ✅"
        echo ""
        echo "You're ready to commit your changes!"
        exit 0
    else
        print_error "$failed_checks quality check(s) failed ❌"
        echo ""
        echo "Please fix the issues above before committing."
        exit 1
    fi
}

# Help function
show_help() {
    echo "Quality Check Script for Adelaide Weather Frontend"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --fix          Run linting and formatting fixes"
    echo "  --fast         Skip tests and build (quick check)"
    echo ""
    echo "This script runs:"
    echo "  • TypeScript type checking"
    echo "  • ESLint code linting"
    echo "  • Prettier format checking"
    echo "  • Unit tests"
    echo "  • Test coverage"
    echo "  • Build verification"
    echo "  • Security audit"
    echo "  • Bundle size analysis"
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    --fix)
        print_status "Running fixes..."
        npm run lint:fix
        npm run format
        print_success "Fixes applied. Run the script again to verify."
        exit 0
        ;;
    --fast)
        print_status "Running fast quality checks..."
        failed_checks=0
        
        if ! run_check "TypeScript Type Check" "npm run type-check"; then
            ((failed_checks++))
        fi
        
        if ! run_check "ESLint" "npm run lint"; then
            ((failed_checks++))
        fi
        
        if ! run_check "Prettier Format Check" "npm run format:check"; then
            ((failed_checks++))
        fi
        
        if [[ $failed_checks -eq 0 ]]; then
            print_success "Fast quality checks passed! ✅"
            exit 0
        else
            print_error "$failed_checks fast check(s) failed ❌"
            exit 1
        fi
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown option: $1"
        show_help
        exit 1
        ;;
esac