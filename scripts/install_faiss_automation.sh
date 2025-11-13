#!/bin/bash
"""
FAISS Index Automation Installation Script
=========================================

Installs and configures the FAISS index automation system with all dependencies,
service configuration, and monitoring setup.

Usage:
    sudo ./install_faiss_automation.sh [--dev|--production]

Author: ML Infrastructure Team
Version: 1.0.0 - T-015 FAISS Index Automation
"""

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INSTALL_MODE="${1:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check Python version
    if ! python3 --version | grep -E "3\.[8-9]|3\.1[0-9]" > /dev/null; then
        log_error "Python 3.8+ is required"
        exit 1
    fi
    
    # Check available memory
    TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $TOTAL_MEM -lt 4 ]]; then
        log_warning "Less than 4GB RAM available. FAISS rebuilds may fail."
    fi
    
    # Check disk space
    AVAILABLE_SPACE=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    if [[ $AVAILABLE_SPACE -lt 10485760 ]]; then  # 10GB in KB
        log_warning "Less than 10GB disk space available. Consider cleaning up."
    fi
    
    log_success "System requirements check completed"
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Upgrade pip
    python3 -m pip install --upgrade pip
    
    # Install required packages
    python3 -m pip install prometheus-client schedule psutil filelock pyyaml
    
    # Install existing project requirements
    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        python3 -m pip install -r "$PROJECT_ROOT/requirements.txt"
    fi
    
    log_success "Python dependencies installed"
}

# Create system user
create_user() {
    log_info "Creating service user..."
    
    if ! id "faiss-rebuild" &>/dev/null; then
        useradd -r -s /bin/false -d /var/lib/faiss-rebuild -c "FAISS Rebuild Service" faiss-rebuild
        log_success "Created user: faiss-rebuild"
    else
        log_info "User faiss-rebuild already exists"
    fi
}

# Create directories
create_directories() {
    log_info "Creating service directories..."
    
    # Configuration directory
    mkdir -p /etc/faiss-rebuild
    chown root:faiss-rebuild /etc/faiss-rebuild
    chmod 750 /etc/faiss-rebuild
    
    # Log directory
    mkdir -p /var/log/faiss-rebuild
    chown faiss-rebuild:faiss-rebuild /var/log/faiss-rebuild
    chmod 755 /var/log/faiss-rebuild
    
    # Runtime directory
    mkdir -p /var/lib/faiss-rebuild
    chown faiss-rebuild:faiss-rebuild /var/lib/faiss-rebuild
    chmod 755 /var/lib/faiss-rebuild
    
    # PID directory
    mkdir -p /var/run/faiss-rebuild
    chown faiss-rebuild:faiss-rebuild /var/run/faiss-rebuild
    chmod 755 /var/run/faiss-rebuild
    
    # Project directories (ensure correct permissions)
    chown -R faiss-rebuild:faiss-rebuild "$PROJECT_ROOT/indices" 2>/dev/null || true
    chown -R faiss-rebuild:faiss-rebuild "$PROJECT_ROOT/logs" 2>/dev/null || true
    
    log_success "Service directories created"
}

# Generate default configuration
create_config() {
    log_info "Creating default configuration..."
    
    CONFIG_FILE="/etc/faiss-rebuild/config.json"
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        cat > "$CONFIG_FILE" << EOF
{
  "scheduler": {
    "rebuild_schedule": "0 2 * * 0",
    "timezone": "UTC",
    "max_rebuild_duration_hours": 4,
    "health_check_interval_minutes": 5,
    "max_consecutive_failures": 3,
    "failure_cooldown_hours": 24,
    "enable_notifications": true,
    "notification_channels": ["log"],
    "log_level": "INFO",
    "log_file": "/var/log/faiss-rebuild/scheduler.log",
    "max_memory_gb": 8.0,
    "max_cpu_percent": 80.0,
    "rebuild_config": {
      "embeddings_dir": "embeddings",
      "indices_dir": "indices",
      "backup_dir": "indices/backups",
      "staging_dir": "indices/staging",
      "horizons": [6, 12, 24, 48],
      "index_types": ["flatip", "ivfpq"],
      "validation_enabled": true,
      "validation_sample_size": 1000,
      "min_recall_threshold": 0.95,
      "max_latency_threshold_ms": 100.0,
      "max_backups": 5,
      "backup_compression": true,
      "require_validation_pass": true,
      "enable_rollback": true,
      "max_rebuild_time_minutes": 60,
      "enable_metrics": true,
      "enable_alerts": true
    }
  },
  "monitoring": {
    "enable_prometheus": true,
    "metrics_port": 9100,
    "metrics_path": "/metrics",
    "health_check_port": 8080,
    "health_check_path": "/health",
    "max_rebuild_duration_minutes": 240.0,
    "max_failure_rate": 0.2,
    "max_consecutive_failures": 3,
    "min_success_rate_24h": 0.8,
    "metrics_retention_days": 30,
    "events_retention_days": 90,
    "integrate_with_existing_monitoring": true,
    "export_to_grafana": true
  }
}
EOF
        
        chown root:faiss-rebuild "$CONFIG_FILE"
        chmod 640 "$CONFIG_FILE"
        
        log_success "Default configuration created: $CONFIG_FILE"
    else
        log_info "Configuration file already exists: $CONFIG_FILE"
    fi
}

# Create systemd service
create_systemd_service() {
    log_info "Creating systemd service..."
    
    SERVICE_FILE="/etc/systemd/system/faiss-rebuild.service"
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=FAISS Index Rebuild Service
Documentation=file://$PROJECT_ROOT/FAISS_INDEX_AUTOMATION_README.md
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=faiss-rebuild
Group=faiss-rebuild
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONPATH=$PROJECT_ROOT
ExecStart=/usr/bin/python3 $PROJECT_ROOT/scripts/faiss_rebuild_service.py --config /etc/faiss-rebuild/config.json start
ExecReload=/bin/kill -HUP \$MAINPID
ExecStop=/bin/kill -TERM \$MAINPID
Restart=always
RestartSec=10
TimeoutStopSec=30

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$PROJECT_ROOT/logs $PROJECT_ROOT/indices /var/log/faiss-rebuild /var/lib/faiss-rebuild /var/run/faiss-rebuild

# Resource limits
MemoryLimit=8G
CPUQuota=200%
TasksMax=100

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=faiss-rebuild

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    systemctl enable faiss-rebuild
    
    log_success "Systemd service created and enabled"
}

# Create log rotation
create_logrotate() {
    log_info "Setting up log rotation..."
    
    LOGROTATE_FILE="/etc/logrotate.d/faiss-rebuild"
    
    cat > "$LOGROTATE_FILE" << EOF
/var/log/faiss-rebuild/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 faiss-rebuild faiss-rebuild
    postrotate
        systemctl reload faiss-rebuild || true
    endscript
}
EOF
    
    log_success "Log rotation configured"
}

# Create cron job for maintenance
create_maintenance_cron() {
    log_info "Setting up maintenance cron job..."
    
    CRON_FILE="/etc/cron.d/faiss-rebuild-maintenance"
    
    cat > "$CRON_FILE" << EOF
# FAISS Rebuild Maintenance Tasks
# Run daily at 1 AM
0 1 * * * faiss-rebuild cd $PROJECT_ROOT && python3 scripts/faiss_rebuild_cli.py maintenance cleanup >/dev/null 2>&1

# Health check every 6 hours
0 */6 * * * faiss-rebuild cd $PROJECT_ROOT && python3 scripts/faiss_rebuild_cli.py monitor --health >/var/log/faiss-rebuild/health-check.log 2>&1
EOF
    
    chmod 644 "$CRON_FILE"
    
    log_success "Maintenance cron jobs created"
}

# Setup monitoring integration
setup_monitoring() {
    log_info "Setting up monitoring integration..."
    
    # Create Prometheus configuration snippet
    PROMETHEUS_CONFIG="/etc/faiss-rebuild/prometheus-rules.yml"
    
    python3 "$PROJECT_ROOT/core/faiss_rebuild_monitoring.py" --action alerts --output "$PROMETHEUS_CONFIG"
    chown root:faiss-rebuild "$PROMETHEUS_CONFIG"
    chmod 640 "$PROMETHEUS_CONFIG"
    
    # Create Grafana dashboard
    GRAFANA_DASHBOARD="/etc/faiss-rebuild/grafana-dashboard.json"
    
    python3 "$PROJECT_ROOT/core/faiss_rebuild_monitoring.py" --action dashboard --output "$GRAFANA_DASHBOARD"
    chown root:faiss-rebuild "$GRAFANA_DASHBOARD"
    chmod 640 "$GRAFANA_DASHBOARD"
    
    log_success "Monitoring configuration created"
    log_info "Import $GRAFANA_DASHBOARD into Grafana"
    log_info "Add $PROMETHEUS_CONFIG to Prometheus rules"
}

# Validate installation
validate_installation() {
    log_info "Validating installation..."
    
    # Check service can start
    if systemctl start faiss-rebuild; then
        sleep 5
        if systemctl is-active --quiet faiss-rebuild; then
            log_success "Service started successfully"
            
            # Check health endpoint
            if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
                log_success "Health endpoint responding"
            else
                log_warning "Health endpoint not responding (may take a moment to initialize)"
            fi
            
            systemctl stop faiss-rebuild
        else
            log_error "Service failed to start properly"
            systemctl status faiss-rebuild
            return 1
        fi
    else
        log_error "Service failed to start"
        return 1
    fi
    
    # Test CLI
    if su - faiss-rebuild -s /bin/bash -c "cd $PROJECT_ROOT && python3 scripts/faiss_rebuild_cli.py status" >/dev/null 2>&1; then
        log_success "CLI working correctly"
    else
        log_warning "CLI test failed - check permissions"
    fi
    
    log_success "Installation validation completed"
}

# Create firewall rules (if needed)
setup_firewall() {
    if command -v ufw >/dev/null 2>&1; then
        log_info "Configuring UFW firewall rules..."
        
        # Allow health check port (internal only)
        ufw allow from 127.0.0.1 to any port 8080
        
        # Allow metrics port (adjust as needed)
        ufw allow from 127.0.0.1 to any port 9100
        
        log_success "Firewall rules configured"
    elif command -v firewall-cmd >/dev/null 2>&1; then
        log_info "Configuring firewalld rules..."
        
        firewall-cmd --permanent --add-rich-rule="rule family='ipv4' source address='127.0.0.1' port protocol='tcp' port='8080' accept"
        firewall-cmd --permanent --add-rich-rule="rule family='ipv4' source address='127.0.0.1' port protocol='tcp' port='9100' accept"
        firewall-cmd --reload
        
        log_success "Firewall rules configured"
    else
        log_info "No supported firewall found, skipping firewall configuration"
    fi
}

# Main installation function
main() {
    log_info "Starting FAISS Index Automation installation..."
    log_info "Installation mode: $INSTALL_MODE"
    log_info "Project root: $PROJECT_ROOT"
    
    check_root
    check_requirements
    install_dependencies
    create_user
    create_directories
    create_config
    create_systemd_service
    create_logrotate
    create_maintenance_cron
    setup_monitoring
    
    if [[ "$INSTALL_MODE" == "production" ]]; then
        setup_firewall
    fi
    
    validate_installation
    
    log_success "FAISS Index Automation installation completed!"
    echo
    log_info "Next steps:"
    echo "  1. Review configuration: /etc/faiss-rebuild/config.json"
    echo "  2. Start the service: sudo systemctl start faiss-rebuild"
    echo "  3. Check status: sudo systemctl status faiss-rebuild"
    echo "  4. View logs: sudo journalctl -u faiss-rebuild -f"
    echo "  5. Test CLI: python3 $PROJECT_ROOT/scripts/faiss_rebuild_cli.py status"
    echo
    log_info "Documentation: $PROJECT_ROOT/FAISS_INDEX_AUTOMATION_README.md"
}

# Run main function
main "$@"