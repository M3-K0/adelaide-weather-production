#!/usr/bin/env python3
"""
Design Temporal Alignment Verification System
"""
import numpy as np
import pandas as pd
import hashlib
import json
from pathlib import Path

def calculate_file_hash(filepath):
    """Calculate SHA-256 hash of file"""
    hash_sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def analyze_database_integrity(horizon):
    """Comprehensive database integrity analysis"""
    
    outcomes_path = f'outcomes/outcomes_{horizon}.npy'
    metadata_path = f'outcomes/metadata_{horizon}_clean.parquet'
    
    if not Path(outcomes_path).exists() or not Path(metadata_path).exists():
        return None
    
    # Load data
    outcomes = np.load(outcomes_path)
    metadata = pd.read_parquet(metadata_path)
    
    # Basic statistics
    total_values = outcomes.size
    zero_count = np.sum(outcomes == 0)
    zero_percentage = 100 * zero_count / total_values
    
    # Row-level analysis
    completely_zero_rows = np.all(outcomes == 0, axis=1).sum()
    valid_rows = outcomes.shape[0] - completely_zero_rows
    valid_percentage = 100 * valid_rows / outcomes.shape[0]
    
    # Variable-level analysis
    variable_stats = {}
    variables = ['z500', 't2m', 't850', 'q850', 'u10', 'v10', 'u850', 'v850', 'cape']
    
    for i, var in enumerate(variables):
        col_data = outcomes[:, i]
        variable_stats[var] = {
            'min': float(col_data.min()),
            'max': float(col_data.max()),
            'mean': float(col_data.mean()),
            'std': float(col_data.std()),
            'zeros': int(np.sum(col_data == 0)),
            'zero_percentage': float(100 * np.sum(col_data == 0) / len(col_data))
        }
    
    # Temporal analysis
    temporal_info = {
        'init_time_min': str(metadata['init_time'].min()),
        'init_time_max': str(metadata['init_time'].max()),
        'valid_time_min': str(metadata['valid_time'].min()),
        'valid_time_max': str(metadata['valid_time'].max()),
        'total_patterns': len(metadata)
    }
    
    # Check temporal alignment
    time_diff = pd.to_datetime(metadata['valid_time']) - pd.to_datetime(metadata['init_time'])
    expected_diff = pd.Timedelta(hours=int(horizon[:-1]))
    alignment_correct = (time_diff == expected_diff).all()
    alignment_errors = (~(time_diff == expected_diff)).sum()
    
    # Calculate file hashes
    outcomes_hash = calculate_file_hash(outcomes_path)
    metadata_hash = calculate_file_hash(metadata_path)
    
    # Uniqueness analysis
    col_0_unique = len(np.unique(outcomes[:, 0]))
    uniqueness_ratio = col_0_unique / outcomes.shape[0]
    
    return {
        'horizon': horizon,
        'file_info': {
            'outcomes_path': outcomes_path,
            'metadata_path': metadata_path,
            'outcomes_hash': outcomes_hash,
            'metadata_hash': metadata_hash,
            'outcomes_size_mb': round(Path(outcomes_path).stat().st_size / 1024 / 1024, 2),
            'metadata_size_mb': round(Path(metadata_path).stat().st_size / 1024 / 1024, 2)
        },
        'data_quality': {
            'shape': list(outcomes.shape),
            'dtype': str(outcomes.dtype),
            'total_values': total_values,
            'zero_count': zero_count,
            'zero_percentage': round(zero_percentage, 1),
            'completely_zero_rows': completely_zero_rows,
            'valid_rows': valid_rows,
            'valid_percentage': round(valid_percentage, 1),
            'uniqueness_ratio': round(uniqueness_ratio, 6)
        },
        'temporal_alignment': {
            'alignment_correct': alignment_correct,
            'alignment_errors': alignment_errors,
            'expected_offset_hours': int(horizon[:-1]),
            **temporal_info
        },
        'variable_statistics': variable_stats,
        'corruption_indicators': {
            'excessive_zeros': zero_percentage > 50,
            'completely_zero_rows_present': completely_zero_rows > 0,
            'poor_uniqueness': uniqueness_ratio < 0.95,
            'temporal_misalignment': alignment_errors > 0
        }
    }

def verify_temporal_alignment():
    """Expert-required temporal alignment verification"""
    print("=== TEMPORAL ALIGNMENT VERIFICATION SYSTEM ===")
    
    verification_results = {}
    
    # Analyze each horizon
    horizons = ['6h', '12h', '24h', '48h']
    for horizon in horizons:
        result = analyze_database_integrity(horizon)
        if result:
            verification_results[horizon] = result
            
            # Print summary
            print(f"\n{horizon} Database:")
            print(f"  Valid data: {result['data_quality']['valid_percentage']:.1f}%")
            print(f"  Temporal alignment: {'✅' if result['temporal_alignment']['alignment_correct'] else '❌'}")
            print(f"  Uniqueness ratio: {result['data_quality']['uniqueness_ratio']:.6f}")
            print(f"  SHA-256: {result['file_info']['outcomes_hash'][:16]}...")
    
    # Cross-horizon corruption analysis
    print(f"\n=== CROSS-HORIZON DUPLICATION DETECTION ===")
    
    hashes = {}
    for horizon, data in verification_results.items():
        if data and 'file_info' in data:
            hashes[horizon] = data['file_info']['outcomes_hash']
    
    # Check for identical hashes
    hash_groups = {}
    for horizon, hash_val in hashes.items():
        if hash_val not in hash_groups:
            hash_groups[hash_val] = []
        hash_groups[hash_val].append(horizon)
    
    for hash_val, horizons_list in hash_groups.items():
        if len(horizons_list) > 1:
            print(f"  ⚠️  IDENTICAL files: {', '.join(horizons_list)} (hash: {hash_val[:16]}...)")
        else:
            print(f"  ✅ Unique: {horizons_list[0]} (hash: {hash_val[:16]}...)")
    
    # Data shifting detection
    print(f"\n=== DATA SHIFTING DETECTION ===")
    
    if '6h' in verification_results and '12h' in verification_results:
        data_6h = np.load('outcomes/outcomes_6h.npy')
        data_12h = np.load('outcomes/outcomes_12h.npy')
        
        # Test for shifting
        n = min(data_6h.shape[0], data_12h.shape[0]) - 1
        is_shifted = np.allclose(data_12h[:n], data_6h[1:n+1], rtol=1e-5)
        
        print(f"  12h vs 6h shifted: {'⚠️  SHIFTED COPY DETECTED' if is_shifted else '✅ Unique data'}")
        verification_results['cross_horizon_analysis'] = {
            'shifting_detected': is_shifted,
            'correlation_6h_12h': float(np.corrcoef(data_6h[1:1000, 0], data_12h[:999, 0])[0,1])
        }
    
    return verification_results

def create_json_sidecars(verification_results):
    """Create JSON sidecar files with database metadata"""
    
    sidecar_dir = Path('outcomes/sidecars')
    sidecar_dir.mkdir(exist_ok=True)
    
    # Create individual sidecar files
    for horizon, data in verification_results.items():
        if horizon == 'cross_horizon_analysis':
            continue
            
        sidecar_path = sidecar_dir / f'outcomes_{horizon}_sidecar.json'
        
        with open(sidecar_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"✅ Created sidecar: {sidecar_path}")
    
    # Create master analysis file
    master_path = sidecar_dir / 'database_integrity_analysis.json'
    
    with open(master_path, 'w') as f:
        json.dump(verification_results, f, indent=2, default=str)
    
    print(f"✅ Created master analysis: {master_path}")
    
    return sidecar_dir

if __name__ == "__main__":
    # Run full verification system
    results = verify_temporal_alignment()
    
    # Create JSON sidecars
    sidecar_dir = create_json_sidecars(results)
    
    print(f"\n=== VERIFICATION COMPLETE ===")
    print(f"Sidecar files created in: {sidecar_dir}")
    print(f"Master analysis: {sidecar_dir}/database_integrity_analysis.json")