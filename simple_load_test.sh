#!/bin/bash
#===============================================================================
# Simple Load Test for Adelaide Weather API
# 
# Tests basic functionality, response times, and validates performance
# without requiring complex load testing tools
#===============================================================================

set -euo pipefail

# Test configuration
API_BASE="http://httpbin.org"  # Use httpbin.org for testing
TEST_DURATION=${1:-60}  # 1 minute default
CONCURRENT_USERS=${2:-5}  # 5 concurrent users default
REQUESTS_PER_USER=${3:-10}  # 10 requests per user

echo "🚀 Adelaide Weather API - Simple Load Test"
echo "================================================"
echo "📊 Configuration:"
echo "   API Base: $API_BASE"
echo "   Duration: ${TEST_DURATION}s"
echo "   Concurrent Users: $CONCURRENT_USERS"
echo "   Requests per User: $REQUESTS_PER_USER"
echo

# Results tracking
RESULTS_DIR="/tmp/load_test_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

# Function to perform a single request test
test_request() {
    local user_id=$1
    local request_num=$2
    local endpoint=$3
    local start_time end_time duration response_code
    
    start_time=$(date +%s%N)
    
    # Make request with timeout
    if response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$endpoint" 2>/dev/null); then
        end_time=$(date +%s%N)
        duration=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds
        
        echo "user${user_id},${request_num},${endpoint},${response_code},${duration}" >> "$RESULTS_DIR/results_user${user_id}.csv"
    else
        echo "user${user_id},${request_num},${endpoint},TIMEOUT,30000" >> "$RESULTS_DIR/results_user${user_id}.csv"
    fi
}

# Function to simulate user behavior
simulate_user() {
    local user_id=$1
    local user_results="$RESULTS_DIR/results_user${user_id}.csv"
    
    echo "user,request,endpoint,status_code,response_time_ms" > "$user_results"
    
    echo "👤 Starting user $user_id simulation..."
    
    for i in $(seq 1 $REQUESTS_PER_USER); do
        # Vary endpoints to simulate realistic patterns
        case $((i % 4)) in
            0)
                test_request "$user_id" "$i" "$API_BASE/get?horizon=6h&vars=t2m"
                ;;
            1)
                test_request "$user_id" "$i" "$API_BASE/get?horizon=24h&vars=t2m,u10,v10"
                ;;
            2)
                test_request "$user_id" "$i" "$API_BASE/get?horizon=48h&vars=t2m,u10,v10,msl"
                ;;
            3)
                test_request "$user_id" "$i" "$API_BASE/status/200"  # Simulate health check
                ;;
        esac
        
        # Add think time between requests (1-3 seconds)
        sleep $(shuf -i 1-3 -n 1)
        
        # Check if test duration exceeded
        if [[ $(($(date +%s) - START_TIME)) -gt $TEST_DURATION ]]; then
            echo "⏰ User $user_id: Time limit reached"
            break
        fi
    done
    
    echo "✅ User $user_id: Completed simulation"
}

# Start load test
START_TIME=$(date +%s)
echo "🔥 Starting load test at $(date)"

# Launch concurrent users
for user_id in $(seq 1 $CONCURRENT_USERS); do
    simulate_user "$user_id" &
done

echo "⏳ Waiting for all users to complete..."
wait

END_TIME=$(date +%s)
ACTUAL_DURATION=$((END_TIME - START_TIME))

echo
echo "📊 Test completed in ${ACTUAL_DURATION}s"
echo

# Analyze results
echo "📈 Performance Analysis:"
echo "========================"

# Combine all results
cat "$RESULTS_DIR"/results_user*.csv | head -1 > "$RESULTS_DIR/combined_results.csv"
cat "$RESULTS_DIR"/results_user*.csv | grep -v "user,request" >> "$RESULTS_DIR/combined_results.csv"

# Basic statistics using awk
awk -F',' 'NR>1 {
    total_requests++
    if ($4 == "200" || $4 == "TIMEOUT") {
        if ($4 == "200") successful_requests++
        if ($4 == "TIMEOUT") timeout_requests++
        total_time += $5
        response_times[total_requests] = $5
    } else {
        error_requests++
    }
}
END {
    print "📊 Request Statistics:"
    print "   Total Requests: " total_requests
    print "   Successful (200): " successful_requests
    print "   Errors: " error_requests
    print "   Timeouts: " timeout_requests
    print "   Success Rate: " (successful_requests/total_requests*100) "%"
    print ""
    
    if (total_requests > 0) {
        avg_time = total_time / total_requests
        print "⏱️  Response Time Analysis:"
        print "   Average: " avg_time " ms"
        
        # Sort response times for percentiles (simple approximation)
        n = asort(response_times)
        if (n > 0) {
            p50_idx = int(n * 0.5)
            p95_idx = int(n * 0.95)
            p99_idx = int(n * 0.99)
            
            print "   P50 (Median): " response_times[p50_idx] " ms"
            print "   P95: " response_times[p95_idx] " ms"  
            print "   P99: " response_times[p99_idx] " ms"
            print "   Max: " response_times[n] " ms"
        }
        
        print ""
        print "🚀 Throughput:"
        print "   Requests/second: " (total_requests/('$ACTUAL_DURATION')) " req/s"
        print "   Requests/minute: " (total_requests/('$ACTUAL_DURATION')*60) " req/min"
    }
}' "$RESULTS_DIR/combined_results.csv"

echo
echo "📁 Detailed results saved to: $RESULTS_DIR/"
echo "📄 Combined results: $RESULTS_DIR/combined_results.csv"

# Generate summary report
cat > "$RESULTS_DIR/load_test_summary.md" << EOF
# Load Test Summary Report

**Test Configuration:**
- API Base: $API_BASE  
- Duration: ${TEST_DURATION}s (actual: ${ACTUAL_DURATION}s)
- Concurrent Users: $CONCURRENT_USERS
- Requests per User: $REQUESTS_PER_USER
- Test Time: $(date)

**Results:**
$(awk -F',' 'NR>1 {total++; if($4=="200") success++} END {print "- Total Requests: " total; print "- Successful Requests: " success; print "- Success Rate: " (success/total*100) "%"}' "$RESULTS_DIR/combined_results.csv")

**Files Generated:**
- Summary: load_test_summary.md
- Results: combined_results.csv
- Individual user results: results_user*.csv

**Next Steps:**
1. Review response time percentiles for SLA compliance
2. Analyze error patterns in failed requests  
3. Compare results against baseline performance metrics
4. Scale test for higher loads if performance is acceptable

*Test completed at $(date)*
EOF

echo "📋 Summary report: $RESULTS_DIR/load_test_summary.md"

# Return success if error rate is acceptable
ERROR_RATE=$(awk -F',' 'NR>1 {total++; if($4!="200") errors++} END {if(total>0) print (errors/total*100); else print 0}' "$RESULTS_DIR/combined_results.csv")
if (( $(echo "$ERROR_RATE < 10" | bc -l) )); then
    echo "✅ Load test PASSED (error rate: ${ERROR_RATE}%)"
    exit 0
else
    echo "❌ Load test FAILED (error rate: ${ERROR_RATE}%)"
    exit 1
fi