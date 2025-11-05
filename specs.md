# Adelaide Weather Forecasting System - Technical Specifications

## System Overview
Production-ready analog ensemble forecasting system for Adelaide using CNN embeddings with InfoNCE contrastive learning.

## Technical Specifications

### Model Architecture
- **Encoder**: WeatherCNNEncoder with FiLM conditioning
- **Embedding Dimension**: 256 (L2-normalized)
- **Input Shape**: [16, 16, 9] variables (Adelaide region)
- **Lead Times**: {6h, 12h, 24h, 48h}

### Target Variables
- 2m Temperature (K)
- Precipitation (mm/h)
- 10m Wind U-component (m/s)
- 10m Wind V-component (m/s)
- Mean Sea Level Pressure (Pa)

### Data Configuration
- **Training Data**: ERA5 2010-2018 (for index building)
- **Evaluation Data**: ERA5 2019-2020 (holdout testing)
- **Spatial Domain**: Adelaide region (lat: -33 to -37, lon: 137 to 141)
- **Temporal Resolution**: 6-hourly
- **Total Timesteps**: ~70k (2010-2020)

### Similarity & Retrieval
- **Distance Metric**: Cosine similarity on L2-normalized embeddings
- **Index Type**: Per-horizon FAISS indices (FlatIP + IVF-PQ)
- **Retrieval Settings**: K=100 neighbors, τ=0.1 temperature
- **Temporal Filtering**: No future constraint, seasonal window ±30 days

### FAISS Configuration
- **IndexFlatIP**: Baseline brute-force for ground truth
- **IndexIVFPQ**: Production index
  - nlist: 512-1024 (coarse quantizer clusters)
  - m: 32 (PQ sub-vectors)
  - nbits: 8 (bits per PQ code)
  - nprobe: 32-64 (search clusters)

### Ensemble Configuration
- **Weighting**: Softmax over cosine similarities with temperature τ
- **Deterministic**: Weighted mean forecast
- **Probabilistic**: Empirical quantiles (q10, q50, q90)
- **Event Probabilities**: Precipitation thresholds {0.1, 1.0, 10.0} mm

### Evaluation Metrics
- **Temperature/Pressure**: MAE, RMSE
- **Wind**: RMSE on U/V components
- **Precipitation**: Brier score, CRPS, reliability diagrams
- **Baselines**: Persistence, day-of-year climatology

### Performance Targets
- **Skill**: 24h temperature MAE beats persistence by ≥10%
- **Latency**: End-to-end forecast <2 minutes
- **Recall**: FAISS recall@K ≥95% vs brute force

### Operational Requirements
- **Real-time Input**: ERA5T or GFS analysis fields
- **Output Format**: NetCDF + JSON
- **Deployment**: Docker container with CPU inference
- **Monitoring**: Distance distributions, runtime stats, skill tracking

## File Structure
```
weather-forecast-final/
├── models/
│   ├── cnn_encoder.py          # Trained CNN encoder
│   └── best_model.pt           # Trained weights
├── embeddings/                 # Generated embeddings per horizon
│   ├── embeddings_6h.npy
│   ├── embeddings_12h.npy  
│   ├── embeddings_24h.npy
│   ├── embeddings_48h.npy
│   └── metadata.parquet        # Timestamps, targets, indices
├── indices/                    # FAISS indices per horizon
│   ├── faiss_6h_flatip.faiss
│   ├── faiss_6h_ivfpq.faiss
│   └── ... (for each horizon)
├── scripts/
│   ├── generate_embeddings.py  # Batch embedding generation
│   ├── build_indices.py        # FAISS index construction
│   ├── analog_forecaster.py    # Retrieval and ensemble
│   └── evaluate_system.py      # Backtesting framework
└── outputs/
    ├── evaluation/              # Backtest results
    ├── settings/                # Tuned hyperparameters
    └── forecasts/               # Generated forecasts
```

## Implementation Priority
1. **GPU-Critical** (Days 1-3): Embedding generation, FAISS training
2. **Validation** (Days 4-5): Retrieval system, evaluation framework  
3. **Production** (Days 6-7): Real-time integration, deployment

## Success Criteria
- [ ] All embeddings generated and validated
- [ ] FAISS indices built with performance benchmarks
- [ ] Analog retrieval system functional
- [ ] Evaluation shows skill vs baselines
- [ ] Real-time ingestion pipeline operational
- [ ] Complete Docker deployment ready

Last Updated: 2025-10-23