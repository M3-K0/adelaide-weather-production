#!/usr/bin/env python3
"""
Device Manager and GPU/CPU Switch
==================================

Automatic device detection with manual override capabilities via environment
variables. Provides graceful degradation from GPU to CPU for FAISS operations.

Features:
- Automatic GPU detection and capability assessment
- Environment variable overrides (FAISS_GPU_ENABLED, FAISS_FORCE_CPU)
- Graceful degradation with fallback strategies
- Device resource monitoring
- FAISS GPU/CPU index compatibility

Author: Performance Specialist
Version: 1.0.0 - Resource Guardrails Implementation
"""

import os
import logging
import warnings
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    """Device types for computation."""
    CPU = "cpu"
    GPU = "gpu"
    AUTO = "auto"

@dataclass
class DeviceCapabilities:
    """Device capability information."""
    device_type: DeviceType
    device_count: int
    memory_mb: Optional[float]
    compute_capability: Optional[str]
    driver_version: Optional[str]
    available: bool
    performance_score: float  # Relative performance score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_type': self.device_type.value,
            'device_count': self.device_count,
            'memory_mb': self.memory_mb,
            'compute_capability': self.compute_capability,
            'driver_version': self.driver_version,
            'available': self.available,
            'performance_score': self.performance_score
        }

@dataclass
class DeviceSelection:
    """Selected device configuration."""
    device_type: DeviceType
    device_id: Optional[int]
    capabilities: DeviceCapabilities
    selection_reason: str
    fallback_applied: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_type': self.device_type.value,
            'device_id': self.device_id,
            'capabilities': self.capabilities.to_dict(),
            'selection_reason': self.selection_reason,
            'fallback_applied': self.fallback_applied
        }

class DeviceManager:
    """Manages device selection and GPU/CPU switching for FAISS operations."""
    
    def __init__(self):
        """Initialize device manager."""
        self.cpu_capabilities: Optional[DeviceCapabilities] = None
        self.gpu_capabilities: List[DeviceCapabilities] = []
        self.selected_device: Optional[DeviceSelection] = None
        self.faiss_gpu_available = False
        
        # Load environment configuration
        self._load_env_config()
        
        # Detect available devices
        self._detect_devices()
        
        # Select optimal device
        self._select_device()
        
        logger.info(f"DeviceManager initialized with device: {self.selected_device.device_type.value}")
    
    def _load_env_config(self):
        """Load device configuration from environment variables."""
        # FAISS_GPU_ENABLED: explicit GPU enable/disable
        self.gpu_enabled = os.getenv('FAISS_GPU_ENABLED', 'auto').lower()
        
        # FAISS_FORCE_CPU: force CPU usage (overrides GPU_ENABLED)
        self.force_cpu = os.getenv('FAISS_FORCE_CPU', 'false').lower() in ['true', '1', 'yes']
        
        # FAISS_GPU_DEVICE: specific GPU device ID
        gpu_device = os.getenv('FAISS_GPU_DEVICE', 'auto')
        self.gpu_device_id = None if gpu_device == 'auto' else int(gpu_device)
        
        # FAISS_MEMORY_FRACTION: fraction of GPU memory to use
        self.gpu_memory_fraction = float(os.getenv('FAISS_GPU_MEMORY_FRACTION', '0.8'))
        
        logger.info(f"Device config: GPU_ENABLED={self.gpu_enabled}, FORCE_CPU={self.force_cpu}")
        if self.gpu_device_id is not None:
            logger.info(f"GPU device override: {self.gpu_device_id}")
    
    def _detect_devices(self):
        """Detect available CPU and GPU devices."""
        # Always detect CPU capabilities
        self._detect_cpu()
        
        # Detect GPU capabilities if not forced to CPU
        if not self.force_cpu:
            self._detect_gpu()
            self._detect_faiss_gpu()
    
    def _detect_cpu(self):
        """Detect CPU capabilities."""
        try:
            try:
                import psutil
                cpu_count = psutil.cpu_count(logical=False)
                
                # Estimate CPU performance score based on core count and frequency
                try:
                    cpu_freq = psutil.cpu_freq()
                    base_freq = cpu_freq.max if cpu_freq else 2000  # 2GHz default
                    performance_score = cpu_count * (base_freq / 2000)  # Normalized to 2GHz
                except:
                    performance_score = cpu_count * 1.0  # Fallback scoring
                
            except ImportError:
                # Fallback when psutil not available
                cpu_count = os.cpu_count() or 1
                performance_score = cpu_count * 1.0
            
            self.cpu_capabilities = DeviceCapabilities(
                device_type=DeviceType.CPU,
                device_count=cpu_count,
                memory_mb=None,  # System memory handled separately
                compute_capability=None,
                driver_version=None,
                available=True,
                performance_score=performance_score
            )
            
            logger.info(f"CPU detected: {cpu_count} cores, performance score: {performance_score:.1f}")
            
        except Exception as e:
            logger.warning(f"CPU detection failed: {e}")
            # Fallback CPU capabilities
            self.cpu_capabilities = DeviceCapabilities(
                device_type=DeviceType.CPU,
                device_count=1,
                memory_mb=None,
                compute_capability=None,
                driver_version=None,
                available=True,
                performance_score=1.0
            )
    
    def _detect_gpu(self):
        """Detect GPU capabilities using multiple detection methods."""
        self.gpu_capabilities = []
        
        # Try PyTorch CUDA detection
        gpu_caps = self._detect_pytorch_gpu()
        if gpu_caps:
            self.gpu_capabilities.extend(gpu_caps)
            return
        
        # Try pynvml detection
        gpu_caps = self._detect_pynvml_gpu()
        if gpu_caps:
            self.gpu_capabilities.extend(gpu_caps)
            return
        
        logger.info("No GPU devices detected")
    
    def _detect_pytorch_gpu(self) -> List[DeviceCapabilities]:
        """Detect GPU using PyTorch."""
        try:
            import torch
            
            if not torch.cuda.is_available():
                return []
            
            gpu_capabilities = []
            device_count = torch.cuda.device_count()
            
            for i in range(device_count):
                props = torch.cuda.get_device_properties(i)
                
                # Calculate performance score (simplified)
                compute_capability = f"{props.major}.{props.minor}"
                memory_mb = props.total_memory / (1024**2)
                
                # Performance scoring based on memory and compute capability
                performance_score = memory_mb / 1000 * float(props.major)
                
                gpu_cap = DeviceCapabilities(
                    device_type=DeviceType.GPU,
                    device_count=1,
                    memory_mb=memory_mb,
                    compute_capability=compute_capability,
                    driver_version=None,  # Not available via PyTorch
                    available=True,
                    performance_score=performance_score
                )
                
                gpu_capabilities.append(gpu_cap)
                logger.info(f"GPU {i} detected via PyTorch: {memory_mb:.0f}MB, CC {compute_capability}")
            
            return gpu_capabilities
            
        except ImportError:
            logger.debug("PyTorch not available for GPU detection")
            return []
        except Exception as e:
            logger.warning(f"PyTorch GPU detection failed: {e}")
            return []
    
    def _detect_pynvml_gpu(self) -> List[DeviceCapabilities]:
        """Detect GPU using pynvml (NVIDIA Management Library)."""
        try:
            import pynvml
            
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            
            gpu_capabilities = []
            
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # Get memory info
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                memory_mb = memory_info.total / (1024**2)
                
                # Get device name and compute capability
                name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                
                try:
                    major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
                    compute_capability = f"{major}.{minor}"
                except:
                    compute_capability = "unknown"
                
                # Get driver version
                try:
                    driver_version = pynvml.nvmlSystemGetDriverVersion().decode('utf-8')
                except:
                    driver_version = "unknown"
                
                # Performance scoring
                performance_score = memory_mb / 1000
                if compute_capability != "unknown":
                    performance_score *= float(major)
                
                gpu_cap = DeviceCapabilities(
                    device_type=DeviceType.GPU,
                    device_count=1,
                    memory_mb=memory_mb,
                    compute_capability=compute_capability,
                    driver_version=driver_version,
                    available=True,
                    performance_score=performance_score
                )
                
                gpu_capabilities.append(gpu_cap)
                logger.info(f"GPU {i} detected via pynvml: {name}, {memory_mb:.0f}MB, CC {compute_capability}")
            
            return gpu_capabilities
            
        except ImportError:
            logger.debug("pynvml not available for GPU detection")
            return []
        except Exception as e:
            logger.warning(f"pynvml GPU detection failed: {e}")
            return []
    
    def _detect_faiss_gpu(self):
        """Detect FAISS GPU support availability."""
        try:
            import faiss
            
            # Check if GPU resources can be created
            if hasattr(faiss, 'StandardGpuResources'):
                try:
                    # Try to create GPU resources
                    res = faiss.StandardGpuResources()
                    self.faiss_gpu_available = True
                    logger.info("FAISS GPU support detected and available")
                except Exception as e:
                    logger.warning(f"FAISS GPU resources creation failed: {e}")
                    self.faiss_gpu_available = False
            else:
                logger.info("FAISS compiled without GPU support")
                self.faiss_gpu_available = False
                
        except ImportError:
            logger.warning("FAISS not available")
            self.faiss_gpu_available = False
        except Exception as e:
            logger.warning(f"FAISS GPU detection failed: {e}")
            self.faiss_gpu_available = False
    
    def _select_device(self):
        """Select optimal device based on configuration and capabilities."""
        # Force CPU if requested
        if self.force_cpu:
            self.selected_device = DeviceSelection(
                device_type=DeviceType.CPU,
                device_id=None,
                capabilities=self.cpu_capabilities,
                selection_reason="Forced CPU via FAISS_FORCE_CPU",
                fallback_applied=False
            )
            return
        
        # Check GPU enablement setting
        if self.gpu_enabled.lower() in ['false', '0', 'no']:
            self.selected_device = DeviceSelection(
                device_type=DeviceType.CPU,
                device_id=None,
                capabilities=self.cpu_capabilities,
                selection_reason="GPU disabled via FAISS_GPU_ENABLED",
                fallback_applied=False
            )
            return
        
        # Auto selection logic
        if self.gpu_enabled.lower() in ['true', '1', 'yes', 'auto']:
            # Prefer GPU if available and FAISS supports it
            if self.gpu_capabilities and self.faiss_gpu_available:
                # Select best GPU (highest performance score)
                best_gpu = max(self.gpu_capabilities, key=lambda g: g.performance_score)
                
                # Use specific device if requested
                device_id = self.gpu_device_id
                if device_id is not None and device_id < len(self.gpu_capabilities):
                    selected_gpu = self.gpu_capabilities[device_id]
                    reason = f"GPU {device_id} selected via FAISS_GPU_DEVICE"
                else:
                    selected_gpu = best_gpu
                    device_id = self.gpu_capabilities.index(best_gpu)
                    reason = f"Best GPU selected (performance score: {best_gpu.performance_score:.1f})"
                
                self.selected_device = DeviceSelection(
                    device_type=DeviceType.GPU,
                    device_id=device_id,
                    capabilities=selected_gpu,
                    selection_reason=reason,
                    fallback_applied=False
                )
                return
            
            # Fallback to CPU if GPU not available
            fallback_reason = []
            if not self.gpu_capabilities:
                fallback_reason.append("No GPU detected")
            if not self.faiss_gpu_available:
                fallback_reason.append("FAISS GPU support unavailable")
            
            self.selected_device = DeviceSelection(
                device_type=DeviceType.CPU,
                device_id=None,
                capabilities=self.cpu_capabilities,
                selection_reason=f"Fallback to CPU: {', '.join(fallback_reason)}",
                fallback_applied=True
            )
            
            if self.gpu_enabled.lower() in ['true', '1', 'yes']:
                logger.warning(f"GPU requested but unavailable, falling back to CPU")
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get comprehensive device information."""
        return {
            'selected_device': self.selected_device.to_dict() if self.selected_device else None,
            'cpu_capabilities': self.cpu_capabilities.to_dict() if self.cpu_capabilities else None,
            'gpu_capabilities': [gpu.to_dict() for gpu in self.gpu_capabilities],
            'faiss_gpu_available': self.faiss_gpu_available,
            'environment_config': {
                'gpu_enabled': self.gpu_enabled,
                'force_cpu': self.force_cpu,
                'gpu_device_id': self.gpu_device_id,
                'gpu_memory_fraction': self.gpu_memory_fraction
            }
        }
    
    def is_gpu_selected(self) -> bool:
        """Check if GPU is selected for computation."""
        return (self.selected_device and 
                self.selected_device.device_type == DeviceType.GPU)
    
    def is_cpu_selected(self) -> bool:
        """Check if CPU is selected for computation."""
        return (self.selected_device and 
                self.selected_device.device_type == DeviceType.CPU)
    
    def get_selected_device_type(self) -> DeviceType:
        """Get the selected device type."""
        if self.selected_device:
            return self.selected_device.device_type
        return DeviceType.CPU  # Default fallback
    
    def create_faiss_gpu_resource(self):
        """Create FAISS GPU resource if GPU is selected."""
        if not self.is_gpu_selected():
            raise RuntimeError("GPU not selected or available")
        
        if not self.faiss_gpu_available:
            raise RuntimeError("FAISS GPU support not available")
        
        try:
            import faiss
            
            # Create GPU resources
            res = faiss.StandardGpuResources()
            
            # Configure memory if fraction specified
            if hasattr(res, 'setTempMemory'):
                gpu_cap = self.selected_device.capabilities
                if gpu_cap.memory_mb:
                    temp_memory = int(gpu_cap.memory_mb * self.gpu_memory_fraction * 1024 * 1024)
                    res.setTempMemory(temp_memory)
                    logger.info(f"GPU memory configured: {temp_memory / (1024**2):.0f}MB")
            
            return res
            
        except Exception as e:
            logger.error(f"Failed to create FAISS GPU resource: {e}")
            raise
    
    def get_optimal_index_type(self) -> str:
        """Get optimal FAISS index type for selected device."""
        if self.is_gpu_selected():
            return "GPU_IVF"  # GPU-optimized index
        else:
            return "IVF_PQ"   # CPU-optimized index
    
    def validate_device_selection(self) -> Dict[str, Any]:
        """Validate current device selection and capabilities."""
        validation_results = {
            'device_selected': self.selected_device is not None,
            'device_available': False,
            'performance_adequate': False,
            'memory_sufficient': False,
            'issues': []
        }
        
        if not self.selected_device:
            validation_results['issues'].append("No device selected")
            return validation_results
        
        device = self.selected_device
        
        # Check device availability
        if device.capabilities.available:
            validation_results['device_available'] = True
        else:
            validation_results['issues'].append("Selected device not available")
        
        # Check performance adequacy
        min_performance_score = 1.0  # Minimum acceptable performance
        if device.capabilities.performance_score >= min_performance_score:
            validation_results['performance_adequate'] = True
        else:
            validation_results['issues'].append(
                f"Performance score {device.capabilities.performance_score:.1f} < {min_performance_score}"
            )
        
        # Check memory sufficiency for GPU
        if device.device_type == DeviceType.GPU and device.capabilities.memory_mb:
            min_gpu_memory = 1024  # 1GB minimum
            if device.capabilities.memory_mb >= min_gpu_memory:
                validation_results['memory_sufficient'] = True
            else:
                validation_results['issues'].append(
                    f"GPU memory {device.capabilities.memory_mb:.0f}MB < {min_gpu_memory}MB minimum"
                )
        else:
            validation_results['memory_sufficient'] = True  # CPU memory handled separately
        
        validation_results['overall_valid'] = (
            validation_results['device_available'] and
            validation_results['performance_adequate'] and
            validation_results['memory_sufficient']
        )
        
        return validation_results

# Global device manager instance
_device_manager: Optional[DeviceManager] = None

def get_device_manager() -> DeviceManager:
    """Get or create global device manager instance."""
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceManager()
    return _device_manager

def get_selected_device_type() -> DeviceType:
    """Convenience function to get selected device type."""
    manager = get_device_manager()
    return manager.get_selected_device_type()

def is_gpu_enabled() -> bool:
    """Convenience function to check if GPU is enabled."""
    manager = get_device_manager()
    return manager.is_gpu_selected()

def is_cpu_fallback() -> bool:
    """Check if current selection is a CPU fallback."""
    manager = get_device_manager()
    return (manager.selected_device and 
            manager.selected_device.fallback_applied)