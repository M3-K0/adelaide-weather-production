#!/bin/bash
# =============================================================================
# Adelaide Weather System - SSL Certificate Generator
# =============================================================================
# 
# Generates self-signed SSL certificates for development and testing.
# For production, replace these with proper SSL certificates from a CA.
# 
# Usage:
#   ./generate_certs.sh [domain]
# 
# Example:
#   ./generate_certs.sh localhost
#   ./generate_certs.sh weather.example.com
# 
# =============================================================================

set -euo pipefail

# Configuration
DOMAIN="${1:-localhost}"
SSL_DIR="$(dirname "$0")"
CERT_FILE="$SSL_DIR/cert.pem"
KEY_FILE="$SSL_DIR/key.pem"
DAYS_VALID=365

# Certificate subject information
COUNTRY="AU"
STATE="South Australia"
CITY="Adelaide"
ORGANIZATION="Adelaide Weather Forecasting System"
UNIT="Development"

echo "============================================================================="
echo "Generating SSL certificates for Adelaide Weather System"
echo "============================================================================="
echo "Domain: $DOMAIN"
echo "Certificate path: $CERT_FILE"
echo "Private key path: $KEY_FILE"
echo "Valid for: $DAYS_VALID days"
echo "============================================================================="

# Check if OpenSSL is available
if ! command -v openssl &> /dev/null; then
    echo "Error: OpenSSL is not installed or not in PATH"
    echo "Please install OpenSSL to generate certificates"
    exit 1
fi

# Backup existing certificates if they exist
if [[ -f "$CERT_FILE" ]]; then
    echo "Backing up existing certificate..."
    mv "$CERT_FILE" "$CERT_FILE.backup.$(date +%Y%m%d-%H%M%S)"
fi

if [[ -f "$KEY_FILE" ]]; then
    echo "Backing up existing private key..."
    mv "$KEY_FILE" "$KEY_FILE.backup.$(date +%Y%m%d-%H%M%S)"
fi

# Generate private key
echo "Generating RSA private key..."
openssl genrsa -out "$KEY_FILE" 2048

# Set secure permissions on private key
chmod 600 "$KEY_FILE"

# Generate certificate signing request and self-signed certificate
echo "Generating self-signed certificate..."
openssl req -new -x509 -key "$KEY_FILE" -out "$CERT_FILE" -days $DAYS_VALID \
    -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORGANIZATION/OU=$UNIT/CN=$DOMAIN" \
    -extensions v3_req \
    -config <(cat <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = $COUNTRY
ST = $STATE
L = $CITY
O = $ORGANIZATION
OU = $UNIT
CN = $DOMAIN

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = localhost
DNS.3 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF
)

# Set secure permissions on certificate
chmod 644 "$CERT_FILE"

# Verify the generated certificate
echo ""
echo "Certificate generated successfully!"
echo ""
echo "Certificate details:"
openssl x509 -in "$CERT_FILE" -text -noout | grep -E "(Subject:|Not Before:|Not After:|DNS:|IP Address:)" || true

echo ""
echo "============================================================================="
echo "SSL certificates generated successfully!"
echo "============================================================================="
echo "Certificate: $CERT_FILE"
echo "Private Key: $KEY_FILE"
echo ""
echo "IMPORTANT NOTES:"
echo "1. These are self-signed certificates for development/testing only"
echo "2. Browsers will show security warnings for self-signed certificates"
echo "3. For production, obtain certificates from a trusted Certificate Authority"
echo "4. Consider using Let's Encrypt for free production certificates"
echo ""
echo "To trust this certificate locally (Chrome/Firefox):"
echo "1. Open https://$DOMAIN in browser"
echo "2. Click 'Advanced' -> 'Proceed to $DOMAIN (unsafe)'"
echo "3. Or import $CERT_FILE into your browser's trusted certificates"
echo "============================================================================="