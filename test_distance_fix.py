#!/usr/bin/env python3
"""
Test Distance Calculation Fix
============================

Test the corrected distance calculation to ensure realistic distance values.
"""

import asyncio
import numpy as np
import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from api.services.analog_search import AnalogSearchService, AnalogSearchConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_distance_fix():
    """Test that the distance calculation fix works correctly."""
    logger.info("🧪 Testing Distance Calculation Fix")
    
    # Initialize service
    config = AnalogSearchConfig()
    service = AnalogSearchService(config)
    await service.initialize()
    
    try:
        from datetime import datetime, timezone
        query_time = datetime.now(timezone.utc)
        
        # Test multiple horizons
        for horizon in [6, 12, 24, 48]:
            logger.info(f"\n--- Testing {horizon}h horizon ---")
            
            search_result = await service.search_analogs(
                query_time=query_time,
                horizon=horizon,
                k=10,
                correlation_id=f"distance-fix-test-{horizon}h"
            )
            
            if search_result.success:
                distances = search_result.distances
                logger.info(f"✅ Search successful")
                logger.info(f"   Distances: {distances}")
                logger.info(f"   Range: {np.min(distances):.4f} to {np.max(distances):.4f}")
                logger.info(f"   Mean: {np.mean(distances):.4f}, Std: {np.std(distances):.4f}")
                
                # Check for realistic distance values
                if np.all(distances > 1e-6):  # Not zero
                    logger.info(f"   ✅ No zero distances")
                else:
                    logger.error(f"   ❌ Still has zero distances")
                
                if np.all(distances < 10.0):  # Reasonable upper bound
                    logger.info(f"   ✅ Distances in reasonable range")
                else:
                    logger.warning(f"   ⚠️ Some distances > 10.0")
                
                # Check monotonicity (distances should be sorted)
                if np.all(distances[:-1] <= distances[1:] + 1e-6):
                    logger.info(f"   ✅ Distances properly sorted")
                else:
                    logger.warning(f"   ⚠️ Distance ordering violation")
                    
            else:
                logger.error(f"❌ Search failed: {search_result.error_message}")
        
        logger.info("\n🎉 Distance calculation fix testing completed!")
        
    finally:
        await service.shutdown()

if __name__ == "__main__":
    asyncio.run(test_distance_fix())