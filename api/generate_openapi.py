#!/usr/bin/env python3
"""
OpenAPI Schema Generator
=======================

Generates OpenAPI schema from FastAPI application for TypeScript type generation.

Usage:
    python generate_openapi.py
    
Output:
    - openapi.json: Complete OpenAPI schema
    - Used by frontend for TypeScript type generation
"""

import json
import sys
import os

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

def generate_openapi_schema():
    """Generate and save OpenAPI schema."""
    try:
        # Get OpenAPI schema from FastAPI app
        schema = app.openapi()
        
        # Enhance schema with additional metadata
        schema["info"]["x-api-version"] = "1.0.0"
        schema["info"]["x-generated-at"] = "2025-01-25T23:30:00Z"
        schema["info"]["x-system"] = "Adelaide Weather Forecasting System"
        
        # Save to file
        output_path = os.path.join(os.path.dirname(__file__), "openapi.json")
        with open(output_path, "w") as f:
            json.dump(schema, f, indent=2)
            
        print(f"✅ OpenAPI schema generated: {output_path}")
        print(f"📋 Endpoints: {len(schema.get('paths', {}))}")
        print(f"🔧 Components: {len(schema.get('components', {}).get('schemas', {}))}")
        
        # Also save to frontend directory for type generation
        frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "openapi.json")
        os.makedirs(os.path.dirname(frontend_path), exist_ok=True)
        with open(frontend_path, "w") as f:
            json.dump(schema, f, indent=2)
            
        print(f"✅ Schema copied to frontend: {frontend_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate OpenAPI schema: {e}")
        return False

if __name__ == "__main__":
    success = generate_openapi_schema()
    sys.exit(0 if success else 1)