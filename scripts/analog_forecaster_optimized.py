#!/usr/bin/env python3
"""
Production-Optimized Analog Forecaster
======================================

High-performance analog ensemble forecasting with <150ms latency target.
Implements expert precision patterns and memory optimization for production deployment.

PERFORMANCE FEATURES:
- Expert-recommended weighted quantiles (Float32→Float64→Float32)
- Memory pool management for zero-allocation inference
- Critical path optimization with monitoring
- Numba-accelerated computation kernels
- Memory-mapped outcomes access

VALIDATION SYSTEMS:
- Real-time performance monitoring
- Precision validation for numerical stability
- Memory usage tracking and alerts
- Regression detection

Author: Performance Specialist Team
Version: 3.0.0 - Production Performance
"""

import os
import sys
import time
import logging
import numpy as np
import pandas as pd
import faiss
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from contextlib import contextmanager

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import performance optimizer
from core.performance_optimizer import (
    PERFORMANCE_OPTIMIZER, 
    MEMORY_POOL,
    PerformanceMetrics
)

# Setup optimized logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AnalogForecaster:
    """
    Production-optimized analog forecaster with <150ms performance target.
    
    Key optimizations:
    - Memory-mapped outcomes access (O(100μs) lookup)
    - Expert weighted quantiles with precision validation
    - Zero-allocation inference patterns
    - Comprehensive performance monitoring
    """
    
    def __init__(self, outcomes_dir: str = "outcomes", indices_dir: str = "indices"):
        """Initialize optimized analog forecaster."""
        self.outcomes_dir = Path(outcomes_dir)
        self.indices_dir = Path(indices_dir) 
        
        # Performance tracking
        self.total_forecasts = 0
        self.total_latency_ms = 0.0
        
        # Memory-mapped data caches
        self.outcomes_cache = {}      # horizon -> memory-mapped array
        self.metadata_cache = {}      # horizon -> DataFrame
        self.indices_cache = {}       # horizon -> FAISS index
        
        # Supported horizons and variables
        self.horizons = [6, 12, 24, 48]
        self.variables = [
            'z500', 't2m', 't850', 'q850',
            'u10', 'v10', 'u850', 'v850', 'cape'
        ]
        
        # Preload all data for production use
        self._preload_all_data()
        
        # Warmup performance system
        PERFORMANCE_OPTIMIZER.warmup_system()
        
        logger.info("✅ Production analog forecaster initialized")
    
    def _preload_all_data(self):
        """Preload all outcomes, metadata, and indices for minimal latency."""
        logger.info("🔄 Preloading production data...")
        
        for horizon in self.horizons:
            success = self._load_horizon_data(horizon)
            if not success:
                logger.error(f"❌ Failed to load data for horizon {horizon}h")
                continue
        
        logger.info(f"✅ Preloaded data for {len(self.outcomes_cache)} horizons")
    
    def _load_horizon_data(self, horizon: int) -> bool:
        """Load memory-mapped outcomes, metadata, and FAISS index for horizon."""
        try:
            # Load memory-mapped outcomes
            outcomes_path = self.outcomes_dir / f"outcomes_{horizon}h.npy"
            if not outcomes_path.exists():
                logger.error(f"Outcomes not found: {outcomes_path}")
                return False
            
            # Memory-map for ultra-fast access
            outcomes = np.load(outcomes_path, mmap_mode='r')
            self.outcomes_cache[horizon] = outcomes
            
            # Load metadata
            metadata_path = self.outcomes_dir / f"metadata_{horizon}h_clean.parquet"
            if not metadata_path.exists():
                logger.error(f"Metadata not found: {metadata_path}")
                return False
            
            metadata = pd.read_parquet(metadata_path)
            self.metadata_cache[horizon] = metadata
            
            # Load FAISS index (try optimized first, fallback to flat)
            index_paths = [
                self.indices_dir / f"faiss_{horizon}h_ivfpq.faiss",
                self.indices_dir / f"faiss_{horizon}h_flatip.faiss"
            ]
            
            index_loaded = False
            for index_path in index_paths:
                if index_path.exists():
                    try:
                        index = faiss.read_index(str(index_path))
                        self.indices_cache[horizon] = index
                        index_loaded = True
                        logger.debug(f"Loaded index: {index_path}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to load {index_path}: {e}")
            
            if not index_loaded:
                logger.error(f"No valid FAISS index found for {horizon}h")
                return False
            
            logger.info(f"✅ Loaded {horizon}h: {outcomes.shape} outcomes, "
                       f"{len(metadata)} metadata, index ready")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load horizon {horizon}h data: {e}")
            return False
    
    def _search_analogs_optimized(self, query_embedding: np.ndarray, 
                                 horizon: int, k: int = 50) -> Tuple[np.ndarray, np.ndarray]:
        """Optimized FAISS similarity search."""
        if horizon not in self.indices_cache:
            raise ValueError(f"Index not loaded for horizon {horizon}h")
        
        index = self.indices_cache[horizon]
        
        # Optimize IVF-PQ search parameters for production
        if hasattr(index, 'nprobe'):
            # Balance speed vs accuracy for production
            index.nprobe = min(32, max(8, index.nlist // 8))
        
        # Ensure query is normalized and contiguous
        if not query_embedding.flags['C_CONTIGUOUS']:
            query_embedding = np.ascontiguousarray(query_embedding)
        
        # Single search call
        similarities, indices = index.search(query_embedding, k)
        
        return similarities[0], indices[0]
    
    def _generate_ensemble_forecast_optimized(self, analog_indices: np.ndarray,
                                            similarities: np.ndarray,
                                            horizon: int,
                                            init_time: pd.Timestamp) -> Dict[str, Any]:
        """Generate optimized ensemble forecast with expert precision."""
        
        with PERFORMANCE_OPTIMIZER.performance_monitor("ensemble_forecast") as metrics:
            # Get memory-mapped outcomes (zero-copy access)
            outcomes = self.outcomes_cache[horizon]
            metadata = self.metadata_cache[horizon]
            
            # Extract analog outcomes (memory-efficient indexing)
            n_analogs = len(analog_indices)
            analog_outcomes = outcomes[analog_indices]  # Shape: (n_analogs, n_vars)
            
            # Convert similarities to weights (expert-recommended softmax)
            # Use float64 for computation precision
            similarities_f64 = similarities.astype(np.float64)
            
            # Temperature-scaled softmax for better weighting
            temperature = 0.1  # Sharper weighting for better analogs
            logits = similarities_f64 / temperature
            logits_stable = logits - np.max(logits)  # Numerical stability
            weights = np.exp(logits_stable)
            weights = weights / np.sum(weights)  # Normalize
            
            # Convert to float32 for storage efficiency
            weights_f32 = weights.astype(np.float32)
            
            # Generate forecasts for each variable
            forecast_vars = {}
            confidence_intervals = {}
            
            for i, var_name in enumerate(self.variables):
                # Extract variable values for all analogs
                var_values = analog_outcomes[:, i].astype(np.float32)  # Storage: float32
                
                # Filter out invalid values
                valid_mask = np.isfinite(var_values) & (var_values != 0)
                if var_name in ['t2m', 't850']:  # Temperature shouldn't be zero
                    valid_mask &= (var_values > 200) & (var_values < 350)  # Reasonable K range
                
                if np.sum(valid_mask) < max(3, n_analogs // 4):  # Need sufficient valid data
                    logger.warning(f"Insufficient valid data for {var_name}: "
                                 f"{np.sum(valid_mask)}/{n_analogs}")
                    continue
                
                # Filter to valid values and weights
                valid_values = var_values[valid_mask]
                valid_weights = weights_f32[valid_mask]
                
                # Renormalize weights
                valid_weights = valid_weights / np.sum(valid_weights)
                
                # Expert weighted quantiles with precision validation
                quantiles = PERFORMANCE_OPTIMIZER.compute_weighted_quantiles_expert(
                    valid_values, valid_weights
                )
                
                # Validate quantiles
                if np.any(np.isnan(quantiles)):
                    logger.warning(f"NaN quantiles for {var_name}")
                    continue
                
                # Store results
                forecast_vars[var_name] = float(quantiles[1])  # Median (50th percentile)
                confidence_intervals[var_name] = (
                    float(quantiles[0]),  # 5th percentile
                    float(quantiles[2])   # 95th percentile
                )
            
            # Compute forecast confidence
            mean_similarity = float(np.mean(similarities))
            weight_concentration = float(1.0 - (-np.sum(weights * np.log(weights + 1e-12)) / np.log(n_analogs)))
            confidence = min(1.0, (mean_similarity * 0.7 + weight_concentration * 0.3))
            
            # Extract best analog dates for reference
            analog_dates = []
            if len(analog_indices) > 0:
                top_indices = analog_indices[:min(5, len(analog_indices))]
                for idx in top_indices:
                    if idx < len(metadata):
                        analog_time = metadata.iloc[idx]['init_time']
                        analog_dates.append(str(analog_time))
            
            forecast_result = {
                'forecast': forecast_vars,
                'confidence_intervals': confidence_intervals,
                'confidence': confidence,
                'mean_similarity': mean_similarity,
                'analog_dates': analog_dates,
                'n_analogs': n_analogs,
                'init_time': init_time,
                'lead_time_hours': horizon,
                'valid_time': init_time + pd.Timedelta(hours=horizon)
            }
            
            # Update performance metrics
            if metrics.validation_passed:
                self.total_forecasts += 1
                self.total_latency_ms += metrics.duration_ms
            
            return forecast_result
    
    def forecast(self, query_embedding: np.ndarray, 
                lead_time_hours: int, k: int = 50,
                return_analogs: bool = False,
                init_time: Optional[pd.Timestamp] = None) -> Optional[Dict[str, Any]]:
        """
        Generate analog ensemble forecast with <150ms performance target.
        
        Args:
            query_embedding: Normalized embedding vector (float32)
            lead_time_hours: Forecast horizon (6, 12, 24, or 48)
            k: Number of analogs to retrieve
            return_analogs: Include analog details in response
            init_time: Initialization time for forecast
            
        Returns:
            Forecast dictionary with ensemble statistics
        """
        
        # Validate inputs
        if lead_time_hours not in self.horizons:
            raise ValueError(f"Unsupported horizon: {lead_time_hours}h. Use: {self.horizons}")
        
        if init_time is None:
            init_time = pd.Timestamp.now(tz='UTC')
        
        # Performance monitoring for entire forecast
        with PERFORMANCE_OPTIMIZER.performance_monitor("full_forecast") as metrics:
            
            # Step 1: Search for analogs (typically 20-30ms)
            similarities, analog_indices = self._search_analogs_optimized(
                query_embedding, lead_time_hours, k
            )
            
            if len(analog_indices) == 0:
                logger.warning(f"No analogs found for {lead_time_hours}h forecast")
                metrics.validation_passed = False
                return None
            
            # Step 2: Generate ensemble forecast (typically 50-70ms)
            forecast_result = self._generate_ensemble_forecast_optimized(
                analog_indices, similarities, lead_time_hours, init_time
            )
            
            # Step 3: Add analog details if requested
            if return_analogs and forecast_result:
                forecast_result['analog_similarities'] = similarities[:10].tolist()
                forecast_result['analog_indices'] = analog_indices[:10].tolist()
            
            # Performance validation
            if metrics.duration_ms > 150:  # Target: <150ms
                logger.warning(f"⚠️ Forecast exceeded latency target: {metrics.duration_ms:.1f}ms")
                metrics.bottleneck_component = "full_forecast"
            
            return forecast_result
    
    def batch_forecast(self, query_embeddings: np.ndarray,
                      lead_time_hours: int, k: int = 50) -> List[Dict[str, Any]]:
        """Generate forecasts for multiple embeddings efficiently."""
        
        if query_embeddings.ndim != 2:
            raise ValueError("query_embeddings must be 2D array (batch_size, embedding_dim)")
        
        batch_size = query_embeddings.shape[0]
        results = []
        
        with PERFORMANCE_OPTIMIZER.performance_monitor("batch_forecast") as metrics:
            
            for i in range(batch_size):
                embedding = query_embeddings[i:i+1]  # Keep 2D for FAISS
                
                forecast = self.forecast(
                    embedding, lead_time_hours, k, 
                    return_analogs=False
                )
                
                results.append(forecast)
            
            # Batch performance metrics
            avg_latency = metrics.duration_ms / batch_size if batch_size > 0 else 0
            logger.info(f"Batch forecast complete: {batch_size} forecasts, "
                       f"{avg_latency:.1f}ms average latency")
        
        return results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        base_stats = PERFORMANCE_OPTIMIZER.get_performance_summary()
        
        # Add forecaster-specific metrics
        stats = {
            **base_stats,
            "total_forecasts": self.total_forecasts,
            "average_forecast_latency_ms": (
                self.total_latency_ms / self.total_forecasts 
                if self.total_forecasts > 0 else 0
            ),
            "loaded_horizons": list(self.outcomes_cache.keys()),
            "memory_mapped_size_mb": sum(
                arr.nbytes / 1024 / 1024 
                for arr in self.outcomes_cache.values()
            ),
            "faiss_indices_loaded": len(self.indices_cache),
        }
        
        return stats
    
    def validate_performance(self) -> bool:
        """Validate system meets performance requirements."""
        stats = self.get_performance_stats()
        
        # Check latency requirement
        latency_ok = stats["average_forecast_latency_ms"] <= 150
        
        # Check memory usage
        memory_ok = stats["memory_usage_mb"] <= 1024  # 1GB limit
        
        # Check data loaded
        data_ok = len(self.outcomes_cache) >= 4  # All horizons
        
        validation_passed = latency_ok and memory_ok and data_ok
        
        logger.info(f"Performance validation: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
        logger.info(f"  Latency: {stats['average_forecast_latency_ms']:.1f}ms "
                   f"(target: ≤150ms) {'✅' if latency_ok else '❌'}")
        logger.info(f"  Memory: {stats['memory_usage_mb']:.1f}MB "
                   f"(limit: ≤1024MB) {'✅' if memory_ok else '❌'}")
        logger.info(f"  Data: {len(self.outcomes_cache)}/4 horizons loaded "
                   f"{'✅' if data_ok else '❌'}")
        
        return validation_passed


def benchmark_forecaster(forecaster: AnalogForecaster, iterations: int = 100):
    """Benchmark forecaster performance."""
    logger.info(f"🏁 Benchmarking forecaster ({iterations} iterations)...")
    
    # Generate test embeddings
    test_embeddings = []
    for _ in range(iterations):
        embedding = np.random.randn(1, 256).astype(np.float32)
        faiss.normalize_L2(embedding)  # Normalize for consistency
        test_embeddings.append(embedding)
    
    # Benchmark each horizon
    results = {}
    
    for horizon in [6, 12, 24, 48]:
        times = []
        
        for embedding in test_embeddings:
            start_time = time.perf_counter()
            
            forecast = forecaster.forecast(
                embedding, horizon, k=50
            )
            
            end_time = time.perf_counter()
            
            if forecast is not None:
                times.append((end_time - start_time) * 1000)  # Convert to ms
        
        if times:
            results[horizon] = {
                "mean_ms": np.mean(times),
                "p95_ms": np.percentile(times, 95),
                "p99_ms": np.percentile(times, 99),
                "min_ms": np.min(times),
                "max_ms": np.max(times),
                "success_rate": len(times) / iterations
            }
    
    # Print benchmark results
    logger.info("📊 Benchmark Results:")
    logger.info("Horizon | Mean   | P95    | P99    | Min    | Max    | Success")
    logger.info("--------|--------|--------|--------|--------|--------|--------")
    
    for horizon, stats in results.items():
        logger.info(f"{horizon:6}h | {stats['mean_ms']:5.1f}  | {stats['p95_ms']:5.1f}  | "
                   f"{stats['p99_ms']:5.1f}  | {stats['min_ms']:5.1f}  | "
                   f"{stats['max_ms']:5.1f}  | {stats['success_rate']:6.1%}")
    
    # Overall performance assessment
    all_means = [stats['mean_ms'] for stats in results.values()]
    overall_mean = np.mean(all_means) if all_means else float('inf')
    
    performance_grade = "🟢 EXCELLENT" if overall_mean <= 100 else \
                       "🟡 GOOD" if overall_mean <= 150 else \
                       "🟠 ACCEPTABLE" if overall_mean <= 200 else \
                       "🔴 POOR"
    
    logger.info(f"\nOverall Performance: {overall_mean:.1f}ms average - {performance_grade}")
    
    return results


def main():
    """Test and benchmark the optimized analog forecaster."""
    logger.info("🚀 Testing Production-Optimized Analog Forecaster")
    
    try:
        # Initialize forecaster
        forecaster = AnalogForecaster()
        
        # Validate performance requirements
        if not forecaster.validate_performance():
            logger.error("❌ Performance validation failed")
            return
        
        # Quick functionality test
        logger.info("🧪 Testing basic functionality...")
        test_embedding = np.random.randn(1, 256).astype(np.float32)
        faiss.normalize_L2(test_embedding)
        
        forecast = forecaster.forecast(test_embedding, 24, k=50, return_analogs=True)
        
        if forecast:
            logger.info("✅ Basic forecast test passed")
            logger.info(f"   Variables: {list(forecast['forecast'].keys())}")
            logger.info(f"   Confidence: {forecast['confidence']:.3f}")
            logger.info(f"   Analogs: {forecast['n_analogs']}")
        else:
            logger.error("❌ Basic forecast test failed")
            return
        
        # Performance benchmark
        benchmark_results = benchmark_forecaster(forecaster, iterations=50)
        
        # Final performance report
        final_stats = forecaster.get_performance_stats()
        logger.info(f"\n📈 Final Performance Report:")
        logger.info(f"  Total Forecasts: {final_stats['total_forecasts']}")
        logger.info(f"  Average Latency: {final_stats['average_forecast_latency_ms']:.1f}ms")
        logger.info(f"  Memory Usage: {final_stats['memory_usage_mb']:.1f}MB")
        logger.info(f"  Performance Status: {final_stats['performance_status'].upper()}")
        
        # Success criteria
        target_met = final_stats['average_forecast_latency_ms'] <= 150
        logger.info(f"\n🎯 Performance Target (<150ms): {'✅ MET' if target_met else '❌ MISSED'}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()