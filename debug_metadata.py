#!/usr/bin/env python3
"""Debug metadata structure"""

import pandas as pd
import numpy as np
from pathlib import Path

# Examine metadata structure for 24h horizon
metadata_path = Path('embeddings/metadata_24h.parquet')
metadata = pd.read_parquet(metadata_path)

print('📊 Metadata Structure for 24h horizon:')
print(f'   Shape: {metadata.shape}')
print(f'   Columns: {list(metadata.columns)}')
print()
print('First 5 rows:')
print(metadata.head())
print()
print('Data types:')
print(metadata.dtypes)
print()
print('Date range:')
if 'timestamp' in metadata.columns:
    print(f'   From: {metadata["timestamp"].min()}')
    print(f'   To: {metadata["timestamp"].max()}')
elif 'init_time' in metadata.columns:
    print(f'   From: {metadata["init_time"].min()}')
    print(f'   To: {metadata["init_time"].max()}')

# Check available variables
print()
print('Sample data values:')
for col in metadata.columns[:8]:  # Show first 8 columns
    if metadata[col].dtype != 'object':
        print(f'   {col}: {metadata[col].iloc[0]:.3f} (range: {metadata[col].min():.3f} to {metadata[col].max():.3f})')
    else:
        print(f'   {col}: {metadata[col].iloc[0]}')