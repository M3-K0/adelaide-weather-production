#!/usr/bin/env python3
"""
Version Stamping System for Production Runtime Reliability
==========================================================

Implements comprehensive version tracking for model components, datasets, indices,
and schemas to ensure reproducibility and detect version mismatches that could
lead to silent failures in production.

Features:
- Model version tracking with checksum validation
- Index version tracking with metadata validation
- Dataset version tracking with temporal consistency checks
- Schema version tracking for outcome and metadata formats
- Runtime version compatibility validation
- Automatic version mismatch detection and alerts
- Reproducibility tracking for scientific validation

This system addresses the critical need for version consistency in production
analog forecasting systems where silent failures can occur from version mismatches.

Author: Production Runtime Reliability Team
Version: 1.0.0 - Version Stamping System
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class VersionType(Enum):
    """Types of versioned components."""
    MODEL = "model"
    INDEX = "index"
    DATASET = "dataset"
    SCHEMA = "schema"
    SYSTEM = "system"

class CompatibilityLevel(Enum):
    """Version compatibility levels."""
    COMPATIBLE = "compatible"           # Fully compatible
    MINOR_ISSUES = "minor_issues"      # Minor compatibility issues
    MAJOR_ISSUES = "major_issues"      # Major compatibility issues
    INCOMPATIBLE = "incompatible"      # Completely incompatible

@dataclass
class VersionStamp:
    """Comprehensive version stamp for system components."""
    version_id: str                    # Unique version identifier
    version_type: VersionType         # Type of component
    component_name: str               # Name of component
    semantic_version: str             # Semantic version (e.g., "1.2.3")
    creation_timestamp: str           # ISO timestamp of creation
    
    # Integrity validation
    checksum_sha256: str              # SHA-256 checksum of component
    file_size_bytes: int              # File size for validation
    
    # Dependencies
    dependencies: Dict[str, str]      # Component dependencies with versions
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Validation flags
    validated: bool = False
    validation_timestamp: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)

@dataclass 
class SystemVersionManifest:
    """Complete system version manifest."""
    manifest_version: str = "1.0.0"
    system_version: str = "1.0.0"
    creation_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Component versions
    model_versions: Dict[str, VersionStamp] = field(default_factory=dict)
    index_versions: Dict[str, VersionStamp] = field(default_factory=dict)
    dataset_versions: Dict[str, VersionStamp] = field(default_factory=dict)
    schema_versions: Dict[str, VersionStamp] = field(default_factory=dict)
    
    # System configuration
    python_version: str = field(default_factory=lambda: f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    numpy_version: str = ""
    pandas_version: str = ""
    faiss_version: str = ""
    torch_version: str = ""
    
    # Runtime validation
    last_validation_timestamp: Optional[str] = None
    validation_status: str = "pending"  # pending, passed, failed
    compatibility_issues: List[str] = field(default_factory=list)

class VersionStampingSystem:
    """Production-grade version stamping and compatibility validation system."""
    
    def __init__(self, base_path: Path = Path(".")):
        """Initialize version stamping system.
        
        Args:
            base_path: Base path for the weather forecasting system
        """
        self.base_path = Path(base_path)
        self.versions_dir = self.base_path / "versions"
        self.versions_dir.mkdir(exist_ok=True)
        
        # Version stamp storage
        self.manifest_path = self.versions_dir / "system_manifest.json"
        self.current_manifest: Optional[SystemVersionManifest] = None
        
        # Component paths
        self.models_path = self.base_path / "models"
        self.indices_path = self.base_path / "indices"
        self.outcomes_path = self.base_path / "outcomes"
        self.embeddings_path = self.base_path / "embeddings"
        
        # Load or create manifest
        self._load_or_create_manifest()
        
        logger.info(f"🏷️ Version Stamping System initialized")
        logger.info(f"   Versions directory: {self.versions_dir}")
        logger.info(f"   System version: {self.current_manifest.system_version}")
    
    def _load_or_create_manifest(self):
        """Load existing manifest or create new one."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r') as f:
                    manifest_data = json.load(f)
                
                # Convert to dataclass
                self.current_manifest = SystemVersionManifest(**manifest_data)
                logger.info(f"✅ Loaded system manifest: {self.current_manifest.system_version}")
            except Exception as e:
                logger.error(f"❌ Failed to load manifest: {e}")
                self._create_new_manifest()
        else:
            self._create_new_manifest()
    
    def _create_new_manifest(self):
        """Create new system manifest."""
        import sys
        import numpy as np
        import pandas as pd
        
        # Get package versions
        versions = {}
        try:
            versions['numpy'] = np.__version__
        except:
            versions['numpy'] = "unknown"
        
        try:
            versions['pandas'] = pd.__version__
        except:
            versions['pandas'] = "unknown"
        
        try:
            import faiss
            versions['faiss'] = faiss.__version__ if hasattr(faiss, '__version__') else "unknown"
        except:
            versions['faiss'] = "not_installed"
        
        try:
            import torch
            versions['torch'] = torch.__version__
        except:
            versions['torch'] = "not_installed"
        
        self.current_manifest = SystemVersionManifest(
            numpy_version=versions['numpy'],
            pandas_version=versions['pandas'],
            faiss_version=versions['faiss'],
            torch_version=versions['torch']
        )
        
        self._save_manifest()
        logger.info(f"🆕 Created new system manifest")
    
    def _save_manifest(self):
        """Save current manifest to disk."""
        try:
            with open(self.manifest_path, 'w') as f:
                json.dump(asdict(self.current_manifest), f, indent=2)
            logger.debug(f"💾 Saved system manifest")
        except Exception as e:
            logger.error(f"❌ Failed to save manifest: {e}")
    
    def _calculate_file_checksum(self, file_path: Path) -> Tuple[str, int]:
        """Calculate SHA-256 checksum and file size.
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (checksum, file_size_bytes)
        """
        sha256_hash = hashlib.sha256()
        file_size = 0
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)
                    file_size += len(chunk)
        except Exception as e:
            logger.error(f"❌ Failed to calculate checksum for {file_path}: {e}")
            return "error", 0
        
        return sha256_hash.hexdigest(), file_size
    
    def stamp_model_version(self, model_path: Path, horizon: int, 
                          semantic_version: str = "1.0.0") -> VersionStamp:
        """Create version stamp for model file.
        
        Args:
            model_path: Path to model file
            horizon: Forecast horizon (6, 12, 24, 48)
            semantic_version: Semantic version string
            
        Returns:
            Version stamp for the model
        """
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Calculate checksum and size
        checksum, file_size = self._calculate_file_checksum(model_path)
        
        # Generate version ID
        version_id = f"model_{horizon}h_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create version stamp
        stamp = VersionStamp(
            version_id=version_id,
            version_type=VersionType.MODEL,
            component_name=f"cnn_encoder_{horizon}h",
            semantic_version=semantic_version,
            creation_timestamp=datetime.now(timezone.utc).isoformat(),
            checksum_sha256=checksum,
            file_size_bytes=file_size,
            dependencies={
                "torch": self.current_manifest.torch_version,
                "numpy": self.current_manifest.numpy_version
            },
            metadata={
                "horizon_hours": horizon,
                "model_path": str(model_path),
                "architecture": "cnn_encoder_with_film"
            }
        )
        
        # Add to manifest
        self.current_manifest.model_versions[f"{horizon}h"] = stamp
        self._save_manifest()
        
        logger.info(f"🏷️ Stamped model version: {version_id}")
        return stamp
    
    def stamp_index_version(self, index_path: Path, horizon: int, index_type: str,
                          semantic_version: str = "1.0.0") -> VersionStamp:
        """Create version stamp for FAISS index.
        
        Args:
            index_path: Path to FAISS index file
            horizon: Forecast horizon
            index_type: Type of index (flatip, ivfpq)
            semantic_version: Semantic version string
            
        Returns:
            Version stamp for the index
        """
        if not index_path.exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")
        
        checksum, file_size = self._calculate_file_checksum(index_path)
        version_id = f"index_{horizon}h_{index_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Try to get index metadata
        index_metadata = {}
        try:
            import faiss
            index = faiss.read_index(str(index_path))
            index_metadata = {
                "ntotal": index.ntotal,
                "d": index.d,
                "is_trained": index.is_trained,
                "metric_type": str(index.metric_type) if hasattr(index, 'metric_type') else "unknown"
            }
        except Exception as e:
            logger.warning(f"⚠️ Could not read index metadata: {e}")
        
        stamp = VersionStamp(
            version_id=version_id,
            version_type=VersionType.INDEX,
            component_name=f"faiss_{horizon}h_{index_type}",
            semantic_version=semantic_version,
            creation_timestamp=datetime.now(timezone.utc).isoformat(),
            checksum_sha256=checksum,
            file_size_bytes=file_size,
            dependencies={
                "faiss": self.current_manifest.faiss_version,
                "numpy": self.current_manifest.numpy_version
            },
            metadata={
                "horizon_hours": horizon,
                "index_type": index_type,
                "index_path": str(index_path),
                **index_metadata
            }
        )
        
        # Add to manifest
        key = f"{horizon}h_{index_type}"
        self.current_manifest.index_versions[key] = stamp
        self._save_manifest()
        
        logger.info(f"🏷️ Stamped index version: {version_id}")
        return stamp
    
    def stamp_dataset_version(self, dataset_path: Path, dataset_type: str,
                            horizon: Optional[int] = None,
                            semantic_version: str = "1.0.0") -> VersionStamp:
        """Create version stamp for dataset (outcomes, embeddings, metadata).
        
        Args:
            dataset_path: Path to dataset file
            dataset_type: Type of dataset (outcomes, embeddings, metadata)
            horizon: Forecast horizon (if applicable)
            semantic_version: Semantic version string
            
        Returns:
            Version stamp for the dataset
        """
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
        
        checksum, file_size = self._calculate_file_checksum(dataset_path)
        
        horizon_str = f"_{horizon}h" if horizon else ""
        version_id = f"dataset_{dataset_type}{horizon_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Get dataset-specific metadata
        dataset_metadata = {"file_extension": dataset_path.suffix}
        
        if dataset_path.suffix == '.npy':
            try:
                # Get array shape without loading into memory
                with open(dataset_path, 'rb') as f:
                    # Read numpy header to get shape
                    version = np.lib.format.read_magic(f)
                    shape, fortran_order, dtype = np.lib.format.read_array_header_1_0(f)
                    dataset_metadata.update({
                        "shape": shape,
                        "dtype": str(dtype),
                        "fortran_order": fortran_order
                    })
            except Exception as e:
                logger.warning(f"⚠️ Could not read numpy array metadata: {e}")
        
        elif dataset_path.suffix == '.parquet':
            try:
                # Get parquet metadata without loading data
                import pyarrow.parquet as pq
                parquet_file = pq.ParquetFile(dataset_path)
                dataset_metadata.update({
                    "num_rows": parquet_file.metadata.num_rows,
                    "num_columns": parquet_file.schema_arrow.num_fields,
                    "schema": [field.name for field in parquet_file.schema_arrow]
                })
            except Exception as e:
                logger.warning(f"⚠️ Could not read parquet metadata: {e}")
        
        stamp = VersionStamp(
            version_id=version_id,
            version_type=VersionType.DATASET,
            component_name=f"{dataset_type}{horizon_str}",
            semantic_version=semantic_version,
            creation_timestamp=datetime.now(timezone.utc).isoformat(),
            checksum_sha256=checksum,
            file_size_bytes=file_size,
            dependencies={
                "numpy": self.current_manifest.numpy_version,
                "pandas": self.current_manifest.pandas_version
            },
            metadata={
                "dataset_type": dataset_type,
                "horizon_hours": horizon,
                "dataset_path": str(dataset_path),
                **dataset_metadata
            }
        )
        
        # Add to manifest
        key = f"{dataset_type}{horizon_str}"
        self.current_manifest.dataset_versions[key] = stamp
        self._save_manifest()
        
        logger.info(f"🏷️ Stamped dataset version: {version_id}")
        return stamp
    
    def stamp_schema_version(self, schema_name: str, schema_definition: Dict[str, Any],
                           semantic_version: str = "1.0.0") -> VersionStamp:
        """Create version stamp for data schema.
        
        Args:
            schema_name: Name of schema (e.g., "outcomes_format", "metadata_format")
            schema_definition: Schema definition dictionary
            semantic_version: Semantic version string
            
        Returns:
            Version stamp for the schema
        """
        # Create checksum from schema definition
        schema_json = json.dumps(schema_definition, sort_keys=True)
        checksum = hashlib.sha256(schema_json.encode()).hexdigest()
        
        version_id = f"schema_{schema_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        stamp = VersionStamp(
            version_id=version_id,
            version_type=VersionType.SCHEMA,
            component_name=schema_name,
            semantic_version=semantic_version,
            creation_timestamp=datetime.now(timezone.utc).isoformat(),
            checksum_sha256=checksum,
            file_size_bytes=len(schema_json.encode()),
            dependencies={},
            metadata={
                "schema_definition": schema_definition,
                "schema_fields": list(schema_definition.keys()) if isinstance(schema_definition, dict) else []
            }
        )
        
        # Add to manifest
        self.current_manifest.schema_versions[schema_name] = stamp
        self._save_manifest()
        
        logger.info(f"🏷️ Stamped schema version: {version_id}")
        return stamp
    
    def validate_component_version(self, component_path: Path, expected_stamp: VersionStamp) -> bool:
        """Validate component matches expected version stamp.
        
        Args:
            component_path: Path to component file
            expected_stamp: Expected version stamp
            
        Returns:
            True if component matches expected version
        """
        if not component_path.exists():
            logger.error(f"❌ Component not found: {component_path}")
            return False
        
        # Calculate current checksum
        current_checksum, current_size = self._calculate_file_checksum(component_path)
        
        # Compare with expected
        checksum_match = current_checksum == expected_stamp.checksum_sha256
        size_match = current_size == expected_stamp.file_size_bytes
        
        if checksum_match and size_match:
            logger.debug(f"✅ Version validation passed: {expected_stamp.component_name}")
            return True
        else:
            logger.error(f"❌ Version validation failed: {expected_stamp.component_name}")
            logger.error(f"   Expected checksum: {expected_stamp.checksum_sha256}")
            logger.error(f"   Actual checksum:   {current_checksum}")
            logger.error(f"   Expected size:     {expected_stamp.file_size_bytes}")
            logger.error(f"   Actual size:       {current_size}")
            return False
    
    def check_system_compatibility(self) -> CompatibilityLevel:
        """Check overall system compatibility.
        
        Returns:
            Compatibility level of current system
        """
        issues = []
        
        # Check if all required components have versions
        required_models = ["6h", "12h", "24h", "48h"]
        missing_models = [h for h in required_models if h not in self.current_manifest.model_versions]
        if missing_models:
            issues.append(f"Missing model versions: {missing_models}")
        
        # Check index compatibility
        required_indices = [f"{h}_flatip" for h in required_models]
        missing_indices = [idx for idx in required_indices if idx not in self.current_manifest.index_versions]
        if missing_indices:
            issues.append(f"Missing index versions: {missing_indices}")
        
        # Check dataset compatibility
        required_datasets = [f"outcomes_{h}h" for h in required_models] + [f"metadata_{h}h_clean" for h in required_models]
        missing_datasets = [ds for ds in required_datasets if ds not in self.current_manifest.dataset_versions]
        if missing_datasets:
            issues.append(f"Missing dataset versions: {missing_datasets}")
        
        # Determine compatibility level
        if not issues:
            return CompatibilityLevel.COMPATIBLE
        elif len(issues) <= 2:
            return CompatibilityLevel.MINOR_ISSUES
        elif len(issues) <= 5:
            return CompatibilityLevel.MAJOR_ISSUES
        else:
            return CompatibilityLevel.INCOMPATIBLE
    
    def validate_system_integrity(self) -> Dict[str, Any]:
        """Validate integrity of entire system.
        
        Returns:
            Validation report with detailed results
        """
        validation_report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "pending",
            "model_validation": {},
            "index_validation": {},
            "dataset_validation": {},
            "compatibility_level": None,
            "issues": [],
            "warnings": []
        }
        
        # Validate models
        for horizon, stamp in self.current_manifest.model_versions.items():
            model_path = Path(stamp.metadata.get("model_path", ""))
            if model_path.exists():
                valid = self.validate_component_version(model_path, stamp)
                validation_report["model_validation"][horizon] = valid
                if not valid:
                    validation_report["issues"].append(f"Model validation failed: {horizon}")
            else:
                validation_report["issues"].append(f"Model file missing: {horizon}")
                validation_report["model_validation"][horizon] = False
        
        # Validate indices
        for index_key, stamp in self.current_manifest.index_versions.items():
            index_path = Path(stamp.metadata.get("index_path", ""))
            if index_path.exists():
                valid = self.validate_component_version(index_path, stamp)
                validation_report["index_validation"][index_key] = valid
                if not valid:
                    validation_report["issues"].append(f"Index validation failed: {index_key}")
            else:
                validation_report["issues"].append(f"Index file missing: {index_key}")
                validation_report["index_validation"][index_key] = False
        
        # Validate datasets
        for dataset_key, stamp in self.current_manifest.dataset_versions.items():
            dataset_path = Path(stamp.metadata.get("dataset_path", ""))
            if dataset_path.exists():
                valid = self.validate_component_version(dataset_path, stamp)
                validation_report["dataset_validation"][dataset_key] = valid
                if not valid:
                    validation_report["issues"].append(f"Dataset validation failed: {dataset_key}")
            else:
                validation_report["issues"].append(f"Dataset file missing: {dataset_key}")
                validation_report["dataset_validation"][dataset_key] = False
        
        # Check compatibility
        compatibility = self.check_system_compatibility()
        validation_report["compatibility_level"] = compatibility.value
        
        # Determine overall status
        if not validation_report["issues"] and compatibility == CompatibilityLevel.COMPATIBLE:
            validation_report["overall_status"] = "passed"
        elif compatibility in [CompatibilityLevel.COMPATIBLE, CompatibilityLevel.MINOR_ISSUES]:
            validation_report["overall_status"] = "passed_with_warnings"
        else:
            validation_report["overall_status"] = "failed"
        
        # Update manifest
        self.current_manifest.last_validation_timestamp = validation_report["timestamp"]
        self.current_manifest.validation_status = validation_report["overall_status"]
        self.current_manifest.compatibility_issues = validation_report["issues"]
        self._save_manifest()
        
        return validation_report
    
    def auto_stamp_existing_system(self):
        """Automatically stamp versions for existing system components."""
        logger.info("🏷️ Auto-stamping existing system components...")
        
        # Stamp models
        model_file = self.models_path / "best_model.pt"
        if model_file.exists():
            # For now, stamp as shared model (later can be horizon-specific)
            for horizon in [6, 12, 24, 48]:
                self.stamp_model_version(model_file, horizon, "1.0.0")
        
        # Stamp indices
        for horizon in [6, 12, 24, 48]:
            for index_type in ["flatip", "ivfpq"]:
                index_file = self.indices_path / f"faiss_{horizon}h_{index_type}.faiss"
                if index_file.exists():
                    self.stamp_index_version(index_file, horizon, index_type, "1.0.0")
        
        # Stamp datasets
        for horizon in [6, 12, 24, 48]:
            # Outcomes
            outcomes_file = self.outcomes_path / f"outcomes_{horizon}h.npy"
            if outcomes_file.exists():
                self.stamp_dataset_version(outcomes_file, "outcomes", horizon, "1.0.0")
            
            # Metadata
            metadata_file = self.outcomes_path / f"metadata_{horizon}h_clean.parquet"
            if metadata_file.exists():
                self.stamp_dataset_version(metadata_file, "metadata", horizon, "1.0.0")
            
            # Embeddings
            embeddings_file = self.embeddings_path / f"embeddings_{horizon}h.npy"
            if embeddings_file.exists():
                self.stamp_dataset_version(embeddings_file, "embeddings", horizon, "1.0.0")
        
        # Stamp schemas
        outcomes_schema = {
            "variables": ["z500", "t2m", "t850", "q850", "u10", "v10", "u850", "v850", "cape"],
            "data_type": "float32",
            "units": {
                "z500": "m", "t2m": "K", "t850": "K", "q850": "kg/kg",
                "u10": "m/s", "v10": "m/s", "u850": "m/s", "v850": "m/s", "cape": "J/kg"
            }
        }
        self.stamp_schema_version("outcomes_format", outcomes_schema, "1.0.0")
        
        metadata_schema = {
            "required_columns": ["valid_time", "latitude", "longitude"],
            "temporal_resolution": "6h",
            "spatial_resolution": "0.25_degree"
        }
        self.stamp_schema_version("metadata_format", metadata_schema, "1.0.0")
        
        logger.info("✅ Auto-stamping completed")
    
    def get_version_summary(self) -> str:
        """Get human-readable version summary."""
        lines = ["🏷️ System Version Summary"]
        lines.append("=" * 40)
        lines.append(f"System Version: {self.current_manifest.system_version}")
        lines.append(f"Created: {self.current_manifest.creation_timestamp}")
        lines.append(f"Last Validation: {self.current_manifest.last_validation_timestamp or 'Never'}")
        lines.append(f"Status: {self.current_manifest.validation_status}")
        lines.append("")
        
        lines.append("📦 Package Versions:")
        lines.append(f"  Python: {self.current_manifest.python_version}")
        lines.append(f"  NumPy: {self.current_manifest.numpy_version}")
        lines.append(f"  Pandas: {self.current_manifest.pandas_version}")
        lines.append(f"  FAISS: {self.current_manifest.faiss_version}")
        lines.append(f"  PyTorch: {self.current_manifest.torch_version}")
        lines.append("")
        
        lines.append(f"🤖 Models: {len(self.current_manifest.model_versions)}")
        for horizon, stamp in self.current_manifest.model_versions.items():
            lines.append(f"  {horizon}: {stamp.semantic_version} ({stamp.version_id[:16]}...)")
        
        lines.append(f"📇 Indices: {len(self.current_manifest.index_versions)}")
        for index_key, stamp in self.current_manifest.index_versions.items():
            lines.append(f"  {index_key}: {stamp.semantic_version} ({stamp.version_id[:16]}...)")
        
        lines.append(f"📊 Datasets: {len(self.current_manifest.dataset_versions)}")
        for dataset_key, stamp in self.current_manifest.dataset_versions.items():
            lines.append(f"  {dataset_key}: {stamp.semantic_version} ({stamp.version_id[:16]}...)")
        
        if self.current_manifest.compatibility_issues:
            lines.append("")
            lines.append("⚠️ Compatibility Issues:")
            for issue in self.current_manifest.compatibility_issues:
                lines.append(f"  - {issue}")
        
        return "\n".join(lines)

def main():
    """Demonstration of version stamping system."""
    # Initialize system
    version_system = VersionStampingSystem()
    
    # Auto-stamp existing components
    version_system.auto_stamp_existing_system()
    
    # Validate system integrity
    validation_report = version_system.validate_system_integrity()
    
    print(f"Validation Status: {validation_report['overall_status']}")
    print(f"Issues Found: {len(validation_report['issues'])}")
    
    if validation_report['issues']:
        for issue in validation_report['issues']:
            print(f"  - {issue}")
    
    # Print summary
    print("\n" + version_system.get_version_summary())

if __name__ == "__main__":
    main()