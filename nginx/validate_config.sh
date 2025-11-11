#!/bin/bash
# =============================================================================
# Adelaide Weather System - Nginx Configuration Validator
# =============================================================================
# 
# Validates nginx configuration using Docker without affecting running services
# 
# Usage:
#   ./validate_config.sh
# 
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"
NGINX_CONF="$SCRIPT_DIR/nginx.conf"
SSL_DIR="$SCRIPT_DIR/ssl"

echo "============================================================================="
echo "Validating Adelaide Weather System Nginx Configuration"
echo "============================================================================="

# Check if configuration file exists
if [[ ! -f "$NGINX_CONF" ]]; then
    echo "Error: nginx.conf not found at $NGINX_CONF"
    exit 1
fi

# Check if SSL certificates exist
if [[ ! -f "$SSL_DIR/cert.pem" ]] || [[ ! -f "$SSL_DIR/key.pem" ]]; then
    echo "Warning: SSL certificates not found. Generating them now..."
    if [[ -x "$SSL_DIR/generate_certs.sh" ]]; then
        cd "$SSL_DIR" && ./generate_certs.sh localhost
    else
        echo "Error: Cannot generate SSL certificates. Please run:"
        echo "  cd $SSL_DIR && ./generate_certs.sh localhost"
        exit 1
    fi
fi

echo "Testing nginx configuration syntax..."

# Run nginx configuration test in a temporary container
docker run --rm \
    -v "$NGINX_CONF:/etc/nginx/nginx.conf:ro" \
    -v "$SSL_DIR:/etc/nginx/ssl:ro" \
    nginx:1.24-alpine \
    nginx -t

if [[ $? -eq 0 ]]; then
    echo ""
    echo "============================================================================="
    echo "✅ Nginx configuration validation PASSED"
    echo "============================================================================="
    echo "Configuration file: $NGINX_CONF"
    echo "SSL certificates: $SSL_DIR"
    echo ""
    echo "Configuration is ready for deployment with docker-compose!"
    echo "============================================================================="
else
    echo ""
    echo "============================================================================="
    echo "❌ Nginx configuration validation FAILED"
    echo "============================================================================="
    echo "Please check the configuration file for syntax errors."
    exit 1
fi