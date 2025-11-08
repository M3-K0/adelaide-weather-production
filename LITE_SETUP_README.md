# Adelaide Weather - Lite Development Setup

Quick and minimal setup for local development with just API and UI services.

## What's Included

✅ **API Service** (port 8000)
✅ **UI Service** (port 3000)
✅ **Hot reload** for development
✅ **Test data generation**

❌ No monitoring stack (Prometheus, Grafana)
❌ No nginx reverse proxy
❌ No production features

## Quick Start

### 1. First Time Setup

Run the setup script to generate test FAISS indices and data:

```bash
./setup-lite.sh
```

This will:
- Install required Python dependencies (numpy, pandas, faiss-cpu, pyarrow)
- Generate test FAISS indices for all horizons (6h, 12h, 24h, 48h)
- Create embeddings and metadata files
- Create empty directories for outcomes and models

**Generated directories:**
- `indices/` - FAISS index files (6574-13148 vectors per horizon)
- `embeddings/` - Embedding vectors and metadata (.npy and .parquet files)
- `outcomes/` - Ready for forecast outcomes
- `models/` - Ready for model files

### 2. Start Services

```bash
docker-compose -f docker-compose.lite.yml up -d
```

### 3. Verify It's Working

```bash
# Check API health
curl http://localhost:8000/health

# Test forecast endpoint
curl -H "Authorization: Bearer dev-token-change-in-production" \
  "http://localhost:8000/forecast?horizon=24h&vars=t2m,u10,v10"
```

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Frontend UI | http://localhost:3000 | Next.js web interface |
| API Direct | http://localhost:8000 | FastAPI backend |
| API Health | http://localhost:8000/health | Health check endpoint |
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| API Metrics | http://localhost:8000/metrics | Prometheus metrics |

## Development Commands

```bash
# View all logs
docker-compose -f docker-compose.lite.yml logs -f

# View API logs only
docker-compose -f docker-compose.lite.yml logs -f api

# View UI logs only
docker-compose -f docker-compose.lite.yml logs -f ui

# Stop services
docker-compose -f docker-compose.lite.yml down

# Rebuild and restart (after code changes)
docker-compose -f docker-compose.lite.yml up -d --build

# Clean everything (including volumes)
docker-compose -f docker-compose.lite.yml down -v
```

## Test Data Details

The setup script creates realistic test data:

- **Embedding dimension:** 256
- **Index type:** FlatIP (baseline) and IVF-PQ (optimized)
- **6h horizon:** 6,574 vectors
- **12h horizon:** 6,574 vectors
- **24h horizon:** 13,148 vectors
- **48h horizon:** 13,148 vectors
- **Total vectors:** 52,592 (matching production system)

All embeddings are:
- L2 normalized for cosine similarity
- Deterministically seeded for reproducibility
- Stored with metadata (timestamps, horizon, indices)

## Troubleshooting

### "No such file or directory: indices/faiss_24h_flatip.faiss"

Run the setup script first:
```bash
./setup-lite.sh
```

### "Permission denied: ./setup-lite.sh"

Make the script executable:
```bash
chmod +x setup-lite.sh
```

### API not starting / health check fails

Check the logs:
```bash
docker-compose -f docker-compose.lite.yml logs api
```

Common issues:
- Volumes not mounted correctly (check docker-compose.lite.yml)
- Indices not generated (run setup-lite.sh)
- Port 8000 already in use

### UI not accessible

Check if the container is running:
```bash
docker-compose -f docker-compose.lite.yml ps
```

Check UI logs:
```bash
docker-compose -f docker-compose.lite.yml logs ui
```

## Switching to Full Setup

For production-like setup with monitoring:

```bash
# Stop lite setup
docker-compose -f docker-compose.lite.yml down

# Start full setup
docker-compose up -d --profile monitoring
```

## What's Different from Full Setup?

| Feature | Lite Setup | Full Setup |
|---------|------------|------------|
| API Service | ✅ | ✅ |
| UI Service | ✅ | ✅ |
| Nginx Proxy | ❌ | ✅ |
| Prometheus | ❌ | ✅ (profile) |
| Grafana | ❌ | ✅ (profile) |
| Redis Cache | ❌ | ✅ (production) |
| Resource Limits | ❌ | ✅ |
| Production Config | ❌ | ✅ |
| Direct Port Access | ✅ 3000, 8000 | ✅ 80, 3000, 8000 |

## Notes

- Uses development API token: `dev-token-change-in-production`
- Rate limit: 300 requests/minute (relaxed for dev)
- Debug mode enabled
- CORS accepts localhost origins
- No persistent volumes (data in containers)
