#!/usr/bin/env python3
"""
Enhanced OpenAPI Schema Generator for Adelaide Weather Forecasting System
=========================================================================

Enhanced OpenAPI schema generation with CI/CD integration and comprehensive validation.
Supports automated TypeScript type generation and Pact contract testing.

Features:
- Enhanced metadata with version tracking
- Schema validation and integrity checks
- Frontend type generation integration
- CI/CD pipeline compatibility
- Error handling and reporting
- Change detection for incremental builds

Usage:
    python enhanced_openapi_generator.py [--validate] [--output-dir DIR] [--format json|yaml]
    
Environment Variables:
    CI: Set to "true" in CI environment for enhanced logging
    API_VERSION: Override API version (default: auto-detect from git)
    BUILD_ID: Build identifier for traceability
"""

import json
import yaml
import sys
import os
import hashlib
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

class OpenAPIGenerator:
    """Enhanced OpenAPI schema generator with validation and CI integration."""
    
    def __init__(self, output_dir: Optional[str] = None, format_type: str = "json"):
        self.output_dir = output_dir or os.path.dirname(__file__)
        self.format_type = format_type
        self.is_ci = os.getenv("CI", "").lower() == "true"
        self.api_version = self._detect_api_version()
        self.build_id = os.getenv("BUILD_ID", "local")
        
    def _detect_api_version(self) -> str:
        """Detect API version from environment or git."""
        # Try environment variable first
        if env_version := os.getenv("API_VERSION"):
            return env_version
            
        # Try to get from git
        try:
            import subprocess
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__)
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
            
        # Fallback to version from app or default
        return getattr(app, "version", "1.0.0")
    
    def _calculate_schema_hash(self, schema: Dict[str, Any]) -> str:
        """Calculate schema hash for change detection."""
        # Remove dynamic fields for stable hashing
        stable_schema = schema.copy()
        if "info" in stable_schema:
            stable_schema["info"] = {
                k: v for k, v in stable_schema["info"].items()
                if not k.startswith("x-generated")
            }
        
        schema_str = json.dumps(stable_schema, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(schema_str.encode()).hexdigest()[:12]
    
    def _enhance_schema_metadata(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance schema with comprehensive metadata."""
        enhanced_schema = schema.copy()
        
        # Enhanced info section
        if "info" not in enhanced_schema:
            enhanced_schema["info"] = {}
            
        enhanced_schema["info"].update({
            "x-api-version": self.api_version,
            "x-generated-at": datetime.now(timezone.utc).isoformat(),
            "x-system": "Adelaide Weather Forecasting System",
            "x-build-id": self.build_id,
            "x-generator": "enhanced-openapi-generator",
            "x-schema-hash": self._calculate_schema_hash(schema),
            "x-ci-environment": self.is_ci,
        })
        
        # Add version to components for tracking
        if "components" not in enhanced_schema:
            enhanced_schema["components"] = {}
            
        enhanced_schema["components"]["x-metadata"] = {
            "generated": {
                "timestamp": enhanced_schema["info"]["x-generated-at"],
                "version": self.api_version,
                "hash": enhanced_schema["info"]["x-schema-hash"],
                "build": self.build_id
            },
            "endpoints": len(enhanced_schema.get("paths", {})),
            "schemas": len(enhanced_schema.get("components", {}).get("schemas", {})),
            "enhanced_features": [
                "risk_assessment",
                "analogs_summary", 
                "narrative_generation",
                "uncertainty_quantification",
                "health_monitoring"
            ]
        }
        
        return enhanced_schema
    
    def _validate_schema(self, schema: Dict[str, Any]) -> Tuple[bool, list]:
        """Validate OpenAPI schema completeness and quality."""
        errors = []
        warnings = []
        
        # Check required sections
        required_sections = ["openapi", "info", "paths"]
        for section in required_sections:
            if section not in schema:
                errors.append(f"Missing required section: {section}")
        
        # Validate paths
        if "paths" in schema:
            paths = schema["paths"]
            if not paths:
                errors.append("No API paths defined")
            
            # Check for enhanced endpoints
            expected_paths = ["/forecast", "/health", "/metrics"]
            for path in expected_paths:
                if path not in paths:
                    warnings.append(f"Expected path missing: {path}")
        
        # Validate components/schemas
        if "components" in schema and "schemas" in schema["components"]:
            schemas = schema["components"]["schemas"]
            
            # Check for enhanced schema types
            expected_schemas = [
                "ForecastResponse",
                "RiskAssessment", 
                "AnalogsSummary",
                "VariableResult",
                "HealthResponse"
            ]
            
            for schema_name in expected_schemas:
                if schema_name not in schemas:
                    warnings.append(f"Expected schema missing: {schema_name}")
        
        # Log validation results
        if self.is_ci:
            print(f"::group::Schema Validation Results")
            
        if errors:
            print("❌ Schema validation errors:")
            for error in errors:
                print(f"  - {error}")
                if self.is_ci:
                    print(f"::error::{error}")
        
        if warnings:
            print("⚠️ Schema validation warnings:")
            for warning in warnings:
                print(f"  - {warning}")
                if self.is_ci:
                    print(f"::warning::{warning}")
        
        if not errors and not warnings:
            print("✅ Schema validation passed")
            
        if self.is_ci:
            print("::endgroup::")
        
        return len(errors) == 0, errors + warnings
    
    def _save_schema(self, schema: Dict[str, Any], filename: str) -> str:
        """Save schema to file in specified format."""
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, "w") as f:
            if self.format_type == "yaml":
                yaml.dump(schema, f, default_flow_style=False, sort_keys=False)
            else:
                json.dump(schema, f, indent=2, sort_keys=False)
        
        return filepath
    
    def _copy_to_frontend(self, schema: Dict[str, Any]) -> Optional[str]:
        """Copy schema to frontend directory for type generation."""
        try:
            frontend_dir = os.path.join(os.path.dirname(self.output_dir), "frontend")
            if not os.path.exists(frontend_dir):
                print(f"⚠️ Frontend directory not found: {frontend_dir}")
                return None
                
            frontend_path = os.path.join(frontend_dir, "openapi.json")
            
            with open(frontend_path, "w") as f:
                json.dump(schema, f, indent=2)
            
            return frontend_path
        except Exception as e:
            print(f"⚠️ Failed to copy to frontend: {e}")
            return None
    
    def _check_for_changes(self, schema: Dict[str, Any]) -> bool:
        """Check if schema has changed since last generation."""
        current_hash = self._calculate_schema_hash(schema)
        hash_file = os.path.join(self.output_dir, ".openapi_hash")
        
        if os.path.exists(hash_file):
            try:
                with open(hash_file, "r") as f:
                    previous_hash = f.read().strip()
                    if previous_hash == current_hash:
                        return False
            except Exception:
                pass
        
        # Save current hash
        with open(hash_file, "w") as f:
            f.write(current_hash)
        
        return True
    
    def generate(self, validate: bool = True) -> bool:
        """Generate OpenAPI schema with validation and metadata."""
        try:
            if self.is_ci:
                print("::group::OpenAPI Schema Generation")
            
            print("🚀 Generating OpenAPI schema...")
            print(f"📍 API Version: {self.api_version}")
            print(f"🏗️ Build ID: {self.build_id}")
            print(f"📁 Output Directory: {self.output_dir}")
            print(f"📄 Format: {self.format_type}")
            
            # Generate schema from FastAPI app
            try:
                schema = app.openapi()
            except Exception as e:
                print(f"❌ Failed to generate schema from FastAPI app: {e}")
                if self.is_ci:
                    print(f"::error::Failed to generate OpenAPI schema: {e}")
                return False
            
            # Check for changes
            if not self._check_for_changes(schema):
                print("✨ No changes detected in schema")
                if not self.is_ci:  # In CI, always regenerate for consistency
                    return True
            
            # Enhance with metadata
            enhanced_schema = self._enhance_schema_metadata(schema)
            
            # Validate schema
            if validate:
                is_valid, issues = self._validate_schema(enhanced_schema)
                if not is_valid:
                    print("❌ Schema validation failed")
                    return False
            
            # Save schema files
            filename = f"openapi.{self.format_type}"
            output_path = self._save_schema(enhanced_schema, filename)
            
            print(f"✅ OpenAPI schema generated: {output_path}")
            print(f"📋 Endpoints: {len(enhanced_schema.get('paths', {}))}")
            print(f"🔧 Components: {len(enhanced_schema.get('components', {}).get('schemas', {}))}")
            print(f"🏷️ Schema Hash: {enhanced_schema['info']['x-schema-hash']}")
            
            # Copy to frontend
            frontend_path = self._copy_to_frontend(enhanced_schema)
            if frontend_path:
                print(f"✅ Schema copied to frontend: {frontend_path}")
            
            # Generate metadata file for CI
            if self.is_ci:
                metadata = {
                    "schema_hash": enhanced_schema["info"]["x-schema-hash"],
                    "api_version": self.api_version,
                    "generated_at": enhanced_schema["info"]["x-generated-at"],
                    "build_id": self.build_id,
                    "endpoints_count": len(enhanced_schema.get("paths", {})),
                    "schemas_count": len(enhanced_schema.get("components", {}).get("schemas", {})),
                    "output_files": [output_path] + ([frontend_path] if frontend_path else [])
                }
                
                metadata_path = os.path.join(self.output_dir, "openapi_metadata.json")
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
                
                print(f"📊 Metadata saved: {metadata_path}")
                
                # Set GitHub Actions output
                print(f"::set-output name=schema_hash::{metadata['schema_hash']}")
                print(f"::set-output name=api_version::{metadata['api_version']}")
            
            if self.is_ci:
                print("::endgroup::")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to generate OpenAPI schema: {e}")
            if self.is_ci:
                print(f"::error::OpenAPI generation failed: {e}")
            return False


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Generate OpenAPI schema for Adelaide Weather Forecasting System"
    )
    parser.add_argument(
        "--validate", 
        action="store_true", 
        help="Validate generated schema"
    )
    parser.add_argument(
        "--output-dir", 
        help="Output directory for generated files"
    )
    parser.add_argument(
        "--format", 
        choices=["json", "yaml"], 
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip schema validation"
    )
    
    args = parser.parse_args()
    
    generator = OpenAPIGenerator(
        output_dir=args.output_dir,
        format_type=args.format
    )
    
    validate = args.validate or not args.no_validate
    success = generator.generate(validate=validate)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()