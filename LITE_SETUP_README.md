# Adelaide Weather - Lite Development Setup

Quick and minimal setup for local development with just API and UI services using your **real ERA5 data**.

## What's Included

✅ **API Service** (port 8000)
✅ **UI Service** (port 3000)
✅ **Hot reload** for development
✅ **Uses your local ERA5 data**

❌ No monitoring stack (Prometheus, Grafana)
❌ No nginx reverse proxy
❌ No production features
❌ No fake/test/mock data

## Quick Start

### 1. Put Your Data in Place

You have **real ERA5 data locally**. Put it in one of these locations:

**Option A: In the repo directory**
```bash
# Create data directory in repo
mkdir -p data/era5/zarr

# Copy or symlink your ERA5 data here
cp -r /path/to/your/era5_surface_2010_2020.zarr data/era5/zarr/
cp -r /path/to/your/era5_pressure_2010_2019.zarr data/era5/zarr/
```

**Option B: Symlink from another location**
```bash
# Symlink if data is elsewhere
ln -s /path/to/your/weather-data ./data
```

**Option C: Use custom path**
Edit `docker-compose.lite.yml` and uncomment/modify the volume mount:
```yaml
volumes:
  - ${HOME}/weather-data:/app/data:ro  # Your custom path
```

### 2. Verify Data Structure

Your data should be in one of these structures:

**Raw ERA5 data:**
```
data/
└── era5/
    └── zarr/
        ├── era5_surface_2010_2020.zarr/
        └── era5_pressure_2010_2019.zarr/
```

**OR processed data (indices/embeddings/outcomes):**
```
indices/
├── faiss_6h_flatip.faiss
├── faiss_12h_flatip.faiss
├── faiss_24h_flatip.faiss
└── faiss_48h_flatip.faiss

embeddings/
├── embeddings_6h.npy
├── embeddings_12h.npy
├── embeddings_24h.npy
├── embeddings_48h.npy
├── metadata_6h.parquet
├── metadata_12h.parquet
├── metadata_24h.parquet
└── metadata_48h.parquet

outcomes/
└── (outcomes database files)
```

### 3. Start Services

```bash
docker-compose -f docker-compose.lite.yml up -d
```

### 4. Verify It's Working

```bash
# Check API health
curl http://localhost:8000/health

# Test forecast endpoint (use your real token or the dev one)
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

## Processing Your ERA5 Data

If you have raw ERA5 zarr files but need to generate the indices/embeddings/outcomes:

### Generate Embeddings
```bash
cd scripts
python generate_embeddings.py --horizon 24
```

### Build Outcomes Database
```bash
python scripts/build_outcomes_database.py --horizon 24
```

### Build FAISS Indices
```bash
python scripts/build_faiss_index.py --horizon 24
```

Or use the automated pipeline:
```bash
./scripts/full_pipeline.sh
```

## Data Size Reference

Your ERA5 data is probably:
- **Surface data (2010-2020):** ~50-100 GB
- **Pressure data (2010-2019):** ~30-80 GB
- **Processed indices:** ~500 MB
- **Embeddings:** ~10-20 GB
- **Outcomes:** ~5-10 GB

That's why it's too big for git! 😄

## Troubleshooting

### "No such file or directory: data/era5/zarr/..."

Check your data mount:
```bash
# Verify data directory exists
ls -la data/era5/zarr/

# Verify volume mount in docker
docker-compose -f docker-compose.lite.yml config | grep -A 5 volumes
```

### "FAISS index not found"

Either:
1. Generate indices from your ERA5 data (see "Processing Your ERA5 Data" above)
2. Copy pre-generated indices to `./indices/` directory

### API fails to start

Check logs:
```bash
docker-compose -f docker-compose.lite.yml logs api
```

Common issues:
- Data not mounted correctly
- Missing indices/embeddings
- Port 8000 already in use

### Permission issues with mounted data

If running on Linux and getting permission errors:
```bash
# Make data readable
chmod -R +r data/
```

Or update the Dockerfile to match your user ID.

## Data Location Options

Three ways to mount your data:

### 1. Default (./data)
```yaml
volumes:
  - ./data:/app/data:ro
```

### 2. Home directory
```yaml
volumes:
  - ${HOME}/weather-data:/app/data:ro
```

### 3. Environment variable
```bash
export DATA_DIR=/mnt/bigdisk/weather-data
docker-compose -f docker-compose.lite.yml up -d
```

With volume:
```yaml
volumes:
  - ${DATA_DIR:-./data}:/app/data:ro
```

## What's Different from Full Setup?

| Feature | Lite Setup | Full Setup |
|---------|------------|------------|
| API Service | ✅ | ✅ |
| UI Service | ✅ | ✅ |
| Real ERA5 Data | ✅ | ✅ |
| Nginx Proxy | ❌ | ✅ |
| Prometheus | ❌ | ✅ (profile) |
| Grafana | ❌ | ✅ (profile) |
| Redis Cache | ❌ | ✅ (production) |
| Resource Limits | ❌ | ✅ |
| Production Config | ❌ | ✅ |

## Notes

- **Data is read-only** (`:ro` mount) to prevent accidental modifications
- Uses development API token: `dev-token-change-in-production`
- Rate limit: 300 requests/minute (relaxed for dev)
- Debug mode enabled
- CORS accepts localhost origins
- Data stays on your host machine (not copied into containers)
- `.gitignore` excludes `data/`, `indices/`, `embeddings/`, `outcomes/` (too big for git)
