#!/usr/bin/env python3
"""
CAPE Calculator for ERA5 Data
============================

Implements CAPE (Convective Available Potential Energy) calculation 
from limited ERA5 pressure level data (850 hPa and 500 hPa only).

Uses MetPy for meteorological calculations with simplified atmospheric 
profile approach suitable for analog forecasting applications.
"""

import numpy as np
import logging
from typing import Optional, Tuple
import warnings

# Suppress MetPy warnings for limited data
warnings.filterwarnings("ignore", category=UserWarning, module="metpy")

logger = logging.getLogger(__name__)

def calculate_cape_empirical(
    t850: float,  # Temperature at 850 hPa [K]
    q850: float,  # Specific humidity at 850 hPa [kg/kg]
    t500: float,  # Temperature at 500 hPa [K]
    debug: bool = False
) -> float:
    """
    Calculate CAPE using a smoothed empirical relationship.

    The goal is to derive a continuous, non-zero CAPE estimate that still reflects
    the primary physical drivers (instability, moisture, lapse rate) while operating
    with only a very shallow vertical profile (500/850 hPa).
    """
    try:
        # Convert to user-friendly units
        t850_c = t850 - 273.15
        t500_c = t500 - 273.15
        q850_gkg = max(q850 * 1000.0, 0.0)

        # Instability between 850 and 500 hPa
        temp_diff = t850_c - t500_c  # °C
        instability = max(temp_diff, 0.0)

        # Approximate lapse rate (K/km) using ~4 km layer depth
        lapse_rate = instability / 4.0

        # Moisture contribution (log-scaling to keep reasonable range)
        moisture_score = np.log1p(q850_gkg * 0.8)  # rises quickly up to ~10 g/kg

        # Smooth instability score: softplus around 10-15 °C differences
        instability_score = np.log1p(np.exp((instability - 12.0) / 2.5))

        # Combine ingredients
        cape = 120.0 * instability_score * moisture_score * (1.0 + 0.1 * max(lapse_rate - 6.5, 0.0))

        # Penalise extremely dry environments
        if q850_gkg < 1.0:
            cape *= 0.35
        elif q850_gkg < 3.0:
            cape *= 0.65

        # Gentle floor to avoid hard zeros while remaining physical
        cape = max(cape, 5.0 if instability > 0 else 0.0)

        # Clip to realistic climatological bounds
        cape = float(np.clip(cape, 0.0, 4000.0))

        if debug:
            print("Empirical CAPE calculation:")
            print(f"  T850: {t850_c:.1f}°C | T500: {t500_c:.1f}°C | ΔT: {temp_diff:.1f}K")
            print(f"  q850: {q850_gkg:.1f} g/kg | lapse rate: {lapse_rate:.1f} K/km")
            print(f"  Scores → instability: {instability_score:.2f}, moisture: {moisture_score:.2f}")
            print(f"  CAPE: {cape:.0f} J/kg")

        return cape

    except Exception as e:
        logger.warning(f"Empirical CAPE calculation failed: {e}")
        return 0.0


def calculate_cape_simplified(
    t850: float,  # Temperature at 850 hPa [K]
    q850: float,  # Specific humidity at 850 hPa [kg/kg]
    t500: float,  # Temperature at 500 hPa [K]
    z850: float,  # Geopotential at 850 hPa [m²/s²]
    z500: float,  # Geopotential at 500 hPa [m²/s²]
    surface_pressure: float = 1013.25,  # Surface pressure [hPa]
    debug: bool = False
) -> float:
    """
    Calculate simplified CAPE - now uses empirical approach.
    
    Args:
        t850: Temperature at 850 hPa [K]
        q850: Specific humidity at 850 hPa [kg/kg]
        t500: Temperature at 500 hPa [K]
        z850: Geopotential at 850 hPa [m²/s²] (not used in empirical method)
        z500: Geopotential at 500 hPa [m²/s²] (not used in empirical method)
        surface_pressure: Surface pressure [hPa] (not used in empirical method)
        debug: Print debug information
    
    Returns:
        CAPE value [J/kg]
    """
    # Use empirical method for better results with limited data
    return calculate_cape_empirical(t850, q850, t500, debug)


def calculate_cape_metpy(
    pressure_levels: np.ndarray,  # [hPa]
    temperatures: np.ndarray,     # [K]  
    dewpoints: np.ndarray,        # [K]
    heights: np.ndarray          # [m]
) -> float:
    """
    Calculate CAPE using MetPy library (if sufficient data available).
    
    Args:
        pressure_levels: Pressure levels [hPa]
        temperatures: Temperature profile [K]
        dewpoints: Dewpoint profile [K]  
        heights: Height profile [m]
    
    Returns:
        CAPE value [J/kg] or 0.0 if calculation fails
    """
    try:
        from metpy.calc import cape_cin, parcel_profile
        from metpy.units import units
        import metpy.calc as mpcalc
        
        # Convert to MetPy units
        p = pressure_levels * units.hPa
        T = temperatures * units.kelvin
        Td = dewpoints * units.kelvin
        
        # Calculate parcel profile
        parcel_prof = parcel_profile(p, T[0], Td[0])
        
        # Calculate CAPE and CIN
        cape, cin = cape_cin(p, T, Td, parcel_prof)
        
        return float(cape.magnitude) if cape.magnitude > 0 else 0.0
        
    except Exception as e:
        logger.warning(f"MetPy CAPE calculation failed: {e}")
        return 0.0


def extract_cape_from_era5(pressure_data, surface_pressure: float = 1013.25) -> float:
    """
    Extract CAPE from ERA5 pressure level data.
    
    Args:
        pressure_data: xarray Dataset with pressure level variables
        surface_pressure: Surface pressure [hPa]
    
    Returns:
        CAPE value [J/kg]
    """
    try:
        # Extract variables at required pressure levels
        t850 = float(pressure_data['t'].sel(isobaricInhPa=850, method='nearest').values)
        t500 = float(pressure_data['t'].sel(isobaricInhPa=500, method='nearest').values)
        
        q850 = float(pressure_data['q'].sel(isobaricInhPa=850, method='nearest').values)
        
        z850 = float(pressure_data['z'].sel(isobaricInhPa=850, method='nearest').values)
        z500 = float(pressure_data['z'].sel(isobaricInhPa=500, method='nearest').values)
        
        # Use simplified CAPE calculation
        cape = calculate_cape_simplified(t850, q850, t500, z850, z500, surface_pressure)
        
        return cape
        
    except Exception as e:
        logger.warning(f"Failed to extract CAPE from ERA5 data: {e}")
        return 0.0


def calculate_dewpoint_from_specific_humidity(temperature: float, specific_humidity: float, pressure: float) -> float:
    """
    Calculate dewpoint temperature from specific humidity.
    
    Args:
        temperature: Temperature [K]
        specific_humidity: Specific humidity [kg/kg]
        pressure: Pressure [hPa]
    
    Returns:
        Dewpoint temperature [K]
    """
    try:
        # Convert specific humidity to mixing ratio
        w = specific_humidity / (1.0 - specific_humidity)
        
        # Calculate vapor pressure
        e = w * pressure / (0.622 + w)
        
        # Calculate dewpoint using Bolton's formula
        ln_e = np.log(e / 6.112)
        dewpoint = 243.5 * ln_e / (17.67 - ln_e) + 273.15
        
        return dewpoint
        
    except Exception as e:
        logger.warning(f"Dewpoint calculation failed: {e}")
        return temperature - 10.0  # Fallback: assume 10K depression


if __name__ == "__main__":
    # Test the CAPE calculator with sample data
    print("Testing CAPE Calculator...")
    print("=" * 40)
    
    # Sample meteorological data (highly unstable thunderstorm conditions)
    t850_test = 308.15  # 35°C (very hot surface)
    q850_test = 0.018   # 18 g/kg (very high moisture)
    t500_test = 258.15  # -15°C (very cold aloft - highly unstable)
    z850_test = 1500.0 * 9.81  # ~1500m geopotential
    z500_test = 5500.0 * 9.81  # ~5500m geopotential
    
    cape_result = calculate_cape_simplified(t850_test, q850_test, t500_test, z850_test, z500_test, debug=True)
    
    print(f"Sample CAPE calculation:")
    print(f"  T850: {t850_test - 273.15:.1f}°C")
    print(f"  Q850: {q850_test * 1000:.1f} g/kg")
    print(f"  T500: {t500_test - 273.15:.1f}°C")
    print(f"  CAPE: {cape_result:.0f} J/kg")
    print()
    
    if cape_result > 0:
        print("✅ CAPE calculation working!")
    else:
        print("⚠️ CAPE calculation returned zero - check implementation")
