#!/bin/bash
# Simple script to start the weather forecasting web services

echo "🚀 Starting Adelaide Weather Forecasting Web Services"
echo "======================================================"

# Check if required directories exist
if [ ! -d "api" ]; then
    echo "❌ API directory not found"
    exit 1
fi

if [ ! -d "frontend" ]; then
    echo "❌ Frontend directory not found"
    exit 1
fi

# Set environment variables
export API_TOKEN="dev-token-change-in-production"
export CORS_ORIGINS="http://localhost:3000"
export LOG_LEVEL="INFO"
export RATE_LIMIT_PER_MINUTE="60"

# Start API in background
echo "🔧 Starting FastAPI server on port 8000..."
cd api
python3 test_main.py &
API_PID=$!
cd ..

echo "✅ API started with PID: $API_PID"

# Wait a moment for API to start
sleep 3

# Test API health
echo "🔍 Testing API health..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API health check passed"
else
    echo "❌ API health check failed"
    kill $API_PID 2>/dev/null
    exit 1
fi

echo ""
echo "🎉 Services Started Successfully!"
echo "=================================="
echo "📡 API Server: http://localhost:8000"
echo "📖 API Docs: http://localhost:8000/docs"
echo "🔍 Health Check: http://localhost:8000/health"
echo ""
echo "🏠 Frontend: Not started (requires Node.js setup)"
echo "   To start frontend:"
echo "   cd frontend && npm install && npm run dev"
echo ""
echo "🛑 To stop services:"
echo "   kill $API_PID"
echo ""
echo "Press Ctrl+C to stop all services..."

# Keep script running and handle cleanup
trap "echo 'Stopping services...'; kill $API_PID 2>/dev/null; exit 0" INT

# Wait for API process
wait $API_PID