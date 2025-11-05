# A100 Deployment Guide - Adelaide Weather Forecasting
## Optimized for Fast, Reliable Training

> **All H200 learnings consolidated into this A100-ready package**

## 🚀 Quick Start (5 minutes)

```bash
# 1. Upload & extract
tar -xzf weather-forecast-final.tar.gz
cd weather-forecast-final

# 2. Install dependencies (includes critical dask fix)
pip install -r requirements.txt

# 3. Test setup
python scripts/quick_start.py

# 4. Start training (if test passes)
python scripts/train_embeddings_optimized.py
```

## 🔧 Critical Fixes Applied

### ✅ **I/O Bottleneck Fixed**
- **Dask dependency added** for zarr chunking
- **Chunked data loading** (chunk_size=50) for fast reading
- **Optimized batch sizes** for A100 (32 default, tested up to 256)

### ✅ **Training Stability Guaranteed**  
- **Config unification**: temperature=0.2, lr=0.0003
- **FiLM safe initialization**: gamma=1, beta=0 prevents vanishing gradients
- **Learning rate scheduler** with floor (min_lr=1e-5)
- **Gradient clipping**: 5.0 for stability
- **Mixed precision**: Disabled by default for reliability

### ✅ **GPU Optimization**
- **Efficient tensor placement** with `non_blocking=True`
- **Batch size optimized** for A100 (40-80GB VRAM)
- **Memory-efficient data loading**

### ✅ **Comprehensive Monitoring**
- **FiLM gamma tracking** (first 200 steps)
- **Gradient flow monitoring**
- **200-step smoke test** before full training
- **Automatic model checkpointing**

## 📊 Expected Performance on A100

### **Training Speed**
- **Smoke test**: ~200 seconds (200 steps)
- **Full epoch**: ~10-15 minutes (depending on data size)
- **Complete training**: ~3-5 hours (20 epochs)

### **Resource Usage**
- **GPU Memory**: 5-15GB (out of 40-80GB A100)
- **GPU Utilization**: 30-70% (optimal for this model size)
- **Cost**: ~$15-25 for complete training

### **Learning Targets**
- **Initial Loss**: ~4.16 (random baseline)
- **Target Loss**: <2.0 (meaningful learning)
- **FiLM Gamma Range**: 0.2-5.0 (healthy evolution)

## 🎯 Smoke Test Success Criteria

**✅ PASS:**
- All 200 steps complete without errors
- Loss decreases from ~4.16 to <3.0
- FiLM gamma evolves from 1.0 to 0.5-2.0 range
- No NaN/Inf losses
- Gradient norms healthy (>1e-10)

**❌ ABORT:**
- Any step fails with errors
- Loss plateaus above 4.0 
- FiLM gamma outside 0.1-10.0 range
- NaN/Inf losses appear
- Gradient norms collapse to 0

## 🔍 Monitoring Commands

```bash
# GPU utilization (should show 30-70%)
nvidia-smi -l 1

# Training logs (real-time)
tail -f outputs/training_optimized_*/training.log

# Check model checkpoints
ls -la outputs/training_optimized_*/
```

## 🛠️ Troubleshooting

### **Issue: Low GPU utilization (<10%)**
```bash
# Increase batch size
sed -i 's/batch_size: 32/batch_size: 64/' configs/model.yaml
# Or try 128 for larger A100s
```

### **Issue: CUDA memory errors**
```bash
# Reduce batch size
sed -i 's/batch_size: 32/batch_size: 16/' configs/model.yaml
```

### **Issue: Slow data loading**
```bash
# Check if dask is installed
python -c "import dask; print('Dask OK')"
# Reinstall if needed
pip install dask
```

### **Issue: Loss not decreasing**
- Check FiLM gamma stats in logs
- Verify gradient norms are healthy
- Ensure temperature=0.2 in config

## 📁 Package Contents

```
weather-forecast-final/
├── A100_DEPLOYMENT_GUIDE.md      # This guide
├── requirements.txt               # All dependencies (includes dask!)
├── configs/
│   ├── model.yaml                # Unified configuration
│   ├── data.yaml                 
│   └── training.yaml             
├── models/
│   └── cnn_encoder.py            # Model with FiLM safe initialization
├── scripts/
│   ├── train_embeddings_optimized.py  # Main training (all fixes)
│   ├── quick_start.py                 # Setup validation
│   └── validate_embeddings.py         # Post-training validation
└── data/                         # ERA5 data (upload separately)
    └── era5/zarr/
```

## 💡 Pro Tips

### **For Maximum Speed:**
- Use batch_size: 64-128 on A100-80GB
- Enable mixed precision after smoke test passes
- Use faster storage (NVMe SSD) for zarr files

### **For Stability:**
- Keep default batch_size: 32
- Leave mixed precision disabled
- Monitor FiLM gamma stats closely

### **For Cost Efficiency:**
- Run smoke test first (5 minutes, <$1)
- Monitor training closely in first hour
- Abort if learning plateaus

## 🎉 Success Indicators

**Training is working perfectly when you see:**
- ✅ Loss: 4.16 → <2.0 (steady decrease)
- ✅ FiLM gamma: 1.0 → 0.5-2.0 (healthy evolution)  
- ✅ GPU utilization: 30-70% (efficient usage)
- ✅ Step time: <10 seconds (fast progress)
- ✅ No errors or warnings in logs

## 🔄 Next Steps After Training

1. **Validate embeddings**: `python scripts/validate_embeddings.py`
2. **Build FAISS index** for similarity search
3. **Implement analog forecasting** pipeline
4. **Evaluate against baselines** (persistence, climatology)

---

**This package incorporates all lessons learned from H200 testing and is optimized for reliable A100 deployment. Happy training! 🚀**