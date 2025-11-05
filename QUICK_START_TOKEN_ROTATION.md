# Quick Start Guide - API Token Rotation

## Prerequisites

```bash
# Set required environment variables
export ENVIRONMENT=production  # or staging/development
export CREDENTIAL_MASTER_KEY=<your_secure_master_key>
```

## Common Operations

### 🔄 Rotate API Token
```bash
# Basic rotation (generates new 64-character token)
python api/token_rotation_cli.py rotate --user admin

# Custom length rotation
python api/token_rotation_cli.py rotate --length 48 --user admin
```

### 📤 Export Token for Environment Use
```bash
# Export as environment variable command
python api/token_rotation_cli.py export

# Apply to current shell
eval "$(python api/token_rotation_cli.py export)"

# Custom environment variable name
python api/token_rotation_cli.py export --env-var MY_API_TOKEN
```

### 🔍 Check System Health
```bash
# Quick health check
python api/token_rotation_cli.py health

# Detailed validation
python api/token_rotation_cli.py validate
```

### 📋 View Audit Trail
```bash
# Last 7 days
python api/token_rotation_cli.py audit --days 7

# Filter by operation
python api/token_rotation_cli.py audit --operation rotate_token --days 30

# JSON format for automation
python api/token_rotation_cli.py audit --format json --days 1
```

### 💾 Backup Management
```bash
# List available backups
python api/token_rotation_cli.py list-backups

# Restore from backup (emergency)
python api/token_rotation_cli.py restore --backup-id <backup_id>
```

## Emergency Procedures

### 🚨 Token Compromise
1. Immediately rotate token:
   ```bash
   python api/token_rotation_cli.py rotate --user emergency
   ```

2. Export new token:
   ```bash
   eval "$(python api/token_rotation_cli.py export)"
   ```

3. Update application configuration and restart services

4. Review audit logs:
   ```bash
   python api/token_rotation_cli.py audit --days 30
   ```

### 🔧 System Recovery
If system issues occur:

1. Check health:
   ```bash
   python api/token_rotation_cli.py health
   ```

2. If needed, restore from backup:
   ```bash
   python api/token_rotation_cli.py list-backups
   python api/token_rotation_cli.py restore --backup-id <most_recent>
   ```

3. Validate restoration:
   ```bash
   python api/token_rotation_cli.py validate
   ```

## Automation Scripts

### Daily Health Check
```bash
#!/bin/bash
# daily_token_health.sh
HEALTH=$(python api/token_rotation_cli.py health)
if [[ $HEALTH == *"ERROR"* ]] || [[ $HEALTH == *"FAIL"* ]]; then
    echo "TOKEN HEALTH ISSUE: $HEALTH" | mail -s "Token Health Alert" ops-team@company.com
fi
```

### Weekly Token Rotation
```bash
#!/bin/bash
# weekly_rotation.sh
python api/token_rotation_cli.py rotate --user automated
if [ $? -eq 0 ]; then
    echo "Token rotated successfully at $(date)" >> /var/log/token_rotation.log
    # Update your deployment configuration here
    # kubectl set env deployment/api API_TOKEN="$(python api/token_rotation_cli.py export | cut -d'=' -f2 | tr -d "'")"
else
    echo "Token rotation failed at $(date)" >> /var/log/token_rotation.log
fi
```

## Integration with CI/CD

### Docker Environment
```dockerfile
# In your Dockerfile
ENV CREDENTIAL_MASTER_KEY=""
ENV ENVIRONMENT="production"

# Copy token management tools
COPY api/token_rotation_cli.py /app/
COPY api/enhanced_token_manager.py /app/
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: adelaide-weather-api
spec:
  template:
    spec:
      containers:
      - name: api
        env:
        - name: CREDENTIAL_MASTER_KEY
          valueFrom:
            secretKeyRef:
              name: token-master-key
              key: master-key
        - name: ENVIRONMENT
          value: "production"
```

### Health Check Endpoint
Add to your monitoring:
```bash
# Health check command
curl -f http://localhost:8000/health || python api/token_rotation_cli.py health
```

## Troubleshooting

### Common Issues

1. **"Master key not found"**
   ```bash
   export CREDENTIAL_MASTER_KEY=<your_key>
   ```

2. **"Token validation failed"**
   ```bash
   python api/token_rotation_cli.py validate
   # Check token entropy and length requirements
   ```

3. **"Permission denied"**
   ```bash
   # Check directory permissions
   chmod 700 ~/.adelaide-weather/
   ```

4. **"No tokens found"**
   ```bash
   # Generate initial token
   python api/token_rotation_cli.py generate --length 64
   ```

### Verification Commands
```bash
# Verify CLI is working
python api/token_rotation_cli.py --help

# Verify configuration
python api/token_rotation_cli.py health

# Verify token strength
python api/token_rotation_cli.py validate

# Verify audit logging
python api/token_rotation_cli.py audit --days 1
```

## Security Notes

- 🔒 Tokens are never displayed in logs (only hashes for correlation)
- 🛡️ All operations require user attribution for audit trails
- 🔑 Master keys should be stored securely (preferably in secret management systems)
- 📊 Regular audit log reviews are recommended
- 🔄 Token rotation every 90 days is recommended
- 💾 Backup retention is 30 days by default

## Need Help?

```bash
# CLI help
python api/token_rotation_cli.py --help
python api/token_rotation_cli.py <command> --help

# Run demonstration
python demo_token_rotation.py

# Run test suite
python test_token_rotation_integration.py
```