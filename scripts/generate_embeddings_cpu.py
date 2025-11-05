#!/usr/bin/env python3
"""
Adelaide Weather Forecasting: CPU-Optimized Embedding Generation
==============================================================

Generates embeddings using CPU with optimized batching and threading.
Much more practical than A100 for this model size.

Usage:
    python generate_embeddings_cpu.py --config configs/model.yaml --output embeddings/
"""

import os
import sys
import argparse
import time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import xarray as xr
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
from multiprocessing import Pool, cpu_count

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from models.cnn_encoder import WeatherCNNEncoder as CNNEncoder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mock class for loading checkpoint (needed for model loading)
class ProductionTrainingConfig:
    """Mock config class for checkpoint loading"""
    pass

class CPUEmbeddingGenerator:
    """CPU-optimized embedding generator for weather analog retrieval."""
    
    def __init__(self, model_path: str, config_path: str, num_threads: Optional[int] = None):
        """Initialize CPU embedding generator.
        
        Args:
            model_path: Path to trained model weights
            config_path: Path to model configuration  
            num_threads: Number of CPU threads (default: all cores)
        """
        # Set CPU threading
        if num_threads is None:
            num_threads = cpu_count()
        torch.set_num_threads(num_threads)
        logger.info(f"Using {num_threads} CPU threads")
        
        self.device = 'cpu'
        self.lead_times = [6, 12, 24, 48]  # Hours
        
        # Load trained model
        logger.info(f"Loading model from {model_path}")
        self.model = CNNEncoder(config_path=config_path)
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        logger.info("✅ Model loaded for CPU inference")
        
        # Load normalization statistics
        if 'norm_stats' in checkpoint:
            self.norm_stats = checkpoint['norm_stats']
            logger.info("✅ Normalization statistics loaded")
        else:
            logger.warning("⚠️ No normalization stats in checkpoint")
            self.norm_stats = None
            
        # Load ERA5 data
        self._load_era5_data()
        
    def _load_era5_data(self):
        """Load and preprocess ERA5 data."""
        logger.info("Loading ERA5 data...")
        
        try:
            # Load surface data (MSL pressure)
            surface_path = "data/era5/zarr/era5_surface_2010_2020.zarr"
            self.surface_ds = xr.open_zarr(surface_path, chunks={'time': 50})
            logger.info(f"Surface data shape: {self.surface_ds.dims}")
            
            # Load pressure level data  
            pressure_path = "data/era5/zarr/era5_pressure_2010_2019.zarr"
            self.pressure_ds = xr.open_zarr(pressure_path, chunks={'time': 50})
            logger.info(f"Pressure data shape: {self.pressure_ds.dims}")
            
            # Slice to Adelaide region
            self.surface_ds = self.surface_ds.sel(
                latitude=slice(-33, -37),
                longitude=slice(137, 141)
            )
            self.pressure_ds = self.pressure_ds.sel(
                latitude=slice(-33, -37),
                longitude=slice(137, 141),
                isobaricInhPa=[500, 850]
            )
            
            logger.info(f"✅ ERA5 data loaded - Adelaide region sliced")
            logger.info(f"Surface grid: {self.surface_ds.latitude.size} x {self.surface_ds.longitude.size}")
            logger.info(f"Time range: {self.surface_ds.time.min().values} to {self.surface_ds.time.max().values}")
            
        except Exception as e:
            logger.error(f"Failed to load ERA5 data: {e}")
            raise
            
    def _normalize_variables(self, weather_array: np.ndarray) -> np.ndarray:
        """Apply per-variable normalization."""
        if self.norm_stats is None:
            return weather_array
            
        # Apply normalization per channel
        normalized = weather_array.copy()
        for i in range(weather_array.shape[-1]):
            var_name = f'var_{i}'
            if var_name in self.norm_stats:
                mean = self.norm_stats[var_name]['mean']
                std = self.norm_stats[var_name]['std']
                normalized[..., i] = (normalized[..., i] - mean) / (std + 1e-8)
                
        return normalized
        
    def _extract_weather_data(self, time_val: pd.Timestamp) -> Optional[np.ndarray]:
        """Extract weather data for a specific timestamp."""
        try:
            # Extract surface variables (MSL pressure)
            surface_data = self.surface_ds.sel(time=time_val, method='nearest')
            msl_data = surface_data['msl'].values
            
            # Extract pressure level variables
            pressure_data = self.pressure_ds.sel(time=time_val, method='nearest')
            
            # Variables: z, t, u, v at 500 and 850 hPa
            all_arrays = []
            
            # Surface MSL pressure
            if msl_data.shape == (16, 16):
                # Resize to 21x21 to match model input
                msl_resized = np.resize(msl_data, (21, 21))
                all_arrays.append(msl_resized)
            else:
                return None
                
            # Pressure level variables
            pressure_vars = ['z', 't', 'u', 'v']
            for var in pressure_vars:
                for level in [500, 850]:
                    try:
                        var_data = pressure_data[var].sel(isobaricInhPa=level).values
                        if var_data.shape == (16, 16):
                            var_resized = np.resize(var_data, (21, 21))
                            all_arrays.append(var_resized)
                        else:
                            return None
                    except KeyError:
                        return None
                        
            # Stack to create input array (21, 21, 9)
            if len(all_arrays) == 9:  # 1 surface + 8 pressure level
                weather_array = np.stack(all_arrays, axis=-1)
                return self._normalize_variables(weather_array)
            else:
                return None
                
        except Exception as e:
            return None
            
    def generate_embeddings_for_horizon(self, lead_time: int, batch_size: int = 16) -> Tuple[np.ndarray, pd.DataFrame]:
        """Generate embeddings for a specific forecast horizon.
        
        Args:
            lead_time: Forecast lead time in hours
            batch_size: Batch size for CPU inference (smaller for memory)
            
        Returns:
            embeddings: (N, 256) normalized embeddings
            metadata: DataFrame with timestamps and target information
        """
        logger.info(f"🚀 Generating embeddings for {lead_time}h horizon (CPU)")
        
        # Get all available timestamps
        times = pd.to_datetime(self.surface_ds.time.values)
        logger.info(f"Processing {len(times)} timestamps")
        
        embeddings_list = []
        metadata_list = []
        
        # Process in smaller batches for CPU
        for i in range(0, len(times), batch_size):
            batch_times = times[i:i+batch_size]
            batch_data = []
            batch_metadata = []
            
            # Prepare batch data
            for time_val in batch_times:
                weather_array = self._extract_weather_data(time_val)
                if weather_array is not None:
                    batch_data.append(weather_array)
                    
                    # Generate metadata
                    time_dt = time_val.to_pydatetime()
                    valid_time = time_dt + timedelta(hours=lead_time)
                    
                    metadata = {
                        'init_time': time_val,
                        'lead_time': lead_time,
                        'valid_time': valid_time,
                        'month': time_dt.month - 1,  # 0-11 for embedding
                        'hour': time_dt.hour,
                        'day_of_year': time_dt.timetuple().tm_yday,
                        'season': (time_dt.month - 1) // 3  # 0-3 for seasons
                    }
                    batch_metadata.append(metadata)
                    
            if not batch_data:
                continue
                
            # Convert to tensor and generate embeddings
            with torch.no_grad():
                # Stack weather data
                weather_tensor = torch.from_numpy(np.stack(batch_data)).float()
                weather_tensor = weather_tensor.permute(0, 3, 1, 2)  # BHWC -> BCHW
                
                # Generate conditioning variables
                batch_len = len(batch_data)
                lead_times_tensor = torch.full((batch_len,), lead_time)
                months_tensor = torch.tensor([m['month'] for m in batch_metadata])
                hours_tensor = torch.tensor([m['hour'] for m in batch_metadata])
                
                # Generate embeddings (CPU inference)
                embeddings = self.model(weather_tensor, lead_times_tensor, months_tensor, hours_tensor)
                    
                # L2 normalize embeddings
                embeddings = F.normalize(embeddings, p=2, dim=1)
                embeddings_cpu = embeddings.numpy().astype(np.float32)
                
            embeddings_list.append(embeddings_cpu)
            metadata_list.extend(batch_metadata)
            
            if (i // batch_size + 1) % 100 == 0:
                logger.info(f"Processed {i + len(batch_times)}/{len(times)} timestamps")
                
        # Combine all embeddings
        all_embeddings = np.vstack(embeddings_list)
        metadata_df = pd.DataFrame(metadata_list)
        
        logger.info(f"✅ Generated {all_embeddings.shape[0]} embeddings for {lead_time}h")
        logger.info(f"Embedding shape: {all_embeddings.shape}")
        
        return all_embeddings, metadata_df
        
    def save_embeddings(self, embeddings: np.ndarray, metadata: pd.DataFrame, 
                       output_dir: Path, lead_time: int):
        """Save embeddings and metadata to disk."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save embeddings
        emb_path = output_dir / f"embeddings_{lead_time}h.npy"
        np.save(emb_path, embeddings)
        logger.info(f"💾 Saved embeddings to {emb_path}")
        
        # Save metadata
        meta_path = output_dir / f"metadata_{lead_time}h.parquet"
        metadata.to_parquet(meta_path, index=False)
        logger.info(f"💾 Saved metadata to {meta_path}")
        
    def generate_all_embeddings(self, output_dir: str, batch_size: int = 16):
        """Generate embeddings for all forecast horizons."""
        output_path = Path(output_dir)
        
        logger.info(f"🎯 Starting CPU embedding generation for all horizons")
        logger.info(f"Output directory: {output_path}")
        logger.info(f"Forecast horizons: {self.lead_times}")
        
        total_start = time.time()
        
        for lead_time in self.lead_times:
            horizon_start = time.time()
            
            embeddings, metadata = self.generate_embeddings_for_horizon(lead_time, batch_size)
            self.save_embeddings(embeddings, metadata, output_path, lead_time)
            
            horizon_time = time.time() - horizon_start
            logger.info(f"⏱️ {lead_time}h horizon completed in {horizon_time:.1f}s")
            
        total_time = time.time() - total_start
        logger.info(f"🎉 All embeddings generated in {total_time:.1f}s")

def main():
    parser = argparse.ArgumentParser(description='Generate embeddings for weather forecasting (CPU)')
    parser.add_argument('--model', default='outputs/training_production_20251021_162407/best_model.pt',
                       help='Path to trained model')
    parser.add_argument('--config', default='configs/model.yaml',
                       help='Path to model config')
    parser.add_argument('--output', default='embeddings/',
                       help='Output directory')
    parser.add_argument('--batch-size', type=int, default=16,
                       help='Batch size for CPU inference')
    parser.add_argument('--threads', type=int, default=None,
                       help='Number of CPU threads')
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = CPUEmbeddingGenerator(
        model_path=args.model,
        config_path=args.config,
        num_threads=args.threads
    )
    
    # Generate all embeddings
    generator.generate_all_embeddings(
        output_dir=args.output,
        batch_size=args.batch_size
    )
    
    logger.info("🎉 CPU embedding generation completed!")

if __name__ == "__main__":
    main()