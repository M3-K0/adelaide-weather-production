#!/usr/bin/env python3
"""
Data Artifacts and FAISS Indices Verification Script
==================================================

Comprehensive verification of all required data artifacts for the Adelaide Weather system:
- FAISS indices availability and integrity
- Embeddings data files and formats
- Outcomes data for analog forecasting
- Configuration path validation
- Data loading performance testing
- Memory usage analysis
"""

import numpy as np
import pandas as pd
import os
from pathlib import Path
import time
import json
from typing import Dict, List, Tuple, Any

# Try to import faiss, fallback if not available
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("⚠️ FAISS not available, will skip FAISS tests")

# Try to import psutil, fallback if not available  
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️ psutil not available, will skip memory analysis")

def check_file_permissions(file_path: Path) -> Dict[str, Any]:
    """Check file permissions and accessibility."""
    try:
        stat = file_path.stat()
        return {
            "exists": True,
            "readable": os.access(file_path, os.R_OK),
            "size_mb": stat.st_size / (1024 * 1024),
            "modified": stat.st_mtime,
            "permissions": oct(stat.st_mode)[-3:]
        }
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }

def test_faiss_index_loading(index_path: Path) -> Dict[str, Any]:
    """Test loading and basic operations on FAISS index."""
    if not FAISS_AVAILABLE:
        return {
            "loaded_successfully": False,
            "error": "FAISS not available"
        }
    
    try:
        start_time = time.time()
        
        # Load index
        index = faiss.read_index(str(index_path))
        load_time = time.time() - start_time
        
        # Get index properties
        result = {
            "loaded_successfully": True,
            "load_time_ms": load_time * 1000,
            "total_vectors": index.ntotal,
            "vector_dimension": index.d,
            "index_type": type(index).__name__,
            "is_trained": index.is_trained if hasattr(index, 'is_trained') else "N/A",
            "memory_usage_mb": 0  # Will be estimated
        }
        
        # Test search functionality
        if index.ntotal > 0:
            # Create a dummy query vector
            query = np.random.rand(1, index.d).astype(np.float32)
            start_search = time.time()
            distances, indices = index.search(query, min(10, index.ntotal))
            search_time = time.time() - start_search
            
            result["search_test"] = {
                "search_time_ms": search_time * 1000,
                "returned_results": len(indices[0]),
                "valid_indices": all(idx >= 0 for idx in indices[0])
            }
        
        return result
        
    except Exception as e:
        return {
            "loaded_successfully": False,
            "error": str(e)
        }

def test_numpy_array_loading(array_path: Path) -> Dict[str, Any]:
    """Test loading NumPy array and verify format."""
    try:
        start_time = time.time()
        
        # Load array with memory mapping for large files
        if array_path.stat().st_size > 50 * 1024 * 1024:  # > 50MB
            array = np.load(array_path, mmap_mode='r')
        else:
            array = np.load(array_path)
            
        load_time = time.time() - start_time
        
        return {
            "loaded_successfully": True,
            "load_time_ms": load_time * 1000,
            "shape": array.shape,
            "dtype": str(array.dtype),
            "memory_usage_mb": array.nbytes / (1024 * 1024),
            "has_nan": bool(np.isnan(array).any()) if array.size < 1000000 else "skipped_large_array",
            "has_inf": bool(np.isinf(array).any()) if array.size < 1000000 else "skipped_large_array",
            "min_value": float(np.min(array)) if array.size < 1000000 else "skipped_large_array",
            "max_value": float(np.max(array)) if array.size < 1000000 else "skipped_large_array"
        }
        
    except Exception as e:
        return {
            "loaded_successfully": False,
            "error": str(e)
        }

def test_parquet_loading(parquet_path: Path) -> Dict[str, Any]:
    """Test loading Parquet file and verify format."""
    try:
        start_time = time.time()
        df = pd.read_parquet(parquet_path)
        load_time = time.time() - start_time
        
        return {
            "loaded_successfully": True,
            "load_time_ms": load_time * 1000,
            "shape": df.shape,
            "columns": list(df.columns),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
            "has_null": df.isnull().any().any(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
        
    except Exception as e:
        return {
            "loaded_successfully": False,
            "error": str(e)
        }

def measure_memory_usage() -> Dict[str, float]:
    """Measure current memory usage."""
    if not PSUTIL_AVAILABLE:
        return {
            "rss_mb": 0.0,
            "vms_mb": 0.0,
            "percent": 0.0,
            "note": "psutil not available"
        }
    
    process = psutil.Process()
    memory_info = process.memory_info()
    return {
        "rss_mb": memory_info.rss / (1024 * 1024),
        "vms_mb": memory_info.vms / (1024 * 1024),
        "percent": process.memory_percent()
    }

def main():
    """Main verification function."""
    print("🔍 Adelaide Weather Data Artifacts Verification")
    print("=" * 60)
    
    base_dir = Path(".")
    results = {
        "verification_time": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "base_directory": str(base_dir.absolute()),
        "faiss_indices": {},
        "embeddings": {},
        "outcomes": {},
        "configuration": {},
        "performance_metrics": {},
        "memory_analysis": {}
    }
    
    # Initial memory measurement
    results["memory_analysis"]["initial"] = measure_memory_usage()
    
    # 1. Verify FAISS indices
    print("\n📊 Testing FAISS Indices...")
    indices_dir = base_dir / "indices"
    if indices_dir.exists():
        for faiss_file in indices_dir.glob("*.faiss"):
            print(f"  Testing: {faiss_file.name}")
            file_info = check_file_permissions(faiss_file)
            if file_info["exists"] and file_info["readable"]:
                index_test = test_faiss_index_loading(faiss_file)
                results["faiss_indices"][faiss_file.name] = {**file_info, **index_test}
                print(f"    ✅ Size: {file_info['size_mb']:.1f}MB, "
                      f"Vectors: {index_test.get('total_vectors', 'N/A')}, "
                      f"Load: {index_test.get('load_time_ms', 0):.1f}ms")
            else:
                results["faiss_indices"][faiss_file.name] = file_info
                print(f"    ❌ File issue: {file_info.get('error', 'Permission denied')}")
    else:
        print("  ❌ Indices directory not found")
    
    # 2. Verify embeddings
    print("\n🧮 Testing Embeddings...")
    embeddings_dir = base_dir / "embeddings"
    if embeddings_dir.exists():
        for embedding_file in embeddings_dir.glob("*.npy"):
            print(f"  Testing: {embedding_file.name}")
            file_info = check_file_permissions(embedding_file)
            if file_info["exists"] and file_info["readable"]:
                array_test = test_numpy_array_loading(embedding_file)
                results["embeddings"][embedding_file.name] = {**file_info, **array_test}
                print(f"    ✅ Shape: {array_test.get('shape', 'N/A')}, "
                      f"Load: {array_test.get('load_time_ms', 0):.1f}ms")
            else:
                results["embeddings"][embedding_file.name] = file_info
                print(f"    ❌ File issue: {file_info.get('error', 'Permission denied')}")
        
        # Also check metadata files
        for metadata_file in embeddings_dir.glob("*.parquet"):
            print(f"  Testing: {metadata_file.name}")
            file_info = check_file_permissions(metadata_file)
            if file_info["exists"] and file_info["readable"]:
                parquet_test = test_parquet_loading(metadata_file)
                results["embeddings"][metadata_file.name] = {**file_info, **parquet_test}
                print(f"    ✅ Shape: {parquet_test.get('shape', 'N/A')}")
            else:
                results["embeddings"][metadata_file.name] = file_info
                print(f"    ❌ File issue: {file_info.get('error', 'Permission denied')}")
    else:
        print("  ❌ Embeddings directory not found")
    
    # 3. Verify outcomes
    print("\n🎯 Testing Outcomes...")
    outcomes_dir = base_dir / "outcomes"
    if outcomes_dir.exists():
        for outcome_file in outcomes_dir.glob("*.npy"):
            print(f"  Testing: {outcome_file.name}")
            file_info = check_file_permissions(outcome_file)
            if file_info["exists"] and file_info["readable"]:
                array_test = test_numpy_array_loading(outcome_file)
                results["outcomes"][outcome_file.name] = {**file_info, **array_test}
                print(f"    ✅ Shape: {array_test.get('shape', 'N/A')}, "
                      f"Load: {array_test.get('load_time_ms', 0):.1f}ms")
            else:
                results["outcomes"][outcome_file.name] = file_info
                print(f"    ❌ File issue: {file_info.get('error', 'Permission denied')}")
        
        # Check metadata files
        for metadata_file in outcomes_dir.glob("*.parquet"):
            print(f"  Testing: {metadata_file.name}")
            file_info = check_file_permissions(metadata_file)
            if file_info["exists"] and file_info["readable"]:
                parquet_test = test_parquet_loading(metadata_file)
                results["outcomes"][metadata_file.name] = {**file_info, **parquet_test}
                print(f"    ✅ Shape: {parquet_test.get('shape', 'N/A')}")
            else:
                results["outcomes"][metadata_file.name] = file_info
    else:
        print("  ❌ Outcomes directory not found")
    
    # 4. Test configuration paths
    print("\n⚙️ Testing Configuration...")
    config_files = [
        "configs/data.yaml",
        "configs/model.yaml",
        "configs/training.yaml"
    ]
    
    for config_file in config_files:
        config_path = base_dir / config_file
        file_info = check_file_permissions(config_path)
        results["configuration"][config_file] = file_info
        if file_info["exists"]:
            print(f"  ✅ {config_file}: {file_info['size_mb']:.2f}MB")
        else:
            print(f"  ❌ {config_file}: Not found")
    
    # 5. Performance summary
    print("\n⚡ Performance Analysis...")
    
    # Calculate total data size
    total_size_mb = 0
    total_load_time_ms = 0
    successful_loads = 0
    
    for category in ["faiss_indices", "embeddings", "outcomes"]:
        for filename, info in results[category].items():
            if info.get("loaded_successfully"):
                total_size_mb += info.get("size_mb", 0)
                total_load_time_ms += info.get("load_time_ms", 0)
                successful_loads += 1
    
    results["performance_metrics"] = {
        "total_data_size_mb": total_size_mb,
        "total_load_time_ms": total_load_time_ms,
        "successful_loads": successful_loads,
        "average_load_speed_mb_per_sec": (total_size_mb / (total_load_time_ms / 1000)) if total_load_time_ms > 0 else 0
    }
    
    print(f"  📊 Total data size: {total_size_mb:.1f}MB")
    print(f"  ⚡ Total load time: {total_load_time_ms:.0f}ms")
    print(f"  📈 Average speed: {results['performance_metrics']['average_load_speed_mb_per_sec']:.1f}MB/s")
    print(f"  ✅ Successful loads: {successful_loads}")
    
    # Final memory measurement
    results["memory_analysis"]["final"] = measure_memory_usage()
    memory_increase = (results["memory_analysis"]["final"]["rss_mb"] - 
                      results["memory_analysis"]["initial"]["rss_mb"])
    print(f"  💾 Memory usage increase: {memory_increase:.1f}MB")
    
    # 6. Summary
    print("\n📋 Summary:")
    faiss_count = len([k for k, v in results["faiss_indices"].items() if v.get("loaded_successfully")])
    embedding_count = len([k for k, v in results["embeddings"].items() if v.get("loaded_successfully")])
    outcome_count = len([k for k, v in results["outcomes"].items() if v.get("loaded_successfully")])
    config_count = len([k for k, v in results["configuration"].items() if v.get("exists")])
    
    print(f"  ✅ FAISS indices: {faiss_count}/8 expected")
    print(f"  ✅ Embeddings: {embedding_count}/8 expected")  
    print(f"  ✅ Outcomes: {outcome_count}/8 expected")
    print(f"  ✅ Configurations: {config_count}/3 expected")
    
    # Save detailed results
    def convert_numpy_types(obj):
        """Convert numpy types to Python native types for JSON serialization."""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    def clean_for_json(data):
        """Recursively clean data structure for JSON serialization."""
        if isinstance(data, dict):
            return {k: clean_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [clean_for_json(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(clean_for_json(item) for item in data)
        else:
            return convert_numpy_types(data)
    
    clean_results = clean_for_json(results)
    with open("data_verification_report.json", "w") as f:
        json.dump(clean_results, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: data_verification_report.json")
    
    # Return overall status
    all_critical_data_present = (faiss_count >= 8 and embedding_count >= 8 and outcome_count >= 8)
    if all_critical_data_present:
        print("\n🎉 ALL DATA ARTIFACTS VERIFIED AND READY FOR PRODUCTION!")
        return True
    else:
        print("\n❌ MISSING CRITICAL DATA ARTIFACTS - NOT READY FOR PRODUCTION")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)