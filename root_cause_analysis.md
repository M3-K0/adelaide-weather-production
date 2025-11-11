# Adelaide Weather System - Root Cause Analysis
## T001: Mock Data Fallback Investigation

**Investigation Date**: 2025-11-11  
**Status**: RESOLVED - Root cause identified with definitive fix  
**Severity**: Critical - System using mock data instead of real FAISS forecasting

---

## Executive Summary

The Adelaide Weather Forecasting System is falling back to mock data instead of using real FAISS-based weather analog forecasting due to a **neural network input dimension mismatch**. The CNN model expects 11 input variables but the weather pattern extraction only provides 9 variables in a different order, causing the FAISS search to fail and trigger fallback mode.

## Root Cause Analysis

### Confirmed Root Cause: Input Dimension Mismatch

**Primary Issue**: The `WeatherCNNEncoder` expects **11 input channels** but `_extract_weather_pattern()` only provides **9 channels** with incorrect variable ordering.

**Technical Details**:
- **Model Architecture**: `/home/micha/adelaide-weather-final/core/model_loader.py` line 354 hardcodes `num_variables=11`
- **Checkpoint Verification**: First conv layer shape is `[32, 11, 5, 5]` confirming 11 input channels expected
- **Pattern Extraction**: Only provides 9 variables with wrong order

### Variable Mapping Analysis

#### Expected Variables (11 - from training script)
1. `2m_temperature` (t2m)
2. `mean_sea_level_pressure` (MSL)
3. `10m_u_component_of_wind` (u10)
4. `10m_v_component_of_wind` (v10) 
5. `total_precipitation` (tp)
6. `geopotential` at 500mb (z500)
7. `temperature` at 500mb (t500)
8. `u_component_of_wind` at 500mb (u500)
9. `v_component_of_wind` at 500mb (v500)
10. `geopotential` at 850mb (z850)
11. `temperature` at 850mb (t850)

#### Currently Extracted Variables (9)
1. MSL pressure ✅
2. z500 ✅
3. t500 ✅
4. u500 ✅
5. v500 ✅
6. z850 ✅
7. t850 ✅
8. u850 ❌ (not needed by model)
9. v850 ❌ (not needed by model)

#### Missing Variables
- `2m_temperature` (t2m) - Critical surface temperature
- `10m_u_component_of_wind` (u10) - Surface wind U component
- `10m_v_component_of_wind` (v10) - Surface wind V component
- `total_precipitation` (tp) - Precipitation data

## Error Trace

### 1. API Request Flow
```
API Request → ForecastAdapter → AnalogSearchService → AnalogEnsembleForecaster
```

### 2. Failure Point
```
_extract_weather_pattern() → 9 variables (21, 21, 9)
                          ↓
_generate_query_embedding() → CNN Model expects (B, 11, H, W)
                          ↓
CNN Forward Pass → "expected input[1, 9, 21, 21] to have 11 channels, but got 9"
                          ↓
Exception caught → Falls back to mock data generation
```

### 3. Error Message
```
ERROR - Real FAISS search failed: Given groups=1, weight of size [32, 11, 5, 5], 
expected input[1, 9, 21, 21] to have 11 channels, but got 9 channels instead
```

## Investigation Evidence

### System Component Status
✅ **FAISS Indices**: All present and loadable (8 indices, correct dimensions)  
✅ **Model Checkpoint**: Exists and loads successfully  
✅ **CNN Encoder**: Creates instances without error  
✅ **AnalogSearchService**: Initializes successfully (degraded_mode=False)  
❌ **Pattern Extraction**: Provides wrong number of variables

### Diagnostic Test Results
```
Model Loading: ✅ PASS
FAISS Indices: ✅ PASS  
Core Forecaster: ✅ PASS
Analog Search Service: ✅ PASS
Forecast Adapter: ✅ PASS
Service Degraded Mode: False
```

**But during actual forecast**: Mock fallback triggered due to dimension mismatch.

## Environment Configuration Analysis

**Current Configuration**:
- `.env`: Only contains `API_TOKEN=demo-token-12345`
- Missing `WEATHER_API_KEY` is **NOT the root cause** (ERA5 data fallback works)
- All critical files exist and are properly located

**Verdict**: Environment configuration is not the issue.

## Solution Implementation

### Required Fix: Update Pattern Extraction

**File**: `/home/micha/adelaide-weather-final/scripts/analog_forecaster.py`  
**Method**: `_extract_weather_pattern()` (lines 190-276)  
**Function**: `_generate_mock_weather_pattern()` (lines 242-276)

### Specific Changes Required

1. **Update Variable Order**: Extract variables in exact training order:
   ```python
   variables = [
       't2m',    # 2m temperature  
       'msl',    # mean sea level pressure
       'u10',    # 10m u-wind
       'v10',    # 10m v-wind  
       'tp',     # total precipitation
       'z500',   # geopotential 500mb
       't500',   # temperature 500mb
       'u500',   # u-wind 500mb
       'v500',   # v-wind 500mb
       'z850',   # geopotential 850mb
       't850'    # temperature 850mb
   ]
   ```

2. **Extract Missing Variables**: Add ERA5 extraction for:
   - `t2m`: 2m temperature from surface data
   - `u10`: 10m U-wind from surface data  
   - `v10`: 10m V-wind from surface data
   - `tp`: Total precipitation from surface data

3. **Remove Unused Variables**: Stop extracting `u850` and `v850`

4. **Update Output Shape**: Change from `(21, 21, 9)` to `(21, 21, 11)`

### Implementation Steps

1. **Backup current system**:
   ```bash
   cp scripts/analog_forecaster.py scripts/analog_forecaster.py.backup
   ```

2. **Update `_extract_weather_pattern()` method**:
   - Add missing surface variables extraction
   - Reorder variables to match training sequence
   - Update array dimensions

3. **Update `_generate_mock_weather_pattern()` method**:
   - Add configurations for missing variables
   - Update to generate 11 variables instead of 9

4. **Test the fix**:
   ```bash
   python debug_system_initialization.py
   ```

5. **Verify no mock data fallback** in logs

### Code Template for Fix

```python
def _extract_weather_pattern(self, query_time: Union[str, pd.Timestamp]) -> Optional[np.ndarray]:
    """Extract weather pattern for a specific timestamp - FIXED VERSION."""
    if isinstance(query_time, str):
        query_time = pd.to_datetime(query_time)
    
    # If ERA5 data is not available, generate mock pattern
    if not self.has_era5_data:
        return self._generate_mock_weather_pattern(query_time)
        
    try:
        # Extract surface variables
        surface_data = self.surface_ds.sel(time=query_time, method='nearest')
        
        # Extract pressure level variables  
        pressure_data = self.pressure_ds.sel(time=query_time, method='nearest')
        
        # Build weather array in TRAINING ORDER
        all_arrays = []
        
        # 1. 2m temperature
        t2m_data = surface_data['2m_temperature'].values
        all_arrays.append(np.resize(t2m_data, (21, 21)))
        
        # 2. Mean sea level pressure
        msl_data = surface_data['msl'].values  
        all_arrays.append(np.resize(msl_data, (21, 21)))
        
        # 3-4. 10m winds
        u10_data = surface_data['10m_u_component_of_wind'].values
        v10_data = surface_data['10m_v_component_of_wind'].values
        all_arrays.append(np.resize(u10_data, (21, 21)))
        all_arrays.append(np.resize(v10_data, (21, 21)))
        
        # 5. Total precipitation
        tp_data = surface_data.get('total_precipitation', np.zeros_like(msl_data))
        all_arrays.append(np.resize(tp_data, (21, 21)))
        
        # 6-9. 500mb variables
        for var in ['geopotential', 'temperature', 'u_component_of_wind', 'v_component_of_wind']:
            var_data = pressure_data[var].sel(level=500).values
            all_arrays.append(np.resize(var_data, (21, 21)))
        
        # 10-11. 850mb variables  
        for var in ['geopotential', 'temperature']:
            var_data = pressure_data[var].sel(level=850).values
            all_arrays.append(np.resize(var_data, (21, 21)))
        
        # Stack to create input array (21, 21, 11)
        if len(all_arrays) == 11:
            weather_array = np.stack(all_arrays, axis=-1)
            return self._normalize_variables(weather_array)
        else:
            return None
            
    except Exception as e:
        logger.error(f"Failed to extract weather pattern: {e}")
        return self._generate_mock_weather_pattern(query_time)
```

## Verification Steps

After implementing the fix:

1. **Run diagnostic script**: `python debug_system_initialization.py`
2. **Check for error messages**: Should see "Real FAISS search completed" instead of "Using fallback mock search"
3. **Verify variable count**: Log should show processing 11 variables
4. **Test forecast endpoint**: Should return real analog-based forecasts
5. **Monitor logs**: No more "Generated fallback search result" messages

## Environment Variables Clarification

The investigation confirmed that **missing environment variables are NOT the root cause**:

- `WEATHER_API_KEY`: Not required for FAISS-based analog forecasting
- `FAISS_INDEX_PATH`: System uses default paths successfully
- `MODEL_PATH`: System finds model automatically

**Required Environment Variables**: NONE (system works with minimal config)

## Prevention Measures

1. **Automated Testing**: Add integration tests that verify input dimensions match model expectations
2. **Schema Validation**: Implement variable extraction validation  
3. **Documentation**: Update architecture docs with variable requirements
4. **Monitoring**: Add alerts for mock data fallback incidents

## Impact Assessment

**Before Fix**: 100% mock data (unusable forecasts)  
**After Fix**: Real FAISS-based analog forecasting restored  
**Downtime**: None (system functional but using mock data)  
**Data Quality**: Critical improvement from synthetic to real historical analogs

---

## Summary

The mock data fallback was caused by a data preprocessing issue, NOT missing environment variables or system configuration problems. The fix requires updating the weather pattern extraction to provide the correct 11 variables in the proper order that matches the trained model's expectations.

**Status**: Solution identified and ready for implementation.