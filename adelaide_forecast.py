#!/usr/bin/env python3
"""
Adelaide Weather Forecast CLI
============================

Minimal operational forecasting system using analog ensemble method.
Implements compact real-time pipeline: API → Embedding → FAISS → Forecast

Usage:
    python adelaide_forecast.py forecast
    python adelaide_forecast.py forecast --horizons 24 --format json
    python adelaide_forecast.py validate
"""

import sys
import time
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdelaideForecaster:
    """Minimal operational forecasting system."""
    
    def __init__(self):
        self.weather_client = None
        self.embedder = None
        self.forecaster = None
        self.performance_stats = {}
        
    def _initialize_components(self):
        """Initialize forecasting components."""
        try:
            # Import components
            from scripts.weather_api_client import WeatherApiClient
            from core.real_time_embedder import RealTimeEmbedder
            from scripts.analog_forecaster import AnalogForecaster
            
            logger.info("🌤️ Initializing Adelaide Forecast System...")
            
            # Initialize components
            start_time = time.time()
            self.weather_client = WeatherApiClient()
            self.embedder = RealTimeEmbedder()
            self.forecaster = AnalogForecaster()
            
            init_time = time.time() - start_time
            logger.info(f"✅ System initialized in {init_time:.1f}s")
            self.performance_stats['init_time'] = init_time
            
            return True
            
        except ImportError as e:
            logger.error(f"❌ Component import failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False
    
    def get_current_weather(self) -> Optional[Dict]:
        """Get current weather in ERA5 format."""
        logger.info("📡 Fetching current weather data...")
        
        start_time = time.time()
        
        # Get current weather
        current_weather = self.weather_client.get_current_weather()
        if not current_weather:
            logger.error("❌ Failed to get current weather")
            return None
        
        # Convert to ERA5 format
        era5_data = self.weather_client.convert_to_era5_format(current_weather)
        if not era5_data:
            logger.error("❌ Failed to convert to ERA5 format")
            return None
        
        # Validate data quality
        if not self.weather_client.validate_data_quality(era5_data):
            logger.error("❌ Data quality validation failed")
            return None
        
        fetch_time = time.time() - start_time
        self.performance_stats['fetch_time'] = fetch_time
        
        logger.info(f"✅ Weather data acquired in {fetch_time:.1f}s")
        logger.info(f"   Source: {era5_data['source']}")
        logger.info(f"   Completeness: {era5_data.get('data_completeness', 'unknown')}")
        
        return era5_data
    
    def generate_forecast(self, era5_data: Dict, horizons: List[int] = [24]) -> Optional[Dict]:
        """Generate analog ensemble forecast."""
        logger.info(f"🧠 Generating forecast for horizons: {horizons}h")
        
        start_time = time.time()
        
        try:
            # Generate embeddings
            embeddings = self.embedder.generate_batch(era5_data, horizons)
            if embeddings is None:
                logger.error("❌ Embedding generation failed")
                return None
            
            # Generate forecasts for each horizon
            forecasts = {}
            total_analogs = 0
            
            for i, horizon in enumerate(horizons):
                embedding = embeddings[i:i+1]  # Single embedding for this horizon
                
                # Run analog forecast
                forecast_result = self.forecaster.forecast(
                    query_embedding=embedding,
                    lead_time_hours=horizon,
                    k=50,
                    return_analogs=True
                )
                
                if forecast_result:
                    forecasts[f"{horizon}h"] = forecast_result
                    total_analogs += len(forecast_result.get('analog_dates', []))
                    
                    # Log basic forecast info
                    mean_sim = forecast_result.get('mean_similarity', 0)
                    logger.info(f"   H+{horizon}h: {len(forecast_result.get('analog_dates', []))} analogs, "
                              f"similarity {mean_sim:.3f}")
            
            forecast_time = time.time() - start_time
            self.performance_stats['forecast_time'] = forecast_time
            self.performance_stats['embedding_time'] = self.embedder.get_timing_stats().get('total_ms', 0) / 1000
            
            logger.info(f"✅ Forecast complete in {forecast_time:.1f}s ({total_analogs} total analogs)")
            
            return {
                'forecasts': forecasts,
                'performance': self.performance_stats,
                'metadata': {
                    'generated_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
                    'location': 'Adelaide, Australia',
                    'coordinates': [-34.9285, 138.6007],
                    'horizons': horizons
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Forecast generation failed: {e}")
            return None
    
    def format_forecast_text(self, forecast_data: Dict) -> str:
        """Format forecast for text output."""
        lines = []
        lines.append("Adelaide Weather Forecast")
        lines.append("=" * 50)
        lines.append(f"Generated: {forecast_data['metadata']['generated_at']}")
        lines.append("")
        
        # Performance summary
        perf = forecast_data['performance']
        total_time = perf.get('fetch_time', 0) + perf.get('forecast_time', 0)
        lines.append(f"⚡ Performance: {total_time:.1f}s total "
                    f"(fetch: {perf.get('fetch_time', 0):.1f}s, "
                    f"forecast: {perf.get('forecast_time', 0):.1f}s)")
        lines.append("")
        
        # Forecasts
        for horizon_key, forecast in forecast_data['forecasts'].items():
            lines.append(f"🔮 {horizon_key.upper()} Forecast:")
            
            # Extract forecast values
            forecast_vars = forecast.get('forecast', {})
            mean_sim = forecast.get('mean_similarity', 0)
            num_analogs = len(forecast.get('analog_dates', []))
            
            lines.append(f"   Analogs: {num_analogs} patterns (similarity: {mean_sim:.3f})")
            
            # Temperature
            if 't2m' in forecast_vars:
                t2m_k = forecast_vars['t2m']
                t2m_c = t2m_k - 273.15 if t2m_k else None
                if t2m_c:
                    lines.append(f"   Temperature: {t2m_c:.1f}°C")
            
            # Pressure  
            if 'msl' in forecast_vars:
                msl_pa = forecast_vars['msl']
                msl_hpa = msl_pa / 100 if msl_pa else None
                if msl_hpa:
                    lines.append(f"   Pressure: {msl_hpa:.1f} hPa")
            
            # Wind
            if 'u10' in forecast_vars and 'v10' in forecast_vars:
                u10 = forecast_vars['u10']
                v10 = forecast_vars['v10']
                if u10 is not None and v10 is not None:
                    import math
                    wind_speed = math.sqrt(u10**2 + v10**2)
                    wind_dir = math.degrees(math.atan2(-u10, -v10)) % 360
                    lines.append(f"   Wind: {wind_speed:.1f} m/s @ {wind_dir:.0f}°")
            
            # Best analog
            analog_dates = forecast.get('analog_dates', [])
            if analog_dates:
                best_analog = analog_dates[0]
                lines.append(f"   Best analog: {best_analog}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def validate_system(self) -> bool:
        """Validate system components."""
        logger.info("🔍 Validating system components...")
        
        # Check if components can be initialized
        if not self._initialize_components():
            return False
        
        # Test weather data fetch
        logger.info("📡 Testing weather data fetch...")
        era5_data = self.get_current_weather()
        if not era5_data:
            return False
        
        # Test embedding generation  
        logger.info("🧠 Testing embedding generation...")
        if self.embedder.model is None:
            logger.warning("⚠️ Model not available - embedding test skipped")
        else:
            embeddings = self.embedder.generate_batch(era5_data, [24])
            if embeddings is None:
                logger.error("❌ Embedding generation test failed")
                return False
            logger.info(f"✅ Generated test embeddings: {embeddings.shape}")
        
        # Test forecaster
        logger.info("🔮 Testing analog forecaster...")
        try:
            # Use dummy embedding if model not available
            if self.embedder.model is None:
                import numpy as np
                dummy_embedding = np.random.randn(1, 256).astype(np.float32)
                dummy_embedding = dummy_embedding / np.linalg.norm(dummy_embedding)
                test_forecast = self.forecaster.forecast(dummy_embedding, 24, k=10)
            else:
                test_forecast = self.generate_forecast(era5_data, [24])
            
            if test_forecast:
                logger.info("✅ Forecaster test passed")
            else:
                logger.error("❌ Forecaster test failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Forecaster test error: {e}")
            return False
        
        logger.info("🎉 System validation PASSED")
        return True

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Adelaide Weather Forecast System")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Forecast command
    forecast_parser = subparsers.add_parser('forecast', help='Generate weather forecast')
    forecast_parser.add_argument('--horizons', nargs='+', type=int, default=[24],
                                help='Forecast horizons in hours (default: 24)')
    forecast_parser.add_argument('--format', choices=['text', 'json'], default='text',
                                help='Output format (default: text)')
    forecast_parser.add_argument('--output', type=str, help='Save to file')
    forecast_parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate system components')
    validate_parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging
    if hasattr(args, 'debug') and args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize forecaster
    forecaster = AdelaideForecaster()
    
    try:
        if args.command == 'forecast':
            # Initialize components
            if not forecaster._initialize_components():
                sys.exit(1)
            
            # Get current weather
            era5_data = forecaster.get_current_weather()
            if not era5_data:
                sys.exit(1)
            
            # Generate forecast
            forecast_data = forecaster.generate_forecast(era5_data, args.horizons)
            if not forecast_data:
                sys.exit(1)
            
            # Format output
            if args.format == 'json':
                output = json.dumps(forecast_data, indent=2)
            else:
                output = forecaster.format_forecast_text(forecast_data)
            
            # Save or print
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output)
                logger.info(f"💾 Forecast saved to {args.output}")
            else:
                print(output)
        
        elif args.command == 'validate':
            success = forecaster.validate_system()
            sys.exit(0 if success else 1)
        
        else:
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        if hasattr(args, 'debug') and args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()