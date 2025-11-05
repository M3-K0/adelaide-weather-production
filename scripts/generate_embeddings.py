#!/usr/bin/env python3
"""
Adelaide Weather Forecasting: Batch Embedding Generation
========================================================

Generates embeddings for all ERA5 timesteps across multiple forecast horizons
using the trained CNN encoder. Optimized for A100 GPU with mixed precision.

Usage:
    python generate_embeddings.py --config configs/model.yaml --output embeddings/
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
import dask
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from models.cnn_encoder import WeatherCNNEncoder as CNNEncoder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """Generate embeddings for weather analog retrieval system."""
    
    def __init__(self, model_path: str, config_path: str, device: str = 'cuda'):
        """Initialize embedding generator.
        
        Args:
            model_path: Path to trained model weights
            config_path: Path to model configuration
            device: Computation device
        """
        self.device = device
        self.lead_times = [6, 12, 24, 48]  # Hours
        
        # Load trained model
        logger.info(f"Loading model from {model_path}")
        self.model = CNNEncoder(config_path=config_path).to(device)
        checkpoint = torch.load(model_path, map_location=device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        # Apply A100 optimizations
        self.model = self.model.to(memory_format=torch.channels_last)
        torch.backends.cudnn.benchmark = True
        logger.info("✅ Model loaded with A100 optimizations")
        
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
            surface_path = "/workspace/data/era5/surface_2010_2020.zarr"
            self.surface_ds = xr.open_zarr(surface_path, chunks={'time': 100})
            logger.info(f"Surface data shape: {self.surface_ds.dims}")
            
            # Load pressure level data  
            pressure_path = "/workspace/data/era5/pressure_2010_2020.zarr"
            self.pressure_ds = xr.open_zarr(pressure_path, chunks={'time': 100})
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
            logger.warning("No normalization stats available")
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
                logger.warning(f"Unexpected MSL shape: {msl_data.shape}")
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
                            logger.warning(f"Unexpected {var}@{level} shape: {var_data.shape}")
                            return None
                    except KeyError:
                        logger.warning(f"Variable {var} not found at {level}hPa")
                        return None
                        
            # Stack to create input array (21, 21, 9)
            if len(all_arrays) == 9:  # 1 surface + 8 pressure level
                weather_array = np.stack(all_arrays, axis=-1)
                return self._normalize_variables(weather_array)
            else:
                logger.warning(f"Expected 9 variables, got {len(all_arrays)}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting weather data for {time_val}: {e}")
            return None
            
    def generate_embeddings_for_horizon(self, lead_time: int, batch_size: int = 32) -> Tuple[np.ndarray, pd.DataFrame]:
        """Generate embeddings for a specific forecast horizon.
        
        Args:
            lead_time: Forecast lead time in hours
            batch_size: Batch size for GPU inference
            
        Returns:
            embeddings: (N, 256) normalized embeddings
            metadata: DataFrame with timestamps and target information
        """
        logger.info(f"🚀 Generating embeddings for {lead_time}h horizon")
        
        # Get all available timestamps
        times = pd.to_datetime(self.surface_ds.time.values)
        logger.info(f"Processing {len(times)} timestamps")
        
        embeddings_list = []
        metadata_list = []
        
        # Process in batches for memory efficiency
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
                weather_tensor = weather_tensor.contiguous(memory_format=torch.channels_last)
                weather_tensor = weather_tensor.to(self.device)
                
                # Generate conditioning variables
                batch_len = len(batch_data)
                lead_times_tensor = torch.full((batch_len,), lead_time, device=self.device)
                months_tensor = torch.tensor([m['month'] for m in batch_metadata], device=self.device)
                hours_tensor = torch.tensor([m['hour'] for m in batch_metadata], device=self.device)
                
                # Generate embeddings with mixed precision
                with torch.autocast(device_type='cuda', dtype=torch.float16):
                    embeddings = self.model(weather_tensor, lead_times_tensor, months_tensor, hours_tensor)
                    
                # L2 normalize embeddings
                embeddings = F.normalize(embeddings, p=2, dim=1)
                embeddings_cpu = embeddings.cpu().numpy().astype(np.float32)
                
            embeddings_list.append(embeddings_cpu)
            metadata_list.extend(batch_metadata)
            
            if (i // batch_size + 1) % 50 == 0:
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
        
        # Save embedding statistics
        stats = {
            'count': len(embeddings),
            'dimension': embeddings.shape[1],
            'norm_mean': np.linalg.norm(embeddings, axis=1).mean(),
            'norm_std': np.linalg.norm(embeddings, axis=1).std(),
            'lead_time': lead_time,
            'generated_at': datetime.now().isoformat()
        }
        
        stats_path = output_dir / f"stats_{lead_time}h.json"
        import json
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"📊 Saved statistics to {stats_path}")
        
    def generate_all_embeddings(self, output_dir: str, batch_size: int = 32):
        """Generate embeddings for all forecast horizons."""
        output_path = Path(output_dir)
        
        logger.info(f"🎯 Starting embedding generation for all horizons")
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
        
        # Generate combined metadata file
        self._create_combined_metadata(output_path)
        
    def _create_combined_metadata(self, output_dir: Path):
        """Create combined metadata file for all horizons."""
        logger.info("📋 Creating combined metadata file...")
        
        all_metadata = []
        for lead_time in self.lead_times:
            meta_path = output_dir / f"metadata_{lead_time}h.parquet"
            if meta_path.exists():
                df = pd.read_parquet(meta_path)
                all_metadata.append(df)
                
        if all_metadata:
            combined_df = pd.concat(all_metadata, ignore_index=True)
            combined_path = output_dir / "metadata_combined.parquet"
            combined_df.to_parquet(combined_path, index=False)
            logger.info(f"💾 Combined metadata saved to {combined_path}")
            logger.info(f"Total records: {len(combined_df)}")

def main():
    parser = argparse.ArgumentParser(description='Generate embeddings for weather forecasting')
    parser.add_argument('--model', default='outputs/training_production_20251021_162407/best_model.pt',
                       help='Path to trained model')
    parser.add_argument('--config', default='configs/model.yaml',
                       help='Path to model config')
    parser.add_argument('--output', default='embeddings/',
                       help='Output directory')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='Batch size for inference')
    parser.add_argument('--device', default='cuda',
                       help='Computation device')
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = EmbeddingGenerator(
        model_path=args.model,
        config_path=args.config,
        device=args.device
    )
    
    # Generate all embeddings
    generator.generate_all_embeddings(
        output_dir=args.output,
        batch_size=args.batch_size
    )
    
    logger.info("🎉 Embedding generation completed successfully!")

if __name__ == "__main__":
    main()