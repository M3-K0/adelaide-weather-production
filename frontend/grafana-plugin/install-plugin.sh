#!/bin/bash

# Weather Forecast Panel Plugin Installation Script
# This script installs the custom Grafana panel plugin for weather forecasting

set -e

echo "🌦️  Installing Weather Forecast Panel Plugin..."

# Configuration
GRAFANA_PLUGINS_DIR="/var/lib/grafana/plugins"
PLUGIN_NAME="weather-forecast-panel"
PLUGIN_DIR="$GRAFANA_PLUGINS_DIR/$PLUGIN_NAME"
SOURCE_DIR="$(pwd)/weather-forecast-panel"

# Check if Grafana is installed
if ! command -v grafana-server &> /dev/null; then
    echo "❌ Grafana is not installed or not in PATH"
    exit 1
fi

# Check if we're running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root or with sudo"
    exit 1
fi

# Create plugins directory if it doesn't exist
if [ ! -d "$GRAFANA_PLUGINS_DIR" ]; then
    echo "📁 Creating Grafana plugins directory..."
    mkdir -p "$GRAFANA_PLUGINS_DIR"
    chown grafana:grafana "$GRAFANA_PLUGINS_DIR"
fi

# Stop Grafana service
echo "⏹️  Stopping Grafana service..."
systemctl stop grafana-server

# Remove existing plugin if it exists
if [ -d "$PLUGIN_DIR" ]; then
    echo "🗑️  Removing existing plugin installation..."
    rm -rf "$PLUGIN_DIR"
fi

# Build the plugin
echo "🔨 Building plugin..."
cd "$SOURCE_DIR"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build the plugin
echo "🏗️  Building plugin distribution..."
npm run build

# Copy plugin to Grafana plugins directory
echo "📋 Installing plugin to Grafana..."
cp -r "$SOURCE_DIR" "$PLUGIN_DIR"

# Set proper ownership
chown -R grafana:grafana "$PLUGIN_DIR"

# Configure Grafana to allow unsigned plugins (for development)
GRAFANA_CONFIG="/etc/grafana/grafana.ini"
if [ -f "$GRAFANA_CONFIG" ]; then
    echo "⚙️  Configuring Grafana to allow unsigned plugins..."
    
    # Backup original config
    cp "$GRAFANA_CONFIG" "$GRAFANA_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Add or update allow_loading_unsigned_plugins setting
    if grep -q "allow_loading_unsigned_plugins" "$GRAFANA_CONFIG"; then
        sed -i "s/.*allow_loading_unsigned_plugins.*/allow_loading_unsigned_plugins = $PLUGIN_NAME/" "$GRAFANA_CONFIG"
    else
        # Add to [plugins] section or create it
        if grep -q "^\[plugins\]" "$GRAFANA_CONFIG"; then
            sed -i "/^\[plugins\]/a allow_loading_unsigned_plugins = $PLUGIN_NAME" "$GRAFANA_CONFIG"
        else
            echo -e "\n[plugins]\nallow_loading_unsigned_plugins = $PLUGIN_NAME" >> "$GRAFANA_CONFIG"
        fi
    fi
fi

# Update Grafana dashboard with new panel
DASHBOARD_PATH="/home/micha/weather-forecast-final/monitoring/grafana/dashboards"
if [ -d "$DASHBOARD_PATH" ]; then
    echo "📊 Creating weather forecast dashboard..."
    
    cat > "$DASHBOARD_PATH/weather-forecast-panel.json" << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "Weather Forecast Analysis",
    "tags": ["weather", "forecast", "meteorology"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Weather Forecast Panel",
        "type": "weather-forecast-panel",
        "gridPos": {
          "h": 16,
          "w": 24,
          "x": 0,
          "y": 0
        },
        "targets": [
          {
            "expr": "weather_observation",
            "refId": "A",
            "legendFormat": "Observations"
          },
          {
            "expr": "weather_forecast",
            "refId": "B",
            "legendFormat": "Forecast"
          },
          {
            "expr": "analog_similarity_score",
            "refId": "C",
            "legendFormat": "Analog Patterns"
          }
        ],
        "options": {
          "showObservations": true,
          "showForecast": true,
          "showAnalogPatterns": true,
          "showUncertaintyBands": true,
          "animationSpeed": 1000,
          "maxAnalogCount": 5,
          "confidenceThreshold": 0.7,
          "defaultHorizon": "6h",
          "enableHistoricalEvents": true,
          "splitViewRatio": 0.5
        }
      },
      {
        "id": 2,
        "title": "Forecast Metrics",
        "type": "stat",
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 16
        },
        "targets": [
          {
            "expr": "rate(forecast_requests_total[5m])",
            "refId": "A",
            "legendFormat": "Forecast Requests/sec"
          }
        ]
      },
      {
        "id": 3,
        "title": "Analog Pattern Quality",
        "type": "gauge",
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 16
        },
        "targets": [
          {
            "expr": "avg(analog_similarity_score)",
            "refId": "A",
            "legendFormat": "Average Similarity"
          }
        ]
      }
    ],
    "time": {
      "from": "now-24h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
EOF
fi

# Start Grafana service
echo "▶️  Starting Grafana service..."
systemctl start grafana-server

# Wait for Grafana to start
echo "⏳ Waiting for Grafana to start..."
sleep 10

# Check if Grafana is running
if systemctl is-active --quiet grafana-server; then
    echo "✅ Grafana service is running"
else
    echo "❌ Failed to start Grafana service"
    exit 1
fi

# Verify plugin installation
echo "🔍 Verifying plugin installation..."
sleep 5

# Check if plugin appears in Grafana logs
if journalctl -u grafana-server --since "1 minute ago" | grep -q "$PLUGIN_NAME"; then
    echo "✅ Plugin detected in Grafana logs"
else
    echo "⚠️  Plugin may not be loaded - check Grafana logs"
fi

echo ""
echo "🎉 Weather Forecast Panel Plugin installation completed!"
echo ""
echo "📋 Next steps:"
echo "1. Open Grafana at http://localhost:3000"
echo "2. Login with your Grafana credentials"
echo "3. Create a new dashboard"
echo "4. Add a new panel and select 'Weather Forecast Panel' from the visualization list"
echo "5. Configure your Prometheus data source with weather metrics"
echo "6. Set up TimescaleDB connection for historical data"
echo ""
echo "🔧 Configuration:"
echo "- Plugin directory: $PLUGIN_DIR"
echo "- Grafana config: $GRAFANA_CONFIG"
echo "- Dashboard: $DASHBOARD_PATH/weather-forecast-panel.json"
echo ""
echo "📖 For detailed configuration instructions, see the README.md file"
echo ""
echo "🐛 Troubleshooting:"
echo "- Check Grafana logs: journalctl -u grafana-server -f"
echo "- Verify plugin permissions: ls -la $PLUGIN_DIR"
echo "- Test plugin build: cd $SOURCE_DIR && npm run build"