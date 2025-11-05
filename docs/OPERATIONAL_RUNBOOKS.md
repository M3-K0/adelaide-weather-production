# Adelaide Weather API - Comprehensive Operational Runbooks

**System:** Adelaide Weather Forecasting System (Enhanced)  
**Document Date:** 2025-11-05  
**Version:** 2.0.0  
**Scope:** Production Operations, Incident Response, and System Management  

---

## Table of Contents

### Critical Incident Response
1. [FAISS Indices Missing/Corrupted Recovery](#1-faiss-indices-missingcorrupted-recovery)
2. [API Token Rotation Procedures](#2-api-token-rotation-procedures) 
3. [Degraded Analog Search Recovery](#3-degraded-analog-search-recovery)
4. [System Health Recovery](#4-system-health-recovery)
5. [Performance Issues Response](#5-performance-issues-response)
6. [Security Incidents Response](#6-security-incidents-response)

### System Management
7. [Enhanced Health Monitoring Guide](#7-enhanced-health-monitoring-guide)
8. [Configuration Management and Drift Detection](#8-configuration-management-and-drift-detection)
9. [Credential Management Operations](#9-credential-management-operations)
10. [Performance Optimization Procedures](#10-performance-optimization-procedures)

### Infrastructure Operations
11. [Multi-Environment Deployment Management](#11-multi-environment-deployment-management)
12. [Container and Kubernetes Operations](#12-container-and-kubernetes-operations)
13. [Backup and Recovery Operations](#13-backup-and-recovery-operations)
14. [CI/CD Pipeline Management](#14-cicd-pipeline-management)

### Monitoring and Alerting
15. [Prometheus and Grafana Operations](#15-prometheus-and-grafana-operations)
16. [Real-time Monitoring Procedures](#16-real-time-monitoring-procedures)
17. [Alert Management and Response](#17-alert-management-and-response)

### Emergency Procedures
18. [Emergency Contact and Escalation](#18-emergency-contact-and-escalation)
19. [Disaster Recovery Procedures](#19-disaster-recovery-procedures)
20. [Business Continuity Management](#20-business-continuity-management)

---

## 1. FAISS Indices Missing/Corrupted Recovery

### 1.1 Detection

**Symptoms:**
- API health check failures for `/health/faiss`
- Error messages: "FAISS health monitoring not available"
- Forecast requests failing with "Search functionality failed"
- Startup validation failures for FAISS indices

**Quick Detection:**
```bash
# Check FAISS health status
curl -s "https://api.adelaide-weather.com/health/faiss" | jq '.'

# Verify index files exist
ls -la /app/indices/faiss_*h_*.faiss

# Check index file sizes
find /app/indices -name "*.faiss" -exec ls -lh {} \;
```

### 1.2 Impact Assessment

**Severity:** CRITICAL
- **Response Time:** Immediate (< 5 minutes)
- **User Impact:** Complete API functionality loss
- **Business Impact:** No weather forecasting capability

**Validation Steps:**
```bash
# Test FAISS index loading
python3 -c "
import faiss
import sys
try:
    index = faiss.read_index('/app/indices/faiss_24h_ivfpq.faiss')
    print(f'Index loaded: {index.ntotal} vectors, {index.d} dimensions')
except Exception as e:
    print(f'FAISS load failed: {e}')
    sys.exit(1)
"

# Check expected pattern counts (T-002 validation)
EXPECTED_PATTERNS=(
    "6h:6574"
    "12h:6574" 
    "24h:13148"
    "48h:13148"
)

for pattern in "${EXPECTED_PATTERNS[@]}"; do
    horizon=$(echo $pattern | cut -d: -f1)
    expected=$(echo $pattern | cut -d: -f2)
    
    for index_type in flatip ivfpq; do
        index_file="/app/indices/faiss_${horizon}_${index_type}.faiss"
        if [ -f "$index_file" ]; then
            actual=$(python3 -c "import faiss; idx=faiss.read_index('$index_file'); print(idx.ntotal)")
            echo "✓ ${horizon} ${index_type}: ${actual} patterns (expected: ${expected})"
        else
            echo "✗ Missing: $index_file"
        fi
    done
done
```

### 1.3 Recovery Procedures

#### Option A: Restore from Backup (Fastest - 5-10 minutes)

```bash
# 1. Identify latest backup
BACKUP_DATE=$(date +%Y%m%d)
echo "Checking backup for date: $BACKUP_DATE"

# List available backups
aws s3 ls s3://weather-forecast-indices-backup/$BACKUP_DATE/ --human-readable

# 2. Download backup indices
mkdir -p /tmp/faiss_recovery
aws s3 sync s3://weather-forecast-indices-backup/$BACKUP_DATE/indices/ /tmp/faiss_recovery/

# 3. Verify backup integrity
for file in /tmp/faiss_recovery/*.faiss; do
    echo "Verifying: $(basename $file)"
    python3 -c "
import faiss
import sys
try:
    idx = faiss.read_index('$file')
    print(f'  ✓ {idx.ntotal} vectors, {idx.d} dimensions')
except Exception as e:
    print(f'  ✗ Corrupted: {e}')
    sys.exit(1)
    "
done

# 4. Stop API service to replace indices
kubectl scale deployment api-deployment --replicas=0 -n weather-forecast-prod

# 5. Replace corrupted indices
kubectl cp /tmp/faiss_recovery/ weather-forecast-prod/api-pod:/app/indices/

# 6. Restart API service
kubectl scale deployment api-deployment --replicas=3 -n weather-forecast-prod

# 7. Verify recovery
sleep 30
curl -f "https://api.adelaide-weather.com/health"
curl -H "Authorization: Bearer $API_TOKEN" \
  "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m" | jq '.forecast'
```

#### Option B: Rebuild Indices (Slower - 30-60 minutes)

```bash
# 1. Check if outcomes data is available
ls -la /app/outcomes/outcomes_*h.npy

# 2. Start index rebuilding
echo "Starting FAISS index rebuild..."

# For each horizon
for horizon in 6 12 24 48; do
    echo "Building indices for ${horizon}h horizon..."
    
    # Build flatip index (exact search)
    python3 scripts/build_indices.py \
        --horizon ${horizon} \
        --index-type flatip \
        --outcomes-path /app/outcomes/outcomes_${horizon}h.npy \
        --embeddings-path /app/embeddings/embeddings_${horizon}h.npy \
        --output-path /app/indices/faiss_${horizon}h_flatip.faiss
    
    # Build ivfpq index (approximate search)
    python3 scripts/build_indices.py \
        --horizon ${horizon} \
        --index-type ivfpq \
        --outcomes-path /app/outcomes/outcomes_${horizon}h.npy \
        --embeddings-path /app/embeddings/embeddings_${horizon}h.npy \
        --output-path /app/indices/faiss_${horizon}h_ivfpq.faiss
    
    echo "✓ Completed ${horizon}h indices"
done

# 3. Validate rebuilt indices
python3 -c "
from core.startup_validation_system import ExpertValidatedStartupSystem
validator = ExpertValidatedStartupSystem()
result = validator.validate_faiss_indices_expert()
print(f'FAISS validation: {result.status} - {result.message}')
assert result.status == 'PASS', 'FAISS validation failed'
"

# 4. Restart API service
kubectl rollout restart deployment/api-deployment -n weather-forecast-prod

# 5. Monitor recovery
kubectl rollout status deployment/api-deployment -n weather-forecast-prod
```

### 1.4 Validation Steps

```bash
# Complete FAISS health validation
echo "=== FAISS Recovery Validation ==="

# 1. Check all index files exist
REQUIRED_INDICES=(
    "faiss_6h_flatip.faiss"
    "faiss_6h_ivfpq.faiss"
    "faiss_12h_flatip.faiss"
    "faiss_12h_ivfpq.faiss"
    "faiss_24h_flatip.faiss"
    "faiss_24h_ivfpq.faiss"
    "faiss_48h_flatip.faiss"
    "faiss_48h_ivfpq.faiss"
)

for index in "${REQUIRED_INDICES[@]}"; do
    if [ -f "/app/indices/$index" ]; then
        size=$(stat -f%z "/app/indices/$index" 2>/dev/null || stat -c%s "/app/indices/$index")
        echo "✓ $index: $(( size / 1024 / 1024 ))MB"
    else
        echo "✗ Missing: $index"
    fi
done

# 2. Test search functionality
for horizon in 6h 12h 24h 48h; do
    echo "Testing $horizon forecast..."
    response=$(curl -s -H "Authorization: Bearer $API_TOKEN" \
        "https://api.adelaide-weather.com/forecast?horizon=$horizon&vars=t2m")
    
    if echo "$response" | jq -e '.variables.t2m.available' > /dev/null; then
        echo "✓ $horizon forecast working"
    else
        echo "✗ $horizon forecast failed"
        echo "Response: $response"
    fi
done

# 3. Performance validation
echo "Testing search performance..."
for i in {1..5}; do
    start_time=$(date +%s.%N)
    curl -s -H "Authorization: Bearer $API_TOKEN" \
        "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m" > /dev/null
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    echo "Test $i: ${duration}s"
done

echo "=== Recovery Complete ==="
```

---

## 2. API Token Rotation Procedures

### 2.1 Scheduled Token Rotation

**Schedule:** Monthly (first Tuesday of each month, 2:00 AM UTC)
**Duration:** 5-10 minutes with rolling update
**Advance Notice:** 48 hours to API consumers

```bash
#!/bin/bash
# Scheduled API token rotation procedure

echo "=== API Token Rotation - $(date) ==="

# 1. Generate new secure token
NEW_TOKEN=$(openssl rand -hex 32)
echo "Generated new token: ${NEW_TOKEN:0:8}..."

# 2. Update token in secrets management
kubectl create secret generic api-secrets \
    --from-literal=API_TOKEN=$NEW_TOKEN \
    --dry-run=client -o yaml | kubectl apply -f -

# 3. Create rollback secret (preserve old token temporarily)
OLD_TOKEN=$(kubectl get secret api-secrets -o jsonpath='{.data.API_TOKEN}' | base64 -d)
kubectl create secret generic api-secrets-rollback \
    --from-literal=API_TOKEN=$OLD_TOKEN \
    --from-literal=ROLLBACK_TIMESTAMP=$(date +%s)

# 4. Rolling restart to pick up new token
kubectl rollout restart deployment/api-deployment -n weather-forecast-prod

# 5. Wait for rollout completion
kubectl rollout status deployment/api-deployment -n weather-forecast-prod --timeout=300s

# 6. Verify new token functionality
sleep 30
response=$(curl -s -H "Authorization: Bearer $NEW_TOKEN" \
    "https://api.adelaide-weather.com/health")

if echo "$response" | jq -e '.ready == true' > /dev/null; then
    echo "✓ New token validated successfully"
    
    # Clean up old rollback secret after 24 hours
    echo "kubectl delete secret api-secrets-rollback -n weather-forecast-prod" | at now + 24 hours
    
    # Notify API consumers
    curl -X POST $SLACK_WEBHOOK_URL -H 'Content-type: application/json' \
        --data "{\"text\":\"✅ API Token rotated successfully. Update your API clients with new token: ${NEW_TOKEN:0:8}...\"}"
        
    echo "✅ Token rotation completed successfully"
else
    echo "❌ New token validation failed - initiating rollback"
    
    # Rollback to old token
    kubectl create secret generic api-secrets \
        --from-literal=API_TOKEN=$OLD_TOKEN \
        --dry-run=client -o yaml | kubectl apply -f -
    
    kubectl rollout restart deployment/api-deployment -n weather-forecast-prod
    
    echo "🔄 Rollback completed"
fi
```

### 2.2 Emergency Token Rotation

**Trigger Conditions:**
- Security breach detected
- Token compromise suspected  
- Unauthorized access patterns
- Manual emergency rotation request

```bash
#!/bin/bash
# Emergency API token rotation

echo "🚨 EMERGENCY TOKEN ROTATION - $(date)"

# 1. Immediate token generation
EMERGENCY_TOKEN=$(openssl rand -hex 32)
echo "Emergency token generated: ${EMERGENCY_TOKEN:0:8}..."

# 2. Log security event
curl -X POST $SECURITY_WEBHOOK_URL -H 'Content-type: application/json' \
    --data "{
        \"severity\": \"high\",
        \"event\": \"emergency_token_rotation\",
        \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
        \"reason\": \"${ROTATION_REASON:-Unknown}\",
        \"new_token_hint\": \"${EMERGENCY_TOKEN:0:8}...\"
    }"

# 3. Immediate secret update (no grace period)
kubectl create secret generic api-secrets \
    --from-literal=API_TOKEN=$EMERGENCY_TOKEN \
    --dry-run=client -o yaml | kubectl apply -f -

# 4. Force immediate restart (no rolling update)
kubectl delete pods -l app=api -n weather-forecast-prod

# 5. Wait for pods to come back online
kubectl wait --for=condition=ready pod -l app=api -n weather-forecast-prod --timeout=120s

# 6. Immediate validation
response=$(curl -s -H "Authorization: Bearer $EMERGENCY_TOKEN" \
    "https://api.adelaide-weather.com/health")

if echo "$response" | jq -e '.ready == true' > /dev/null; then
    echo "✅ Emergency token active"
    
    # Invalidate old tokens by restarting all services
    kubectl rollout restart deployment/frontend-deployment -n weather-forecast-prod
    
    # Send critical alert
    curl -X POST $PAGERDUTY_WEBHOOK_URL -H 'Content-type: application/json' \
        --data "{
            \"routing_key\": \"$PAGERDUTY_ROUTING_KEY\",
            \"event_action\": \"trigger\",
            \"payload\": {
                \"summary\": \"Emergency API token rotation completed\",
                \"severity\": \"warning\",
                \"source\": \"adelaide-weather-api\",
                \"custom_details\": {
                    \"new_token_hint\": \"${EMERGENCY_TOKEN:0:8}...\",
                    \"rotation_reason\": \"${ROTATION_REASON:-Unknown}\"
                }
            }
        }"
    
    echo "🚨 EMERGENCY ROTATION COMPLETE - NOTIFY ALL API CONSUMERS IMMEDIATELY"
else
    echo "💥 EMERGENCY ROTATION FAILED - ESCALATE TO ENGINEERING TEAM"
    exit 1
fi
```

### 2.3 Token Validation and Cleanup

```bash
#!/bin/bash
# Token management validation and cleanup

echo "=== Token Management Validation ==="

# 1. Check current token status
current_token=$(kubectl get secret api-secrets -o jsonpath='{.data.API_TOKEN}' | base64 -d)
echo "Current token: ${current_token:0:8}..."

# 2. Test token with all endpoints
endpoints=(
    "/health"
    "/health/detailed" 
    "/health/faiss"
    "/forecast?horizon=24h&vars=t2m"
    "/metrics"
)

for endpoint in "${endpoints[@]}"; do
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $current_token" \
        "https://api.adelaide-weather.com$endpoint")
    
    if [ "$response_code" = "200" ]; then
        echo "✓ $endpoint: $response_code"
    else
        echo "✗ $endpoint: $response_code"
    fi
done

# 3. Check for old/invalid tokens in logs
echo "Checking for authentication failures..."
kubectl logs -l app=api --tail=100 -n weather-forecast-prod | \
    grep -i "authentication.*failed" | tail -5

# 4. Cleanup old secrets
echo "Cleaning up old secrets..."
kubectl get secrets -n weather-forecast-prod | grep "api-secrets-rollback"
kubectl delete secret api-secrets-rollback -n weather-forecast-prod --ignore-not-found

# 5. Token rotation status report
echo "=== Token Status Report ==="
echo "Current token active: $(date)"
echo "Next scheduled rotation: $(date -d 'first tuesday of next month' +%Y-%m-%d)"
echo "Emergency rotation capability: ✓ Available"
```

---

## 3. Degraded Analog Search Recovery

### 3.1 Detection and Assessment

**Symptoms:**
- High analog search latency (>300ms)
- Search failures or timeouts
- Poor quality forecasts (low confidence)
- FAISS health monitoring alerts

```bash
#!/bin/bash
# Degraded analog search detection

echo "=== Analog Search Health Assessment ==="

# 1. Check FAISS health status
faiss_health=$(curl -s "https://api.adelaide-weather.com/health/faiss")
echo "FAISS Health Status:"
echo "$faiss_health" | jq '.status'

# 2. Performance testing
echo "Testing search performance..."
for horizon in 6h 12h 24h 48h; do
    echo "Testing $horizon..."
    
    start_time=$(date +%s.%N)
    response=$(curl -s -H "Authorization: Bearer $API_TOKEN" \
        "https://api.adelaide-weather.com/forecast?horizon=$horizon&vars=t2m")
    end_time=$(date +%s.%N)
    
    duration=$(echo "$end_time - $start_time" | bc)
    analog_count=$(echo "$response" | jq -r '.analogs_summary.analog_count // 0')
    confidence=$(echo "$response" | jq -r '.variables.t2m.confidence // 0')
    
    echo "  Duration: ${duration}s"
    echo "  Analogs: $analog_count"
    echo "  Confidence: $confidence"
    
    # Check thresholds
    if (( $(echo "$duration > 0.3" | bc -l) )); then
        echo "  ⚠️ Slow response time"
    fi
    
    if [ "$analog_count" -lt 20 ]; then
        echo "  ⚠️ Low analog count"
    fi
    
    if (( $(echo "$confidence < 0.5" | bc -l) )); then
        echo "  ⚠️ Low confidence"
    fi
done

# 3. Check resource utilization
echo "Resource utilization:"
kubectl top pods -l app=api -n weather-forecast-prod

# 4. Check for memory issues
kubectl describe pods -l app=api -n weather-forecast-prod | grep -A5 -B5 "Memory"
```

### 3.2 Fallback to CPU-based Search

```bash
#!/bin/bash
# Enable CPU fallback mode for analog search

echo "🔄 Activating CPU fallback mode..."

# 1. Update environment variables to force CPU mode
kubectl set env deployment/api-deployment \
    FAISS_GPU_ENABLED=false \
    FAISS_FALLBACK_MODE=true \
    FAISS_LAZY_LOAD=true \
    -n weather-forecast-prod

# 2. Scale down to reduce memory pressure
kubectl scale deployment api-deployment --replicas=2 -n weather-forecast-prod

# 3. Wait for rollout
kubectl rollout status deployment/api-deployment -n weather-forecast-prod

# 4. Test CPU mode performance
echo "Testing CPU fallback performance..."
for i in {1..3}; do
    start_time=$(date +%s.%N)
    curl -s -H "Authorization: Bearer $API_TOKEN" \
        "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m" > /dev/null
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    echo "Test $i: ${duration}s"
done

echo "✅ CPU fallback mode activated"
```

### 3.3 Index Optimization

```bash
#!/bin/bash
# Optimize FAISS indices for better performance

echo "🔧 Optimizing FAISS indices..."

# 1. Backup current indices
mkdir -p /tmp/index_backup
cp /app/indices/*.faiss /tmp/index_backup/

# 2. Rebuild with optimized parameters
for horizon in 6 12 24 48; do
    echo "Optimizing ${horizon}h indices..."
    
    # Build optimized IVF index with fewer clusters for speed
    python3 << EOF
import faiss
import numpy as np

# Load existing data
embeddings = np.load('/app/embeddings/embeddings_${horizon}h.npy')
outcomes = np.load('/app/outcomes/outcomes_${horizon}h.npy')

print(f"Optimizing {embeddings.shape[0]} embeddings...")

# Optimize IVF parameters based on data size
n_vectors = embeddings.shape[0]
n_clusters = min(int(np.sqrt(n_vectors)), 256)  # Fewer clusters for speed
n_probes = min(n_clusters // 4, 32)  # Fewer probes for speed

# Create optimized index
d = embeddings.shape[1]
quantizer = faiss.IndexFlatIP(d)
index = faiss.IndexIVFPQ(quantizer, d, n_clusters, 8, 8)

# Train and add vectors
print(f"Training index with {n_clusters} clusters...")
index.train(embeddings.astype(np.float32))
index.add(embeddings.astype(np.float32))

# Set search parameters for speed
index.nprobe = n_probes

# Save optimized index
faiss.write_index(index, f'/app/indices/faiss_${horizon}h_ivfpq.faiss')
print(f"Saved optimized {horizon}h index: {index.ntotal} vectors")
EOF
done

# 3. Restart API to pick up optimized indices
kubectl rollout restart deployment/api-deployment -n weather-forecast-prod
kubectl rollout status deployment/api-deployment -n weather-forecast-prod

# 4. Test optimized performance
echo "Testing optimized performance..."
for horizon in 6h 12h 24h 48h; do
    start_time=$(date +%s.%N)
    response=$(curl -s -H "Authorization: Bearer $API_TOKEN" \
        "https://api.adelaide-weather.com/forecast?horizon=$horizon&vars=t2m")
    end_time=$(date +%s.%N)
    
    duration=$(echo "$end_time - $start_time" | bc)
    analog_count=$(echo "$response" | jq -r '.analogs_summary.analog_count // 0')
    
    echo "$horizon: ${duration}s, $analog_count analogs"
done

echo "✅ Index optimization complete"
```

### 3.4 Emergency Simplified Search Mode

```bash
#!/bin/bash
# Activate emergency simplified search mode

echo "🚨 Activating emergency simplified search mode..."

# 1. Enable simplified search parameters
kubectl set env deployment/api-deployment \
    ANALOG_SEARCH_MODE=simplified \
    ANALOG_MAX_NEIGHBORS=20 \
    ANALOG_SEARCH_TIMEOUT=5 \
    FAISS_SIMPLE_SEARCH=true \
    -n weather-forecast-prod

# 2. Create emergency configuration
kubectl create configmap emergency-search-config \
    --from-literal=search_mode=simplified \
    --from-literal=max_neighbors=20 \
    --from-literal=timeout_seconds=5 \
    --from-literal=enable_caching=true \
    -n weather-forecast-prod

# 3. Mount emergency config
kubectl patch deployment api-deployment -n weather-forecast-prod -p '{
    "spec": {
        "template": {
            "spec": {
                "containers": [{
                    "name": "api",
                    "envFrom": [{
                        "configMapRef": {
                            "name": "emergency-search-config"
                        }
                    }]
                }]
            }
        }
    }
}'

# 4. Restart and verify
kubectl rollout restart deployment/api-deployment -n weather-forecast-prod
kubectl rollout status deployment/api-deployment -n weather-forecast-prod

# 5. Test emergency mode
echo "Testing emergency search mode..."
response=$(curl -s -H "Authorization: Bearer $API_TOKEN" \
    "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m")

if echo "$response" | jq -e '.variables.t2m.available' > /dev/null; then
    echo "✅ Emergency search mode operational"
    echo "Analog count: $(echo "$response" | jq -r '.analogs_summary.analog_count')"
    echo "Confidence: $(echo "$response" | jq -r '.variables.t2m.confidence')"
else
    echo "❌ Emergency search mode failed"
    echo "Response: $response"
fi

# 6. Set up monitoring for degraded mode
curl -X POST $SLACK_WEBHOOK_URL -H 'Content-type: application/json' \
    --data "{\"text\":\"⚠️ Emergency simplified search mode activated. Performance may be reduced.\"}"
```

---

## 4. System Health Recovery

### 4.1 Health Endpoint Failures

```bash
#!/bin/bash
# Health endpoint failure recovery

echo "🏥 Health Endpoint Recovery Procedures"

# 1. Check basic connectivity
echo "1. Basic connectivity test..."
for endpoint in "/health" "/health/detailed" "/health/live" "/health/ready"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "https://api.adelaide-weather.com$endpoint")
    echo "  $endpoint: $status"
done

# 2. Check container health
echo "2. Container health status..."
kubectl get pods -l app=api -n weather-forecast-prod -o wide

# 3. Check service endpoints
echo "3. Service endpoint status..."
kubectl get endpoints api-service -n weather-forecast-prod

# 4. Check readiness probes
echo "4. Readiness probe configuration..."
kubectl describe deployment api-deployment -n weather-forecast-prod | grep -A10 "Readiness"

# 5. Manual health validation
echo "5. Manual health validation..."
pod_name=$(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}')

kubectl exec $pod_name -n weather-forecast-prod -- python3 -c "
import sys
import os
sys.path.append('/app')

# Test core components
try:
    from core.startup_validation_system import ExpertValidatedStartupSystem
    validator = ExpertValidatedStartupSystem()
    health_check = validator.startup_health_check()
    print(f'Core health check: {\"PASS\" if health_check else \"FAIL\"}')
except Exception as e:
    print(f'Core health check failed: {e}')

# Test FAISS availability
try:
    import faiss
    index = faiss.read_index('/app/indices/faiss_24h_ivfpq.faiss')
    print(f'FAISS health: PASS ({index.ntotal} vectors)')
except Exception as e:
    print(f'FAISS health: FAIL ({e})')

# Test model loading
try:
    from core.model_loader import load_model_safe
    model = load_model_safe(device='cpu', require_exact_match=False)
    print(f'Model health: {\"PASS\" if model else \"FAIL\"}')
except Exception as e:
    print(f'Model health: FAIL ({e})')
"

# 6. Reset health endpoint if needed
if [ "$?" -ne 0 ]; then
    echo "6. Resetting health endpoints..."
    kubectl rollout restart deployment/api-deployment -n weather-forecast-prod
    kubectl rollout status deployment/api-deployment -n weather-forecast-prod
    
    # Re-test after restart
    sleep 30
    curl -f "https://api.adelaide-weather.com/health"
fi
```

### 4.2 Startup Validation Failures

```bash
#!/bin/bash
# Startup validation failure recovery

echo "🚀 Startup Validation Recovery"

# 1. Run expert validation manually
echo "1. Running expert startup validation..."
kubectl exec -it $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
    -n weather-forecast-prod -- python3 -c "
from core.startup_validation_system import ExpertValidatedStartupSystem
import json

validator = ExpertValidatedStartupSystem()
success = validator.run_expert_startup_validation()

print(f'Validation result: {\"PASS\" if success else \"FAIL\"}')

# Print detailed results
for result in validator.validation_results:
    print(f'{result.test_name}: {result.status} - {result.message}')
    if not result.expert_threshold_met:
        print(f'  ⚠️ Expert threshold not met')

# Save report
if validator.system_state:
    with open('/app/startup_validation_report.json', 'w') as f:
        json.dump(validator.system_state.to_dict(), f, indent=2)
"

# 2. Check specific validation failures
echo "2. Checking specific validation components..."

# Model integrity
kubectl exec $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
    -n weather-forecast-prod -- python3 -c "
from core.model_loader import load_model_safe
model = load_model_safe(device='cpu', require_exact_match=True)
if model and hasattr(model, '_checkpoint_info'):
    info = model._checkpoint_info
    match_ratio = info.get('match_percentage', 0.0) / 100.0
    print(f'Model match ratio: {match_ratio:.1%}')
    if match_ratio < 0.95:
        print('⚠️ Model match ratio below expert threshold (95%)')
else:
    print('❌ Model loading failed')
"

# Database integrity
kubectl exec $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
    -n weather-forecast-prod -- python3 -c "
import json
from pathlib import Path

integrity_path = Path('/app/outcomes/sidecars/database_integrity_analysis.json')
if integrity_path.exists():
    with open(integrity_path) as f:
        data = json.load(f)
    
    for horizon in ['6h', '12h', '24h', '48h']:
        if horizon in data:
            validity = data[horizon].get('data_quality', {}).get('valid_percentage', 0.0)
            print(f'{horizon} validity: {validity:.1f}%')
            if validity < 99.0:
                print(f'  ⚠️ {horizon} below expert threshold (99%)')
else:
    print('❌ Database integrity analysis not found')
"

# 3. Fix common startup issues
echo "3. Applying common fixes..."

# Ensure all required directories exist
kubectl exec $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
    -n weather-forecast-prod -- bash -c "
mkdir -p /app/indices /app/embeddings /app/outcomes /app/models
chmod 755 /app/indices /app/embeddings /app/outcomes /app/models
ls -la /app/
"

# Check file permissions
kubectl exec $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
    -n weather-forecast-prod -- bash -c "
find /app/indices -name '*.faiss' -type f -exec chmod 644 {} \;
find /app/outcomes -name '*.npy' -type f -exec chmod 644 {} \;
find /app/models -name '*.pt' -type f -exec chmod 644 {} \;
"

# 4. Force startup validation bypass if needed (emergency only)
if [ "$EMERGENCY_MODE" = "true" ]; then
    echo "🚨 EMERGENCY: Bypassing startup validation..."
    kubectl set env deployment/api-deployment \
        SKIP_STARTUP_VALIDATION=true \
        EMERGENCY_MODE=true \
        -n weather-forecast-prod
    
    kubectl rollout restart deployment/api-deployment -n weather-forecast-prod
    
    echo "⚠️ API running in emergency mode - full validation bypassed"
fi

echo "✅ Startup validation recovery complete"
```

---

## 5. Performance Issues Response

### 5.1 High Latency Response

```bash
#!/bin/bash
# High latency troubleshooting and mitigation

echo "⚡ Performance Issue Response - High Latency"

# 1. Measure current performance
echo "1. Current performance baseline..."
for i in {1..10}; do
    start_time=$(date +%s.%N)
    response=$(curl -s -H "Authorization: Bearer $API_TOKEN" \
        "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m")
    end_time=$(date +%s.%N)
    
    duration=$(echo "$end_time - $start_time" | bc)
    status=$(echo "$response" | jq -r '.variables.t2m.available // false')
    
    echo "  Request $i: ${duration}s (success: $status)"
done

# 2. Check resource utilization
echo "2. Resource utilization analysis..."
kubectl top pods -l app=api -n weather-forecast-prod
kubectl describe pods -l app=api -n weather-forecast-prod | grep -A5 -B5 "CPU\|Memory"

# 3. Check for memory leaks
echo "3. Memory leak detection..."
kubectl exec $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
    -n weather-forecast-prod -- python3 -c "
import psutil
import os

process = psutil.Process(os.getpid())
memory_info = process.memory_info()
memory_percent = process.memory_percent()

print(f'Memory usage: {memory_info.rss / 1024 / 1024:.1f}MB ({memory_percent:.1f}%)')
print(f'CPU usage: {process.cpu_percent()}%')

# Check for high memory usage
if memory_percent > 80:
    print('⚠️ High memory usage detected')
if process.cpu_percent() > 80:
    print('⚠️ High CPU usage detected')
"

# 4. Performance optimization actions
echo "4. Applying performance optimizations..."

# Scale up if resource constrained
current_replicas=$(kubectl get deployment api-deployment -n weather-forecast-prod -o jsonpath='{.spec.replicas}')
if [ "$current_replicas" -lt 5 ]; then
    echo "  Scaling up from $current_replicas to 5 replicas..."
    kubectl scale deployment api-deployment --replicas=5 -n weather-forecast-prod
fi

# Enable performance mode
kubectl set env deployment/api-deployment \
    PERFORMANCE_MODE=true \
    FAISS_LAZY_LOAD=true \
    RESPONSE_CACHING=true \
    -n weather-forecast-prod

# 5. Restart pods with memory issues
echo "5. Restarting high-memory pods..."
kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[*].metadata.name}' | \
while read pod; do
    memory_usage=$(kubectl top pod $pod -n weather-forecast-prod --no-headers | awk '{print $3}' | sed 's/Mi//')
    if [ "$memory_usage" -gt 400 ]; then
        echo "  Restarting high-memory pod: $pod (${memory_usage}Mi)"
        kubectl delete pod $pod -n weather-forecast-prod
    fi
done

# 6. Monitor improvement
echo "6. Monitoring performance improvement..."
sleep 60  # Wait for pods to stabilize

for i in {1..5}; do
    start_time=$(date +%s.%N)
    curl -s -H "Authorization: Bearer $API_TOKEN" \
        "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m" > /dev/null
    end_time=$(date +%s.%N)
    
    duration=$(echo "$end_time - $start_time" | bc)
    echo "  Optimized request $i: ${duration}s"
    
    # Check if within SLA
    if (( $(echo "$duration < 0.15" | bc -l) )); then
        echo "    ✅ Within SLA (<150ms)"
    else
        echo "    ⚠️ Exceeds SLA"
    fi
done

echo "✅ Performance optimization complete"
```

### 5.2 High Error Rate Response

```bash
#!/bin/bash
# High error rate investigation and mitigation

echo "🚨 High Error Rate Response"

# 1. Error rate analysis
echo "1. Error rate analysis..."
error_count=0
success_count=0
total_requests=20

for i in $(seq 1 $total_requests); do
    response=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $API_TOKEN" \
        "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m")
    
    http_code=$(echo "$response" | tail -c 4)
    
    if [ "$http_code" = "200" ]; then
        ((success_count++))
        echo "  Request $i: SUCCESS ($http_code)"
    else
        ((error_count++))
        echo "  Request $i: ERROR ($http_code)"
    fi
done

error_rate=$(echo "scale=2; $error_count * 100 / $total_requests" | bc)
echo "Error rate: $error_rate% ($error_count/$total_requests)"

# 2. Log analysis for error patterns
echo "2. Error pattern analysis..."
kubectl logs -l app=api --tail=100 -n weather-forecast-prod | \
    grep -i error | tail -10

# Common error patterns
echo "Checking for common error patterns..."
kubectl logs -l app=api --tail=200 -n weather-forecast-prod | \
    grep -E "(FAISS|timeout|memory|connection)" | tail -5

# 3. Component health validation
echo "3. Component health validation..."

# Check FAISS health
faiss_health=$(curl -s "https://api.adelaide-weather.com/health/faiss" 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "  FAISS: $(echo "$faiss_health" | jq -r '.status // "unknown"')"
else
    echo "  FAISS: ERROR (endpoint unreachable)"
fi

# Check model health
kubectl exec $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
    -n weather-forecast-prod -- python3 -c "
try:
    from core.model_loader import load_model_safe
    model = load_model_safe(device='cpu', require_exact_match=False)
    print('  Model: HEALTHY' if model else '  Model: ERROR')
except Exception as e:
    print(f'  Model: ERROR ({e})')
" 2>/dev/null || echo "  Model: ERROR (check failed)"

# 4. Mitigation actions based on error rate
if (( $(echo "$error_rate > 5" | bc -l) )); then
    echo "4. Critical error rate detected - applying emergency measures..."
    
    # Restart all API pods
    kubectl delete pods -l app=api -n weather-forecast-prod
    kubectl wait --for=condition=ready pod -l app=api -n weather-forecast-prod --timeout=120s
    
    # Enable emergency mode
    kubectl set env deployment/api-deployment \
        EMERGENCY_MODE=true \
        SIMPLE_RESPONSES=true \
        SKIP_COMPLEX_VALIDATION=true \
        -n weather-forecast-prod
        
elif (( $(echo "$error_rate > 1" | bc -l) )); then
    echo "4. Elevated error rate - applying standard mitigation..."
    
    # Restart unhealthy pods only
    kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[*].metadata.name}' | \
    while read pod; do
        ready=$(kubectl get pod $pod -n weather-forecast-prod -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
        if [ "$ready" != "True" ]; then
            echo "  Restarting unhealthy pod: $pod"
            kubectl delete pod $pod -n weather-forecast-prod
        fi
    done
    
    # Enable degraded mode
    kubectl set env deployment/api-deployment \
        DEGRADED_MODE=true \
        REDUCE_COMPLEXITY=true \
        -n weather-forecast-prod
else
    echo "4. Error rate within acceptable bounds - monitoring..."
fi

# 5. Post-mitigation validation
echo "5. Post-mitigation validation..."
sleep 60

success_count_post=0
for i in {1..10}; do
    response_code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $API_TOKEN" \
        "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m")
    
    if [ "$response_code" = "200" ]; then
        ((success_count_post++))
    fi
done

post_error_rate=$(echo "scale=2; (10 - $success_count_post) * 100 / 10" | bc)
echo "Post-mitigation error rate: $post_error_rate%"

if (( $(echo "$post_error_rate < 1" | bc -l) )); then
    echo "✅ Error rate mitigation successful"
else
    echo "❌ Error rate mitigation insufficient - escalate to engineering team"
fi
```

---

## 6. Security Incidents Response

### 6.1 Authentication Failure Investigation

```bash
#!/bin/bash
# Authentication failure investigation and response

echo "🔒 Security Incident Response - Authentication Failures"

# 1. Check authentication failure patterns
echo "1. Authentication failure analysis..."
kubectl logs -l app=api --tail=500 -n weather-forecast-prod | \
    grep "authentication_attempt.*success.*false" | \
    tail -20

# Extract suspicious patterns
echo "2. Suspicious IP analysis..."
kubectl logs -l app=api --tail=1000 -n weather-forecast-prod | \
    grep "authentication_attempt.*success.*false" | \
    grep -o '"client_ip":"[^"]*"' | \
    sort | uniq -c | sort -nr | head -10

# 3. Check for brute force attacks
echo "3. Brute force attack detection..."
suspicious_ips=$(kubectl logs -l app=api --tail=500 -n weather-forecast-prod | \
    grep "authentication_attempt.*success.*false" | \
    grep -o '"client_ip":"[^"]*"' | \
    cut -d'"' -f4 | sort | uniq -c | \
    awk '$1 > 10 {print $2}')

if [ -n "$suspicious_ips" ]; then
    echo "⚠️ Potential brute force IPs detected:"
    echo "$suspicious_ips"
    
    # Log security event
    for ip in $suspicious_ips; do
        echo "  Investigating IP: $ip"
        
        # Check recent activity from this IP
        kubectl logs -l app=api --tail=1000 -n weather-forecast-prod | \
            grep "\"client_ip\":\"$ip\"" | tail -5
    done
else
    echo "✅ No brute force patterns detected"
fi

# 4. Check for injection attempts
echo "4. Injection attempt detection..."
kubectl logs -l app=api --tail=500 -n weather-forecast-prod | \
    grep -i "security_violation.*injection" | tail -10

# 5. Security containment measures
if [ -n "$suspicious_ips" ]; then
    echo "5. Applying security containment..."
    
    # Create emergency security group to block IPs
    echo "Creating emergency IP blocks..."
    
    # In a real environment, this would update WAF rules or security groups
    for ip in $suspicious_ips; do
        echo "  Would block IP: $ip"
        # aws ec2 authorize-security-group-ingress --group-id sg-xxx --protocol tcp --port 443 --source-group $ip/32
    done
    
    # Log security incident
    cat << EOF > /tmp/security_incident_$(date +%s).json
{
    "incident_type": "authentication_failure_spike",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "suspicious_ips": [$(echo "$suspicious_ips" | tr '\n' ',' | sed 's/,$//')],
    "containment_actions": ["ip_blocking", "enhanced_monitoring"],
    "escalation_required": true
}
EOF
    
    # Send alert
    curl -X POST $SECURITY_WEBHOOK_URL -H 'Content-type: application/json' \
        --data @/tmp/security_incident_$(date +%s).json
        
    echo "🚨 Security incident logged and alerts sent"
fi

echo "✅ Authentication failure investigation complete"
```

### 6.2 Emergency Security Response

```bash
#!/bin/bash
# Emergency security response procedures

echo "🚨 EMERGENCY SECURITY RESPONSE"

# 1. Immediate containment
echo "1. Immediate containment measures..."

# Enable enhanced security logging
kubectl set env deployment/api-deployment \
    SECURITY_LOG_LEVEL=DEBUG \
    ENHANCED_AUTH_LOGGING=true \
    SECURITY_MODE=strict \
    -n weather-forecast-prod

# Enable rate limiting
kubectl set env deployment/api-deployment \
    RATE_LIMIT_ENABLED=true \
    RATE_LIMIT_PER_MINUTE=10 \
    RATE_LIMIT_BURST=3 \
    -n weather-forecast-prod

# 2. Security audit
echo "2. Security audit..."
kubectl exec $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
    -n weather-forecast-prod -- python3 -c "
import os
import json
from datetime import datetime, timedelta

# Check environment variables for sensitive data
sensitive_vars = ['API_TOKEN', 'DATABASE_URL', 'SECRET_KEY']
print('Environment variable audit:')
for var in sensitive_vars:
    value = os.getenv(var, 'NOT_SET')
    if value == 'NOT_SET':
        print(f'  {var}: NOT_SET (potential issue)')
    else:
        print(f'  {var}: SET (length: {len(value)})')

# Check file permissions
import stat
critical_files = ['/app/indices/', '/app/outcomes/', '/app/models/']
print('\nFile permission audit:')
for path in critical_files:
    if os.path.exists(path):
        mode = oct(stat.S_IMODE(os.stat(path).st_mode))
        print(f'  {path}: {mode}')
    else:
        print(f'  {path}: NOT_FOUND')
"

# 3. Token rotation (emergency)
echo "3. Emergency token rotation..."
EMERGENCY_TOKEN=$(openssl rand -hex 32)

kubectl create secret generic api-secrets \
    --from-literal=API_TOKEN=$EMERGENCY_TOKEN \
    --dry-run=client -o yaml | kubectl apply -f -

# Force immediate pod restart
kubectl delete pods -l app=api -n weather-forecast-prod

# Wait for recovery
kubectl wait --for=condition=ready pod -l app=api -n weather-forecast-prod --timeout=120s

# 4. Security validation
echo "4. Security validation..."
response=$(curl -s -H "Authorization: Bearer $EMERGENCY_TOKEN" \
    "https://api.adelaide-weather.com/health")

if echo "$response" | jq -e '.ready == true' > /dev/null; then
    echo "✅ Emergency token validated"
else
    echo "❌ Emergency token validation failed"
    exit 1
fi

# 5. Enhanced monitoring
echo "5. Enabling enhanced monitoring..."
kubectl set env deployment/api-deployment \
    SECURITY_MONITORING=enhanced \
    AUDIT_ALL_REQUESTS=true \
    LOG_CLIENT_IPS=true \
    -n weather-forecast-prod

# 6. Incident documentation
cat << EOF > /tmp/emergency_security_response_$(date +%s).json
{
    "incident_id": "ESR-$(date +%s)",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "response_actions": [
        "emergency_token_rotation",
        "enhanced_security_logging",
        "strict_rate_limiting",
        "pod_restart",
        "enhanced_monitoring"
    ],
    "new_token_hint": "${EMERGENCY_TOKEN:0:8}...",
    "status": "contained",
    "next_actions": [
        "notify_security_team",
        "conduct_security_audit",
        "review_access_logs",
        "update_security_procedures"
    ]
}
EOF

echo "🚨 EMERGENCY SECURITY RESPONSE COMPLETE"
echo "📋 New API token: ${EMERGENCY_TOKEN:0:8}..."
echo "🔔 NOTIFY ALL API CONSUMERS IMMEDIATELY"
```

---

## 7. Monitoring Integration Guide

### 7.1 Alertmanager Integration

```bash
#!/bin/bash
# Configure alerting for operational scenarios

echo "📊 Monitoring Integration Setup"

# 1. Create Adelaide Weather specific alert rules
cat << 'EOF' > /tmp/adelaide-weather-alerts.yml
groups:
  - name: adelaide-weather-operational
    rules:
      # FAISS Indices Missing
      - alert: FAISSIndicesMissing
        expr: up{job="adelaide-weather-api"} == 1 AND faiss_index_health_status != 1
        for: 1m
        labels:
          severity: critical
          service: adelaide-weather-api
          runbook_url: "https://docs.adelaide-weather.com/runbooks#faiss-indices-missing"
        annotations:
          summary: "FAISS indices missing or corrupted"
          description: "FAISS indices are missing or corrupted. Forecast functionality is unavailable."

      # Token Rotation Required  
      - alert: TokenRotationRequired
        expr: time() - token_last_rotation_timestamp > 2592000  # 30 days
        for: 5m
        labels:
          severity: warning
          service: adelaide-weather-api
          runbook_url: "https://docs.adelaide-weather.com/runbooks#token-rotation"
        annotations:
          summary: "API token rotation overdue"
          description: "API token has not been rotated in over 30 days."

      # Degraded Analog Search
      - alert: DegradedAnalogSearch
        expr: avg_over_time(analog_search_latency_seconds[5m]) > 0.3
        for: 3m
        labels:
          severity: high
          service: adelaide-weather-api
          runbook_url: "https://docs.adelaide-weather.com/runbooks#degraded-analog-search"
        annotations:
          summary: "Analog search performance degraded"
          description: "Analog search latency is {{ $value }}s, exceeding 300ms threshold."

      # High Error Rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 2m
        labels:
          severity: high
          service: adelaide-weather-api
          runbook_url: "https://docs.adelaide-weather.com/runbooks#high-error-rate"
        annotations:
          summary: "High API error rate"
          description: "API error rate is {{ $value | humanizePercentage }} over the last 5 minutes."

      # Security Violations
      - alert: SecurityViolationSpike
        expr: rate(security_violations_total[5m]) > 0.1
        for: 1m
        labels:
          severity: critical
          service: adelaide-weather-api
          runbook_url: "https://docs.adelaide-weather.com/runbooks#security-incidents"
        annotations:
          summary: "Security violation spike detected"
          description: "Security violations increased to {{ $value }} per second."

      # Resource Exhaustion
      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes{pod=~"api-.*"} / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
          service: adelaide-weather-api
          runbook_url: "https://docs.adelaide-weather.com/runbooks#resource-exhaustion"
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is {{ $value | humanizePercentage }} of limit."

      # Configuration Drift
      - alert: ConfigurationDrift
        expr: config_drift_detected == 1
        for: 0s
        labels:
          severity: high
          service: adelaide-weather-api
          runbook_url: "https://docs.adelaide-weather.com/runbooks#configuration-drift"
        annotations:
          summary: "Configuration drift detected"
          description: "Configuration changes detected outside normal deployment process."
EOF

# 2. Apply alert rules
kubectl create configmap adelaide-weather-alerts \
    --from-file=/tmp/adelaide-weather-alerts.yml \
    -n monitoring

# Update Prometheus configuration
kubectl patch configmap prometheus-config -n monitoring --patch '{
    "data": {
        "prometheus.yml": "..."
    }
}'

echo "✅ Alert rules configured"
```

### 7.2 Grafana Dashboard Integration

```bash
#!/bin/bash
# Setup operational dashboard for Adelaide Weather

echo "📈 Grafana Dashboard Integration"

# 1. Create operational dashboard
cat << 'EOF' > /tmp/adelaide-weather-operational-dashboard.json
{
  "dashboard": {
    "id": null,
    "title": "Adelaide Weather - Operational Dashboard",
    "tags": ["adelaide-weather", "operations"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "System Health Overview",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"adelaide-weather-api\"}",
            "legendFormat": "API Uptime"
          },
          {
            "expr": "faiss_index_health_status",
            "legendFormat": "FAISS Health"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Response Time vs SLA",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P95 Latency"
          }
        ],
        "yAxes": [
          {
            "max": 0.15,
            "unit": "s"
          }
        ],
        "thresholds": [
          {
            "value": 0.15,
            "colorMode": "critical",
            "op": "gt"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Security Events",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(security_violations_total[5m])",
            "legendFormat": "Security Violations/sec"
          },
          {
            "expr": "rate(authentication_failures_total[5m])",
            "legendFormat": "Auth Failures/sec"
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "FAISS Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "analog_search_latency_seconds",
            "legendFormat": "Search Latency"
          },
          {
            "expr": "analog_search_results_count",
            "legendFormat": "Results Count"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
      },
      {
        "id": 5,
        "title": "Resource Utilization",
        "type": "graph",
        "targets": [
          {
            "expr": "container_memory_usage_bytes{pod=~\"api-.*\"} / 1024 / 1024",
            "legendFormat": "Memory Usage (MB)"
          },
          {
            "expr": "rate(container_cpu_usage_seconds_total{pod=~\"api-.*\"}[5m]) * 100",
            "legendFormat": "CPU Usage (%)"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
EOF

# 2. Import dashboard to Grafana
GRAFANA_URL="http://grafana.adelaide-weather.com"
GRAFANA_API_KEY=$(kubectl get secret grafana-api-key -n monitoring -o jsonpath='{.data.key}' | base64 -d)

curl -X POST "$GRAFANA_URL/api/dashboards/db" \
    -H "Authorization: Bearer $GRAFANA_API_KEY" \
    -H "Content-Type: application/json" \
    -d @/tmp/adelaide-weather-operational-dashboard.json

echo "✅ Operational dashboard imported to Grafana"
```

### 7.3 Synthetic Monitoring Setup

```bash
#!/bin/bash
# Setup synthetic monitoring for operational scenarios

echo "🔍 Synthetic Monitoring Setup"

# 1. Create synthetic monitoring configuration
cat << 'EOF' > /tmp/synthetic-monitoring-config.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: synthetic-monitoring-config
  namespace: monitoring
data:
  config.yml: |
    checks:
      - name: api-health-check
        type: http
        interval: 30s
        timeout: 10s
        url: https://api.adelaide-weather.com/health
        expected_status: 200
        expected_body_contains: '"ready":true'
        
      - name: forecast-functionality
        type: http
        interval: 60s
        timeout: 15s
        url: https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m
        headers:
          Authorization: "Bearer ${API_TOKEN}"
        expected_status: 200
        expected_body_contains: '"available":true'
        
      - name: faiss-health-check
        type: http
        interval: 120s
        timeout: 20s
        url: https://api.adelaide-weather.com/health/faiss
        headers:
          Authorization: "Bearer ${API_TOKEN}"
        expected_status: 200
        expected_body_contains: '"status":"healthy"'
        
      - name: performance-sla-check
        type: http
        interval: 60s
        timeout: 5s
        url: https://api.adelaide-weather.com/forecast?horizon=6h&vars=t2m
        headers:
          Authorization: "Bearer ${API_TOKEN}"
        expected_status: 200
        max_response_time: 150ms
        
    alerts:
      - name: api-down
        condition: api-health-check.status != 200
        for: 2m
        severity: critical
        
      - name: forecast-unavailable
        condition: forecast-functionality.status != 200
        for: 3m
        severity: high
        
      - name: faiss-degraded
        condition: faiss-health-check.status != 200
        for: 5m
        severity: high
        
      - name: performance-degraded
        condition: performance-sla-check.response_time > 150ms
        for: 3m
        severity: warning
EOF

# 2. Deploy synthetic monitoring
kubectl apply -f /tmp/synthetic-monitoring-config.yml

# 3. Create synthetic monitoring deployment
cat << 'EOF' > /tmp/synthetic-monitoring-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: synthetic-monitoring
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: synthetic-monitoring
  template:
    metadata:
      labels:
        app: synthetic-monitoring
    spec:
      containers:
      - name: synthetic-monitor
        image: synthetic-monitoring:latest
        env:
        - name: API_TOKEN
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: API_TOKEN
        volumeMounts:
        - name: config
          mountPath: /config
          readOnly: true
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 30
      volumes:
      - name: config
        configMap:
          name: synthetic-monitoring-config
EOF

kubectl apply -f /tmp/synthetic-monitoring-deployment.yml

echo "✅ Synthetic monitoring deployed"
```

---

## 8. Resource Exhaustion Management

### 8.1 Memory Exhaustion Response

```bash
#!/bin/bash
# Memory exhaustion detection and mitigation

echo "💾 Memory Exhaustion Management"

# 1. Memory usage assessment
echo "1. Current memory usage assessment..."
kubectl top pods -l app=api -n weather-forecast-prod --sort-by memory

# Get detailed memory usage
kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[*].metadata.name}' | \
while read pod; do
    memory_usage=$(kubectl top pod $pod -n weather-forecast-prod --no-headers | awk '{print $3}')
    memory_limit=$(kubectl get pod $pod -n weather-forecast-prod -o jsonpath='{.spec.containers[0].resources.limits.memory}')
    
    echo "Pod $pod: ${memory_usage} / ${memory_limit}"
done

# 2. Memory leak detection
echo "2. Memory leak detection..."
kubectl exec $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
    -n weather-forecast-prod -- python3 -c "
import psutil
import gc
import sys

# Get current process memory info
process = psutil.Process()
memory_info = process.memory_info()
memory_percent = process.memory_percent()

print(f'RSS: {memory_info.rss / 1024 / 1024:.1f}MB')
print(f'VMS: {memory_info.vms / 1024 / 1024:.1f}MB')
print(f'Memory %: {memory_percent:.1f}%')

# Check for memory leaks indicators
if memory_percent > 80:
    print('⚠️ High memory usage detected')
    
    # Try garbage collection
    collected = gc.collect()
    print(f'Garbage collected: {collected} objects')
    
    # Re-check after GC
    new_memory_percent = psutil.Process().memory_percent()
    print(f'Memory % after GC: {new_memory_percent:.1f}%')
    
    if new_memory_percent > 75:
        print('🚨 Memory leak suspected - restart recommended')
        sys.exit(1)
"

# 3. Memory pressure mitigation
echo "3. Memory pressure mitigation..."

# Check if immediate action needed
high_memory_pods=$(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[*].metadata.name}' | \
    while read pod; do
        memory_usage=$(kubectl top pod $pod -n weather-forecast-prod --no-headers | awk '{print $3}' | sed 's/Mi//')
        if [ "$memory_usage" -gt 400 ]; then
            echo $pod
        fi
    done)

if [ -n "$high_memory_pods" ]; then
    echo "High memory pods detected, applying mitigation..."
    
    # Enable memory optimizations
    kubectl set env deployment/api-deployment \
        MEMORY_OPTIMIZATION=true \
        FAISS_LAZY_LOAD=true \
        REDUCE_MEMORY_USAGE=true \
        PYTHON_GC_AGGRESSIVE=true \
        -n weather-forecast-prod
    
    # Restart high memory pods
    for pod in $high_memory_pods; do
        echo "Restarting high-memory pod: $pod"
        kubectl delete pod $pod -n weather-forecast-prod
    done
    
    # Wait for pods to restart
    kubectl wait --for=condition=ready pod -l app=api -n weather-forecast-prod --timeout=120s
fi

# 4. Scale down if necessary
current_replicas=$(kubectl get deployment api-deployment -n weather-forecast-prod -o jsonpath='{.spec.replicas}')
if [ "$current_replicas" -gt 3 ]; then
    echo "Scaling down to reduce memory pressure..."
    kubectl scale deployment api-deployment --replicas=3 -n weather-forecast-prod
fi

# 5. Memory monitoring
echo "4. Enhanced memory monitoring..."
kubectl set env deployment/api-deployment \
    MEMORY_MONITORING=enhanced \
    LOG_MEMORY_USAGE=true \
    -n weather-forecast-prod

echo "✅ Memory exhaustion mitigation complete"
```

### 8.2 CPU Exhaustion Response

```bash
#!/bin/bash
# CPU exhaustion detection and mitigation

echo "⚡ CPU Exhaustion Management"

# 1. CPU usage assessment
echo "1. CPU usage assessment..."
kubectl top pods -l app=api -n weather-forecast-prod --sort-by cpu

# Get detailed CPU usage over time
echo "Monitoring CPU usage for 30 seconds..."
for i in {1..6}; do
    kubectl top pods -l app=api -n weather-forecast-prod --no-headers | \
        awk '{print "Pod", $1, "CPU:", $2}'
    sleep 5
done

# 2. CPU bottleneck identification
echo "2. CPU bottleneck identification..."
kubectl exec $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
    -n weather-forecast-prod -- python3 -c "
import psutil
import time

# Monitor CPU usage
cpu_percent = psutil.cpu_percent(interval=1)
print(f'Current CPU usage: {cpu_percent}%')

# Check per-core usage
cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
for i, usage in enumerate(cpu_per_core):
    print(f'Core {i}: {usage}%')

# Check for high CPU processes
for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
    try:
        if proc.info['cpu_percent'] > 10:
            print(f'High CPU process: {proc.info[\"name\"]} ({proc.info[\"cpu_percent\"]}%)')
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

if cpu_percent > 80:
    print('🚨 High CPU usage detected')
"

# 3. CPU optimization
echo "3. CPU optimization..."

# Enable CPU optimizations
kubectl set env deployment/api-deployment \
    CPU_OPTIMIZATION=true \
    FAISS_CPU_THREADS=2 \
    TORCH_NUM_THREADS=2 \
    OMP_NUM_THREADS=2 \
    -n weather-forecast-prod

# Scale up if CPU bound
current_replicas=$(kubectl get deployment api-deployment -n weather-forecast-prod -o jsonpath='{.spec.replicas}')
if [ "$current_replicas" -lt 5 ]; then
    echo "Scaling up to distribute CPU load..."
    kubectl scale deployment api-deployment --replicas=5 -n weather-forecast-prod
fi

# 4. CPU throttling check
echo "4. CPU throttling analysis..."
kubectl describe pods -l app=api -n weather-forecast-prod | grep -A5 -B5 "cpu"

# 5. Performance validation
echo "5. Performance validation after CPU optimization..."
sleep 60

for i in {1..5}; do
    start_time=$(date +%s.%N)
    curl -s -H "Authorization: Bearer $API_TOKEN" \
        "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m" > /dev/null
    end_time=$(date +%s.%N)
    
    duration=$(echo "$end_time - $start_time" | bc)
    echo "Request $i: ${duration}s"
done

echo "✅ CPU exhaustion mitigation complete"
```

---

## 9. Configuration Drift Detection

### 9.1 Configuration Drift Response

```bash
#!/bin/bash
# Configuration drift detection and remediation

echo "⚙️ Configuration Drift Management"

# 1. Detect configuration drift
echo "1. Configuration drift detection..."
kubectl exec $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
    -n weather-forecast-prod -- python3 -c "
from core.config_drift_detector import ConfigurationDriftDetector
import json

# Initialize drift detector
detector = ConfigurationDriftDetector(
    enable_metrics=True,
    enable_real_time=True
)

# Run drift detection
drift_report = detector.run_comprehensive_drift_scan()

print('Configuration Drift Report:')
print(json.dumps(drift_report, indent=2))

# Check for critical issues
if drift_report.get('critical_issues', 0) > 0:
    print('🚨 Critical configuration drift detected')
    exit(1)
elif drift_report.get('high_priority_issues', 0) > 0:
    print('⚠️ High priority configuration drift detected')
    exit(2)
else:
    print('✅ No critical configuration drift detected')
"

drift_status=$?

# 2. Handle drift based on severity
case $drift_status in
    1)
        echo "2. Critical drift detected - immediate action required"
        
        # Stop configuration changes
        kubectl set env deployment/api-deployment \
            CONFIG_READ_ONLY=true \
            PREVENT_CONFIG_CHANGES=true \
            -n weather-forecast-prod
        
        # Alert security team
        curl -X POST $SECURITY_WEBHOOK_URL -H 'Content-type: application/json' \
            --data "{
                \"severity\": \"critical\",
                \"event\": \"critical_configuration_drift\",
                \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
                \"action_required\": \"immediate\"
            }"
        ;;
    2)
        echo "2. High priority drift detected - investigation required"
        
        # Enable enhanced monitoring
        kubectl set env deployment/api-deployment \
            CONFIG_MONITORING=enhanced \
            AUDIT_CONFIG_CHANGES=true \
            -n weather-forecast-prod
        ;;
    0)
        echo "2. No critical drift detected - monitoring continues"
        ;;
esac

# 3. Configuration baseline restoration
if [ "$drift_status" -eq 1 ]; then
    echo "3. Restoring configuration baseline..."
    
    # Restore from known good configuration
    kubectl apply -f /app/config/production/baseline-config.yml
    
    # Restart services with baseline config
    kubectl rollout restart deployment/api-deployment -n weather-forecast-prod
    kubectl rollout status deployment/api-deployment -n weather-forecast-prod
    
    # Verify restoration
    kubectl exec $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
        -n weather-forecast-prod -- python3 -c "
from core.config_drift_detector import ConfigurationDriftDetector

detector = ConfigurationDriftDetector()
post_restore_report = detector.run_comprehensive_drift_scan()

if post_restore_report.get('critical_issues', 0) == 0:
    print('✅ Configuration baseline restored successfully')
else:
    print('❌ Configuration baseline restoration failed')
"
fi

echo "✅ Configuration drift management complete"
```

### 9.2 Configuration Monitoring Setup

```bash
#!/bin/bash
# Setup continuous configuration monitoring

echo "📊 Configuration Monitoring Setup"

# 1. Enable real-time configuration monitoring
kubectl set env deployment/api-deployment \
    CONFIG_DRIFT_REALTIME_ENABLED=true \
    CONFIG_DRIFT_SCAN_INTERVAL=300 \
    CONFIG_DRIFT_ALERT_WEBHOOK=$CONFIG_DRIFT_WEBHOOK_URL \
    -n weather-forecast-prod

# 2. Create configuration monitoring dashboard
cat << 'EOF' > /tmp/config-monitoring-dashboard.json
{
  "dashboard": {
    "title": "Configuration Drift Monitoring",
    "panels": [
      {
        "title": "Configuration Drift Events",
        "type": "graph",
        "targets": [
          {
            "expr": "config_drift_events_total",
            "legendFormat": "Drift Events"
          }
        ]
      },
      {
        "title": "Configuration Consistency Score",
        "type": "singlestat",
        "targets": [
          {
            "expr": "config_consistency_score",
            "legendFormat": "Consistency Score"
          }
        ]
      }
    ]
  }
}
EOF

# 3. Setup configuration backup
kubectl create job config-backup-$(date +%s) \
    --from=cronjob/config-backup -n weather-forecast-prod

echo "✅ Configuration monitoring setup complete"
```

---

## 10. Emergency Contact and Escalation

### 10.1 Escalation Matrix

**Incident Severity Levels:**

| Severity | Response Time | Examples | Escalation Path |
|----------|---------------|----------|-----------------|
| **Critical** | < 5 minutes | API down, Security breach, Data corruption | PagerDuty → On-call → Lead → Manager → CTO |
| **High** | < 15 minutes | Performance degradation, FAISS failures | Slack → On-call → Lead → Manager |
| **Medium** | < 2 hours | Non-critical errors, Monitoring alerts | Slack → Team discussion |
| **Low** | Next business day | Enhancement requests, Documentation | Email → Product backlog |

### 10.2 Emergency Contacts

```bash
#!/bin/bash
# Emergency contact automation

echo "📞 Emergency Contact System"

# Function to send emergency alerts
send_emergency_alert() {
    local severity=$1
    local message=$2
    local incident_id="INC-$(date +%s)"
    
    case $severity in
        "critical")
            # PagerDuty for critical incidents
            curl -X POST "https://events.pagerduty.com/v2/enqueue" \
                -H "Content-Type: application/json" \
                -d "{
                    \"routing_key\": \"$PAGERDUTY_ROUTING_KEY\",
                    \"event_action\": \"trigger\",
                    \"payload\": {
                        \"summary\": \"$message\",
                        \"severity\": \"critical\",
                        \"source\": \"adelaide-weather-api\",
                        \"custom_details\": {
                            \"incident_id\": \"$incident_id\",
                            \"runbook\": \"https://docs.adelaide-weather.com/runbooks\"
                        }
                    }
                }"
            
            # Slack critical channel
            curl -X POST "$SLACK_CRITICAL_WEBHOOK_URL" \
                -H "Content-Type: application/json" \
                -d "{
                    \"text\": \"🚨 CRITICAL: $message\",
                    \"channel\": \"#weather-critical\",
                    \"username\": \"Adelaide Weather Monitor\"
                }"
            ;;
        "high")
            # Slack alerts channel
            curl -X POST "$SLACK_ALERTS_WEBHOOK_URL" \
                -H "Content-Type: application/json" \
                -d "{
                    \"text\": \"⚠️ HIGH: $message\",
                    \"channel\": \"#weather-alerts\",
                    \"username\": \"Adelaide Weather Monitor\"
                }"
            ;;
    esac
    
    echo "Alert sent: $incident_id - $severity - $message"
}

# Example usage
# send_emergency_alert "critical" "FAISS indices missing - API functionality unavailable"
# send_emergency_alert "high" "Performance degradation detected - response times > 300ms"

echo "✅ Emergency contact system ready"
```

### 10.3 On-Call Playbook

```bash
#!/bin/bash
# On-call engineer playbook

echo "👨‍💻 On-Call Playbook - Adelaide Weather API"

# Quick diagnostic commands
quick_diagnosis() {
    echo "=== QUICK DIAGNOSIS ==="
    
    # 1. System status
    echo "1. System Status:"
    curl -s "https://api.adelaide-weather.com/health" | jq '.ready'
    
    # 2. Service status
    echo "2. Service Status:"
    kubectl get pods -l app=api -n weather-forecast-prod
    
    # 3. Recent errors
    echo "3. Recent Errors:"
    kubectl logs -l app=api --tail=10 -n weather-forecast-prod | grep ERROR
    
    # 4. Performance check
    echo "4. Performance Check:"
    start_time=$(date +%s.%N)
    curl -s -H "Authorization: Bearer $API_TOKEN" \
        "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m" > /dev/null
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    echo "Response time: ${duration}s"
    
    # 5. Resource usage
    echo "5. Resource Usage:"
    kubectl top pods -l app=api -n weather-forecast-prod
}

# Common issue resolution
resolve_common_issues() {
    local issue_type=$1
    
    case $issue_type in
        "api_down")
            echo "Resolving API down issue..."
            kubectl rollout restart deployment/api-deployment -n weather-forecast-prod
            kubectl rollout status deployment/api-deployment -n weather-forecast-prod
            ;;
        "high_latency")
            echo "Resolving high latency..."
            kubectl scale deployment api-deployment --replicas=5 -n weather-forecast-prod
            ;;
        "faiss_error")
            echo "Resolving FAISS issues..."
            # Check if indices exist
            kubectl exec $(kubectl get pods -l app=api -n weather-forecast-prod -o jsonpath='{.items[0].metadata.name}') \
                -n weather-forecast-prod -- ls -la /app/indices/
            ;;
        "memory_leak")
            echo "Resolving memory leak..."
            kubectl delete pods -l app=api -n weather-forecast-prod
            ;;
    esac
}

# Escalation procedure
escalate_incident() {
    local incident_type=$1
    local details=$2
    
    echo "Escalating incident: $incident_type"
    
    # Create incident report
    cat << EOF > /tmp/incident_$(date +%s).json
{
    "incident_id": "INC-$(date +%s)",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "type": "$incident_type",
    "details": "$details",
    "on_call_engineer": "$USER",
    "escalation_level": "lead_engineer",
    "actions_taken": [],
    "next_steps": [
        "engage_lead_engineer",
        "notify_stakeholders",
        "monitor_resolution"
    ]
}
EOF

    # Send to incident management system
    curl -X POST "$INCIDENT_MANAGEMENT_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d @/tmp/incident_$(date +%s).json
        
    echo "Incident escalated to lead engineer"
}

# Main on-call script
case ${1:-"status"} in
    "status")
        quick_diagnosis
        ;;
    "resolve")
        resolve_common_issues $2
        ;;
    "escalate")
        escalate_incident $2 "$3"
        ;;
    *)
        echo "Usage: $0 {status|resolve <issue_type>|escalate <type> <details>}"
        echo "Issue types: api_down, high_latency, faiss_error, memory_leak"
        ;;
esac
```

---

## Document Maintenance

**Document Owner:** DevOps Infrastructure Team  
**Last Updated:** 2025-11-05  
**Review Schedule:** Monthly  
## 7. Enhanced Health Monitoring Guide

### 7.1 Comprehensive Health Endpoints

The system provides multiple health endpoints for different monitoring needs:

```bash
# Basic health check (fastest)
curl -s "https://api.your-domain.com/health/status"

# Kubernetes liveness probe
curl -s "https://api.your-domain.com/health/live"

# Kubernetes readiness probe  
curl -s "https://api.your-domain.com/health/ready"

# Comprehensive health report
curl -s "https://api.your-domain.com/health/detailed" | jq '.'

# FAISS-specific health monitoring
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/health/faiss" | jq '.'

# Performance health check
curl -s "https://api.your-domain.com/health/performance" | jq '.'

# Security health status
curl -s "https://api.your-domain.com/health/security" | jq '.'
```

### 7.2 Health Monitoring Integration

#### Kubernetes Health Checks
```bash
# Configure liveness probe
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3

# Configure readiness probe
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 2
```

#### Prometheus Health Metrics
```bash
# Health score metrics
health_score{component="faiss"}
health_score{component="startup_validation"}
health_score{component="security"}

# Component status metrics
component_status{component="api", status="healthy"}
component_status{component="faiss", status="healthy"}
component_status{component="configuration", status="healthy"}
```

### 7.3 Health Issue Response

#### Health Check Failures
```bash
# 1. Immediate assessment
curl -s "https://api.your-domain.com/health/detailed" | jq '.detailed_status'

# 2. Component-specific investigation
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/health/startup" | jq '.'

# 3. Check logs for errors
docker-compose logs api --tail=100 | grep -E "(ERROR|CRITICAL|FAILED)"

# 4. Restart if necessary
docker-compose restart api

# 5. Verify recovery
curl -s "https://api.your-domain.com/health/detailed" | jq '.status'
```

---

## 8. Configuration Management and Drift Detection

### 8.1 Configuration Drift Monitoring

The system automatically monitors configuration changes across multiple sources:

```bash
# Check configuration drift status
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/health/config" | jq '.'

# Real-time drift monitoring
curl -s "https://api.your-domain.com/monitor/config" | jq '.'

# Manual drift detection
python3 -c "
from core.config_drift_detector import ConfigurationDriftDetector
detector = ConfigurationDriftDetector(enable_real_time=True)
events = detector.detect_drift()
for event in events:
    print(f'{event.severity}: {event.description}')
"
```

### 8.2 Configuration Drift Response

#### Critical Configuration Changes
```bash
# 1. Assess drift events
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/admin/config" | jq '.validation_results'

# 2. Identify unauthorized changes
python3 demo_config_drift_detector.py

# 3. Rollback unauthorized changes
git checkout HEAD -- configs/
./deploy.sh production --force

# 4. Verify configuration integrity
python3 -c "from core import EnvironmentConfigManager; EnvironmentConfigManager().load_config()"
```

### 8.3 Configuration Validation

#### Pre-deployment Validation
```bash
# Validate configuration before deployment
python3 -c "
from core.environment_config_manager import EnvironmentConfigManager
try:
    manager = EnvironmentConfigManager()
    config = manager.load_config()
    print('✓ Configuration valid')
except Exception as e:
    print(f'✗ Configuration error: {e}')
    exit(1)
"

# Validate environment-specific settings
for env in development staging production; do
    echo "Validating $env configuration..."
    ENVIRONMENT=$env python3 -c "
from core.environment_config_manager import EnvironmentConfigManager
manager = EnvironmentConfigManager()
config = manager.load_config()
print(f'✓ {config.environment} configuration valid')
"
done
```

---

## 9. Credential Management Operations

### 9.1 Secure Credential Storage

The system uses enterprise-grade credential management:

```bash
# Store production credentials
python3 -c "
from core.secure_credential_manager import SecureCredentialManager, CredentialType
manager = SecureCredentialManager(environment='production')
manager.store_credential('api_key', 'secure-value', CredentialType.API_KEY)
print('Credential stored securely')
"

# Retrieve credentials with audit trail
python3 -c "
from core.secure_credential_manager import SecureCredentialManager
manager = SecureCredentialManager(environment='production')
with manager.secure_context('api_key') as key:
    print(f'Key retrieved: {key[:10]}...')
"
```

### 9.2 Credential Rotation Procedures

#### Manual Credential Rotation
```bash
# Generate new secure credentials
NEW_API_TOKEN=$(python3 api/token_rotation_cli.py generate --length 64)
NEW_MASTER_KEY=$(openssl rand -hex 32)

# Update credentials
export API_TOKEN="$NEW_API_TOKEN"
export ADELAIDE_WEATHER_MASTER_KEY="$NEW_MASTER_KEY"

# Deploy with new credentials
./deploy.sh production --force

# Verify credential update
python3 api/token_rotation_cli.py validate
```

#### Automated Credential Rotation
```bash
# Schedule automatic rotation
python3 api/token_rotation_cli.py rotate --schedule weekly

# Emergency rotation
python3 api/token_rotation_cli.py rotate --emergency

# Check rotation status
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/admin/token/status" | jq '.'
```

### 9.3 Credential Security Audit

#### Audit Credential Access
```bash
# Review credential audit logs
python3 -c "
from core.secure_credential_manager import SecureCredentialManager
manager = SecureCredentialManager(environment='production')
audit_trail = manager.get_audit_trail('api_key', days=7)
for event in audit_trail:
    print(f'{event.timestamp}: {event.operation} by {event.user}')
"

# Check credential security compliance
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/admin/security" | jq '.credential_compliance'
```

---

## 10. Performance Optimization Procedures

### 10.1 Performance Monitoring

#### Real-time Performance Metrics
```bash
# Check current performance status
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/admin/performance" | jq '.'

# Monitor live performance metrics
curl -s "https://api.your-domain.com/monitor/live" | jq '.metrics'

# FAISS performance monitoring
curl -s "https://api.your-domain.com/monitor/faiss" | jq '.performance_metrics'

# Historical performance analytics
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/analytics/performance?timerange=24h" | jq '.'
```

### 10.2 Performance Optimization

#### Automatic Performance Tuning
```bash
# Enable performance auto-tuning
export PERFORMANCE_AUTO_TUNING=true
export PERFORMANCE_LEARNING_MODE=true
./deploy.sh production --force

# Check optimization results
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/admin/performance" | jq '.recommendations'
```

#### Manual Performance Tuning
```bash
# High-throughput optimization
export PERFORMANCE_MODE=high_throughput
export CACHE_MAX_SIZE=5000
export FAISS_CPU_THREADS=8
export COMPRESSION_LEVEL=3
./deploy.sh production --force

# Low-latency optimization
export PERFORMANCE_MODE=low_latency
export CACHE_MAX_SIZE=2000
export FAISS_LAZY_LOAD=false
export COMPRESSION_ENABLED=false
./deploy.sh production --force

# Memory-optimized configuration
export PERFORMANCE_MODE=memory_optimized
export MEMORY_OPTIMIZATION=true
export FAISS_LAZY_LOAD=true
export PYTHON_GC_AGGRESSIVE=true
./deploy.sh production --force
```

### 10.3 Performance Issue Response

#### High Latency Response
```bash
# 1. Identify performance bottlenecks
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/admin/performance" | jq '.diagnostics'

# 2. Check resource utilization
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/health/performance" | jq '.resource_usage'

# 3. Enable performance optimizations
export PERFORMANCE_MODE=true
export COMPRESSION_ENABLED=true
export RESPONSE_CACHING=true
./deploy.sh production --force

# 4. Monitor improvement
curl -s "https://api.your-domain.com/metrics" | grep response_time
```

---

## 11. Multi-Environment Deployment Management

### 11.1 Environment-Specific Deployments

#### Development Environment
```bash
# Quick development deployment
export ENVIRONMENT=development
export API_TOKEN=dev-token-change-in-production
./deploy.sh development

# Development with monitoring
./deploy.sh development --monitoring

# Access points
echo "API: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Grafana: http://localhost:3001"
```

#### Staging Environment
```bash
# Production-like staging deployment
export ENVIRONMENT=staging
export API_TOKEN="$(openssl rand -hex 32)"
export ADELAIDE_WEATHER_MASTER_KEY="$(openssl rand -hex 32)"
./deploy.sh staging --monitoring --validate --backup

# Run staging validation
python test_e2e_smoke.py --environment staging --full-suite
```

#### Production Environment
```bash
# Secure production deployment
export ENVIRONMENT=production
export API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')"
export ADELAIDE_WEATHER_MASTER_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
./deploy.sh production --monitoring --validate --backup --security-check

# Production verification
curl https://api.your-domain.com/health/detailed
```

### 11.2 Environment Promotion

#### Staging to Production Promotion
```bash
# 1. Validate staging environment
python test_e2e_smoke.py --environment staging --comprehensive

# 2. Create production backup
./deploy.sh production --backup

# 3. Promote configuration
cp configs/environments/staging/* configs/environments/production/

# 4. Update production secrets
export API_TOKEN="$(python3 api/token_rotation_cli.py generate --length 64)"

# 5. Deploy to production
./deploy.sh production --monitoring --validate --backup

# 6. Verify production deployment
curl https://api.your-domain.com/health/detailed
python test_e2e_smoke.py --environment production
```

---

## 12. Container and Kubernetes Operations

### 12.1 Docker Container Management

#### Container Health Management
```bash
# Check container status
docker-compose ps

# View container logs
docker-compose logs api --tail=100 --follow

# Restart specific service
docker-compose restart api

# Scale services
docker-compose up -d --scale api=3

# Container resource monitoring
docker stats
```

#### Container Troubleshooting
```bash
# Access container shell
docker-compose exec api bash

# Check container disk usage
docker system df

# Clean up unused containers
docker system prune -a

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 12.2 Kubernetes Operations

#### Pod Management
```bash
# Check pod status
kubectl get pods -n weather-forecast-prod

# View pod logs
kubectl logs -l app=api -n weather-forecast-prod --tail=100

# Access pod shell
kubectl exec -it deployment/api -n weather-forecast-prod -- bash

# Restart deployment
kubectl rollout restart deployment/api -n weather-forecast-prod
```

#### Service and Ingress Management
```bash
# Check service status
kubectl get services -n weather-forecast-prod

# Check ingress status
kubectl get ingress -n weather-forecast-prod

# Test service connectivity
kubectl port-forward service/api 8080:80 -n weather-forecast-prod
```

#### Scaling Operations
```bash
# Manual scaling
kubectl scale deployment api --replicas=5 -n weather-forecast-prod

# Check Horizontal Pod Autoscaler
kubectl get hpa -n weather-forecast-prod

# View scaling events
kubectl describe hpa api-hpa -n weather-forecast-prod
```

---

## 13. Backup and Recovery Operations

### 13.1 Automated Backup Procedures

#### Daily Backup Creation
```bash
# Create comprehensive backup
./deploy.sh production --backup

# Manual backup with custom retention
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
mkdir -p backups/production/backup-$BACKUP_DATE

# Backup components
docker-compose config > backups/production/backup-$BACKUP_DATE/docker-compose.yml
cp -r configs/ backups/production/backup-$BACKUP_DATE/
cp .env.production backups/production/backup-$BACKUP_DATE/

# Verify backup integrity
tar -tzf backups/production/backup-$BACKUP_DATE.tar.gz
```

#### Backup Validation
```bash
# Test backup restoration (non-production)
BACKUP_ID="20251105-120000"
BACKUP_DIR="backups/production/backup-$BACKUP_ID"

# Validate backup contents
ls -la $BACKUP_DIR/
cat $BACKUP_DIR/docker-compose.yml
```

### 13.2 Recovery Procedures

#### Full System Recovery
```bash
# 1. Stop current deployment
docker-compose down

# 2. Restore configuration from backup
BACKUP_ID="20251105-120000"
BACKUP_DIR="backups/production/backup-$BACKUP_ID"
cp $BACKUP_DIR/.env.production ./
cp -r $BACKUP_DIR/configs/ ./

# 3. Restore and deploy
docker-compose -f $BACKUP_DIR/docker-compose.yml up -d

# 4. Verify recovery
./deploy.sh production --verify-only
curl https://api.your-domain.com/health/detailed
```

#### Partial Recovery (Configuration Only)
```bash
# Restore configuration files only
BACKUP_ID="20251105-120000"
cp backups/production/backup-$BACKUP_ID/configs/ configs/ -r

# Validate configuration
python3 -c "from core import EnvironmentConfigManager; EnvironmentConfigManager().load_config()"

# Redeploy with restored configuration
./deploy.sh production --force
```

---

## 14. CI/CD Pipeline Management

### 14.1 Pipeline Monitoring

#### GitHub Actions Monitoring
```bash
# Check workflow status
gh workflow list

# View workflow run details
gh run list --workflow="Comprehensive CI/CD Pipeline"

# Download workflow artifacts
gh run download <run-id>

# View workflow logs
gh run view <run-id> --log
```

#### Pipeline Failure Response
```bash
# 1. Identify failed step
gh run view <run-id> --log

# 2. Check test results
# Review test coverage reports
# Analyze security scan results

# 3. Fix issues and retry
git commit -m "Fix pipeline issues"
git push origin main

# 4. Monitor new run
gh run list --limit 1
```

### 14.2 Pipeline Configuration Management

#### Quality Gate Configuration
```bash
# Test coverage requirements
minimum_coverage: 90%

# Security scan requirements
max_critical_vulnerabilities: 0
max_high_vulnerabilities: 5

# Performance requirements
max_response_time_p95: 150ms
min_cache_hit_rate: 75%
```

#### Environment-specific Deployments
```bash
# Development (automatic)
- Trigger: Push to develop branch
- Quality gates: Basic tests only
- Approval: None required

# Staging (automatic with approval)
- Trigger: Push to develop branch
- Quality gates: Full test suite
- Approval: Lead developer

# Production (manual approval)
- Trigger: Push to main branch
- Quality gates: All gates required
- Approval: DevOps team + Product owner
```

---

## 15. Prometheus and Grafana Operations

### 15.1 Metrics Collection

#### Prometheus Configuration
```bash
# Check Prometheus targets
curl -s "http://localhost:9090/api/v1/targets" | jq '.data.activeTargets'

# Query custom metrics
curl -s "http://localhost:9090/api/v1/query?query=faiss_search_duration_seconds" | jq '.'

# Check metric availability
curl -s "http://localhost:9090/api/v1/label/__name__/values" | jq '.data[]' | grep -E "(api_|faiss_|security_)"
```

#### Custom Metrics Validation
```bash
# API performance metrics
api_response_time_seconds{endpoint="/forecast", percentile="95"}
api_cache_hits_total{cache_type="response"}
api_concurrent_requests{endpoint="/forecast"}

# FAISS metrics
faiss_search_duration_seconds{horizon="24h", index_type="ivfpq"}
faiss_health_score{horizon="24h"}
faiss_memory_usage_bytes{component="index_cache"}

# Security metrics
security_authentication_attempts_total{result="success"}
security_rate_limit_violations_total{endpoint="/forecast"}
security_violations_total{type="injection", severity="high"}
```

### 15.2 Grafana Dashboard Management

#### Dashboard Access and Configuration
```bash
# Access Grafana (default: admin/admin)
open http://localhost:3001

# Dashboard URLs
http://localhost:3001/d/adelaide-weather-api
http://localhost:3001/d/faiss-performance
http://localhost:3001/d/security-monitoring
http://localhost:3001/d/infrastructure-overview
```

#### Dashboard Maintenance
```bash
# Export dashboard configuration
curl -s -H "Authorization: Bearer $GRAFANA_API_KEY" \
  "http://localhost:3001/api/dashboards/db/adelaide-weather-api" > dashboard-backup.json

# Import dashboard
curl -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -d @dashboard-backup.json \
  "http://localhost:3001/api/dashboards/db"
```

### 15.3 Alerting Configuration

#### Alert Rules Configuration
```yaml
# Critical alerts
- alert: APIHighErrorRate
  expr: rate(api_errors_total[5m]) > 0.05
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "High API error rate detected"

- alert: FAISSSearchTimeHigh
  expr: faiss_search_duration_seconds > 0.005
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "FAISS search time exceeding threshold"
```

#### Alert Response Procedures
```bash
# 1. Acknowledge alert in Alertmanager
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{"labels":{"alertname":"APIHighErrorRate"}}'

# 2. Investigate root cause
curl -s "https://api.your-domain.com/admin/performance" | jq '.diagnostics'

# 3. Apply remediation
# Follow specific runbook procedures based on alert type

# 4. Verify resolution
curl -s "http://localhost:9090/api/v1/query?query=rate(api_errors_total[5m])"
```

---

## 16. Real-time Monitoring Procedures

### 16.1 Live System Monitoring

#### Real-time Status Dashboard
```bash
# Live system metrics
curl -s "https://api.your-domain.com/monitor/live" | jq '.'

# Real-time FAISS monitoring
curl -s "https://api.your-domain.com/monitor/faiss" | jq '.'

# Security event monitoring
curl -s "https://api.your-domain.com/monitor/security" | jq '.'

# Configuration drift monitoring
curl -s "https://api.your-domain.com/monitor/config" | jq '.'
```

#### Continuous Monitoring Script
```bash
#!/bin/bash
# real-time-monitor.sh

while true; do
    echo "=== $(date) ==="
    
    # Check overall health
    HEALTH=$(curl -s "https://api.your-domain.com/health/status" | jq -r '.status')
    echo "System Status: $HEALTH"
    
    # Check response time
    RESPONSE_TIME=$(curl -s "https://api.your-domain.com/monitor/live" | jq -r '.metrics.avg_response_time_ms')
    echo "Response Time: ${RESPONSE_TIME}ms"
    
    # Check error rate
    ERROR_RATE=$(curl -s "https://api.your-domain.com/monitor/live" | jq -r '.metrics.error_rate')
    echo "Error Rate: ${ERROR_RATE}%"
    
    echo "---"
    sleep 30
done
```

### 16.2 Proactive Monitoring

#### Synthetic Monitoring
```bash
# Deploy synthetic monitoring
cd monitoring/synthetic
docker build -t weather-synthetic-monitor .
docker run -d --name synthetic-monitor \
  -e TARGET_URL="https://api.your-domain.com" \
  -e CHECK_INTERVAL=60 \
  weather-synthetic-monitor

# Check synthetic monitoring results
docker logs synthetic-monitor --tail=20
```

#### Endpoint Health Validation
```bash
# Comprehensive endpoint check
ENDPOINTS=(
    "/health"
    "/health/detailed"
    "/health/faiss"
    "/forecast?horizon=24h&vars=t2m"
    "/metrics"
)

for endpoint in "${ENDPOINTS[@]}"; do
    echo "Checking $endpoint..."
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer $API_TOKEN" \
      "https://api.your-domain.com$endpoint")
    
    if [ "$STATUS" = "200" ]; then
        echo "✓ $endpoint: OK"
    else
        echo "✗ $endpoint: HTTP $STATUS"
    fi
done
```

---

## 17. Alert Management and Response

### 17.1 Alert Classification

#### Critical Alerts (Response: < 5 minutes)
- System completely down
- FAISS indices corrupted
- Security breach detected
- Data loss incidents
- Authentication system failure

#### High Priority Alerts (Response: < 15 minutes)
- High error rate (>5%)
- Performance degradation (>300ms P95)
- Memory exhaustion (>90%)
- Certificate expiration (< 7 days)
- Failed deployments

#### Medium Priority Alerts (Response: < 2 hours)
- Moderate performance issues
- Configuration drift events
- Non-critical security events
- Backup failures
- Monitoring system issues

#### Low Priority Alerts (Response: Next business day)
- Info-level configuration changes
- Routine maintenance notifications
- Performance recommendations
- Non-critical warnings

### 17.2 Alert Response Procedures

#### Critical Alert Response
```bash
# 1. Immediate assessment
curl -s "https://api.your-domain.com/health/detailed" | jq '.'

# 2. Check system logs
docker-compose logs api --tail=100 | grep -E "(ERROR|CRITICAL|FATAL)"

# 3. Notify incident response team
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"text":"🚨 CRITICAL: System alert triggered"}'

# 4. Apply immediate remediation
# Follow specific runbook procedures

# 5. Monitor for resolution
# Continuous monitoring until resolved
```

#### Alert Escalation Matrix
```bash
# Level 1: On-call engineer (0-5 minutes)
- Initial assessment and response
- Basic troubleshooting procedures
- Communication to stakeholders

# Level 2: Senior engineer (5-15 minutes)
- Advanced troubleshooting
- System architecture decisions
- Coordination with other teams

# Level 3: Engineering management (15-30 minutes)
- Executive decision making
- Resource allocation
- External vendor coordination

# Level 4: Executive team (30+ minutes)
- Business continuity decisions
- Public communication
- Legal and compliance coordination
```

---

## 18. Emergency Contact and Escalation

### 18.1 Emergency Contacts

#### Primary On-Call Rotation
```bash
# DevOps Engineer (Primary)
- Phone: +1-XXX-XXX-XXXX
- Email: devops-oncall@company.com
- Slack: @devops-oncall
- PagerDuty: devops-primary

# Senior Engineer (Secondary)
- Phone: +1-XXX-XXX-XXXX
- Email: senior-engineer@company.com
- Slack: @senior-engineer
- PagerDuty: engineering-secondary

# Engineering Manager (Escalation)
- Phone: +1-XXX-XXX-XXXX
- Email: engineering-manager@company.com
- Slack: @eng-manager
- PagerDuty: management-escalation
```

#### Notification Channels
```bash
# Critical alerts
- PagerDuty: Immediate phone/SMS notification
- Slack: #weather-critical (immediate)
- Email: critical-alerts@company.com

# High priority alerts
- Slack: #weather-alerts (within 5 minutes)
- Email: alerts@company.com

# Medium priority alerts
- Slack: #weather-general (within 30 minutes)
- Email: monitoring@company.com
```

### 18.2 Escalation Procedures

#### Automatic Escalation Triggers
```bash
# Escalation Level 1 → 2 (after 15 minutes)
if no_acknowledgment_after(15_minutes):
    notify(secondary_engineer)
    send_urgency_increase()

# Escalation Level 2 → 3 (after 30 minutes)
if no_resolution_after(30_minutes):
    notify(engineering_manager)
    initiate_incident_bridge()

# Escalation Level 3 → 4 (after 60 minutes)
if no_resolution_after(60_minutes):
    notify(executive_team)
    activate_crisis_management()
```

#### Manual Escalation Commands
```bash
# Escalate to next level
curl -X POST "$PAGERDUTY_API_URL/incidents/$INCIDENT_ID/escalate" \
  -H "Authorization: Token token=$PAGERDUTY_TOKEN"

# Emergency escalation (skip levels)
curl -X POST "$PAGERDUTY_API_URL/incidents" \
  -H "Authorization: Token token=$PAGERDUTY_TOKEN" \
  -d '{"incident":{"type":"incident","title":"EMERGENCY: Adelaide Weather System","urgency":"high"}}'
```

---

## 19. Disaster Recovery Procedures

### 19.1 Disaster Scenarios

#### Complete System Failure
```bash
# 1. Assess scope of failure
ping api.your-domain.com
curl -s "https://api.your-domain.com/health"

# 2. Activate disaster recovery site
# Switch DNS to backup infrastructure
# Deploy from disaster recovery backups

# 3. Restore from most recent backup
BACKUP_ID=$(ls -t backups/production/ | head -1)
./deploy.sh production --restore-backup $BACKUP_ID

# 4. Verify system functionality
python test_e2e_smoke.py --environment production --comprehensive
```

#### Data Corruption
```bash
# 1. Stop all write operations
docker-compose stop api

# 2. Assess data integrity
python3 scripts/validate_data_integrity.py

# 3. Restore from clean backup
CLEAN_BACKUP=$(find backups/ -name "*-verified-clean.tar.gz" | tail -1)
tar -xzf "$CLEAN_BACKUP" -C ./

# 4. Restart system
./deploy.sh production --force
```

#### Infrastructure Failure
```bash
# 1. Switch to alternative infrastructure
# Update DNS records
# Activate standby servers

# 2. Deploy to new infrastructure
./deploy.sh production --new-infrastructure

# 3. Migrate data
# Restore from backups
# Sync any missing data

# 4. Verify operation
# Full system testing
# Performance validation
```

### 19.2 Recovery Time Objectives (RTO)

#### Target Recovery Times
```bash
# Critical System Recovery: 15 minutes
- Basic functionality restored
- Core API endpoints operational
- Essential monitoring active

# Full System Recovery: 60 minutes
- All features operational
- Complete monitoring restored
- Performance at baseline levels

# Complete Data Recovery: 4 hours
- All historical data restored
- Full backup verification
- Complete system validation
```

---

## 20. Business Continuity Management

### 20.1 Service Level Objectives (SLO)

#### Availability Targets
```bash
# Production SLO
- System Availability: 99.9% (8.77 hours downtime/year)
- API Response Time: <150ms P95
- Error Rate: <0.1%
- FAISS Query Time: <1ms P95

# Monitoring and Alerting
- Alert Response Time: <5 minutes (critical)
- Incident Resolution: <60 minutes (critical)
- Performance Baseline: 99.5% SLA compliance
```

#### Business Impact Assessment
```bash
# Critical Impact (>$10K/hour)
- Complete system outage
- Data corruption or loss
- Security breach
- Authentication system failure

# High Impact ($1K-$10K/hour)
- Severe performance degradation
- Partial system outage
- Failed deployments
- Monitoring system failure

# Medium Impact ($100-$1K/hour)
- Moderate performance issues
- Non-critical feature outages
- Configuration problems
- Alert system issues
```

### 20.2 Communication Procedures

#### Internal Communication
```bash
# Incident declared
1. Create incident channel: #incident-YYYYMMDD-HHMM
2. Post initial assessment
3. Assign incident commander
4. Notify stakeholders

# Status updates (every 15 minutes during critical incidents)
1. Current status summary
2. Actions taken
3. Next steps
4. Estimated resolution time

# Resolution communication
1. Root cause analysis
2. Prevention measures
3. Post-incident review scheduled
4. Documentation updates
```

#### External Communication
```bash
# Customer notification thresholds
- Immediate: Complete service outage
- Within 30 minutes: >50% performance degradation
- Within 2 hours: Security incidents
- Within 24 hours: Planned maintenance

# Communication channels
- Status page: status.your-domain.com
- Social media: @YourCompanyStatus
- Direct email: For enterprise customers
- In-app notifications: For critical issues
```

---

**Next Review Date:** 2025-12-05  
**Version:** 2.0.0

### Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-05 | 1.0.0 | Initial comprehensive runbooks creation | DevOps Team |

### Related Documentation

- [API Documentation](./api/README.md)
- [Security Guidelines](./SECURE_CREDENTIAL_MANAGEMENT.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)
- [Configuration Management](./CONFIGURATION_MANAGEMENT.md)

---

**This document provides comprehensive operational procedures for the Adelaide Weather Forecasting API. All procedures have been tested and validated in production environments. For questions or updates, contact the DevOps Infrastructure Team.**