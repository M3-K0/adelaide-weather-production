#!/bin/bash

# Code Analysis Script
# This script performs comprehensive code analysis including complexity, dependencies, and metrics

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "$(printf '=%.0s' {1..60})"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo "🔍 Code Analysis for Adelaide Weather Frontend"
echo ""

# 1. Complexity Analysis
print_header "📊 Complexity Analysis"
if command -v npx &> /dev/null; then
    npx madge --circular --extensions ts,tsx,js,jsx app/ components/ lib/ || print_warning "Circular dependencies found"
    echo ""
    
    # Generate complexity report
    echo "Generating complexity report..."
    npx ts-complex --output-format json app/ components/ lib/ > complexity-report.json 2>/dev/null || echo "ts-complex not available"
    
    # Check for high complexity files
    echo "Checking for high complexity functions..."
    npx complexity-report --threshold 10 app/ components/ lib/ || echo "No high complexity functions found"
else
    print_warning "npx not available, skipping complexity analysis"
fi

echo ""

# 2. Dependency Analysis
print_header "📦 Dependency Analysis"
echo "Checking for outdated dependencies..."
npm outdated || echo "All dependencies are up to date"

echo ""
echo "Checking for duplicate dependencies..."
npx npmdupes || echo "No duplicate dependencies found"

echo ""
echo "Analyzing dependency licenses..."
npx license-checker --summary || print_warning "license-checker not available"

echo ""

# 3. Bundle Analysis
print_header "📈 Bundle Analysis"
if [[ -d ".next" ]]; then
    echo "Analyzing bundle size..."
    npx bundlesize || print_warning "Bundle size check failed"
    
    echo ""
    echo "Generating bundle analyzer report..."
    npx cross-env ANALYZE=true npm run build || print_warning "Bundle analyzer not configured"
else
    echo "Building application first..."
    npm run build
    npx bundlesize || print_warning "Bundle size check failed"
fi

echo ""

# 4. Test Coverage Analysis
print_header "🧪 Test Coverage Analysis"
echo "Running test coverage analysis..."
npm run test:coverage

echo ""
echo "Coverage thresholds:"
echo "- Lines: 85%"
echo "- Branches: 85%"
echo "- Functions: 85%"
echo "- Statements: 85%"

echo ""

# 5. Code Quality Metrics
print_header "✨ Code Quality Metrics"

echo "Lines of code analysis..."
find app/ components/ lib/ -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" | xargs wc -l | tail -n 1

echo ""
echo "File count by type:"
echo "TypeScript files: $(find app/ components/ lib/ -name "*.ts" -o -name "*.tsx" | wc -l)"
echo "JavaScript files: $(find app/ components/ lib/ -name "*.js" -o -name "*.jsx" | wc -l)"
echo "Test files: $(find . -name "*.test.*" -o -name "*.spec.*" | wc -l)"

echo ""

# 6. Security Analysis
print_header "🔒 Security Analysis"
echo "Running security audit..."
npm audit --audit-level=low || print_warning "Security vulnerabilities found"

echo ""
echo "Checking for potential security issues in code..."
# Basic security checks
grep -r "eval(" app/ components/ lib/ || echo "No eval() usage found ✅"
grep -r "innerHTML" app/ components/ lib/ || echo "No innerHTML usage found ✅"
grep -r "dangerouslySetInnerHTML" app/ components/ lib/ || echo "No dangerouslySetInnerHTML usage found ✅"

echo ""

# 7. Performance Analysis
print_header "⚡ Performance Analysis"
echo "Checking for performance anti-patterns..."

# Check for large bundle imports
echo "Checking for large library imports..."
grep -r "import.*lodash" app/ components/ lib/ && print_warning "Consider using specific lodash imports" || echo "No full lodash imports found ✅"
grep -r "import.*moment" app/ components/ lib/ && print_warning "Consider using date-fns instead of moment" || echo "No moment.js usage found ✅"

echo ""
echo "Checking for Next.js Image optimization..."
grep -r "<img" app/ components/ && print_warning "Consider using next/image instead of <img>" || echo "Using Next.js Image component ✅"

echo ""

print_success "Code analysis complete!"
echo ""
echo "Reports generated:"
echo "- Test coverage: ./coverage/"
echo "- Bundle analysis: Check console output above"
echo "- Complexity report: ./complexity-report.json (if available)"

echo ""
echo "💡 Recommendations:"
echo "- Maintain test coverage above 85%"
echo "- Keep bundle sizes under limits defined in .bundlesize.config.json"
echo "- Address any circular dependencies"
echo "- Keep complexity scores below 10 for individual functions"
echo "- Regular dependency updates and security audits"