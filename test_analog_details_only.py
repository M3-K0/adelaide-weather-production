#!/usr/bin/env python3
"""
Test Analog Details API Only
============================

Focus specifically on the analog_details_api that's still failing.
"""

import asyncio
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timezone
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from api.services.analog_search import AnalogSearchService, AnalogSearchConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_analog_details_api():
    """Test the analog details API specifically."""
    logger.info("🔍 Testing Analog Details API")
    
    # Initialize service
    config = AnalogSearchConfig()
    service = AnalogSearchService(config)
    await service.initialize()
    
    try:
        query_time = datetime.now(timezone.utc)
        
        logger.info(f"Testing analog details for {query_time}")
        
        # Test the full analog details API
        analog_details = await service.get_analog_details(
            query_time=query_time,
            horizon=24,
            variable="temperature",
            k=5,
            correlation_id="test-details"
        )
        
        logger.info(f"Analog details result keys: {list(analog_details.keys())}")
        logger.info(f"Success: {analog_details.get('success', 'NOT FOUND')}")
        
        if not analog_details.get("success", False):
            logger.error(f"❌ Analog details API failed: {analog_details.get('error', 'Unknown error')}")
            return False
        
        # Check for required sections
        required_sections = ["analogs", "search_metadata", "timeline_data", "similarity_analysis", "meteorological_context"]
        missing_sections = []
        for section in required_sections:
            if section not in analog_details:
                missing_sections.append(section)
                logger.error(f"❌ Missing required section: {section}")
        
        if missing_sections:
            logger.error(f"❌ Missing sections: {missing_sections}")
            return False
        
        # Validate analog data contains real historical information
        analogs = analog_details["analogs"]
        logger.info(f"Found {len(analogs)} analogs")
        
        if len(analogs) == 0:
            logger.error("❌ No analogs returned in details API")
            return False
        
        # Check first analog for realistic data
        first_analog = analogs[0]
        logger.info(f"First analog keys: {list(first_analog.keys())}")
        
        required_analog_fields = ["rank", "analog_index", "historical_date", "similarity_score", "distance"]
        missing_fields = []
        for field in required_analog_fields:
            if field not in first_analog:
                missing_fields.append(field)
                logger.error(f"❌ Missing analog field: {field}")
        
        if missing_fields:
            logger.error(f"❌ Missing analog fields: {missing_fields}")
            return False
        
        # Validate similarity scores are realistic
        similarity = first_analog["similarity_score"]
        distance = first_analog["distance"]
        logger.info(f"First analog: similarity={similarity}, distance={distance}")
        
        if not (0.0 <= similarity <= 1.0):
            logger.error(f"❌ Invalid similarity score: {similarity}")
            return False
        
        # Check FAISS search metadata
        search_metadata = analog_details["search_metadata"]
        search_method = search_metadata.get("search_method", "unknown")
        logger.info(f"Search method: {search_method}")
        
        if search_method == "fallback_mock":
            logger.warning("⚠️ Analog details using fallback mock instead of real FAISS")
            return False
        
        logger.info("✅ Analog details API working correctly!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Analog details API validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await service.shutdown()

if __name__ == "__main__":
    success = asyncio.run(test_analog_details_api())
    exit(0 if success else 1)