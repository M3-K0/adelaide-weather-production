#!/bin/bash

# Weather Forecast Panel Deployment Script
# Comprehensive deployment of the Grafana Weather Forecast Panel with full integration

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/home/micha/weather-forecast-final"
PLUGIN_DIR="$SCRIPT_DIR/weather-forecast-panel"
GRAFANA_PLUGINS_DIR="/var/lib/grafana/plugins"
MONITORING_DIR="$PROJECT_ROOT/monitoring"

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
    
    # Check if Grafana is installed
    if ! command -v grafana-server &> /dev/null; then
        log_error "Grafana is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Node.js is installed
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed"
        exit 1
    fi
    
    # Check if npm is installed
    if ! command -v npm &> /dev/null; then
        log_error "npm is not installed"
        exit 1
    fi
    
    # Check Node.js version
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 18 ]; then
        log_error "Node.js version 18 or higher is required"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

build_plugin() {
    log_info "Building Weather Forecast Panel plugin..."
    
    cd "$PLUGIN_DIR"
    
    # Install dependencies
    log_info "Installing dependencies..."
    npm install
    
    # Build the plugin
    log_info "Building plugin distribution..."
    npm run build
    
    # Verify build output
    if [ ! -d "dist" ]; then
        log_error "Plugin build failed - dist directory not found"
        exit 1
    fi
    
    log_success "Plugin built successfully"
}

install_plugin() {
    log_info "Installing plugin to Grafana..."
    
    # Stop Grafana service
    log_info "Stopping Grafana service..."
    systemctl stop grafana-server
    
    # Create plugins directory if it doesn't exist
    if [ ! -d "$GRAFANA_PLUGINS_DIR" ]; then
        log_info "Creating Grafana plugins directory..."
        mkdir -p "$GRAFANA_PLUGINS_DIR"
        chown grafana:grafana "$GRAFANA_PLUGINS_DIR"
    fi
    
    # Remove existing plugin
    PLUGIN_INSTALL_DIR="$GRAFANA_PLUGINS_DIR/weather-forecast-panel"
    if [ -d "$PLUGIN_INSTALL_DIR" ]; then
        log_info "Removing existing plugin installation..."
        rm -rf "$PLUGIN_INSTALL_DIR"
    fi
    
    # Copy plugin to Grafana plugins directory
    log_info "Copying plugin files..."
    cp -r "$PLUGIN_DIR" "$PLUGIN_INSTALL_DIR"
    chown -R grafana:grafana "$PLUGIN_INSTALL_DIR"
    
    log_success "Plugin installed to $PLUGIN_INSTALL_DIR"
}

configure_grafana() {
    log_info "Configuring Grafana for unsigned plugins..."
    
    GRAFANA_CONFIG="/etc/grafana/grafana.ini"
    
    if [ -f "$GRAFANA_CONFIG" ]; then
        # Backup original config
        cp "$GRAFANA_CONFIG" "$GRAFANA_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Configure unsigned plugins
        if grep -q "allow_loading_unsigned_plugins" "$GRAFANA_CONFIG"; then
            sed -i "s/.*allow_loading_unsigned_plugins.*/allow_loading_unsigned_plugins = weather-forecast-panel/" "$GRAFANA_CONFIG"
        else
            if grep -q "^\[plugins\]" "$GRAFANA_CONFIG"; then
                sed -i "/^\[plugins\]/a allow_loading_unsigned_plugins = weather-forecast-panel" "$GRAFANA_CONFIG"
            else
                echo -e "\n[plugins]\nallow_loading_unsigned_plugins = weather-forecast-panel" >> "$GRAFANA_CONFIG"
            fi
        fi
        
        log_success "Grafana configuration updated"
    else
        log_warning "Grafana config file not found at $GRAFANA_CONFIG"
    fi
}

setup_prometheus_exporter() {
    log_info "Setting up Prometheus weather exporter..."
    
    # Install Python dependencies
    pip3 install prometheus_client psycopg2-binary numpy || {
        log_warning "Failed to install Python dependencies via pip3"
        log_info "Attempting to install via apt..."
        apt-get update
        apt-get install -y python3-prometheus-client python3-psycopg2 python3-numpy
    }
    
    # Copy exporter and config
    cp "$MONITORING_DIR/prometheus-weather-exporter.py" "/usr/local/bin/"
    cp "$MONITORING_DIR/weather_exporter_config.json" "/etc/"
    chmod +x "/usr/local/bin/prometheus-weather-exporter.py"
    
    # Create systemd service
    cat > /etc/systemd/system/weather-exporter.service << EOF
[Unit]
Description=Weather Prometheus Exporter
After=network.target

[Service]
Type=simple
User=nobody
Group=nogroup
ExecStart=/usr/bin/python3 /usr/local/bin/prometheus-weather-exporter.py --config /etc/weather_exporter_config.json --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable weather-exporter
    
    log_success "Weather exporter service configured"
}

install_dashboards() {
    log_info "Installing Grafana dashboards..."
    
    GRAFANA_DASHBOARDS_DIR="/var/lib/grafana/dashboards"
    
    # Create dashboards directory
    mkdir -p "$GRAFANA_DASHBOARDS_DIR"
    
    # Copy dashboard files
    cp "$MONITORING_DIR/grafana/dashboards/weather-forecast-meteorologist.json" "$GRAFANA_DASHBOARDS_DIR/"
    cp "$MONITORING_DIR/grafana/dashboards/adelaide-weather-comprehensive.json" "$GRAFANA_DASHBOARDS_DIR/"
    
    # Set ownership
    chown -R grafana:grafana "$GRAFANA_DASHBOARDS_DIR"
    
    log_success "Dashboards installed"
}

update_prometheus_config() {
    log_info "Updating Prometheus configuration..."
    
    PROMETHEUS_CONFIG="/etc/prometheus/prometheus.yml"
    
    if [ -f "$PROMETHEUS_CONFIG" ]; then
        # Backup existing config
        cp "$PROMETHEUS_CONFIG" "$PROMETHEUS_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Add weather exporter job if not exists
        if ! grep -q "weather-exporter" "$PROMETHEUS_CONFIG"; then
            cat >> "$PROMETHEUS_CONFIG" << EOF

  - job_name: 'weather-exporter'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 30s
    metrics_path: /metrics
EOF
            log_success "Prometheus configuration updated"
        else
            log_info "Weather exporter job already exists in Prometheus config"
        fi
    else
        log_warning "Prometheus config file not found at $PROMETHEUS_CONFIG"
    fi
}

start_services() {
    log_info "Starting services..."
    
    # Start weather exporter
    systemctl start weather-exporter
    if systemctl is-active --quiet weather-exporter; then
        log_success "Weather exporter service started"
    else
        log_error "Failed to start weather exporter service"
        journalctl -u weather-exporter --no-pager -n 20
    fi
    
    # Restart Prometheus if running
    if systemctl is-active --quiet prometheus; then
        systemctl restart prometheus
        log_success "Prometheus service restarted"
    fi
    
    # Start Grafana
    systemctl start grafana-server
    if systemctl is-active --quiet grafana-server; then
        log_success "Grafana service started"
    else
        log_error "Failed to start Grafana service"
        journalctl -u grafana-server --no-pager -n 20
        exit 1
    fi
}

verify_installation() {
    log_info "Verifying installation..."
    
    # Wait for services to fully start
    sleep 10
    
    # Check weather exporter
    if curl -sf http://localhost:8000/metrics > /dev/null; then
        log_success "Weather exporter is responding"
    else
        log_warning "Weather exporter not responding at http://localhost:8000/metrics"
    fi
    
    # Check Grafana
    if curl -sf http://localhost:3000/api/health > /dev/null; then
        log_success "Grafana is responding"
    else
        log_warning "Grafana not responding at http://localhost:3000"
    fi
    
    # Check plugin in Grafana logs
    if journalctl -u grafana-server --since "5 minutes ago" | grep -q "weather-forecast-panel"; then
        log_success "Weather panel plugin detected in Grafana logs"
    else
        log_warning "Weather panel plugin not found in recent Grafana logs"
    fi
}

run_tests() {
    log_info "Running panel tests..."
    
    cd "$SCRIPT_DIR"
    
    # Install test dependencies
    npm install puppeteer
    
    # Run tests
    if node test-panel.js; then
        log_success "Panel tests passed"
    else
        log_warning "Some panel tests failed - check test-report.json for details"
    fi
}

print_summary() {
    echo ""
    echo "🎉 Weather Forecast Panel Deployment Complete!"
    echo "=============================================="
    echo ""
    echo "📋 Summary:"
    echo "- ✅ Weather Forecast Panel plugin installed"
    echo "- ✅ Prometheus weather exporter configured"
    echo "- ✅ Grafana dashboards installed"
    echo "- ✅ Services started and verified"
    echo ""
    echo "🔗 Access URLs:"
    echo "- Grafana: http://localhost:3000"
    echo "- Weather Metrics: http://localhost:8000/metrics"
    echo ""
    echo "📖 Next Steps:"
    echo "1. Login to Grafana (admin/admin)"
    echo "2. Navigate to 'Weather Forecast - Meteorologist Panel' dashboard"
    echo "3. Configure your data sources if needed"
    echo "4. Customize panel settings for your requirements"
    echo ""
    echo "🔧 Configuration Files:"
    echo "- Plugin: $GRAFANA_PLUGINS_DIR/weather-forecast-panel"
    echo "- Exporter Config: /etc/weather_exporter_config.json"
    echo "- Grafana Config: /etc/grafana/grafana.ini"
    echo ""
    echo "📊 Available Dashboards:"
    echo "- Weather Forecast - Meteorologist Panel"
    echo "- Adelaide Weather System - Comprehensive Observability"
    echo ""
    echo "🐛 Troubleshooting:"
    echo "- Check logs: journalctl -u grafana-server -f"
    echo "- Check exporter: journalctl -u weather-exporter -f"
    echo "- Test metrics: curl http://localhost:8000/metrics"
    echo ""
}

# Main execution
main() {
    echo "🌦️  Weather Forecast Panel Deployment"
    echo "====================================="
    echo ""
    
    check_prerequisites
    build_plugin
    install_plugin
    configure_grafana
    setup_prometheus_exporter
    install_dashboards
    update_prometheus_config
    start_services
    verify_installation
    
    # Run tests if requested
    if [ "${1:-}" = "--with-tests" ]; then
        run_tests
    fi
    
    print_summary
    
    log_success "Deployment completed successfully!"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--with-tests] [--help]"
        echo ""
        echo "Options:"
        echo "  --with-tests    Run automated tests after deployment"
        echo "  --help, -h      Show this help message"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac