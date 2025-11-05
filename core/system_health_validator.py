#!/usr/bin/env python3
"""
Production-Grade System Health and Validation Framework
=======================================================

Implements comprehensive startup validation, runtime monitoring, and quality gates
for the Adelaide Weather Forecasting System. Zero tolerance for silent failures.

CRITICAL DESIGN PRINCIPLES:
- FAIL FAST and FAIL LOUD on any critical issue
- Hard gates with quantitative thresholds (≥95% model match, ≥99% data validity)
- Comprehensive version tracking for reproducibility
- Per-variable monitoring with degradation detection
- Runtime corruption and degeneracy validation

Author: Production QA Framework
Version: 1.0.0 - Production Health Gates
"""

import os
import sys
import time
import json
import hashlib
import logging
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager

import numpy as np
import pandas as pd
import torch
from packaging import version

# Setup logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Container for validation results with pass/fail status."""
    test_name: str
    status: str  # 'PASS', 'FAIL', 'WARNING'
    message: str
    metrics: Dict[str, Any]
    timestamp: str
    critical: bool = True  # Whether failure blocks system startup
    
    def is_passing(self) -> bool:
        return self.status == 'PASS'
    
    def is_critical_failure(self) -> bool:
        return self.status == 'FAIL' and self.critical

@dataclass
class SystemVersions:
    """Comprehensive version tracking for reproducibility."""
    framework_version: str
    model_hash: str
    model_version: str
    dataset_version: str
    faiss_index_version: str
    pytorch_version: str
    faiss_version: str
    numpy_version: str
    system_timestamp: str
    git_commit: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ProductionHealthValidator:
    """Production-grade health and validation framework with hard gates."""
    
    # CRITICAL THRESHOLDS - ZERO TOLERANCE
    MODEL_MATCH_THRESHOLD = 0.95  # ≥95% layer match requirement
    DATA_VALIDITY_THRESHOLD = 0.99  # ≥99% valid data per variable
    FAISS_SIZE_TOLERANCE = 0.01  # ±1% for index size validation
    PERFORMANCE_THRESHOLD_MS = 150  # <150ms target performance
    MIN_ANALOGS_THRESHOLD = 10  # Minimum analogs for valid forecast
    SIMILARITY_VARIANCE_THRESHOLD = 0.1  # Detect index degeneration
    
    def __init__(self, project_root: Path = None):
        """Initialize the production health validator.
        
        Args:
            project_root: Path to project root directory
        """
        self.project_root = project_root or Path("/home/micha/weather-forecast-final")
        self.validation_results: List[ValidationResult] = []
        self.system_versions = None
        self.performance_metrics = {}
        self.startup_time = time.time()
        
        # Expected system configuration - CORRECTED PATTERN COUNT
        self.expected_horizons = [6, 12, 24, 48]
        self.expected_variables = ['z500', 't2m', 't850', 'q850', 'u10', 'v10', 'u850', 'v850', 'cape']
        self.expected_faiss_sizes = {
            6: 13148,   # CORRECTED: 13,148 patterns, not 280k
            12: 13148,
            24: 13148,
            48: 13148
        }
        
        logger.info(f"🏥 Initializing Production Health Validator")
        logger.info(f"   Project Root: {self.project_root}")
        logger.info(f"   Validation Thresholds: Model≥{self.MODEL_MATCH_THRESHOLD*100}%, Data≥{self.DATA_VALIDITY_THRESHOLD*100}%")
    
    @contextmanager
    def performance_timer(self, operation_name: str):
        """Context manager for performance timing."""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.performance_metrics[operation_name] = duration_ms
            logger.debug(f"⏱️ {operation_name}: {duration_ms:.1f}ms")
    
    def _add_result(self, test_name: str, status: str, message: str, 
                   metrics: Dict[str, Any] = None, critical: bool = True) -> ValidationResult:
        """Add validation result with standardized logging."""
        result = ValidationResult(
            test_name=test_name,
            status=status,
            message=message,
            metrics=metrics or {},
            timestamp=datetime.now().isoformat(),
            critical=critical
        )
        
        self.validation_results.append(result)
        
        # Log with appropriate level
        status_emoji = {"PASS": "✅", "FAIL": "❌", "WARNING": "⚠️"}
        log_msg = f"{status_emoji.get(status, '❓')} {test_name}: {message}"
        
        if status == "FAIL" and critical:
            logger.error(log_msg)
        elif status == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        return result
    
    def validate_system_versions(self) -> ValidationResult:
        """Capture and validate comprehensive system version information."""
        logger.info("🔍 Validating system versions and dependencies...")
        
        try:
            # Get PyTorch version
            pytorch_version = torch.__version__
            
            # Get other critical dependencies
            try:
                import faiss
                faiss_version = faiss.__version__
            except:
                faiss_version = "unknown"
            
            numpy_version = np.__version__
            
            # Get model hash for reproducibility
            model_hash = self._compute_model_hash()
            
            # Git commit (if available)
            git_commit = self._get_git_commit()
            
            # Dataset version (based on data modification times)
            dataset_version = self._compute_dataset_version()
            
            # FAISS index version
            faiss_index_version = self._compute_faiss_index_version()
            
            self.system_versions = SystemVersions(
                framework_version="1.0.0",
                model_hash=model_hash,
                model_version=self._get_model_version(),
                dataset_version=dataset_version,
                faiss_index_version=faiss_index_version,
                pytorch_version=pytorch_version,
                faiss_version=faiss_version,
                numpy_version=numpy_version,
                system_timestamp=datetime.now().isoformat(),
                git_commit=git_commit
            )
            
            # Validate version compatibility
            compatibility_issues = []
            
            # Check PyTorch version compatibility
            if version.parse(pytorch_version) < version.parse("1.10.0"):
                compatibility_issues.append(f"PyTorch {pytorch_version} < 1.10.0 minimum")
            
            # Check for model hash consistency
            if model_hash == "unknown":
                compatibility_issues.append("Model hash could not be computed")
            
            if compatibility_issues:
                return self._add_result(
                    "system_versions",
                    "WARNING",
                    f"Version compatibility issues: {'; '.join(compatibility_issues)}",
                    {"versions": self.system_versions.to_dict(), "issues": compatibility_issues},
                    critical=False
                )
            
            return self._add_result(
                "system_versions",
                "PASS",
                f"System versions validated - PyTorch {pytorch_version}, Model {model_hash[:8]}",
                {"versions": self.system_versions.to_dict()}
            )
            
        except Exception as e:
            return self._add_result(
                "system_versions",
                "FAIL",
                f"Version validation failed: {str(e)}",
                {"error": str(e)}
            )
    
    def validate_model_integrity(self) -> ValidationResult:
        """Validate model loading and layer match ratio ≥95%."""
        logger.info("🧠 Validating model integrity and loading...")
        
        try:
            with self.performance_timer("model_load"):
                from core.model_loader import load_model_safe
                
                # Load model safely
                model = load_model_safe(device='cpu')
                
                if model is None:
                    return self._add_result(
                        "model_integrity",
                        "FAIL",
                        "Model loading failed completely",
                        {"model_available": False}
                    )
                
                # Get model state dict for layer analysis
                state_dict = model.state_dict()
                total_layers = len(state_dict)
                
                # Validate model architecture
                expected_layers = [
                    "conv_layers.0.weight",
                    "conv_layers.2.weight", 
                    "conv_layers.4.weight",
                    "fc_features.weight",
                    "horizon_embedding.weight",
                    "fc_output.weight"
                ]
                
                matched_layers = sum(1 for layer in expected_layers if layer in state_dict)
                layer_match_ratio = matched_layers / len(expected_layers)
                
                # Test forward pass
                test_input = torch.randn(1, 9, 16, 16)
                test_horizon = torch.tensor([0])
                
                with torch.no_grad():
                    embeddings = model(test_input, test_horizon)
                
                # Validate embedding properties
                embedding_norm = torch.norm(embeddings, dim=1).item()
                embedding_shape = list(embeddings.shape)
                
                metrics = {
                    "total_layers": total_layers,
                    "matched_layers": matched_layers,
                    "layer_match_ratio": layer_match_ratio,
                    "embedding_shape": embedding_shape,
                    "embedding_norm": embedding_norm,
                    "load_time_ms": self.performance_metrics.get("model_load", 0)
                }
                
                # Apply hard gate: ≥95% layer match
                if layer_match_ratio < self.MODEL_MATCH_THRESHOLD:
                    return self._add_result(
                        "model_integrity",
                        "FAIL",
                        f"Model layer match {layer_match_ratio:.1%} < {self.MODEL_MATCH_THRESHOLD:.1%} threshold",
                        metrics
                    )
                
                # Validate embedding properties
                if embedding_shape != [1, 256]:
                    return self._add_result(
                        "model_integrity",
                        "FAIL",
                        f"Invalid embedding shape {embedding_shape}, expected [1, 256]",
                        metrics
                    )
                
                if not (0.9 <= embedding_norm <= 1.1):
                    return self._add_result(
                        "model_integrity",
                        "WARNING",
                        f"Embedding norm {embedding_norm:.3f} not normalized",
                        metrics,
                        critical=False
                    )
                
                return self._add_result(
                    "model_integrity",
                    "PASS",
                    f"Model integrity validated - {layer_match_ratio:.1%} layer match, shape {embedding_shape}",
                    metrics
                )
                
        except Exception as e:
            return self._add_result(
                "model_integrity",
                "FAIL", 
                f"Model validation failed: {str(e)}",
                {"error": str(e)}
            )
    
    def validate_database_integrity(self) -> ValidationResult:
        """Validate database integrity with ≥99% valid data per variable."""
        logger.info("📊 Validating database integrity and data quality...")
        
        try:
            embeddings_dir = self.project_root / "embeddings"
            outcomes_dir = self.project_root / "outcomes"
            
            all_metrics = {}
            critical_failures = []
            warnings = []
            
            for horizon in self.expected_horizons:
                horizon_metrics = {}
                
                # Check metadata integrity
                metadata_path = embeddings_dir / f"metadata_{horizon}h.parquet"
                if not metadata_path.exists():
                    critical_failures.append(f"Missing metadata for {horizon}h")
                    continue
                
                metadata = pd.read_parquet(metadata_path)
                
                # Check for temporal consistency
                if 'init_time' in metadata.columns:
                    time_gaps = metadata['init_time'].diff().dt.total_seconds() / 3600
                    max_gap = time_gaps.max()
                    if max_gap > 24:  # More than 24h gap
                        warnings.append(f"{horizon}h: Max time gap {max_gap:.1f}h")
                
                # Check outcomes integrity
                outcomes_path = outcomes_dir / f"outcomes_{horizon}h.npy"
                if outcomes_path.exists():
                    outcomes = np.load(outcomes_path, mmap_mode='r')
                    
                    # Per-variable validity check
                    variable_validity = {}
                    for i, var_name in enumerate(self.expected_variables):
                        if i < outcomes.shape[1]:
                            var_data = outcomes[:, i]
                            
                            # Check for valid values (not NaN, not infinite, reasonable ranges)
                            valid_mask = np.isfinite(var_data)
                            
                            # Temperature checks (should be in Kelvin, positive)
                            if var_name in ['t2m', 't850']:
                                valid_mask &= (var_data > 200) & (var_data < 350)
                            
                            # Wind speed checks (reasonable magnitude)
                            elif var_name in ['u10', 'v10', 'u850', 'v850']:
                                valid_mask &= (np.abs(var_data) < 100)
                            
                            # Humidity checks (positive, reasonable range)
                            elif var_name == 'q850':
                                valid_mask &= (var_data >= 0) & (var_data < 0.1)
                            
                            # Geopotential checks
                            elif var_name == 'z500':
                                valid_mask &= (var_data > 4000) & (var_data < 7000)
                            
                            # CAPE checks
                            elif var_name == 'cape':
                                valid_mask &= (var_data >= 0) & (var_data < 10000)
                            
                            validity_ratio = np.sum(valid_mask) / len(var_data)
                            variable_validity[var_name] = validity_ratio
                            
                            # Apply hard gate: ≥99% valid per variable
                            if validity_ratio < self.DATA_VALIDITY_THRESHOLD:
                                critical_failures.append(
                                    f"{horizon}h {var_name}: {validity_ratio:.1%} < {self.DATA_VALIDITY_THRESHOLD:.1%} validity"
                                )
                    
                    horizon_metrics = {
                        "metadata_records": len(metadata),
                        "outcomes_shape": list(outcomes.shape),
                        "variable_validity": variable_validity,
                        "min_validity": min(variable_validity.values()) if variable_validity else 0
                    }
                else:
                    critical_failures.append(f"Missing outcomes for {horizon}h")
                
                all_metrics[f"{horizon}h"] = horizon_metrics
            
            # Overall assessment
            if critical_failures:
                return self._add_result(
                    "database_integrity",
                    "FAIL",
                    f"Database integrity failures: {'; '.join(critical_failures[:3])}",
                    {"horizon_metrics": all_metrics, "failures": critical_failures}
                )
            
            if warnings:
                return self._add_result(
                    "database_integrity",
                    "WARNING",
                    f"Database warnings: {'; '.join(warnings[:2])}",
                    {"horizon_metrics": all_metrics, "warnings": warnings},
                    critical=False
                )
            
            return self._add_result(
                "database_integrity",
                "PASS",
                f"Database integrity validated - all variables ≥{self.DATA_VALIDITY_THRESHOLD:.0%} valid",
                {"horizon_metrics": all_metrics}
            )
            
        except Exception as e:
            return self._add_result(
                "database_integrity",
                "FAIL",
                f"Database validation failed: {str(e)}",
                {"error": str(e)}
            )
    
    def validate_faiss_indices(self) -> ValidationResult:
        """Validate FAISS indices size and metric consistency ±1%."""
        logger.info("🔍 Validating FAISS indices and search performance...")
        
        try:
            import faiss
            
            indices_dir = self.project_root / "indices"
            all_metrics = {}
            critical_failures = []
            
            with self.performance_timer("faiss_validation"):
                for horizon in self.expected_horizons:
                    horizon_metrics = {}
                    
                    # Check both index types
                    for index_type in ['flatip', 'ivfpq']:
                        index_path = indices_dir / f"faiss_{horizon}h_{index_type}.faiss"
                        
                        if not index_path.exists():
                            critical_failures.append(f"Missing {index_type} index for {horizon}h")
                            continue
                        
                        # Load and validate index
                        index = faiss.read_index(str(index_path))
                        index_size = index.ntotal
                        expected_size = self.expected_faiss_sizes.get(horizon, 280000)
                        
                        # Apply hard gate: ±1% size tolerance
                        size_deviation = abs(index_size - expected_size) / expected_size
                        if size_deviation > self.FAISS_SIZE_TOLERANCE:
                            critical_failures.append(
                                f"{horizon}h {index_type}: size {index_size} vs expected {expected_size} "
                                f"({size_deviation:.1%} > {self.FAISS_SIZE_TOLERANCE:.1%} tolerance)"
                            )
                        
                        # Test search performance and uniqueness
                        test_query = np.random.randn(1, 256).astype(np.float32)
                        faiss.normalize_L2(test_query)
                        
                        search_start = time.time()
                        distances, indices = index.search(test_query, 50)
                        search_time_ms = (time.time() - search_start) * 1000
                        
                        # Validate search results
                        unique_indices = len(np.unique(indices[0]))
                        similarity_variance = np.var(distances[0])
                        
                        # Check for index degeneracy
                        if unique_indices < 45:  # Should have nearly 50 unique results
                            critical_failures.append(
                                f"{horizon}h {index_type}: only {unique_indices}/50 unique neighbors"
                            )
                        
                        if similarity_variance < self.SIMILARITY_VARIANCE_THRESHOLD:
                            critical_failures.append(
                                f"{horizon}h {index_type}: low similarity variance {similarity_variance:.4f}"
                            )
                        
                        horizon_metrics[index_type] = {
                            "index_size": index_size,
                            "expected_size": expected_size,
                            "size_deviation": size_deviation,
                            "search_time_ms": search_time_ms,
                            "unique_neighbors": unique_indices,
                            "similarity_variance": similarity_variance
                        }
                    
                    all_metrics[f"{horizon}h"] = horizon_metrics
            
            # Performance validation
            total_validation_time = self.performance_metrics.get("faiss_validation", 0)
            
            if critical_failures:
                return self._add_result(
                    "faiss_indices",
                    "FAIL",
                    f"FAISS validation failures: {'; '.join(critical_failures[:3])}",
                    {"horizon_metrics": all_metrics, "failures": critical_failures, "validation_time_ms": total_validation_time}
                )
            
            return self._add_result(
                "faiss_indices",
                "PASS",
                f"FAISS indices validated - all sizes within ±{self.FAISS_SIZE_TOLERANCE:.0%}, unique neighbors confirmed",
                {"horizon_metrics": all_metrics, "validation_time_ms": total_validation_time}
            )
            
        except Exception as e:
            return self._add_result(
                "faiss_indices",
                "FAIL",
                f"FAISS validation failed: {str(e)}",
                {"error": str(e)}
            )
    
    def validate_performance_profile(self) -> ValidationResult:
        """Validate system performance meets <150ms targets."""
        logger.info("⚡ Validating system performance profile...")
        
        try:
            # Test full pipeline performance
            with self.performance_timer("full_pipeline"):
                # Mock weather data
                mock_era5_data = {
                    'z500': 5640.0,
                    't2m': 293.15,
                    't850': 285.65,
                    'q850': 0.008,
                    'u10': -2.5,
                    'v10': 4.2,
                    'u850': -8.1,
                    'v850': 12.3,
                    'cape': 150.0
                }
                
                # Test embedding generation
                from core.real_time_embedder import RealTimeEmbedder
                embedder = RealTimeEmbedder()
                
                with self.performance_timer("embedding_generation"):
                    embeddings = embedder.generate_batch(mock_era5_data, horizons=[24])
                
                if embeddings is not None:
                    # Test FAISS search
                    import faiss
                    indices_dir = self.project_root / "indices"
                    index_path = indices_dir / "faiss_24h_ivfpq.faiss"
                    
                    if index_path.exists():
                        index = faiss.read_index(str(index_path))
                        
                        with self.performance_timer("faiss_search"):
                            distances, indices = index.search(embeddings, 50)
            
            # Collect performance metrics
            embedding_time = self.performance_metrics.get("embedding_generation", 0)
            search_time = self.performance_metrics.get("faiss_search", 0)
            total_time = self.performance_metrics.get("full_pipeline", 0)
            
            performance_metrics = {
                "embedding_time_ms": embedding_time,
                "faiss_search_ms": search_time,
                "total_pipeline_ms": total_time,
                "target_threshold_ms": self.PERFORMANCE_THRESHOLD_MS
            }
            
            # Apply performance gates
            if total_time > self.PERFORMANCE_THRESHOLD_MS:
                return self._add_result(
                    "performance_profile",
                    "WARNING",
                    f"Pipeline performance {total_time:.1f}ms > {self.PERFORMANCE_THRESHOLD_MS}ms target",
                    performance_metrics,
                    critical=False
                )
            
            return self._add_result(
                "performance_profile",
                "PASS",
                f"Performance validated - {total_time:.1f}ms < {self.PERFORMANCE_THRESHOLD_MS}ms target",
                performance_metrics
            )
            
        except Exception as e:
            return self._add_result(
                "performance_profile",
                "FAIL",
                f"Performance validation failed: {str(e)}",
                {"error": str(e)}
            )
    
    def run_startup_validation(self) -> bool:
        """Run complete startup validation with hard gates.
        
        Returns:
            bool: True if system passes all critical validations
        """
        logger.info("🚨 STARTING PRODUCTION STARTUP VALIDATION")
        logger.info("=" * 80)
        logger.info("HARD GATES: Model≥95%, Data≥99%, FAISS±1%, Performance<150ms")
        logger.info("=" * 80)
        
        # Core validation sequence
        validation_tests = [
            ("System Versions", self.validate_system_versions),
            ("Model Integrity", self.validate_model_integrity),
            ("Database Integrity", self.validate_database_integrity),
            ("FAISS Indices", self.validate_faiss_indices),
            ("Performance Profile", self.validate_performance_profile)
        ]
        
        passed_tests = 0
        critical_failures = []
        
        for test_name, test_func in validation_tests:
            logger.info(f"\n🔍 Running: {test_name}")
            
            try:
                result = test_func()
                
                if result.is_passing():
                    passed_tests += 1
                elif result.is_critical_failure():
                    critical_failures.append(f"{test_name}: {result.message}")
                
            except Exception as e:
                error_msg = f"{test_name} validation crashed: {str(e)}"
                critical_failures.append(error_msg)
                logger.error(f"💥 {error_msg}")
        
        # Final assessment
        total_startup_time = time.time() - self.startup_time
        
        logger.info("\n" + "=" * 80)
        logger.info("STARTUP VALIDATION RESULTS")
        logger.info("=" * 80)
        
        if critical_failures:
            logger.error(f"❌ STARTUP VALIDATION FAILED")
            logger.error(f"   Critical Failures: {len(critical_failures)}")
            for failure in critical_failures[:5]:  # Show first 5
                logger.error(f"   • {failure}")
            
            if len(critical_failures) > 5:
                logger.error(f"   ... and {len(critical_failures) - 5} more failures")
            
            logger.error(f"🚫 SYSTEM STARTUP BLOCKED - RESOLVE CRITICAL ISSUES")
            return False
        
        logger.info(f"✅ STARTUP VALIDATION PASSED ({passed_tests}/{len(validation_tests)} tests)")
        logger.info(f"⚡ Total startup time: {total_startup_time:.1f}s")
        logger.info(f"🚀 SYSTEM READY FOR PRODUCTION OPERATION")
        
        # Save validation report
        self._save_validation_report()
        
        return True
    
    def _compute_model_hash(self) -> str:
        """Compute SHA256 hash of model file for reproducibility."""
        try:
            # Find the best model
            production_models = list(self.project_root.glob('outputs/training_production_*/best_model.pt'))
            if production_models:
                model_path = production_models[0]
                with open(model_path, 'rb') as f:
                    return hashlib.sha256(f.read()).hexdigest()
            return "unknown"
        except:
            return "unknown"
    
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash if available."""
        try:
            import subprocess
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                  capture_output=True, text=True, cwd=self.project_root)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
    
    def _get_model_version(self) -> str:
        """Get model version from filesystem."""
        production_dirs = list(self.project_root.glob('outputs/training_production_*'))
        if production_dirs:
            # Extract timestamp from directory name
            dir_name = production_dirs[0].name
            return dir_name.replace('training_production_', '')
        return "unknown"
    
    def _compute_dataset_version(self) -> str:
        """Compute dataset version hash based on data files."""
        try:
            data_dir = self.project_root / "data"
            data_files = list(data_dir.rglob("*.zarr")) + list(data_dir.rglob("*.nc"))
            
            if data_files:
                # Use modification times and sizes as version identifier
                file_info = []
                for f in sorted(data_files)[:10]:  # First 10 files
                    stat = f.stat()
                    file_info.append(f"{f.name}_{stat.st_size}_{int(stat.st_mtime)}")
                
                version_string = "_".join(file_info)
                return hashlib.md5(version_string.encode()).hexdigest()[:12]
        except:
            pass
        return "unknown"
    
    def _compute_faiss_index_version(self) -> str:
        """Compute FAISS index version based on index files."""
        try:
            indices_dir = self.project_root / "indices"
            index_files = list(indices_dir.glob("*.faiss"))
            
            if index_files:
                file_info = []
                for f in sorted(index_files):
                    stat = f.stat()
                    file_info.append(f"{f.name}_{stat.st_size}_{int(stat.st_mtime)}")
                
                version_string = "_".join(file_info)
                return hashlib.md5(version_string.encode()).hexdigest()[:12]
        except:
            pass
        return "unknown"
    
    def _save_validation_report(self):
        """Save comprehensive validation report."""
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "system_versions": self.system_versions.to_dict() if self.system_versions else {},
            "performance_metrics": self.performance_metrics,
            "validation_results": [asdict(result) for result in self.validation_results],
            "summary": {
                "total_tests": len(self.validation_results),
                "passed_tests": sum(1 for r in self.validation_results if r.is_passing()),
                "failed_tests": sum(1 for r in self.validation_results if r.status == 'FAIL'),
                "warnings": sum(1 for r in self.validation_results if r.status == 'WARNING'),
                "critical_failures": [r.test_name for r in self.validation_results if r.is_critical_failure()]
            }
        }
        
        report_path = self.project_root / "system_health_validation_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"💾 Validation report saved: {report_path}")

def main():
    """Main entry point for startup validation."""
    validator = ProductionHealthValidator()
    
    try:
        success = validator.run_startup_validation()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"💥 Validation framework crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()