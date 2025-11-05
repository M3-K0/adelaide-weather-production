"""
Performance Optimization Middleware for Adelaide Weather Forecasting API
Implements caching, compression, and response optimization for <100ms target
"""

import asyncio
import gzip
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import hashlib
import logging

logger = logging.getLogger(__name__)

class ForecastCache:
    """
    In-memory cache for forecast requests with TTL and intelligent invalidation
    """
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.hit_count = 0
        self.miss_count = 0
        
    def _generate_key(self, horizon: str, variables: str) -> str:
        """Generate cache key from request parameters"""
        key_data = f"forecast:{horizon}:{variables}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, horizon: str, variables: str) -> Optional[Dict[str, Any]]:
        """Get cached forecast data if valid"""
        cache_key = self._generate_key(horizon, variables)
        
        if cache_key not in self.cache:
            self.miss_count += 1
            return None
            
        entry = self.cache[cache_key]
        
        # Check if entry is expired
        if datetime.now() > entry['expires_at']:
            del self.cache[cache_key]
            self.miss_count += 1
            return None
            
        self.hit_count += 1
        logger.debug(f"Cache HIT for {cache_key}")
        return entry['data']
    
    def set(self, horizon: str, variables: str, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Cache forecast data with TTL"""
        cache_key = self._generate_key(horizon, variables)
        expires_at = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
        
        self.cache[cache_key] = {
            'data': data,
            'expires_at': expires_at,
            'created_at': datetime.now()
        }
        
        logger.debug(f"Cache SET for {cache_key}, expires at {expires_at}")
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        keys_to_remove = [key for key in self.cache.keys() if pattern in key]
        for key in keys_to_remove:
            del self.cache[key]
        
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching '{pattern}'")
        return len(keys_to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'cached_entries': len(self.cache),
            'memory_usage_kb': sum(len(str(entry).encode()) for entry in self.cache.values()) / 1024
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired entries from cache"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items() 
            if now > entry['expires_at']
        ]
        
        for key in expired_keys:
            del self.cache[key]
            
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
        return len(expired_keys)

class CompressionMiddleware:
    """
    Response compression middleware for reducing payload sizes with nginx proxy awareness
    """
    
    def __init__(self, minimum_size: Optional[int] = None, compression_level: int = 6):
        # Read configuration from environment with sensible defaults
        self.minimum_size = minimum_size or int(os.getenv('COMPRESSION_MIN_SIZE', '500'))
        self.compression_level = compression_level
        self.compression_enabled = os.getenv('COMPRESSION_ENABLED', 'true').lower() == 'true'
        
        # Track compression metrics
        self.compression_stats = {
            'total_requests': 0,
            'compressed_requests': 0,
            'bytes_saved': 0,
            'compression_ratio_sum': 0.0
        }
    
    def should_compress(self, request: Request, response_body: bytes) -> bool:
        """Determine if response should be compressed"""
        # Skip compression if disabled
        if not self.compression_enabled:
            return False
            
        # Check if already compressed by nginx proxy
        if self._is_behind_proxy(request):
            logger.debug("Skipping compression - behind nginx proxy")
            return False
            
        # Check if client accepts gzip
        accept_encoding = request.headers.get('accept-encoding', '')
        if 'gzip' not in accept_encoding.lower():
            return False
            
        # Check minimum size
        if len(response_body) < self.minimum_size:
            return False
            
        # Check content type (only compress JSON/text responses)
        content_type = getattr(response_body, 'media_type', 'application/json')
        compressible_types = ['application/json', 'text/plain', 'text/html', 'application/xml']
        if not any(ct in content_type for ct in compressible_types):
            return False
            
        return True
    
    def _is_behind_proxy(self, request: Request) -> bool:
        """Check if request is coming through nginx proxy"""
        # Check for common proxy headers
        proxy_headers = [
            'x-forwarded-for',
            'x-forwarded-proto',
            'x-real-ip',
            'x-nginx-proxy'
        ]
        
        for header in proxy_headers:
            if request.headers.get(header):
                return True
                
        # Check if nginx compression is already enabled
        return request.headers.get('accept-encoding', '').find('gzip') != -1 and \
               os.getenv('NGINX_COMPRESSION', 'false').lower() == 'true'
    
    def compress_response(self, response_body: bytes) -> bytes:
        """Compress response body using gzip and track metrics"""
        original_size = len(response_body)
        compressed_body = gzip.compress(response_body, compresslevel=self.compression_level)
        compressed_size = len(compressed_body)
        
        # Update compression stats
        self.compression_stats['total_requests'] += 1
        self.compression_stats['compressed_requests'] += 1
        self.compression_stats['bytes_saved'] += (original_size - compressed_size)
        
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        self.compression_stats['compression_ratio_sum'] += compression_ratio
        
        logger.debug(f"Compressed response: {original_size} -> {compressed_size} bytes "
                    f"({compression_ratio:.2%} of original)")
        
        return compressed_body
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression performance statistics"""
        stats = self.compression_stats.copy()
        if stats['compressed_requests'] > 0:
            stats['average_compression_ratio'] = stats['compression_ratio_sum'] / stats['compressed_requests']
            stats['compression_rate'] = stats['compressed_requests'] / stats['total_requests']
        else:
            stats['average_compression_ratio'] = 0.0
            stats['compression_rate'] = 0.0
            
        return stats

class RateLimitMiddleware:
    """
    Rate limiting middleware with configurable limits and monitoring
    """
    
    def __init__(self):
        # Read rate limit configuration from environment
        self.rate_limit_per_minute = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
        self.rate_limit_enabled = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
        
        # Track rate limiting metrics
        self.rate_limit_stats = {
            'total_requests': 0,
            'limited_requests': 0,
            'current_limit_per_minute': self.rate_limit_per_minute
        }
        
        logger.info(f"Rate limiting configured: {self.rate_limit_per_minute}/minute, enabled: {self.rate_limit_enabled}")
    
    def get_rate_limit_config(self) -> str:
        """Get current rate limit configuration as string for SlowAPI"""
        if not self.rate_limit_enabled:
            return "1000000/minute"  # Effectively unlimited
        return f"{self.rate_limit_per_minute}/minute"
    
    def track_request(self, limited: bool = False):
        """Track rate limiting metrics"""
        self.rate_limit_stats['total_requests'] += 1
        if limited:
            self.rate_limit_stats['limited_requests'] += 1
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        stats = self.rate_limit_stats.copy()
        if stats['total_requests'] > 0:
            stats['limit_rate'] = stats['limited_requests'] / stats['total_requests']
        else:
            stats['limit_rate'] = 0.0
        return stats

class PerformanceMiddleware:
    """
    Main performance middleware coordinating caching, compression, and optimization
    """
    
    def __init__(self):
        self.cache = ForecastCache()
        self.compression = CompressionMiddleware()
        self.rate_limiter = RateLimitMiddleware()
        self.request_times: Dict[str, float] = {}
        
        logger.info(f"Performance middleware initialized with compression min size: {self.compression.minimum_size} bytes")
        
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance optimizations"""
        start_time = time.time()
        
        # Try cache for forecast requests
        if request.url.path == "/forecast":
            cached_response = await self._try_cache(request)
            if cached_response:
                return cached_response
        
        # Process request
        response = await call_next(request)
        
        # Apply performance optimizations
        response = await self._optimize_response(request, response, start_time)
        
        return response
    
    async def _try_cache(self, request: Request) -> Optional[Response]:
        """Try to serve request from cache"""
        params = dict(request.query_params)
        horizon = params.get('horizon', '24h')
        variables = params.get('vars', 't2m,u10,v10')
        
        cached_data = self.cache.get(horizon, variables)
        if cached_data:
            # Add cache headers
            headers = {
                'X-Cache': 'HIT',
                'X-Cache-Key': self.cache._generate_key(horizon, variables),
                'Cache-Control': 'public, max-age=300'
            }
            
            return JSONResponse(content=cached_data, headers=headers)
        
        return None
    
    async def _optimize_response(self, request: Request, response: Response, start_time: float) -> Response:
        """Apply optimizations to response"""
        end_time = time.time()
        response_time = end_time - start_time
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{response_time*1000:.2f}ms"
        response.headers["X-Process-Time"] = str(int(response_time * 1000))
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; object-src 'none'"
        
        # Cache forecast responses
        if request.url.path == "/forecast" and response.status_code == 200:
            await self._cache_response(request, response)
        
        # Apply compression if beneficial
        if hasattr(response, 'body'):
            response = await self._apply_compression(request, response)
        
        # Log slow responses
        if response_time > 0.1:  # 100ms threshold
            logger.warning(f"Slow response: {request.url.path} took {response_time*1000:.2f}ms")
        
        return response
    
    async def _cache_response(self, request: Request, response: Response) -> None:
        """Cache successful forecast responses"""
        if not hasattr(response, 'body'):
            return
            
        try:
            # Parse response body
            body_bytes = response.body
            if isinstance(body_bytes, bytes):
                response_data = json.loads(body_bytes.decode())
            else:
                response_data = body_bytes
            
            # Extract cache parameters
            params = dict(request.query_params)
            horizon = params.get('horizon', '24h')
            variables = params.get('vars', 't2m,u10,v10')
            
            # Determine TTL based on horizon
            ttl_map = {'6h': 180, '12h': 300, '24h': 600, '48h': 900}  # seconds
            ttl = ttl_map.get(horizon, 300)
            
            # Cache the response
            self.cache.set(horizon, variables, response_data, ttl)
            
        except Exception as e:
            logger.error(f"Failed to cache response: {e}")
    
    async def _apply_compression(self, request: Request, response: Response) -> Response:
        """Apply gzip compression if beneficial"""
        if not hasattr(response, 'body'):
            # Track non-compressible request
            self.compression.compression_stats['total_requests'] += 1
            return response
            
        try:
            body_bytes = response.body if isinstance(response.body, bytes) else response.body.encode()
            
            if self.compression.should_compress(request, body_bytes):
                compressed_body = self.compression.compress_response(body_bytes)
                
                # Update response with compressed body and headers
                response.headers["Content-Encoding"] = "gzip"
                response.headers["Content-Length"] = str(len(compressed_body))
                response.headers["Vary"] = "Accept-Encoding"
                response.headers["X-Compression-Ratio"] = f"{len(compressed_body)/len(body_bytes):.3f}"
                
                # Create new response with compressed body
                return Response(
                    content=compressed_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            else:
                # Track non-compressed request
                self.compression.compression_stats['total_requests'] += 1
        
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            # Track failed compression
            self.compression.compression_stats['total_requests'] += 1
        
        return response
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        cache_stats = self.cache.get_stats()
        compression_stats = self.compression.get_compression_stats()
        rate_limit_stats = self.rate_limiter.get_rate_limit_stats()
        
        return {
            'cache': cache_stats,
            'compression': {
                'enabled': self.compression.compression_enabled,
                'minimum_size_bytes': self.compression.minimum_size,
                'compression_level': self.compression.compression_level,
                'stats': compression_stats
            },
            'rate_limiting': {
                'enabled': self.rate_limiter.rate_limit_enabled,
                'limit_per_minute': self.rate_limiter.rate_limit_per_minute,
                'stats': rate_limit_stats
            },
            'optimization': {
                'cache_cleanup_needed': len(self.cache.cache) > 1000,
                'performance_target_ms': 100,
                'total_middleware_requests': compression_stats.get('total_requests', 0)
            }
        }
    
    async def cleanup_task(self) -> None:
        """Periodic cleanup task for cache maintenance"""
        while True:
            try:
                # Cleanup expired cache entries every 5 minutes
                await asyncio.sleep(300)
                expired_count = self.cache.cleanup_expired()
                
                if expired_count > 0:
                    logger.info(f"Performance cleanup: removed {expired_count} expired entries")
                    
            except Exception as e:
                logger.error(f"Performance cleanup failed: {e}")

# Global performance middleware instance
performance_middleware = PerformanceMiddleware()

def get_performance_stats() -> Dict[str, Any]:
    """Get performance statistics for monitoring"""
    return performance_middleware.get_performance_stats()

def get_rate_limit_config() -> str:
    """Get current rate limit configuration for SlowAPI"""
    return performance_middleware.rate_limiter.get_rate_limit_config()

async def clear_cache(pattern: Optional[str] = None) -> Dict[str, Any]:
    """Clear cache entries (admin endpoint)"""
    if pattern:
        cleared = performance_middleware.cache.invalidate_pattern(pattern)
        return {'cleared_entries': cleared, 'pattern': pattern}
    else:
        total_entries = len(performance_middleware.cache.cache)
        performance_middleware.cache.cache.clear()
        performance_middleware.cache.hit_count = 0
        performance_middleware.cache.miss_count = 0
        return {'cleared_entries': total_entries, 'pattern': 'all'}