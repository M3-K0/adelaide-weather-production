"""
API Services Package
===================

Production services for the Adelaide Weather Forecast API.

Services:
- AnalogSearchService: Async FAISS-based analog search with connection pooling
- FAISSHealthMonitor: Real-time FAISS performance and health monitoring
"""

from .analog_search import (
    AnalogSearchService,
    AnalogSearchConfig,
    AnalogSearchResult,
    get_analog_search_service,
    shutdown_analog_search_service
)

from .faiss_health_monitoring import (
    FAISSHealthMonitor,
    FAISSQueryMetrics,
    IndexHealthMetrics,
    get_faiss_health_monitor
)

__all__ = [
    'AnalogSearchService',
    'AnalogSearchConfig', 
    'AnalogSearchResult',
    'get_analog_search_service',
    'shutdown_analog_search_service',
    'FAISSHealthMonitor',
    'FAISSQueryMetrics',
    'IndexHealthMetrics',
    'get_faiss_health_monitor'
]