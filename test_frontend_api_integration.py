#!/usr/bin/env python3
"""
Test Frontend API Integration
=============================

Test the frontend API route to ensure it properly integrates with real FAISS data.
"""

import asyncio
import requests
import json
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_frontend_api():
    """Test the frontend API integration with real FAISS."""
    logger.info("🔍 Testing Frontend API Integration with Real FAISS Data")
    
    # Test different scenarios
    test_cases = [
        {"horizon": "6h", "k": 5},
        {"horizon": "12h", "k": 10}, 
        {"horizon": "24h", "k": 5},
        {"horizon": "48h", "k": 5},
    ]
    
    for test_case in test_cases:
        horizon = test_case["horizon"]
        k = test_case["k"]
        
        logger.info(f"\n--- Testing {horizon} with k={k} ---")
        
        # Test frontend API route
        try:
            url = f"http://localhost:3000/api/analogs"
            params = {
                "horizon": horizon,
                "k": k,
                "variables": "t2m,msl"
            }
            
            logger.info(f"Making request to: {url}")
            logger.info(f"Parameters: {params}")
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Frontend API responded successfully")
                
                # Check for real analog data structure
                if "top_analogs" in data:
                    analogs = data["top_analogs"]
                    logger.info(f"   Found {len(analogs)} analogs")
                    
                    if len(analogs) > 0:
                        first_analog = analogs[0]
                        if "similarity_score" in first_analog and "distance" in first_analog:
                            similarity = first_analog["similarity_score"]
                            distance = first_analog["distance"]
                            logger.info(f"   First analog: similarity={similarity:.4f}, distance={distance:.4f}")
                            
                            # Check if we have realistic values (not synthetic)
                            if similarity > 0 and distance > 0:
                                logger.info(f"   ✅ Real similarity and distance values detected")
                            else:
                                logger.warning(f"   ⚠️ Suspicious zero values")
                        else:
                            logger.warning(f"   ⚠️ Missing similarity/distance fields")
                    else:
                        logger.warning(f"   ⚠️ No analogs returned")
                        
                    # Check search metadata
                    if "search_metadata" in data:
                        search_meta = data["search_metadata"]
                        search_method = search_meta.get("search_method", "unknown")
                        logger.info(f"   Search method: {search_method}")
                        
                        if search_method == "real_faiss":
                            logger.info(f"   ✅ Using real FAISS (not synthetic)")
                        else:
                            logger.warning(f"   ⚠️ Not using real FAISS: {search_method}")
                    else:
                        logger.warning(f"   ⚠️ No search metadata found")
                        
                else:
                    logger.error(f"   ❌ No top_analogs in response")
                    
            else:
                logger.error(f"❌ Frontend API failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️ Frontend server not running on localhost:3000")
            logger.info(f"   This is expected if frontend server isn't started")
        except requests.exceptions.Timeout:
            logger.error(f"❌ Frontend API timeout")
        except Exception as e:
            logger.error(f"❌ Frontend API test failed: {e}")
    
    logger.info("\n🎉 Frontend API integration test completed!")

if __name__ == "__main__":
    test_frontend_api()