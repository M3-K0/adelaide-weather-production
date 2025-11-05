#!/usr/bin/env python3
"""
FAISS Index Validation and Metadata Framework
==============================================

Comprehensive validation system for FAISS index consistency, data alignment,
and performance verification in the Adelaide Weather Forecasting System.

Features:
- Index-embeddings-outcomes alignment verification
- Dataset hash consistency checking
- Index metadata generation and validation
- Performance regression testing
- Data type precision validation
- Embedding normalization verification

Usage:
    from core.index_validator import IndexValidator
    
    validator = IndexValidator()
    results = validator.validate_all_indices()
    validator.generate_validation_report(results)
"""

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

import numpy as np
import pandas as pd
import faiss
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)

@dataclass
class IndexMetadata:
    """Metadata container for FAISS index validation."""
    horizon: int
    creation_date: str
    index_type: str  # 'flatip' or 'ivfpq'
    total_patterns: int
    embedding_dimension: int
    
    # Dataset hashes for consistency
    embeddings_hash: str
    outcomes_hash: str
    metadata_hash: str
    
    # Data split information
    train_patterns: int
    test_patterns: int
    train_date_range: Tuple[str, str]
    test_date_range: Tuple[str, str]
    
    # Validation checksums
    embedding_norm_stats: Dict[str, float]
    index_performance: Dict[str, float]
    consistency_checks: Dict[str, bool]

@dataclass
class ValidationResult:
    """Container for validation results."""
    horizon: int
    index_type: str
    valid: bool
    errors: List[str]
    warnings: List[str]
    performance_metrics: Dict[str, float]
    consistency_scores: Dict[str, float]

class IndexValidator:
    """Comprehensive FAISS index validation framework."""
    
    def __init__(self, 
                 embeddings_dir: Path = Path("embeddings"),
                 outcomes_dir: Path = Path("outcomes"),
                 indices_dir: Path = Path("indices")):
        self.embeddings_dir = embeddings_dir
        self.outcomes_dir = outcomes_dir
        self.indices_dir = indices_dir
        self.horizons = [6, 12, 24, 48]
        self.index_types = ['flatip', 'ivfpq']
        
        # Performance thresholds
        self.performance_thresholds = {
            'max_latency_ms': 150,  # <150ms pipeline requirement
            'min_recall_at_100': 0.95,  # IVF-PQ vs FlatIP recall
            'max_embedding_norm_std': 1e-5,  # Normalization consistency
            'min_self_match_rate': 0.99,  # Self-search accuracy
        }
    
    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file for consistency checking."""
        if not file_path.exists():
            return ""
        
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()[:16]  # First 16 characters for brevity
    
    def compute_array_hash(self, array: np.ndarray) -> str:
        """Compute hash of numpy array content."""
        # Convert to consistent format for hashing
        array_bytes = array.astype(np.float32).tobytes()
        hash_sha256 = hashlib.sha256(array_bytes)
        return hash_sha256.hexdigest()[:16]
    
    def validate_data_alignment(self, horizon: int) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Validate alignment between embeddings, outcomes, and indices."""
        errors = []
        alignment_info = {}
        
        # Load all data components
        try:
            # Embeddings
            emb_path = self.embeddings_dir / f"embeddings_{horizon}h.npy"
            embeddings = np.load(emb_path, mmap_mode='r')
            
            # Outcomes  
            out_path = self.outcomes_dir / f"outcomes_{horizon}h.npy"
            outcomes = np.load(out_path, mmap_mode='r')
            
            # Metadata
            meta_path = self.embeddings_dir / f"metadata_{horizon}h.parquet"
            metadata = pd.read_parquet(meta_path)
            
            # FAISS indices
            flatip_path = self.indices_dir / f"faiss_{horizon}h_flatip.faiss"
            if flatip_path.exists():
                flatip_index = faiss.read_index(str(flatip_path))
            else:
                flatip_index = None
                errors.append(f"FlatIP index not found: {flatip_path}")
            
        except Exception as e:
            errors.append(f"Failed to load data: {e}")
            return False, errors, {}
        
        # Check basic alignment
        alignment_info['embeddings_shape'] = embeddings.shape
        alignment_info['outcomes_shape'] = outcomes.shape
        alignment_info['metadata_length'] = len(metadata)
        
        if embeddings.shape[0] != outcomes.shape[0]:
            errors.append(f"Embeddings-outcomes size mismatch: {embeddings.shape[0]} vs {outcomes.shape[0]}")
        
        if embeddings.shape[0] != len(metadata):
            errors.append(f"Embeddings-metadata size mismatch: {embeddings.shape[0]} vs {len(metadata)}")
        
        # Check train/test split consistency
        if not pd.api.types.is_datetime64_any_dtype(metadata['init_time']):
            metadata['init_time'] = pd.to_datetime(metadata['init_time'])
        
        years = metadata['init_time'].dt.year
        train_mask = years <= 2018
        train_indices = np.where(train_mask)[0]
        test_indices = np.where(~train_mask)[0]
        
        alignment_info['total_samples'] = len(metadata)
        alignment_info['train_samples'] = len(train_indices)
        alignment_info['test_samples'] = len(test_indices)
        
        if flatip_index and flatip_index.ntotal != len(train_indices):
            errors.append(f"Index size mismatch: {flatip_index.ntotal} vs {len(train_indices)} training samples")
        
        # Check date ranges
        train_dates = metadata.iloc[train_indices]['init_time']
        test_dates = metadata.iloc[test_indices]['init_time']
        
        alignment_info['train_date_range'] = (train_dates.min().isoformat(), train_dates.max().isoformat())
        alignment_info['test_date_range'] = (test_dates.min().isoformat(), test_dates.max().isoformat())
        
        return len(errors) == 0, errors, alignment_info
    
    def validate_embedding_normalization(self, horizon: int) -> Tuple[bool, List[str], Dict[str, float]]:
        """Validate L2 normalization of embeddings."""
        errors = []
        norm_stats = {}
        
        try:
            emb_path = self.embeddings_dir / f"embeddings_{horizon}h.npy"
            embeddings = np.load(emb_path, mmap_mode='r')
            
            norms = np.linalg.norm(embeddings, axis=1)
            
            norm_stats = {
                'mean_norm': float(norms.mean()),
                'std_norm': float(norms.std()),
                'min_norm': float(norms.min()),
                'max_norm': float(norms.max()),
                'norm_deviation': float(np.abs(norms - 1.0).max())
            }
            
            # Check normalization
            if norm_stats['std_norm'] > self.performance_thresholds['max_embedding_norm_std']:
                errors.append(f"Embedding normalization inconsistent: std={norm_stats['std_norm']:.8f}")
            
            if norm_stats['norm_deviation'] > 1e-5:
                errors.append(f"Embeddings not properly normalized: max deviation={norm_stats['norm_deviation']:.8f}")
            
        except Exception as e:
            errors.append(f"Failed to validate normalization: {e}")
        
        return len(errors) == 0, errors, norm_stats
    
    def validate_index_performance(self, horizon: int, index_type: str) -> Tuple[bool, List[str], Dict[str, float]]:
        """Validate index search performance and accuracy."""
        errors = []
        perf_metrics = {}
        
        try:
            # Load index
            index_path = self.indices_dir / f"faiss_{horizon}h_{index_type}.faiss"
            if not index_path.exists():
                errors.append(f"Index not found: {index_path}")
                return False, errors, {}
            
            index = faiss.read_index(str(index_path))
            
            # Load embeddings for testing
            emb_path = self.embeddings_dir / f"embeddings_{horizon}h.npy"
            embeddings = np.load(emb_path, mmap_mode='r')
            
            # Get training indices
            meta_path = self.embeddings_dir / f"metadata_{horizon}h.parquet"
            metadata = pd.read_parquet(meta_path)
            
            if not pd.api.types.is_datetime64_any_dtype(metadata['init_time']):
                metadata['init_time'] = pd.to_datetime(metadata['init_time'])
            
            years = metadata['init_time'].dt.year
            train_mask = years <= 2018
            train_indices = np.where(train_mask)[0]
            
            # Performance test: latency
            n_queries = min(50, len(train_indices))
            query_indices = np.random.choice(train_indices, n_queries, replace=False)
            query_embeddings = embeddings[query_indices].astype(np.float32)
            
            start_time = time.time()
            distances, indices = index.search(query_embeddings, 100)
            search_time = time.time() - start_time
            
            latency_ms = (search_time / n_queries) * 1000
            perf_metrics['latency_per_query_ms'] = latency_ms
            perf_metrics['throughput_qps'] = n_queries / search_time
            
            if latency_ms > self.performance_thresholds['max_latency_ms']:
                errors.append(f"Search latency too high: {latency_ms:.1f}ms > {self.performance_thresholds['max_latency_ms']}ms")
            
            # Accuracy test: self-matching
            self_matches = 0
            unique_neighbors = set()
            
            for i, query_idx in enumerate(query_indices[:10]):  # Test first 10
                expected_faiss_idx = np.where(train_indices == query_idx)[0][0]
                closest_faiss_idx = indices[i, 0]
                closest_distance = distances[i, 0]
                
                if closest_faiss_idx == expected_faiss_idx and closest_distance > 0.99:
                    self_matches += 1
                
                # Collect unique neighbors for diversity check
                unique_neighbors.update(indices[i, :10])
            
            self_match_rate = self_matches / min(10, len(query_indices))
            perf_metrics['self_match_rate'] = self_match_rate
            perf_metrics['unique_neighbors_ratio'] = len(unique_neighbors) / (min(10, len(query_indices)) * 10)
            
            if self_match_rate < self.performance_thresholds['min_self_match_rate']:
                errors.append(f"Self-match rate too low: {self_match_rate:.3f} < {self.performance_thresholds['min_self_match_rate']}")
            
            # Similarity variance check
            mean_similarities = distances[:, :10].mean(axis=1)
            perf_metrics['mean_similarity'] = float(mean_similarities.mean())
            perf_metrics['similarity_std'] = float(mean_similarities.std())
            
        except Exception as e:
            errors.append(f"Performance validation failed: {e}")
        
        return len(errors) == 0, errors, perf_metrics
    
    def generate_index_metadata(self, horizon: int, index_type: str) -> Optional[IndexMetadata]:
        """Generate comprehensive metadata for an index."""
        try:
            # File paths
            index_path = self.indices_dir / f"faiss_{horizon}h_{index_type}.faiss"
            emb_path = self.embeddings_dir / f"embeddings_{horizon}h.npy"
            out_path = self.outcomes_dir / f"outcomes_{horizon}h.npy"
            meta_path = self.embeddings_dir / f"metadata_{horizon}h.parquet"
            
            if not all(p.exists() for p in [index_path, emb_path, out_path, meta_path]):
                return None
            
            # Load data
            index = faiss.read_index(str(index_path))
            embeddings = np.load(emb_path, mmap_mode='r')
            outcomes = np.load(out_path, mmap_mode='r')
            metadata = pd.read_parquet(meta_path)
            
            # Compute hashes
            embeddings_hash = self.compute_array_hash(embeddings)
            outcomes_hash = self.compute_array_hash(outcomes)
            metadata_hash = self.compute_file_hash(meta_path)
            
            # Train/test split
            if not pd.api.types.is_datetime64_any_dtype(metadata['init_time']):
                metadata['init_time'] = pd.to_datetime(metadata['init_time'])
            
            years = metadata['init_time'].dt.year
            train_mask = years <= 2018
            train_indices = np.where(train_mask)[0]
            test_indices = np.where(~train_mask)[0]
            
            train_dates = metadata.iloc[train_indices]['init_time']
            test_dates = metadata.iloc[test_indices]['init_time']
            
            # Embedding normalization stats
            norms = np.linalg.norm(embeddings, axis=1)
            norm_stats = {
                'mean': float(norms.mean()),
                'std': float(norms.std()),
                'min': float(norms.min()),
                'max': float(norms.max())
            }
            
            # Basic performance metrics
            _, _, perf_metrics = self.validate_index_performance(horizon, index_type)
            
            # Consistency checks
            _, errors, _ = self.validate_data_alignment(horizon)
            _, norm_errors, _ = self.validate_embedding_normalization(horizon)
            
            consistency_checks = {
                'data_alignment': len(errors) == 0,
                'normalization': len(norm_errors) == 0,
                'index_size_match': index.ntotal == len(train_indices),
                'dimension_match': index.d == embeddings.shape[1]
            }
            
            return IndexMetadata(
                horizon=horizon,
                creation_date=datetime.now().isoformat(),
                index_type=index_type,
                total_patterns=index.ntotal,
                embedding_dimension=index.d,
                embeddings_hash=embeddings_hash,
                outcomes_hash=outcomes_hash,
                metadata_hash=metadata_hash,
                train_patterns=len(train_indices),
                test_patterns=len(test_indices),
                train_date_range=(train_dates.min().isoformat(), train_dates.max().isoformat()),
                test_date_range=(test_dates.min().isoformat(), test_dates.max().isoformat()),
                embedding_norm_stats=norm_stats,
                index_performance=perf_metrics,
                consistency_checks=consistency_checks
            )
            
        except Exception as e:
            logger.error(f"Failed to generate metadata for {horizon}h {index_type}: {e}")
            return None
    
    def validate_single_index(self, horizon: int, index_type: str) -> ValidationResult:
        """Validate a single FAISS index comprehensively."""
        errors = []
        warnings = []
        performance_metrics = {}
        consistency_scores = {}
        
        # Data alignment validation
        alignment_valid, alignment_errors, alignment_info = self.validate_data_alignment(horizon)
        errors.extend(alignment_errors)
        consistency_scores['data_alignment'] = 1.0 if alignment_valid else 0.0
        
        # Normalization validation
        norm_valid, norm_errors, norm_stats = self.validate_embedding_normalization(horizon)
        errors.extend(norm_errors)
        consistency_scores['normalization'] = 1.0 if norm_valid else 0.0
        performance_metrics.update(norm_stats)
        
        # Performance validation
        perf_valid, perf_errors, perf_metrics = self.validate_index_performance(horizon, index_type)
        errors.extend(perf_errors)
        consistency_scores['performance'] = 1.0 if perf_valid else 0.0
        performance_metrics.update(perf_metrics)
        
        # Overall validation result
        overall_valid = len(errors) == 0
        
        return ValidationResult(
            horizon=horizon,
            index_type=index_type,
            valid=overall_valid,
            errors=errors,
            warnings=warnings,
            performance_metrics=performance_metrics,
            consistency_scores=consistency_scores
        )
    
    def validate_all_indices(self) -> Dict[str, ValidationResult]:
        """Validate all FAISS indices in the system."""
        results = {}
        
        for horizon in self.horizons:
            for index_type in self.index_types:
                index_path = self.indices_dir / f"faiss_{horizon}h_{index_type}.faiss"
                if index_path.exists():
                    key = f"{horizon}h_{index_type}"
                    results[key] = self.validate_single_index(horizon, index_type)
                    logger.info(f"Validated {key}: {'✅' if results[key].valid else '❌'}")
        
        return results
    
    def generate_metadata_sidecars(self) -> Dict[str, IndexMetadata]:
        """Generate metadata sidecar files for all indices."""
        metadata_files = {}
        
        for horizon in self.horizons:
            for index_type in self.index_types:
                metadata = self.generate_index_metadata(horizon, index_type)
                if metadata:
                    key = f"{horizon}h_{index_type}"
                    metadata_files[key] = metadata
                    
                    # Save to file
                    output_path = self.indices_dir / f"faiss_{horizon}h_{index_type}.metadata.json"
                    with open(output_path, 'w') as f:
                        json.dump(asdict(metadata), f, indent=2)
                    
                    logger.info(f"Generated metadata: {output_path}")
        
        return metadata_files
    
    def generate_validation_report(self, results: Dict[str, ValidationResult]) -> str:
        """Generate a comprehensive validation report."""
        lines = ["🔍 FAISS INDEX VALIDATION REPORT"]
        lines.append("=" * 50)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")
        
        # Summary
        total_indices = len(results)
        valid_indices = sum(1 for r in results.values() if r.valid)
        
        lines.append(f"📊 SUMMARY")
        lines.append(f"   Total indices: {total_indices}")
        lines.append(f"   Valid indices: {valid_indices}")
        lines.append(f"   Invalid indices: {total_indices - valid_indices}")
        lines.append(f"   Success rate: {valid_indices/total_indices*100:.1f}%")
        lines.append("")
        
        # Per-index results
        for key, result in results.items():
            status = "✅ VALID" if result.valid else "❌ INVALID"
            lines.append(f"🔍 {key.upper()}: {status}")
            
            # Performance metrics
            if result.performance_metrics:
                latency = result.performance_metrics.get('latency_per_query_ms', 0)
                self_match = result.performance_metrics.get('self_match_rate', 0)
                lines.append(f"   🚀 Performance: {latency:.1f}ms latency, {self_match:.1%} self-match rate")
            
            # Consistency scores
            if result.consistency_scores:
                avg_score = np.mean(list(result.consistency_scores.values()))
                lines.append(f"   📏 Consistency: {avg_score:.1%} average score")
            
            # Errors and warnings
            if result.errors:
                lines.append(f"   ❌ Errors ({len(result.errors)}):")
                for error in result.errors[:3]:  # Show first 3 errors
                    lines.append(f"      • {error}")
                if len(result.errors) > 3:
                    lines.append(f"      • ... and {len(result.errors)-3} more")
            
            if result.warnings:
                lines.append(f"   ⚠️  Warnings ({len(result.warnings)}):")
                for warning in result.warnings[:2]:
                    lines.append(f"      • {warning}")
            
            lines.append("")
        
        # Performance summary
        latencies = [r.performance_metrics.get('latency_per_query_ms', 0) 
                    for r in results.values() if r.performance_metrics]
        if latencies:
            lines.append(f"⚡ PERFORMANCE ANALYSIS")
            lines.append(f"   Average latency: {np.mean(latencies):.1f}ms")
            lines.append(f"   Max latency: {np.max(latencies):.1f}ms")
            lines.append(f"   Threshold compliance: {sum(1 for l in latencies if l <= 150)} / {len(latencies)} indices")
            lines.append("")
        
        # Recommendations
        lines.append(f"💡 RECOMMENDATIONS")
        if valid_indices == total_indices:
            lines.append("   ✅ All indices are valid and performing well")
            lines.append("   🔄 Continue regular validation checks")
        else:
            lines.append("   🔧 Address validation errors in failing indices")
            lines.append("   📈 Monitor performance metrics for degradation")
            if latencies and np.max(latencies) > 150:
                lines.append("   ⚡ Optimize indices exceeding 150ms latency threshold")
        
        return "\n".join(lines)
    
    def save_validation_report(self, results: Dict[str, ValidationResult], 
                              output_path: Path = None) -> Path:
        """Save validation report to file."""
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.indices_dir / f"validation_report_{timestamp}.txt"
        
        report = self.generate_validation_report(results)
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Validation report saved: {output_path}")
        return output_path


def main():
    """CLI interface for index validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate FAISS indices')
    parser.add_argument('--embeddings', default='embeddings/', help='Embeddings directory')
    parser.add_argument('--outcomes', default='outcomes/', help='Outcomes directory')
    parser.add_argument('--indices', default='indices/', help='Indices directory')
    parser.add_argument('--generate-metadata', action='store_true', help='Generate metadata sidecars')
    parser.add_argument('--output', help='Output path for validation report')
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = IndexValidator(
        embeddings_dir=Path(args.embeddings),
        outcomes_dir=Path(args.outcomes),
        indices_dir=Path(args.indices)
    )
    
    # Generate metadata if requested
    if args.generate_metadata:
        print("🔧 Generating index metadata sidecars...")
        metadata = validator.generate_metadata_sidecars()
        print(f"✅ Generated metadata for {len(metadata)} indices")
    
    # Run validation
    print("🔍 Validating all FAISS indices...")
    results = validator.validate_all_indices()
    
    # Generate and save report
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = None
    
    report_path = validator.save_validation_report(results, output_path)
    
    # Print summary
    valid_count = sum(1 for r in results.values() if r.valid)
    total_count = len(results)
    
    print(f"\n📊 Validation Summary:")
    print(f"   Valid indices: {valid_count}/{total_count}")
    print(f"   Report saved: {report_path}")
    
    if valid_count == total_count:
        print("✅ All indices are valid!")
    else:
        print("❌ Some indices have validation errors")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())