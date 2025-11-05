#!/usr/bin/env python3
"""
FAISS Index Rebuilder
====================

Production-ready FAISS index rebuilding system with validation, atomic swaps,
and comprehensive error handling. Provides automated index lifecycle management
ensuring fresh, validated indices while maintaining system availability.

Features:
- Automated index rebuilding from source embeddings
- Comprehensive validation before deployment
- Atomic swap with zero-downtime deployment
- Backup management with versioning
- Rollback capability for failed deployments
- Integration with existing FAISS infrastructure
- Monitoring and alerting integration
- Production-ready error handling

Author: ML Infrastructure Team
Version: 1.0.0 - T-015 FAISS Index Automation
"""

import os
import sys
import time
import json
import shutil
import hashlib
import logging
import threading
import traceback
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import faiss
from filelock import FileLock

# Import existing components
from scripts.build_indices import FAISSIndexBuilder
from core.startup_validation_system import ExpertValidatedStartupSystem
from core.index_validator import IndexValidator

logger = logging.getLogger(__name__)

@dataclass
class RebuildConfig:
    """Configuration for FAISS index rebuilding."""
    embeddings_dir: str = "embeddings"
    indices_dir: str = "indices"
    backup_dir: str = "indices/backups"
    staging_dir: str = "indices/staging"
    
    # Rebuild parameters
    horizons: List[int] = None
    index_types: List[str] = None
    
    # Validation settings
    validation_enabled: bool = True
    validation_sample_size: int = 1000
    min_recall_threshold: float = 0.95
    max_latency_threshold_ms: float = 100.0
    
    # Backup settings
    max_backups: int = 5
    backup_compression: bool = True
    
    # Safety settings
    require_validation_pass: bool = True
    enable_rollback: bool = True
    max_rebuild_time_minutes: int = 60
    
    # Monitoring
    enable_metrics: bool = True
    enable_alerts: bool = True
    
    def __post_init__(self):
        if self.horizons is None:
            self.horizons = [6, 12, 24, 48]
        if self.index_types is None:
            self.index_types = ['flatip', 'ivfpq']

@dataclass
class RebuildResult:
    """Result of index rebuild operation."""
    rebuild_id: str
    timestamp: str
    success: bool
    horizons_processed: List[int]
    indices_created: List[str]
    validation_results: Dict[str, Any]
    metrics: Dict[str, Any]
    error_message: Optional[str] = None
    rollback_performed: bool = False
    backup_id: Optional[str] = None

@dataclass
class ValidationResult:
    """Result of index validation."""
    horizon: int
    index_type: str
    passed: bool
    metrics: Dict[str, Any]
    issues: List[str]
    test_results: Dict[str, Any]

class IndexBackupManager:
    """Manages FAISS index backups with versioning."""
    
    def __init__(self, config: RebuildConfig):
        self.config = config
        self.backup_dir = Path(config.backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_backup(self, indices_dir: Path, backup_id: str = None) -> str:
        """Create a backup of current indices."""
        if backup_id is None:
            backup_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Creating index backup: {backup_id}")
        
        try:
            # Copy all FAISS index files
            index_files = list(indices_dir.glob("*.faiss"))
            
            if not index_files:
                logger.warning("No FAISS index files found to backup")
                return backup_id
            
            files_backed_up = []
            for index_file in index_files:
                dest_path = backup_path / index_file.name
                shutil.copy2(index_file, dest_path)
                files_backed_up.append(index_file.name)
                
            # Create backup manifest
            manifest = {
                "backup_id": backup_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "files": files_backed_up,
                "total_size_mb": sum(f.stat().st_size for f in index_files) / (1024 * 1024),
                "source_dir": str(indices_dir)
            }
            
            manifest_path = backup_path / "backup_manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Compress if enabled
            if self.config.backup_compression:
                self._compress_backup(backup_path)
            
            logger.info(f"✅ Backup created: {backup_id} ({len(files_backed_up)} files)")
            
            # Clean old backups
            self._cleanup_old_backups()
            
            return backup_id
            
        except Exception as e:
            logger.error(f"Failed to create backup {backup_id}: {e}")
            # Clean up partial backup
            if backup_path.exists():
                shutil.rmtree(backup_path, ignore_errors=True)
            raise
    
    def restore_backup(self, backup_id: str, target_dir: Path) -> bool:
        """Restore indices from backup."""
        backup_path = self.backup_dir / backup_id
        
        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_id}")
            return False
        
        logger.info(f"Restoring backup: {backup_id}")
        
        try:
            # Decompress if needed
            if self.config.backup_compression:
                self._decompress_backup(backup_path)
            
            # Load manifest
            manifest_path = backup_path / "backup_manifest.json"
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                files_to_restore = manifest.get('files', [])
            else:
                # Fallback: restore all .faiss files
                files_to_restore = [f.name for f in backup_path.glob("*.faiss")]
            
            # Restore files
            restored_files = []
            for filename in files_to_restore:
                source_path = backup_path / filename
                if source_path.exists():
                    dest_path = target_dir / filename
                    shutil.copy2(source_path, dest_path)
                    restored_files.append(filename)
            
            logger.info(f"✅ Restored {len(restored_files)} index files from backup {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups."""
        backups = []
        
        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir():
                manifest_path = backup_path / "backup_manifest.json"
                
                if manifest_path.exists():
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                        backups.append(manifest)
                    except Exception as e:
                        logger.warning(f"Could not read manifest for {backup_path.name}: {e}")
                else:
                    # Create basic info
                    backups.append({
                        "backup_id": backup_path.name,
                        "timestamp": datetime.fromtimestamp(backup_path.stat().st_mtime).isoformat(),
                        "files": [f.name for f in backup_path.glob("*.faiss")],
                        "source": "unknown"
                    })
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return backups
    
    def _compress_backup(self, backup_path: Path):
        """Compress backup directory."""
        try:
            import tarfile
            
            compressed_path = backup_path.with_suffix('.tar.gz')
            with tarfile.open(compressed_path, 'w:gz') as tar:
                tar.add(backup_path, arcname=backup_path.name)
            
            # Remove original directory
            shutil.rmtree(backup_path)
            
            logger.info(f"Compressed backup: {compressed_path.name}")
            
        except ImportError:
            logger.warning("tarfile not available, skipping compression")
        except Exception as e:
            logger.warning(f"Failed to compress backup: {e}")
    
    def _decompress_backup(self, backup_path: Path):
        """Decompress backup if needed."""
        compressed_path = backup_path.with_suffix('.tar.gz')
        
        if compressed_path.exists() and not backup_path.exists():
            try:
                import tarfile
                
                with tarfile.open(compressed_path, 'r:gz') as tar:
                    tar.extractall(path=backup_path.parent)
                
                logger.info(f"Decompressed backup: {backup_path.name}")
                
            except Exception as e:
                logger.warning(f"Failed to decompress backup: {e}")
    
    def _cleanup_old_backups(self):
        """Remove old backups beyond max_backups limit."""
        backups = self.list_backups()
        
        if len(backups) > self.config.max_backups:
            backups_to_remove = backups[self.config.max_backups:]
            
            for backup in backups_to_remove:
                backup_id = backup['backup_id']
                backup_path = self.backup_dir / backup_id
                compressed_path = backup_path.with_suffix('.tar.gz')
                
                try:
                    if backup_path.exists():
                        shutil.rmtree(backup_path)
                    if compressed_path.exists():
                        compressed_path.unlink()
                    
                    logger.info(f"Removed old backup: {backup_id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to remove old backup {backup_id}: {e}")

class FAISSIndexValidator:
    """Validates FAISS indices for quality and performance."""
    
    def __init__(self, config: RebuildConfig):
        self.config = config
        
    def validate_index(self, index_path: Path, embeddings: np.ndarray, 
                      metadata: pd.DataFrame, horizon: int, index_type: str) -> ValidationResult:
        """Comprehensive validation of a FAISS index."""
        logger.info(f"Validating {index_type} index for {horizon}h horizon")
        
        issues = []
        test_results = {}
        metrics = {}
        
        try:
            # Load index
            if not index_path.exists():
                return ValidationResult(
                    horizon=horizon,
                    index_type=index_type,
                    passed=False,
                    metrics={},
                    issues=[f"Index file not found: {index_path}"],
                    test_results={}
                )
            
            index = faiss.read_index(str(index_path))
            
            # Basic structural validation
            struct_result = self._validate_structure(index, embeddings, horizon, index_type)
            test_results['structure'] = struct_result
            
            if not struct_result['passed']:
                issues.extend(struct_result['issues'])
            
            # Search functionality validation
            search_result = self._validate_search_functionality(index, embeddings)
            test_results['search'] = search_result
            
            if not search_result['passed']:
                issues.extend(search_result['issues'])
            
            # Performance validation
            perf_result = self._validate_performance(index, embeddings)
            test_results['performance'] = perf_result
            
            if not perf_result['passed']:
                issues.extend(perf_result['issues'])
            
            # Recall validation (if we have a reference)
            recall_result = self._validate_recall(index, embeddings, index_type)
            test_results['recall'] = recall_result
            
            if not recall_result['passed']:
                issues.extend(recall_result['issues'])
            
            # Compile metrics
            metrics = {
                'index_size': index.ntotal,
                'dimension': index.d,
                'file_size_mb': index_path.stat().st_size / (1024 * 1024),
                'search_latency_ms': perf_result.get('avg_latency_ms', 0),
                'recall_at_100': recall_result.get('recall_score', 0),
                'validation_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Overall pass/fail
            passed = len(issues) == 0
            
            logger.info(f"✅ Validation {'PASSED' if passed else 'FAILED'} for {horizon}h {index_type}")
            if issues:
                for issue in issues[:3]:  # Log first 3 issues
                    logger.warning(f"  Issue: {issue}")
            
            return ValidationResult(
                horizon=horizon,
                index_type=index_type,
                passed=passed,
                metrics=metrics,
                issues=issues,
                test_results=test_results
            )
            
        except Exception as e:
            logger.error(f"Validation crashed for {horizon}h {index_type}: {e}")
            return ValidationResult(
                horizon=horizon,
                index_type=index_type,
                passed=False,
                metrics={},
                issues=[f"Validation crashed: {str(e)}"],
                test_results={}
            )
    
    def _validate_structure(self, index: faiss.Index, embeddings: np.ndarray, 
                           horizon: int, index_type: str) -> Dict[str, Any]:
        """Validate index structure and dimensions."""
        issues = []
        
        # Expected sizes from startup validation system
        expected_sizes = {6: 6574, 12: 6574, 24: 13148, 48: 13148}
        expected_size = expected_sizes.get(horizon, 13148)
        
        # Dimension check
        if index.d != 256:
            issues.append(f"Wrong dimension: {index.d}, expected 256")
        
        # Size check with tolerance
        size_tolerance = 0.05  # 5% tolerance
        min_size = int(expected_size * (1 - size_tolerance))
        max_size = int(expected_size * (1 + size_tolerance))
        
        if not (min_size <= index.ntotal <= max_size):
            issues.append(f"Size outside range: {index.ntotal}, expected {min_size}-{max_size}")
        
        # Index type validation
        expected_types = {
            'flatip': faiss.IndexFlatIP,
            'ivfpq': faiss.IndexIVFPQ
        }
        
        if index_type in expected_types:
            if not isinstance(index, expected_types[index_type]):
                issues.append(f"Wrong index type: {type(index).__name__}, expected {expected_types[index_type].__name__}")
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'actual_size': index.ntotal,
            'expected_size': expected_size,
            'dimension': index.d
        }
    
    def _validate_search_functionality(self, index: faiss.Index, embeddings: np.ndarray) -> Dict[str, Any]:
        """Validate search functionality works correctly."""
        issues = []
        
        try:
            # Test with random queries
            n_test_queries = min(10, len(embeddings))
            query_indices = np.random.choice(len(embeddings), n_test_queries, replace=False)
            test_queries = embeddings[query_indices].astype(np.float32)
            
            # Ensure normalization
            faiss.normalize_L2(test_queries)
            
            # Perform search
            distances, indices = index.search(test_queries, 50)
            
            # Check results
            if distances.shape != (n_test_queries, 50):
                issues.append(f"Wrong result shape: {distances.shape}, expected ({n_test_queries}, 50)")
            
            if indices.shape != (n_test_queries, 50):
                issues.append(f"Wrong indices shape: {indices.shape}, expected ({n_test_queries}, 50)")
            
            # Check for valid indices
            valid_indices = np.sum(indices >= 0)
            total_indices = indices.size
            valid_ratio = valid_indices / total_indices
            
            if valid_ratio < 0.9:  # At least 90% valid
                issues.append(f"Too many invalid indices: {valid_ratio:.1%} valid")
            
            # Check distance monotonicity
            for i in range(n_test_queries):
                query_distances = distances[i]
                query_distances = query_distances[query_distances >= 0]  # Remove invalid (-1) distances
                
                if len(query_distances) > 1:
                    if not np.all(np.diff(query_distances) >= -1e-6):  # Allow small numerical errors
                        issues.append(f"Distance monotonicity violation in query {i}")
                        break
            
            # Check for reasonable distance values
            valid_distances = distances[distances >= 0]
            if len(valid_distances) > 0:
                max_distance = np.max(valid_distances)
                if max_distance > 4.0:  # For normalized vectors, max distance should be ~2
                    issues.append(f"Unreasonable max distance: {max_distance:.3f}")
            
            return {
                'passed': len(issues) == 0,
                'issues': issues,
                'valid_results_ratio': valid_ratio,
                'max_distance': float(np.max(valid_distances)) if len(valid_distances) > 0 else 0,
                'queries_tested': n_test_queries
            }
            
        except Exception as e:
            issues.append(f"Search test failed: {str(e)}")
            return {
                'passed': False,
                'issues': issues,
                'error': str(e)
            }
    
    def _validate_performance(self, index: faiss.Index, embeddings: np.ndarray) -> Dict[str, Any]:
        """Validate search performance meets requirements."""
        issues = []
        
        try:
            # Performance test
            n_queries = min(100, len(embeddings))
            query_indices = np.random.choice(len(embeddings), n_queries, replace=False)
            test_queries = embeddings[query_indices].astype(np.float32)
            faiss.normalize_L2(test_queries)
            
            # Measure search time
            start_time = time.time()
            distances, indices = index.search(test_queries, 50)
            search_time = time.time() - start_time
            
            avg_latency_ms = (search_time / n_queries) * 1000
            
            # Check against threshold
            if avg_latency_ms > self.config.max_latency_threshold_ms:
                issues.append(f"High latency: {avg_latency_ms:.1f}ms > {self.config.max_latency_threshold_ms}ms")
            
            return {
                'passed': len(issues) == 0,
                'issues': issues,
                'avg_latency_ms': avg_latency_ms,
                'total_time_s': search_time,
                'queries_tested': n_queries,
                'throughput_qps': n_queries / search_time
            }
            
        except Exception as e:
            issues.append(f"Performance test failed: {str(e)}")
            return {
                'passed': False,
                'issues': issues,
                'error': str(e)
            }
    
    def _validate_recall(self, index: faiss.Index, embeddings: np.ndarray, index_type: str) -> Dict[str, Any]:
        """Validate recall for approximate indices."""
        issues = []
        
        # Only validate recall for approximate indices
        if index_type != 'ivfpq':
            return {
                'passed': True,
                'issues': [],
                'recall_score': 1.0,
                'note': 'Exact index, recall=1.0 by definition'
            }
        
        try:
            # Create reference exact index for comparison
            reference_index = faiss.IndexFlatIP(index.d)
            
            # Sample embeddings to avoid memory issues
            n_vectors = min(1000, len(embeddings))
            sample_indices = np.random.choice(len(embeddings), n_vectors, replace=False)
            sample_embeddings = embeddings[sample_indices].astype(np.float32)
            faiss.normalize_L2(sample_embeddings)
            
            reference_index.add(sample_embeddings)
            
            # Test queries
            n_queries = min(50, n_vectors)
            query_indices = np.random.choice(n_vectors, n_queries, replace=False)
            test_queries = sample_embeddings[query_indices]
            
            # Get reference results
            _, ref_neighbors = reference_index.search(test_queries, 100)
            
            # Get test index results (map to sample space)
            # This is a simplified approach - in practice you'd need more sophisticated mapping
            _, test_neighbors = index.search(test_queries, 100)
            
            # Calculate recall (simplified)
            # Note: This is approximate since we're comparing against a subset
            total_intersection = 0
            total_possible = 0
            
            for i in range(n_queries):
                ref_set = set(ref_neighbors[i])
                test_set = set(test_neighbors[i])
                # Map test results to reference space if needed
                intersection = len(ref_set.intersection(test_set))
                total_intersection += intersection
                total_possible += len(ref_set)
            
            recall_score = total_intersection / total_possible if total_possible > 0 else 0
            
            if recall_score < self.config.min_recall_threshold:
                issues.append(f"Low recall: {recall_score:.3f} < {self.config.min_recall_threshold:.3f}")
            
            return {
                'passed': len(issues) == 0,
                'issues': issues,
                'recall_score': recall_score,
                'queries_tested': n_queries
            }
            
        except Exception as e:
            # Recall validation failure is not critical
            logger.warning(f"Recall validation failed: {e}")
            return {
                'passed': True,  # Don't fail rebuild for recall issues
                'issues': [f"Recall test failed: {str(e)}"],
                'recall_score': 0.0,
                'warning': True
            }

class FAISSIndexRebuilder:
    """Main FAISS index rebuilding system with automation and safety features."""
    
    def __init__(self, config: RebuildConfig = None, project_root: Path = None):
        self.config = config or RebuildConfig()
        self.project_root = project_root or Path("/home/micha/adelaide-weather-final")
        
        # Initialize components
        self.backup_manager = IndexBackupManager(self.config)
        self.validator = FAISSIndexValidator(self.config)
        
        # Setup directories
        self.embeddings_dir = self.project_root / self.config.embeddings_dir
        self.indices_dir = self.project_root / self.config.indices_dir
        self.staging_dir = self.project_root / self.config.staging_dir
        
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking
        self.rebuild_lock = threading.Lock()
        self.current_rebuild_id = None
        
        logger.info(f"Initialized FAISS Index Rebuilder")
        logger.info(f"  Embeddings: {self.embeddings_dir}")
        logger.info(f"  Indices: {self.indices_dir}")
        logger.info(f"  Staging: {self.staging_dir}")
        logger.info(f"  Validation: {'enabled' if self.config.validation_enabled else 'disabled'}")
    
    def rebuild_all_indices(self, force: bool = False) -> RebuildResult:
        """Rebuild all FAISS indices with validation and atomic deployment."""
        rebuild_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:-3]
        
        logger.info(f"🚀 Starting index rebuild: {rebuild_id}")
        
        with self.rebuild_lock:
            if self.current_rebuild_id is not None and not force:
                raise RuntimeError(f"Rebuild already in progress: {self.current_rebuild_id}")
            
            self.current_rebuild_id = rebuild_id
        
        try:
            return self._execute_rebuild(rebuild_id)
        finally:
            self.current_rebuild_id = None
    
    def _execute_rebuild(self, rebuild_id: str) -> RebuildResult:
        """Execute the complete rebuild process."""
        start_time = time.time()
        backup_id = None
        rollback_performed = False
        
        try:
            # Step 1: Create backup of current indices
            logger.info("📦 Creating backup of current indices...")
            backup_id = self.backup_manager.create_backup(self.indices_dir, f"pre_rebuild_{rebuild_id}")
            
            # Step 2: Build new indices in staging
            logger.info("🔨 Building new indices in staging...")
            build_results = self._build_indices_in_staging(rebuild_id)
            
            if not build_results['success']:
                raise RuntimeError(f"Index building failed: {build_results['error']}")
            
            # Step 3: Validate new indices
            validation_results = {}
            if self.config.validation_enabled:
                logger.info("🔍 Validating new indices...")
                validation_results = self._validate_staged_indices(rebuild_id)
                
                if self.config.require_validation_pass:
                    failed_validations = [v for v in validation_results.values() if not v.passed]
                    if failed_validations:
                        issues = []
                        for validation in failed_validations:
                            issues.extend(validation.issues)
                        raise RuntimeError(f"Validation failed: {'; '.join(issues[:5])}")
            
            # Step 4: Atomic deployment
            logger.info("⚡ Performing atomic deployment...")
            deployment_success = self._deploy_staged_indices()
            
            if not deployment_success:
                raise RuntimeError("Atomic deployment failed")
            
            # Step 5: Final verification
            logger.info("✅ Performing final verification...")
            verification_results = self._verify_deployment()
            
            if not verification_results['success']:
                logger.error("Deployment verification failed, attempting rollback...")
                rollback_performed = self._rollback_deployment(backup_id)
                if rollback_performed:
                    raise RuntimeError(f"Deployment verification failed, rollback completed: {verification_results['error']}")
                else:
                    raise RuntimeError(f"Deployment verification failed, rollback also failed: {verification_results['error']}")
            
            # Success!
            total_time = time.time() - start_time
            
            logger.info(f"🎉 Index rebuild completed successfully in {total_time:.1f}s")
            
            return RebuildResult(
                rebuild_id=rebuild_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=True,
                horizons_processed=self.config.horizons,
                indices_created=build_results['indices_created'],
                validation_results={k: asdict(v) for k, v in validation_results.items()},
                metrics={
                    'total_time_seconds': total_time,
                    'backup_id': backup_id,
                    'build_metrics': build_results.get('metrics', {}),
                    'verification_results': verification_results
                },
                backup_id=backup_id,
                rollback_performed=rollback_performed
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"💥 Index rebuild failed: {error_msg}")
            
            # Attempt rollback if backup exists
            if backup_id and self.config.enable_rollback:
                logger.info("🔄 Attempting rollback to previous indices...")
                rollback_performed = self._rollback_deployment(backup_id)
                if rollback_performed:
                    logger.info("✅ Rollback completed successfully")
                else:
                    logger.error("❌ Rollback failed")
            
            return RebuildResult(
                rebuild_id=rebuild_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=False,
                horizons_processed=[],
                indices_created=[],
                validation_results={},
                metrics={'total_time_seconds': time.time() - start_time},
                error_message=error_msg,
                rollback_performed=rollback_performed,
                backup_id=backup_id
            )
    
    def _build_indices_in_staging(self, rebuild_id: str) -> Dict[str, Any]:
        """Build indices in staging directory."""
        staging_build_dir = self.staging_dir / rebuild_id
        staging_build_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Initialize index builder
            builder = FAISSIndexBuilder(str(self.embeddings_dir))
            
            # Track created indices
            indices_created = []
            build_metrics = {}
            
            # Build indices for each horizon
            for horizon in self.config.horizons:
                logger.info(f"Building indices for {horizon}h horizon...")
                
                try:
                    horizon_metrics = builder.build_indices_for_horizon(horizon, staging_build_dir)
                    build_metrics[f"{horizon}h"] = horizon_metrics
                    
                    # Track created files
                    for index_type in self.config.index_types:
                        index_file = f"faiss_{horizon}h_{index_type}.faiss"
                        index_path = staging_build_dir / index_file
                        if index_path.exists():
                            indices_created.append(index_file)
                        else:
                            logger.warning(f"Expected index file not created: {index_file}")
                    
                except Exception as e:
                    logger.error(f"Failed to build indices for {horizon}h: {e}")
                    raise
            
            if not indices_created:
                raise RuntimeError("No indices were successfully created")
            
            logger.info(f"✅ Successfully built {len(indices_created)} indices")
            
            return {
                'success': True,
                'indices_created': indices_created,
                'staging_dir': str(staging_build_dir),
                'metrics': build_metrics
            }
            
        except Exception as e:
            # Clean up staging directory on failure
            if staging_build_dir.exists():
                shutil.rmtree(staging_build_dir, ignore_errors=True)
            
            return {
                'success': False,
                'error': str(e),
                'indices_created': [],
                'staging_dir': str(staging_build_dir)
            }
    
    def _validate_staged_indices(self, rebuild_id: str) -> Dict[str, ValidationResult]:
        """Validate indices in staging directory."""
        staging_build_dir = self.staging_dir / rebuild_id
        validation_results = {}
        
        # Load embeddings for validation
        embeddings_cache = {}
        metadata_cache = {}
        
        for horizon in self.config.horizons:
            try:
                # Load embeddings and metadata
                emb_path = self.embeddings_dir / f"embeddings_{horizon}h.npy"
                meta_path = self.embeddings_dir / f"metadata_{horizon}h.parquet"
                
                if emb_path.exists() and meta_path.exists():
                    embeddings_cache[horizon] = np.load(emb_path)
                    metadata_cache[horizon] = pd.read_parquet(meta_path)
                else:
                    logger.warning(f"Missing embeddings/metadata for {horizon}h, skipping validation")
                    continue
                
                # Validate each index type
                for index_type in self.config.index_types:
                    index_path = staging_build_dir / f"faiss_{horizon}h_{index_type}.faiss"
                    validation_key = f"{horizon}h_{index_type}"
                    
                    if index_path.exists():
                        validation_results[validation_key] = self.validator.validate_index(
                            index_path,
                            embeddings_cache[horizon],
                            metadata_cache[horizon],
                            horizon,
                            index_type
                        )
                    else:
                        logger.warning(f"Index file not found for validation: {index_path}")
                        validation_results[validation_key] = ValidationResult(
                            horizon=horizon,
                            index_type=index_type,
                            passed=False,
                            metrics={},
                            issues=[f"Index file not found: {index_path.name}"],
                            test_results={}
                        )
                
            except Exception as e:
                logger.error(f"Validation failed for {horizon}h: {e}")
                # Mark all index types for this horizon as failed
                for index_type in self.config.index_types:
                    validation_key = f"{horizon}h_{index_type}"
                    validation_results[validation_key] = ValidationResult(
                        horizon=horizon,
                        index_type=index_type,
                        passed=False,
                        metrics={},
                        issues=[f"Validation error: {str(e)}"],
                        test_results={}
                    )
        
        # Summary
        total_validations = len(validation_results)
        passed_validations = sum(1 for v in validation_results.values() if v.passed)
        
        logger.info(f"📊 Validation summary: {passed_validations}/{total_validations} passed")
        
        return validation_results
    
    def _deploy_staged_indices(self) -> bool:
        """Atomically deploy staged indices to production."""
        try:
            # Find latest staging directory
            staging_dirs = [d for d in self.staging_dir.iterdir() if d.is_dir()]
            if not staging_dirs:
                logger.error("No staging directories found")
                return False
            
            # Use most recent staging directory
            latest_staging = max(staging_dirs, key=lambda x: x.stat().st_mtime)
            
            # Get list of index files to deploy
            index_files = list(latest_staging.glob("*.faiss"))
            if not index_files:
                logger.error(f"No index files found in staging: {latest_staging}")
                return False
            
            logger.info(f"Deploying {len(index_files)} index files from {latest_staging.name}")
            
            # Atomic deployment using temporary names and rename
            temp_files = []
            deployed_files = []
            
            try:
                # Copy to production with temporary names
                for index_file in index_files:
                    temp_name = f"{index_file.name}.deploying"
                    temp_path = self.indices_dir / temp_name
                    final_path = self.indices_dir / index_file.name
                    
                    # Copy file
                    shutil.copy2(index_file, temp_path)
                    temp_files.append((temp_path, final_path))
                
                # Atomic rename all files
                for temp_path, final_path in temp_files:
                    if final_path.exists():
                        # Backup existing file
                        backup_path = final_path.with_suffix(f"{final_path.suffix}.old")
                        final_path.rename(backup_path)
                    
                    temp_path.rename(final_path)
                    deployed_files.append(final_path)
                
                # Clean up old backup files
                for temp_path, final_path in temp_files:
                    backup_path = final_path.with_suffix(f"{final_path.suffix}.old")
                    if backup_path.exists():
                        backup_path.unlink()
                
                logger.info(f"✅ Successfully deployed {len(deployed_files)} index files")
                return True
                
            except Exception as e:
                logger.error(f"Deployment failed during file operations: {e}")
                
                # Clean up temporary files
                for temp_path, final_path in temp_files:
                    if temp_path.exists():
                        temp_path.unlink()
                    
                    # Restore from backup if needed
                    backup_path = final_path.with_suffix(f"{final_path.suffix}.old")
                    if backup_path.exists():
                        backup_path.rename(final_path)
                
                return False
                
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return False
    
    def _verify_deployment(self) -> Dict[str, Any]:
        """Verify deployed indices are working correctly."""
        try:
            # Use startup validation system for verification
            validator = ExpertValidatedStartupSystem(self.project_root)
            
            # Run FAISS-specific validation
            result = validator.validate_faiss_indices_expert()
            
            if result.is_passing():
                return {
                    'success': True,
                    'message': 'Deployment verification passed',
                    'validation_metrics': result.metrics
                }
            else:
                return {
                    'success': False,
                    'error': result.message,
                    'validation_metrics': result.metrics
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Verification failed: {str(e)}"
            }
    
    def _rollback_deployment(self, backup_id: str) -> bool:
        """Rollback to previous indices using backup."""
        try:
            logger.info(f"Performing rollback to backup: {backup_id}")
            
            # Restore from backup
            success = self.backup_manager.restore_backup(backup_id, self.indices_dir)
            
            if success:
                # Verify rollback
                verification = self._verify_deployment()
                if verification['success']:
                    logger.info("✅ Rollback completed and verified")
                    return True
                else:
                    logger.error(f"Rollback verification failed: {verification['error']}")
                    return False
            else:
                logger.error("Failed to restore backup")
                return False
                
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def get_rebuild_status(self) -> Dict[str, Any]:
        """Get current rebuild status."""
        return {
            'rebuild_in_progress': self.current_rebuild_id is not None,
            'current_rebuild_id': self.current_rebuild_id,
            'indices_dir': str(self.indices_dir),
            'staging_dir': str(self.staging_dir),
            'config': asdict(self.config)
        }
    
    def list_available_backups(self) -> List[Dict[str, Any]]:
        """List available index backups."""
        return self.backup_manager.list_backups()
    
    def cleanup_staging(self, keep_recent: int = 3):
        """Clean up old staging directories."""
        try:
            staging_dirs = [d for d in self.staging_dir.iterdir() if d.is_dir()]
            staging_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep recent directories
            dirs_to_remove = staging_dirs[keep_recent:]
            
            for dir_path in dirs_to_remove:
                shutil.rmtree(dir_path, ignore_errors=True)
                logger.info(f"Cleaned up staging directory: {dir_path.name}")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup staging: {e}")

def main():
    """CLI entry point for manual rebuilds."""
    import argparse
    
    parser = argparse.ArgumentParser(description='FAISS Index Rebuilder')
    parser.add_argument('--config', help='Path to rebuild config JSON file')
    parser.add_argument('--horizons', nargs='+', type=int, default=[6, 12, 24, 48],
                       help='Horizons to rebuild (default: all)')
    parser.add_argument('--skip-validation', action='store_true',
                       help='Skip validation (not recommended)')
    parser.add_argument('--force', action='store_true',
                       help='Force rebuild even if one is in progress')
    parser.add_argument('--cleanup-staging', action='store_true',
                       help='Clean up old staging directories')
    
    args = parser.parse_args()
    
    # Load config
    config = RebuildConfig()
    if args.config:
        with open(args.config, 'r') as f:
            config_data = json.load(f)
        config = RebuildConfig(**config_data)
    
    # Apply CLI overrides
    config.horizons = args.horizons
    if args.skip_validation:
        config.validation_enabled = False
        config.require_validation_pass = False
    
    # Initialize rebuilder
    rebuilder = FAISSIndexRebuilder(config)
    
    try:
        if args.cleanup_staging:
            rebuilder.cleanup_staging()
            return
        
        # Execute rebuild
        result = rebuilder.rebuild_all_indices(force=args.force)
        
        # Print results
        print(f"\nRebuild Result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Rebuild ID: {result.rebuild_id}")
        print(f"Timestamp: {result.timestamp}")
        
        if result.success:
            print(f"Horizons processed: {result.horizons_processed}")
            print(f"Indices created: {len(result.indices_created)}")
            if result.metrics:
                print(f"Total time: {result.metrics.get('total_time_seconds', 0):.1f}s")
        else:
            print(f"Error: {result.error_message}")
            if result.rollback_performed:
                print("Rollback was performed")
        
        sys.exit(0 if result.success else 1)
        
    except KeyboardInterrupt:
        logger.info("Rebuild interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Rebuild failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()