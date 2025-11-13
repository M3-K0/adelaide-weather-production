#!/bin/bash
# Simple mock weather API using netcat
# For load testing purposes only

PORT=${1:-8002}
echo "🚀 Starting mock weather API on port $PORT"

# Function to handle HTTP requests
handle_request() {
    local request_line method path
    read request_line
    method=$(echo "$request_line" | cut -d' ' -f1)
    path=$(echo "$request_line" | cut -d' ' -f2)
    
    # Read and discard the headers
    while IFS= read -r line; do
        [[ "$line" == $'\r' ]] && break
    done
    
    # Generate response based on path
    case "$path" in
        "/health")
            echo "HTTP/1.1 200 OK"
            echo "Content-Type: application/json"
            echo "Content-Length: 120"
            echo ""
            echo '{"status":"healthy","ready":true,"timestamp":"2025-11-12T17:00:00Z","version":"1.0.0","services":{"api":"healthy"}}'
            ;;
        "/forecast"*)
            echo "HTTP/1.1 200 OK"
            echo "Content-Type: application/json"
            echo "Content-Length: 300"
            echo ""
            echo '{"forecast":{"t2m":{"value":295.15,"confidence_interval":{"lower":290,"upper":300}}},"metadata":{"horizon":"24h","variables":["t2m"],"forecast_time":"2025-11-12T17:00:00Z"},"performance":{"total_time_ms":25.5}}'
            ;;
        "/metrics")
            echo "HTTP/1.1 200 OK"
            echo "Content-Type: text/plain"
            echo "Content-Length: 100"
            echo ""
            echo '# HELP api_requests_total Total requests'
            echo 'api_requests_total 42'
            ;;
        *)
            echo "HTTP/1.1 404 Not Found"
            echo "Content-Type: application/json"
            echo "Content-Length: 25"
            echo ""
            echo '{"error":"Not found"}'
            ;;
    esac
}

export -f handle_request

echo "📡 Mock API listening on http://localhost:$PORT"
echo "🏥 Health: http://localhost:$PORT/health"
echo "🌤️  Forecast: http://localhost:$PORT/forecast?horizon=24h&vars=t2m"

# Start the server
while true; do
    nc -l -p $PORT -e bash -c handle_request 2>/dev/null || {
        echo "Netcat failed, trying alternative..."
        break
    }
done