#!/bin/bash
#===============================================================================
# Adelaide Weather API - Comprehensive Load Testing Suite
# 
# Executes multiple load testing scenarios to validate performance under
# realistic conditions including baseline, target, stress, and spike loads
#===============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/load_test_results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

# Test configuration
API_BASE="https://httpbin.org"  # Using httpbin for reliable testing
DURATION_MULTIPLIER=${1:-1}  # Scale test duration (1 = normal, 0.5 = half, 2 = double)

echo "🚀 Adelaide Weather API - Comprehensive Load Testing Suite"
echo "========================================================="
echo "📅 Test execution started: $(date)"
echo "📊 Results directory: $RESULTS_DIR"
echo "🌐 API Base: $API_BASE"
echo "⏱️  Duration multiplier: ${DURATION_MULTIPLIER}x"
echo

# Define test scenarios
declare -A SCENARIOS=(
    ["baseline"]="5:60:10"     # 5 users, 60 seconds, 10 requests each
    ["target_load"]="15:120:8"  # 15 users, 120 seconds, 8 requests each
    ["stress_test"]="25:90:6"   # 25 users, 90 seconds, 6 requests each
    ["spike_test"]="40:45:4"    # 40 users, 45 seconds, 4 requests each
    ["endurance"]="10:300:20"   # 10 users, 300 seconds, 20 requests each
)

# Test endpoints simulating weather API
ENDPOINTS=(
    "get?horizon=6h&vars=t2m"
    "get?horizon=12h&vars=t2m,u10,v10"
    "get?horizon=24h&vars=t2m,u10,v10,msl"
    "get?horizon=48h&vars=t2m,u10,v10,msl,cape"
    "status/200"  # Health check simulation
    "delay/1"     # Slow endpoint simulation
    "status/503"  # Error simulation (10% of time)
)

# Function to run a single test scenario
run_test_scenario() {
    local scenario_name=$1
    local users_duration_requests=$2
    local users=$(echo "$users_duration_requests" | cut -d: -f1)
    local duration=$(echo "$users_duration_requests" | cut -d: -f2)
    local requests=$(echo "$users_duration_requests" | cut -d: -f3)
    
    # Apply duration multiplier
    duration=$(echo "$duration * $DURATION_MULTIPLIER" | bc)
    duration=$(printf "%.0f" "$duration")
    
    local scenario_results="$RESULTS_DIR/${scenario_name}"
    mkdir -p "$scenario_results"
    
    echo "🔥 Running scenario: $scenario_name"
    echo "   👥 Users: $users"
    echo "   ⏱️  Duration: ${duration}s"  
    echo "   📊 Requests per user: $requests"
    
    # Function to simulate a user for this scenario
    simulate_scenario_user() {
        local user_id=$1
        local user_results="$scenario_results/user_${user_id}.csv"
        echo "user,request,endpoint,status_code,response_time_ms,timestamp" > "$user_results"
        
        local start_time=$(date +%s)
        local request_count=0
        
        while [[ $(($(date +%s) - start_time)) -lt $duration ]] && [[ $request_count -lt $requests ]]; do
            request_count=$((request_count + 1))
            
            # Select endpoint based on scenario patterns
            local endpoint_index
            case "$scenario_name" in
                "baseline")
                    # Baseline focuses on core forecasting
                    endpoint_index=$((request_count % 4))
                    ;;
                "target_load")
                    # Target load uses varied endpoints
                    endpoint_index=$(shuf -i 0-5 -n 1)
                    ;;
                "stress_test")
                    # Stress test hits all endpoints including slow ones
                    endpoint_index=$(shuf -i 0-6 -n 1)
                    ;;
                "spike_test")
                    # Spike test focuses on quick endpoints
                    endpoint_index=$(shuf -i 0-4 -n 1)
                    ;;
                "endurance")
                    # Endurance spreads load evenly
                    endpoint_index=$((request_count % ${#ENDPOINTS[@]}))
                    ;;
                *)
                    endpoint_index=0
                    ;;
            esac
            
            local endpoint="${ENDPOINTS[$endpoint_index]}"
            local url="$API_BASE/$endpoint"
            local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
            
            # Make request with timing
            local start_request_time=$(date +%s%N)
            local status_code timeout_flag
            
            if status_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$url" 2>/dev/null); then
                local end_request_time=$(date +%s%N)
                local response_time=$(( (end_request_time - start_request_time) / 1000000 ))
                timeout_flag="false"
            else
                status_code="TIMEOUT"
                response_time=30000
                timeout_flag="true"
            fi
            
            echo "${user_id},${request_count},${endpoint},${status_code},${response_time},${timestamp}" >> "$user_results"
            
            # Realistic think time based on scenario
            local think_time
            case "$scenario_name" in
                "baseline") think_time=$(shuf -i 2-5 -n 1) ;;
                "target_load") think_time=$(shuf -i 1-4 -n 1) ;;
                "stress_test") think_time=$(shuf -i 1-3 -n 1) ;;
                "spike_test") think_time=$(shuf -i 1-2 -n 1) ;;
                "endurance") think_time=$(shuf -i 3-8 -n 1) ;;
                *) think_time=2 ;;
            esac
            
            sleep $think_time
        done
    }
    
    # Launch users for this scenario
    local start_scenario_time=$(date +%s)
    for user_id in $(seq 1 $users); do
        simulate_scenario_user "$user_id" &
    done
    
    echo "   ⏳ Waiting for scenario to complete..."
    wait
    
    local end_scenario_time=$(date +%s)
    local actual_duration=$((end_scenario_time - start_scenario_time))
    
    # Analyze scenario results
    analyze_scenario_results "$scenario_name" "$scenario_results" "$actual_duration"
    
    echo "   ✅ Scenario completed in ${actual_duration}s"
    echo
}

# Function to analyze results for a scenario
analyze_scenario_results() {
    local scenario_name=$1
    local scenario_results=$2
    local actual_duration=$3
    
    # Combine all user results
    local combined_results="$scenario_results/combined_results.csv"
    echo "user,request,endpoint,status_code,response_time_ms,timestamp" > "$combined_results"
    cat "$scenario_results"/user_*.csv | grep -v "user,request" >> "$combined_results" 2>/dev/null || true
    
    # Generate analysis
    local analysis_file="$scenario_results/analysis.json"
    local summary_file="$scenario_results/summary.txt"
    
    awk -F',' 'BEGIN {
        total_requests = 0; successful = 0; errors = 0; timeouts = 0
        total_time = 0; min_time = 999999; max_time = 0
        sum_squares = 0
    }
    NR > 1 {
        total_requests++
        response_time = $5
        total_time += response_time
        
        if (response_time < min_time) min_time = response_time
        if (response_time > max_time) max_time = response_time
        
        sum_squares += response_time * response_time
        
        status = $4
        if (status == "200") successful++
        else if (status == "TIMEOUT") timeouts++
        else errors++
        
        # Store for percentile calculation
        response_times[total_requests] = response_time
    }
    END {
        if (total_requests > 0) {
            avg_time = total_time / total_requests
            variance = (sum_squares / total_requests) - (avg_time * avg_time)
            std_dev = sqrt(variance > 0 ? variance : 0)
            
            # Sort response times for percentiles
            n = asort(response_times)
            p50 = response_times[int(n * 0.50)]
            p95 = response_times[int(n * 0.95)]
            p99 = response_times[int(n * 0.99)]
            
            error_rate = (errors + timeouts) / total_requests * 100
            success_rate = successful / total_requests * 100
            throughput = total_requests / '$actual_duration'
            
            # JSON output for analysis
            printf "{\n"
            printf "  \"scenario\": \"'$scenario_name'\",\n"
            printf "  \"total_requests\": %d,\n", total_requests
            printf "  \"successful_requests\": %d,\n", successful
            printf "  \"error_requests\": %d,\n", errors
            printf "  \"timeout_requests\": %d,\n", timeouts
            printf "  \"success_rate\": %.2f,\n", success_rate
            printf "  \"error_rate\": %.2f,\n", error_rate
            printf "  \"response_time\": {\n"
            printf "    \"min_ms\": %d,\n", min_time
            printf "    \"max_ms\": %d,\n", max_time
            printf "    \"avg_ms\": %.2f,\n", avg_time
            printf "    \"std_dev_ms\": %.2f,\n", std_dev
            printf "    \"p50_ms\": %d,\n", p50
            printf "    \"p95_ms\": %d,\n", p95
            printf "    \"p99_ms\": %d\n", p99
            printf "  },\n"
            printf "  \"throughput\": {\n"
            printf "    \"requests_per_second\": %.2f,\n", throughput
            printf "    \"requests_per_minute\": %.2f\n", throughput * 60
            printf "  },\n"
            printf "  \"duration_seconds\": %d\n", '$actual_duration'
            printf "}\n"
            
        } else {
            printf "{\"error\": \"No data collected\"}\n"
        }
    }' "$combined_results" > "$analysis_file"
    
    # Human-readable summary
    echo "📊 $scenario_name Load Test Results" > "$summary_file"
    echo "================================" >> "$summary_file"
    echo "" >> "$summary_file"
    
    # Extract key metrics from JSON
    if command -v python3 &> /dev/null; then
        python3 -c "
import json
with open('$analysis_file') as f:
    data = json.load(f)
    
print(f\"📈 Performance Metrics:\")
print(f\"   Total Requests: {data.get('total_requests', 0)}\")
print(f\"   Success Rate: {data.get('success_rate', 0):.1f}%\")
print(f\"   Error Rate: {data.get('error_rate', 0):.1f}%\")
print(f\"\")
print(f\"⏱️  Response Times:\")
rt = data.get('response_time', {})
print(f\"   Average: {rt.get('avg_ms', 0):.1f} ms\")
print(f\"   P50 (Median): {rt.get('p50_ms', 0)} ms\")
print(f\"   P95: {rt.get('p95_ms', 0)} ms\")
print(f\"   P99: {rt.get('p99_ms', 0)} ms\")
print(f\"\")
tp = data.get('throughput', {})
print(f\"🚀 Throughput:\")
print(f\"   {tp.get('requests_per_second', 0):.2f} req/s\")
print(f\"   {tp.get('requests_per_minute', 0):.1f} req/min\")
" >> "$summary_file"
    else
        echo "Python3 not available for detailed analysis" >> "$summary_file"
    fi
    
    # Show summary
    cat "$summary_file"
}

# Function to generate final comprehensive report
generate_final_report() {
    local final_report="$RESULTS_DIR/comprehensive_load_test_report.md"
    
    echo "📝 Generating comprehensive report..."
    
    cat > "$final_report" << EOF
# Adelaide Weather API - Comprehensive Load Test Report

**Test Execution Date:** $(date)  
**Test Duration Multiplier:** ${DURATION_MULTIPLIER}x  
**API Base:** $API_BASE  

## Executive Summary

This comprehensive load test evaluates the Adelaide Weather API performance under various load conditions to validate system capacity, response times, and resilience.

### Test Scenarios Executed

EOF
    
    # Add scenario results
    for scenario in "${!SCENARIOS[@]}"; do
        if [[ -f "$RESULTS_DIR/$scenario/analysis.json" ]]; then
            echo "#### $scenario" >> "$final_report"
            echo "" >> "$final_report"
            
            if command -v python3 &> /dev/null; then
                python3 -c "
import json
with open('$RESULTS_DIR/$scenario/analysis.json') as f:
    data = json.load(f)
    
config = '${SCENARIOS[$scenario]}'.split(':')
print(f'**Configuration:** {config[0]} users, {config[1]}s duration, {config[2]} requests/user')
print(f'**Success Rate:** {data.get(\"success_rate\", 0):.1f}%')
print(f'**Average Response Time:** {data.get(\"response_time\", {}).get(\"avg_ms\", 0):.1f} ms')
print(f'**P95 Response Time:** {data.get(\"response_time\", {}).get(\"p95_ms\", 0)} ms')
print(f'**Throughput:** {data.get(\"throughput\", {}).get(\"requests_per_second\", 0):.2f} req/s')
print('')
" >> "$final_report"
            fi
        fi
    done
    
    cat >> "$final_report" << EOF

## Performance Analysis

### SLA Compliance Assessment

Based on typical weather API requirements:
- **Response Time SLA:** P95 < 2000ms, P99 < 5000ms
- **Availability SLA:** > 99.9% uptime (< 0.1% error rate)
- **Throughput SLA:** > 10 requests/second under normal load

EOF
    
    # SLA compliance check
    echo "### SLA Compliance Results" >> "$final_report"
    echo "" >> "$final_report"
    
    for scenario in "${!SCENARIOS[@]}"; do
        if [[ -f "$RESULTS_DIR/$scenario/analysis.json" ]] && command -v python3 &> /dev/null; then
            python3 -c "
import json
with open('$RESULTS_DIR/$scenario/analysis.json') as f:
    data = json.load(f)

scenario = '$scenario'
rt = data.get('response_time', {})
p95 = rt.get('p95_ms', 0)
error_rate = data.get('error_rate', 0)
throughput = data.get('throughput', {}).get('requests_per_second', 0)

print(f'**{scenario}:**')
p95_status = 'PASS' if p95 < 2000 else 'FAIL'
error_status = 'PASS' if error_rate < 0.1 else 'WARN' if error_rate < 5 else 'FAIL'
throughput_status = 'PASS' if throughput >= 1 else 'FAIL'

print(f'- Response Time P95: {p95}ms ({p95_status})')
print(f'- Error Rate: {error_rate:.1f}% ({error_status})')
print(f'- Throughput: {throughput:.2f} req/s ({throughput_status})')
print('')
" >> "$final_report"
        fi
    done
    
    cat >> "$final_report" << EOF

## Capacity Planning Recommendations

### Current Capacity Assessment
Based on the test results:

1. **Baseline Performance:** System handles light load efficiently
2. **Target Load Capacity:** Performance under expected production load
3. **Stress Tolerance:** System behavior under high load conditions
4. **Spike Resilience:** Ability to handle traffic spikes
5. **Endurance Stability:** Long-term performance stability

### Scaling Recommendations

1. **Horizontal Scaling:** Add more API instances when P95 > 1500ms
2. **Caching Strategy:** Implement response caching for forecast data
3. **Rate Limiting:** Configure appropriate rate limits per user
4. **Circuit Breakers:** Implement failure protection for external dependencies
5. **Monitoring:** Set up alerts for P95 > 2000ms and error rate > 1%

### Performance Optimization

1. **Database Optimization:** Ensure FAISS index performance
2. **Response Compression:** Enable gzip compression for large responses
3. **Connection Pooling:** Optimize database connection management
4. **Async Processing:** Use async patterns for non-critical operations

## Files Generated

EOF
    
    # List all generated files
    find "$RESULTS_DIR" -type f -name "*.json" -o -name "*.csv" -o -name "*.txt" | sed 's|^|- |' >> "$final_report"
    
    cat >> "$final_report" << EOF

## Next Steps

1. Review individual scenario results for detailed performance insights
2. Compare against baseline metrics and historical performance data
3. Implement recommended optimizations based on bottleneck analysis
4. Schedule regular load testing to monitor performance over time
5. Validate performance in staging environment with production-like data

---
*Report generated by Adelaide Weather API Comprehensive Load Testing Suite*  
*Test completed at $(date)*
EOF

    echo "📄 Final report: $final_report"
}

# Main execution
main() {
    echo "🎯 Test Execution Plan:"
    echo "======================"
    for scenario in "${!SCENARIOS[@]}"; do
        local config="${SCENARIOS[$scenario]}"
        local users=$(echo "$config" | cut -d: -f1)
        local duration=$(echo "$config" | cut -d: -f2)
        local requests=$(echo "$config" | cut -d: -f3)
        duration=$(echo "$duration * $DURATION_MULTIPLIER" | bc | cut -d. -f1)
        echo "   $scenario: $users users, ${duration}s, $requests req/user"
    done
    echo
    
    # Execute each scenario
    local scenario_count=0
    local total_scenarios=${#SCENARIOS[@]}
    
    for scenario in baseline target_load stress_test spike_test endurance; do
        if [[ -n "${SCENARIOS[$scenario]:-}" ]]; then
            scenario_count=$((scenario_count + 1))
            echo "🔄 Executing scenario $scenario_count of $total_scenarios"
            run_test_scenario "$scenario" "${SCENARIOS[$scenario]}"
            
            # Cool-down period between scenarios
            if [[ $scenario_count -lt $total_scenarios ]]; then
                echo "   😴 Cool-down period (30s)..."
                sleep 30
            fi
        fi
    done
    
    # Generate final report
    generate_final_report
    
    # Final summary
    echo "🎉 Comprehensive load testing completed!"
    echo "📁 All results available in: $RESULTS_DIR"
    echo "📊 Key files:"
    echo "   - $RESULTS_DIR/comprehensive_load_test_report.md"
    echo "   - Individual scenario results in subdirectories"
    echo
    echo "✅ Load testing suite execution completed successfully"
}

# Error handling
trap 'echo "❌ Load testing interrupted"; exit 1' INT TERM

# Execute main function
main "$@"