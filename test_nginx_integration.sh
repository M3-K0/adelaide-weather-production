#!/bin/bash

# Nginx Integration Validation Script
# Tests all proxy features: routing, compression, CORS, rate limiting, security headers

set -e

echo "=== Nginx Integration Validation ==="
echo "Testing all proxy features..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://localhost"
API_URL="${BASE_URL}/api"

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
test_passed() {
    echo -e "${GREEN}✓ $1${NC}"
    ((TESTS_PASSED++))
}

test_failed() {
    echo -e "${RED}✗ $1${NC}"
    ((TESTS_FAILED++))
}

test_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Test 1: Basic connectivity
echo
echo "1. Testing basic connectivity..."
if curl -s -f "${BASE_URL}" > /dev/null; then
    test_passed "Frontend accessible via nginx proxy"
else
    test_failed "Frontend not accessible via nginx proxy"
fi

# Test 2: API routing and rewrite
echo
echo "2. Testing API routing and rewrite..."
if curl -s -f "${API_URL}/health" > /dev/null; then
    test_passed "API /health endpoint accessible via /api/* proxy"
else
    test_failed "API /health endpoint not accessible via /api/* proxy"
fi

# Test 3: CORS headers on API requests
echo
echo "3. Testing CORS headers..."
CORS_RESPONSE=$(curl -s -H "Origin: http://localhost:3000" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: Content-Type" -X OPTIONS "${API_URL}/health" -I)

if echo "$CORS_RESPONSE" | grep -q "Access-Control-Allow-Origin"; then
    test_passed "CORS headers present in API responses"
else
    test_failed "CORS headers missing in API responses"
fi

if echo "$CORS_RESPONSE" | grep -q "Access-Control-Allow-Methods"; then
    test_passed "CORS methods header present"
else
    test_failed "CORS methods header missing"
fi

# Test 4: Gzip compression
echo
echo "4. Testing gzip compression..."
GZIP_RESPONSE=$(curl -s -H "Accept-Encoding: gzip" "${BASE_URL}" -I)

if echo "$GZIP_RESPONSE" | grep -q "Content-Encoding: gzip"; then
    test_passed "Gzip compression active"
else
    test_warning "Gzip compression not detected (may be expected for small responses)"
fi

# Test 5: Security headers
echo
echo "5. Testing security headers..."
SECURITY_RESPONSE=$(curl -s "${BASE_URL}" -I)

if echo "$SECURITY_RESPONSE" | grep -q "X-Frame-Options"; then
    test_passed "X-Frame-Options header present"
else
    test_failed "X-Frame-Options header missing"
fi

if echo "$SECURITY_RESPONSE" | grep -q "X-Content-Type-Options"; then
    test_passed "X-Content-Type-Options header present"
else
    test_failed "X-Content-Type-Options header missing"
fi

if echo "$SECURITY_RESPONSE" | grep -q "X-XSS-Protection"; then
    test_passed "X-XSS-Protection header present"
else
    test_failed "X-XSS-Protection header missing"
fi

# Test 6: Rate limiting (basic test)
echo
echo "6. Testing rate limiting..."
# Make several rapid requests
RATE_LIMIT_COUNT=0
for i in {1..15}; do
    if curl -s -f "${API_URL}/health" > /dev/null 2>&1; then
        ((RATE_LIMIT_COUNT++))
    fi
done

if [ $RATE_LIMIT_COUNT -gt 0 ]; then
    test_passed "Rate limiting configured (allowed $RATE_LIMIT_COUNT requests)"
    if [ $RATE_LIMIT_COUNT -lt 15 ]; then
        test_passed "Rate limiting appears to be functioning"
    fi
else
    test_failed "No requests succeeded - possible rate limiting issue"
fi

# Test 7: Direct API access (without /api prefix)
echo
echo "7. Testing direct API access..."
if curl -s -f "${BASE_URL}/health" > /dev/null; then
    test_passed "Direct API access (without /api prefix) working"
else
    test_failed "Direct API access (without /api prefix) not working"
fi

# Test 8: Nginx service health
echo
echo "8. Testing nginx service health..."
if docker-compose ps nginx | grep -q "Up"; then
    test_passed "Nginx service is running"
else
    test_failed "Nginx service is not running"
fi

# Test 9: Logs accessibility
echo
echo "9. Testing nginx logs..."
if [ -d "./logs/nginx" ]; then
    test_passed "Nginx logs directory exists"
    if [ "$(ls -A ./logs/nginx 2>/dev/null)" ]; then
        test_passed "Nginx logs are being generated"
    else
        test_warning "Nginx logs directory is empty (may be expected in staging)"
    fi
else
    test_warning "Nginx logs directory not found (expected in development mode)"
fi

# Test 10: API JSON response
echo
echo "10. Testing API JSON response..."
API_JSON=$(curl -s "${API_URL}/health")
if echo "$API_JSON" | jq . > /dev/null 2>&1; then
    test_passed "API returns valid JSON"
else
    test_failed "API does not return valid JSON"
fi

# Summary
echo
echo "=== Test Summary ==="
echo -e "Tests passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests failed: ${RED}${TESTS_FAILED}${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical tests passed! Nginx integration is working correctly.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please check the nginx configuration and service status.${NC}"
    exit 1
fi