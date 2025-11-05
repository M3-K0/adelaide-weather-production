#!/usr/bin/env python3
"""
Analog Quality Validation Framework
===================================

Implements comprehensive validation of analog search results including uniqueness
checks, similarity variance analysis, and degeneracy detection. Ensures analog
ensemble quality meets production standards.

VALIDATION COMPONENTS:
- Unique neighbor ID validation in search results
- Similarity variance checks (detect index row duplication)  
- Mean/best/stddev similarity logging for degeneracy detection
- Distance/similarity distribution validation
- Temporal consistency of analog patterns
- Spatial coherence validation

QUALITY GATES:
- Minimum unique neighbors threshold (≥95% of requested)
- Similarity variance floor (prevent degenerate indices)
- Distance distribution normality checks
- Temporal spread requirements for ensemble diversity

Author: Production QA Framework
Version: 1.0.0 - Analog Quality Assurance
"""

import logging
import warnings
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

class AnalogQualityStatus(Enum):
    """Analog search quality status."""
    EXCELLENT = "excellent"      # High quality, diverse analogs
    GOOD = "good"               # Acceptable quality
    DEGRADED = "degraded"       # Quality issues detected
    POOR = "poor"               # Significant quality problems
    FAILED = "failed"           # Unacceptable quality

@dataclass
class AnalogSearchMetrics:
    """Comprehensive metrics for analog search results."""
    # Basic search parameters
    requested_analogs: int
    returned_analogs: int
    search_time_ms: float
    
    # Uniqueness validation
    unique_analogs: int
    duplicate_count: int
    uniqueness_ratio: float
    
    # Similarity analysis
    mean_similarity: float
    best_similarity: float
    worst_similarity: float
    similarity_std: float
    similarity_variance: float
    similarity_range: float
    
    # Distribution analysis
    similarity_skewness: float
    similarity_kurtosis: float
    distribution_normality_p: float
    
    # Temporal analysis
    temporal_span_hours: float
    temporal_clustering_score: float
    seasonal_diversity_score: float
    
    # Quality assessment
    overall_quality_score: float
    quality_status: AnalogQualityStatus
    quality_issues: List[str]
    
    # Performance metrics
    index_efficiency: float
    search_accuracy: float

@dataclass
class AnalogEnsembleQuality:
    """Quality assessment for complete analog ensemble."""
    horizon: int
    timestamp: str
    
    # Per-search metrics
    search_metrics: AnalogSearchMetrics
    
    # Ensemble-level analysis
    analog_dates: List[str]
    temporal_distribution: Dict[str, int]  # Season/month counts
    spatial_coherence_score: float
    pattern_diversity_score: float
    
    # Outcome quality
    outcome_completeness: float
    outcome_validity_ratio: float
    outcome_range_coverage: Dict[str, float]  # Per variable
    
    # Final assessment
    ensemble_reliability: str  # 'high', 'medium', 'low', 'unreliable'
    confidence_factor: float   # 0-1 multiplier for forecast confidence
    recommendation: str        # Usage recommendation

class AnalogQualityValidator:
    """Production-grade analog quality validation system."""
    
    # Quality thresholds
    MIN_UNIQUENESS_RATIO = 0.95        # ≥95% unique neighbors
    MIN_SIMILARITY_VARIANCE = 1e-5     # Prevent degenerate indices
    MIN_TEMPORAL_SPAN_HOURS = 72       # Minimum temporal diversity
    MAX_TEMPORAL_CLUSTERING = 0.7      # Prevent temporal overfitting
    MIN_QUALITY_SCORE = 0.6            # Overall quality threshold
    MAX_SIMILARITY_SKEWNESS = 2.0      # Distribution shape limits
    
    def __init__(self, strict_mode: bool = True):
        """Initialize analog quality validator.
        
        Args:
            strict_mode: Enable strict quality gates for production
        """
        self.strict_mode = strict_mode
        self.validation_history = []
        
        # Adjust thresholds based on mode
        if not strict_mode:
            self.MIN_UNIQUENESS_RATIO = 0.90
            self.MIN_QUALITY_SCORE = 0.5
            self.MIN_TEMPORAL_SPAN_HOURS = 48
        
        logger.info(f"🔍 Analog Quality Validator initialized (strict_mode={strict_mode})")
        logger.info(f"   Uniqueness threshold: ≥{self.MIN_UNIQUENESS_RATIO:.0%}")
        logger.info(f"   Quality threshold: ≥{self.MIN_QUALITY_SCORE:.1f}")
    
    def validate_search_results(self, distances: np.ndarray, indices: np.ndarray,
                               analog_metadata: pd.DataFrame, 
                               search_time_ms: float) -> AnalogSearchMetrics:
        """Validate FAISS search results for quality issues.
        
        Args:
            distances: Distance/similarity scores from FAISS search
            indices: Analog indices from FAISS search
            analog_metadata: Metadata for analogs (with timestamps)
            search_time_ms: Time taken for search operation
            
        Returns:
            AnalogSearchMetrics with comprehensive quality assessment
        """
        # Flatten arrays if needed
        if distances.ndim > 1:
            distances = distances.flatten()
        if indices.ndim > 1:
            indices = indices.flatten()
        
        requested_analogs = len(indices)
        returned_analogs = len(indices[indices >= 0])  # Valid indices
        
        # Uniqueness validation
        unique_indices, unique_inverse = np.unique(indices, return_inverse=True)
        unique_analogs = len(unique_indices)
        duplicate_count = returned_analogs - unique_analogs
        uniqueness_ratio = unique_analogs / requested_analogs if requested_analogs > 0 else 0
        
        # Similarity analysis
        valid_distances = distances[indices >= 0]
        if len(valid_distances) > 0:
            mean_similarity = float(np.mean(valid_distances))
            best_similarity = float(np.max(valid_distances))
            worst_similarity = float(np.min(valid_distances))
            similarity_std = float(np.std(valid_distances))
            similarity_variance = float(np.var(valid_distances))
            similarity_range = best_similarity - worst_similarity
            
            # Distribution analysis
            if len(valid_distances) >= 3:
                similarity_skewness = float(stats.skew(valid_distances))
                similarity_kurtosis = float(stats.kurtosis(valid_distances))
                
                # Normality test (Shapiro-Wilk for small samples)
                if len(valid_distances) <= 5000:
                    _, normality_p = stats.shapiro(valid_distances)
                else:
                    _, normality_p = stats.normaltest(valid_distances)
                distribution_normality_p = float(normality_p)
            else:
                similarity_skewness = 0.0
                similarity_kurtosis = 0.0
                distribution_normality_p = 0.0
        else:
            # No valid distances
            mean_similarity = 0.0
            best_similarity = 0.0
            worst_similarity = 0.0
            similarity_std = 0.0
            similarity_variance = 0.0
            similarity_range = 0.0
            similarity_skewness = 0.0
            similarity_kurtosis = 0.0
            distribution_normality_p = 0.0
        
        # Temporal analysis
        temporal_metrics = self._analyze_temporal_distribution(indices, analog_metadata)
        temporal_span_hours = temporal_metrics['span_hours']
        temporal_clustering_score = temporal_metrics['clustering_score']
        seasonal_diversity_score = temporal_metrics['seasonal_diversity']
        
        # Quality assessment
        quality_issues = []
        
        # Uniqueness check
        if uniqueness_ratio < self.MIN_UNIQUENESS_RATIO:
            quality_issues.append(
                f"Low uniqueness ratio: {uniqueness_ratio:.1%} < {self.MIN_UNIQUENESS_RATIO:.1%}"
            )
        
        # Similarity variance check
        if similarity_variance < self.MIN_SIMILARITY_VARIANCE:
            quality_issues.append(
                f"Degenerate similarity variance: {similarity_variance:.2e}"
            )
        
        # Temporal diversity check
        if temporal_span_hours < self.MIN_TEMPORAL_SPAN_HOURS:
            quality_issues.append(
                f"Insufficient temporal span: {temporal_span_hours:.1f}h < {self.MIN_TEMPORAL_SPAN_HOURS}h"
            )
        
        # Temporal clustering check
        if temporal_clustering_score > self.MAX_TEMPORAL_CLUSTERING:
            quality_issues.append(
                f"Excessive temporal clustering: {temporal_clustering_score:.2f}"
            )
        
        # Distribution shape check
        if abs(similarity_skewness) > self.MAX_SIMILARITY_SKEWNESS:
            quality_issues.append(
                f"Extreme similarity skewness: {similarity_skewness:.2f}"
            )
        
        # Performance metrics
        index_efficiency = self._calculate_index_efficiency(search_time_ms, returned_analogs)
        search_accuracy = self._calculate_search_accuracy(distances, indices)
        
        # Overall quality score
        quality_components = [
            uniqueness_ratio,
            min(1.0, similarity_variance / self.MIN_SIMILARITY_VARIANCE),
            min(1.0, temporal_span_hours / self.MIN_TEMPORAL_SPAN_HOURS),
            1.0 - temporal_clustering_score,
            seasonal_diversity_score,
            min(1.0, 1.0 / (1.0 + abs(similarity_skewness)))
        ]
        overall_quality_score = np.mean(quality_components)
        
        # Determine quality status
        if overall_quality_score >= 0.9 and len(quality_issues) == 0:
            quality_status = AnalogQualityStatus.EXCELLENT
        elif overall_quality_score >= 0.75 and len(quality_issues) <= 1:
            quality_status = AnalogQualityStatus.GOOD
        elif overall_quality_score >= self.MIN_QUALITY_SCORE:
            quality_status = AnalogQualityStatus.DEGRADED
        elif overall_quality_score >= 0.3:
            quality_status = AnalogQualityStatus.POOR
        else:
            quality_status = AnalogQualityStatus.FAILED
        
        return AnalogSearchMetrics(
            requested_analogs=requested_analogs,
            returned_analogs=returned_analogs,
            search_time_ms=search_time_ms,
            unique_analogs=unique_analogs,
            duplicate_count=duplicate_count,
            uniqueness_ratio=uniqueness_ratio,
            mean_similarity=mean_similarity,
            best_similarity=best_similarity,
            worst_similarity=worst_similarity,
            similarity_std=similarity_std,
            similarity_variance=similarity_variance,
            similarity_range=similarity_range,
            similarity_skewness=similarity_skewness,
            similarity_kurtosis=similarity_kurtosis,
            distribution_normality_p=distribution_normality_p,
            temporal_span_hours=temporal_span_hours,
            temporal_clustering_score=temporal_clustering_score,
            seasonal_diversity_score=seasonal_diversity_score,
            overall_quality_score=overall_quality_score,
            quality_status=quality_status,
            quality_issues=quality_issues,
            index_efficiency=index_efficiency,
            search_accuracy=search_accuracy
        )
    
    def _analyze_temporal_distribution(self, indices: np.ndarray, 
                                     analog_metadata: pd.DataFrame) -> Dict[str, float]:
        """Analyze temporal distribution of analog patterns."""
        try:
            # Get analog timestamps
            valid_indices = indices[indices >= 0]
            if len(valid_indices) == 0:
                return {
                    'span_hours': 0.0,
                    'clustering_score': 1.0,
                    'seasonal_diversity': 0.0
                }
            
            # Extract timestamps for valid analogs
            analog_times = []
            for idx in valid_indices:
                if idx < len(analog_metadata):
                    timestamp = analog_metadata.iloc[idx].get('init_time')
                    if timestamp is not None:
                        if isinstance(timestamp, str):
                            timestamp = pd.to_datetime(timestamp)
                        analog_times.append(timestamp)
            
            if len(analog_times) < 2:
                return {
                    'span_hours': 0.0,
                    'clustering_score': 1.0,
                    'seasonal_diversity': 0.0
                }
            
            analog_times = pd.to_datetime(analog_times)
            
            # Temporal span
            time_span = analog_times.max() - analog_times.min()
            span_hours = time_span.total_seconds() / 3600
            
            # Temporal clustering (coefficient of variation of time differences)
            time_diffs = np.diff(np.sort(analog_times.values)).astype('timedelta64[h]').astype(float)
            if len(time_diffs) > 0 and np.mean(time_diffs) > 0:
                clustering_score = np.std(time_diffs) / np.mean(time_diffs)
                clustering_score = min(1.0, clustering_score)  # Normalize
            else:
                clustering_score = 1.0
            
            # Seasonal diversity (distribution across months)
            months = analog_times.month
            month_counts = pd.Series(months).value_counts()
            if len(month_counts) > 1:
                # Shannon entropy normalized by max possible entropy
                month_probs = month_counts / len(months)
                entropy = -np.sum(month_probs * np.log(month_probs + 1e-12))
                max_entropy = np.log(12)  # 12 months
                seasonal_diversity = entropy / max_entropy
            else:
                seasonal_diversity = 0.0
            
            return {
                'span_hours': span_hours,
                'clustering_score': clustering_score,
                'seasonal_diversity': seasonal_diversity
            }
            
        except Exception as e:
            logger.warning(f"Temporal analysis failed: {e}")
            return {
                'span_hours': 0.0,
                'clustering_score': 1.0,
                'seasonal_diversity': 0.0
            }
    
    def _calculate_index_efficiency(self, search_time_ms: float, returned_analogs: int) -> float:
        """Calculate index search efficiency."""
        if returned_analogs == 0:
            return 0.0
        
        # Efficiency based on analogs per millisecond
        efficiency = returned_analogs / max(1.0, search_time_ms)
        # Normalize to 0-1 scale (assuming 1 analog/ms is excellent)
        return min(1.0, efficiency)
    
    def _calculate_search_accuracy(self, distances: np.ndarray, indices: np.ndarray) -> float:
        """Calculate search accuracy based on distance monotonicity."""
        valid_distances = distances[indices >= 0]
        if len(valid_distances) < 2:
            return 1.0
        
        # Check if distances are in descending order (higher similarity first)
        sorted_distances = np.sort(valid_distances)[::-1]  # Descending
        
        # Calculate rank correlation (Spearman)
        try:
            correlation, _ = stats.spearmanr(valid_distances, sorted_distances)
            accuracy = max(0.0, correlation) if not np.isnan(correlation) else 0.0
        except:
            accuracy = 0.0
        
        return accuracy
    
    def assess_ensemble_quality(self, horizon: int, search_metrics: AnalogSearchMetrics,
                              analog_outcomes: np.ndarray, analog_metadata: pd.DataFrame) -> AnalogEnsembleQuality:
        """Assess quality of complete analog ensemble.
        
        Args:
            horizon: Forecast horizon in hours
            search_metrics: Search quality metrics
            analog_outcomes: Outcome data for analogs
            analog_metadata: Metadata for analogs
            
        Returns:
            AnalogEnsembleQuality with comprehensive ensemble assessment
        """
        # Extract analog dates
        analog_dates = []
        for i in range(min(len(analog_metadata), analog_outcomes.shape[0])):
            timestamp = analog_metadata.iloc[i].get('init_time')
            if timestamp is not None:
                if isinstance(timestamp, str):
                    analog_dates.append(timestamp)
                else:
                    analog_dates.append(timestamp.isoformat())
        
        # Temporal distribution analysis
        temporal_distribution = self._analyze_temporal_distribution_by_season(analog_dates)
        
        # Spatial coherence (simplified - based on outcome similarity)
        spatial_coherence_score = self._calculate_spatial_coherence(analog_outcomes)
        
        # Pattern diversity (based on outcome variance)
        pattern_diversity_score = self._calculate_pattern_diversity(analog_outcomes)
        
        # Outcome quality assessment
        outcome_completeness = self._assess_outcome_completeness(analog_outcomes)
        outcome_validity_ratio = self._assess_outcome_validity(analog_outcomes)
        outcome_range_coverage = self._assess_outcome_range_coverage(analog_outcomes)
        
        # Determine ensemble reliability
        reliability_factors = [
            search_metrics.overall_quality_score,
            spatial_coherence_score,
            pattern_diversity_score,
            outcome_completeness,
            outcome_validity_ratio
        ]
        
        ensemble_score = np.mean(reliability_factors)
        
        if ensemble_score >= 0.85 and search_metrics.quality_status in [AnalogQualityStatus.EXCELLENT, AnalogQualityStatus.GOOD]:
            ensemble_reliability = 'high'
            confidence_factor = 1.0
            recommendation = 'Use forecast with full confidence'
        elif ensemble_score >= 0.70:
            ensemble_reliability = 'medium' 
            confidence_factor = 0.8
            recommendation = 'Use forecast with moderate confidence'
        elif ensemble_score >= 0.50:
            ensemble_reliability = 'low'
            confidence_factor = 0.6
            recommendation = 'Use forecast with caution, consider ensemble spread'
        else:
            ensemble_reliability = 'unreliable'
            confidence_factor = 0.3
            recommendation = 'Forecast not recommended, quality too low'
        
        return AnalogEnsembleQuality(
            horizon=horizon,
            timestamp=datetime.now().isoformat(),
            search_metrics=search_metrics,
            analog_dates=analog_dates,
            temporal_distribution=temporal_distribution,
            spatial_coherence_score=spatial_coherence_score,
            pattern_diversity_score=pattern_diversity_score,
            outcome_completeness=outcome_completeness,
            outcome_validity_ratio=outcome_validity_ratio,
            outcome_range_coverage=outcome_range_coverage,
            ensemble_reliability=ensemble_reliability,
            confidence_factor=confidence_factor,
            recommendation=recommendation
        )
    
    def _analyze_temporal_distribution_by_season(self, analog_dates: List[str]) -> Dict[str, int]:
        """Analyze temporal distribution by season."""
        distribution = {'spring': 0, 'summer': 0, 'autumn': 0, 'winter': 0}
        
        for date_str in analog_dates:
            try:
                date = pd.to_datetime(date_str)
                month = date.month
                
                if month in [9, 10, 11]:  # Spring (Southern Hemisphere)
                    distribution['spring'] += 1
                elif month in [12, 1, 2]:  # Summer
                    distribution['summer'] += 1
                elif month in [3, 4, 5]:  # Autumn
                    distribution['autumn'] += 1
                else:  # Winter [6, 7, 8]
                    distribution['winter'] += 1
            except:
                continue
        
        return distribution
    
    def _calculate_spatial_coherence(self, analog_outcomes: np.ndarray) -> float:
        """Calculate spatial coherence of analog patterns."""
        if analog_outcomes.size == 0:
            return 0.0
        
        try:
            # Calculate correlation between outcome variables
            if analog_outcomes.shape[1] > 1:
                correlations = np.corrcoef(analog_outcomes.T)
                # Average absolute correlation (excluding diagonal)
                mask = ~np.eye(correlations.shape[0], dtype=bool)
                avg_correlation = np.mean(np.abs(correlations[mask]))
                return min(1.0, avg_correlation)
            else:
                return 1.0
        except:
            return 0.0
    
    def _calculate_pattern_diversity(self, analog_outcomes: np.ndarray) -> float:
        """Calculate pattern diversity based on outcome variance."""
        if analog_outcomes.size == 0:
            return 0.0
        
        try:
            # Normalized variance across analogs
            variances = np.var(analog_outcomes, axis=0)
            means = np.mean(analog_outcomes, axis=0)
            
            # Coefficient of variation for each variable
            cvs = variances / (np.abs(means) + 1e-8)
            
            # Average coefficient of variation (higher = more diverse)
            avg_cv = np.mean(cvs)
            
            # Normalize to 0-1 scale
            diversity_score = min(1.0, avg_cv / 2.0)  # Assume CV of 2.0 is maximum useful diversity
            
            return diversity_score
        except:
            return 0.0
    
    def _assess_outcome_completeness(self, analog_outcomes: np.ndarray) -> float:
        """Assess completeness of outcome data."""
        if analog_outcomes.size == 0:
            return 0.0
        
        # Fraction of non-NaN, finite values
        valid_count = np.sum(np.isfinite(analog_outcomes))
        total_count = analog_outcomes.size
        
        return valid_count / total_count if total_count > 0 else 0.0
    
    def _assess_outcome_validity(self, analog_outcomes: np.ndarray) -> float:
        """Assess validity of outcome values (within reasonable ranges)."""
        if analog_outcomes.size == 0:
            return 0.0
        
        # Define reasonable ranges for different variables (simplified)
        variable_ranges = [
            (4800, 6200),    # z500 (gpm)
            (200, 350),      # t2m (K)
            (200, 340),      # t850 (K)
            (0, 0.030),      # q850 (kg/kg)
            (-50, 50),       # u10 (m/s)
            (-50, 50),       # v10 (m/s)
            (-80, 80),       # u850 (m/s)
            (-80, 80),       # v850 (m/s)
            (0, 8000)        # cape (J/kg)
        ]
        
        valid_counts = []
        for i in range(min(analog_outcomes.shape[1], len(variable_ranges))):
            var_data = analog_outcomes[:, i]
            min_val, max_val = variable_ranges[i]
            
            valid_mask = (var_data >= min_val) & (var_data <= max_val) & np.isfinite(var_data)
            valid_ratio = np.sum(valid_mask) / len(var_data) if len(var_data) > 0 else 0
            valid_counts.append(valid_ratio)
        
        return np.mean(valid_counts) if valid_counts else 0.0
    
    def _assess_outcome_range_coverage(self, analog_outcomes: np.ndarray) -> Dict[str, float]:
        """Assess range coverage for each variable."""
        variable_names = ['z500', 't2m', 't850', 'q850', 'u10', 'v10', 'u850', 'v850', 'cape']
        range_coverage = {}
        
        for i in range(min(analog_outcomes.shape[1], len(variable_names))):
            var_data = analog_outcomes[:, i]
            var_name = variable_names[i]
            
            if len(var_data) > 0 and np.any(np.isfinite(var_data)):
                finite_data = var_data[np.isfinite(var_data)]
                if len(finite_data) > 1:
                    data_range = np.max(finite_data) - np.min(finite_data)
                    # Normalize by typical range for this variable
                    typical_ranges = {
                        'z500': 400, 't2m': 50, 't850': 40, 'q850': 0.02,
                        'u10': 30, 'v10': 30, 'u850': 40, 'v850': 40, 'cape': 2000
                    }
                    typical_range = typical_ranges.get(var_name, 1.0)
                    coverage = min(1.0, data_range / typical_range)
                else:
                    coverage = 0.0
            else:
                coverage = 0.0
            
            range_coverage[var_name] = coverage
        
        return range_coverage
    
    def generate_quality_report(self, ensemble_quality: AnalogEnsembleQuality) -> str:
        """Generate comprehensive quality report."""
        lines = []
        lines.append(f"🔍 Analog Quality Report - Horizon +{ensemble_quality.horizon}h")
        lines.append("=" * 70)
        
        # Search quality summary
        search = ensemble_quality.search_metrics
        lines.append(f"Search Quality: {search.quality_status.value.upper()}")
        lines.append(f"Overall Score: {search.overall_quality_score:.2f}")
        lines.append(f"Uniqueness: {search.unique_analogs}/{search.requested_analogs} "
                    f"({search.uniqueness_ratio:.1%})")
        lines.append(f"Similarity: μ={search.mean_similarity:.3f}, σ={search.similarity_std:.3f}")
        lines.append("")
        
        # Temporal analysis
        lines.append(f"Temporal Analysis:")
        lines.append(f"  Span: {search.temporal_span_hours:.1f} hours")
        lines.append(f"  Clustering: {search.temporal_clustering_score:.2f}")
        lines.append(f"  Seasonal diversity: {search.seasonal_diversity_score:.2f}")
        
        # Seasonal distribution
        total_analogs = sum(ensemble_quality.temporal_distribution.values())
        if total_analogs > 0:
            lines.append(f"  Season distribution:")
            for season, count in ensemble_quality.temporal_distribution.items():
                pct = 100 * count / total_analogs
                lines.append(f"    {season.capitalize()}: {count} ({pct:.0f}%)")
        lines.append("")
        
        # Ensemble quality
        lines.append(f"Ensemble Quality:")
        lines.append(f"  Reliability: {ensemble_quality.ensemble_reliability.upper()}")
        lines.append(f"  Confidence factor: {ensemble_quality.confidence_factor:.1f}")
        lines.append(f"  Spatial coherence: {ensemble_quality.spatial_coherence_score:.2f}")
        lines.append(f"  Pattern diversity: {ensemble_quality.pattern_diversity_score:.2f}")
        lines.append(f"  Outcome completeness: {ensemble_quality.outcome_completeness:.1%}")
        lines.append(f"  Outcome validity: {ensemble_quality.outcome_validity_ratio:.1%}")
        lines.append("")
        
        # Issues and recommendations
        if search.quality_issues:
            lines.append("⚠️  Quality Issues:")
            for issue in search.quality_issues:
                lines.append(f"  • {issue}")
            lines.append("")
        
        lines.append(f"📋 Recommendation: {ensemble_quality.recommendation}")
        
        # Performance
        lines.append("")
        lines.append(f"Performance:")
        lines.append(f"  Search time: {search.search_time_ms:.1f}ms")
        lines.append(f"  Index efficiency: {search.index_efficiency:.3f}")
        lines.append(f"  Search accuracy: {search.search_accuracy:.3f}")
        
        return "\n".join(lines)

def main():
    """Demonstration of analog quality validation."""
    validator = AnalogQualityValidator(strict_mode=True)
    
    # Mock search results for testing
    n_analogs = 50
    distances = np.random.beta(2, 5, n_analogs)  # Realistic similarity distribution
    distances = np.sort(distances)[::-1]  # Descending order
    indices = np.arange(n_analogs)
    
    # Add some quality issues for testing
    indices[45:] = indices[40:45]  # Introduce duplicates
    distances[48:] = distances[47]  # Degenerate similarities
    
    # Mock metadata
    base_time = pd.Timestamp('2020-01-01')
    analog_times = [base_time + pd.Timedelta(hours=h) for h in np.random.randint(0, 8760, n_analogs)]
    analog_metadata = pd.DataFrame({'init_time': analog_times})
    
    # Mock outcome data
    analog_outcomes = np.random.randn(n_analogs, 9)
    # Add realistic scales
    analog_outcomes[:, 0] = 5500 + analog_outcomes[:, 0] * 200  # z500
    analog_outcomes[:, 1] = 293 + analog_outcomes[:, 1] * 10    # t2m
    # ... (other variables)
    
    # Validate search results
    search_metrics = validator.validate_search_results(
        distances, indices, analog_metadata, search_time_ms=15.5
    )
    
    # Assess ensemble quality
    ensemble_quality = validator.assess_ensemble_quality(
        horizon=24, search_metrics=search_metrics, 
        analog_outcomes=analog_outcomes, analog_metadata=analog_metadata
    )
    
    # Generate report
    report = validator.generate_quality_report(ensemble_quality)
    print(report)

if __name__ == "__main__":
    main()