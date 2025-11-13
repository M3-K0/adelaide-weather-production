#!/usr/bin/env python3
"""
Analog Search Metrics Module
============================

Provides Prometheus metrics for analog search operations.
This module contains the metrics definitions for analog search monitoring
as specified in OBS1 requirements.

Metrics:
- analog_real_total: Counter for successful real FAISS searches
- analog_fallback_total: Counter for fallback searches used
- analog_search_seconds: Histogram for search latency with horizon/k labels
- analog_results_count: Gauge for number of analogs returned per horizon

Author: Monitoring & Observability Engineer
Version: 1.0.0 - OBS1 Implementation
"""

from prometheus_client import Counter, Histogram, Gauge, REGISTRY

def _get_or_create_metric(metric_cls, name, documentation, *args, **kwargs):
    """Return existing Prometheus metric or create a new one.
    
    During unit tests or multiple imports, Prometheus registers collectors globally,
    so attempting to create them again raises ValueError. This helper safely reuses
    existing collectors to keep initialization idempotent.
    """
    existing = REGISTRY._names_to_collectors.get(name)
    if existing is not None:
        return existing
    return metric_cls(name, documentation, *args, **kwargs)

# Analog search metrics (OBS1 requirements)
analog_real_total = _get_or_create_metric(
    Counter, 
    'analog_real_total', 
    'Total successful real FAISS analog searches'
)

analog_fallback_total = _get_or_create_metric(
    Counter, 
    'analog_fallback_total', 
    'Total fallback analog searches used'
)

analog_search_seconds = _get_or_create_metric(
    Histogram, 
    'analog_search_seconds', 
    'Analog search latency distribution with horizon and k labels', 
    ['horizon', 'k'], 
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float('inf')]
)

analog_results_count = _get_or_create_metric(
    Gauge, 
    'analog_results_count', 
    'Number of analogs returned per horizon', 
    ['horizon']
)

# Export all metrics for easy access
__all__ = [
    'analog_real_total',
    'analog_fallback_total', 
    'analog_search_seconds',
    'analog_results_count'
]