/**
 * FAISS Validator for E2E Testing
 * 
 * Validates FAISS integration and performance requirements:
 * - Data source must be 'faiss'
 * - Zero fallback usage
 * - Distance monotonicity in search results
 * - FAISS search time p95 < 1ms
 * - Index health and availability
 */

export interface FAISSSearchResult {
  similarity_score: number;
  distance: number;
  metadata: any;
}

export interface FAISSSearchStats {
  total_search_time_ms: number;
  faiss_search_time_ms: number;
  data_source: string;
  fallback_used: boolean;
  index_type?: string;
  indices_used?: string[];
}

export interface FAISSHealthStatus {
  status: string;
  indices_loaded: number;
  memory_usage_mb: number;
  performance_stats: {
    average_search_time_ms: number;
    p95_search_time_ms: number;
    total_searches: number;
    fallback_rate: number;
  };
  indices_status: Array<{
    horizon: string;
    status: string;
    size_mb: number;
    last_updated: string;
  }>;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  metrics: any;
}

export class FAISSValidator {
  private readonly FAISS_SEARCH_TIME_LIMIT_MS = 1.0;
  private readonly MIN_SIMILARITY_SCORE = 0.0;
  private readonly MAX_SIMILARITY_SCORE = 1.0;
  
  /**
   * Validate FAISS search results for correctness and performance
   */
  validateSearchResults(
    results: FAISSSearchResult[], 
    searchStats: FAISSSearchStats,
    expectedCount: number = 100
  ): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // 1. Validate data source requirement
    if (searchStats.data_source !== 'faiss') {
      errors.push(`Data source must be 'faiss', got '${searchStats.data_source}'`);
    }

    // 2. Validate zero fallback requirement
    if (searchStats.fallback_used) {
      errors.push('Fallback usage detected - must be zero for TEST2 requirements');
    }

    // 3. Validate FAISS search time requirement
    if (searchStats.faiss_search_time_ms > this.FAISS_SEARCH_TIME_LIMIT_MS) {
      errors.push(
        `FAISS search time ${searchStats.faiss_search_time_ms.toFixed(3)}ms exceeds ` +
        `${this.FAISS_SEARCH_TIME_LIMIT_MS}ms limit`
      );
    }

    // 4. Validate expected result count
    if (results.length !== expectedCount) {
      errors.push(`Expected ${expectedCount} results, got ${results.length}`);
    }

    // 5. Validate distance monotonicity
    const distanceMonotonicityError = this.validateDistanceMonotonicity(results);
    if (distanceMonotonicityError) {
      errors.push(distanceMonotonicityError);
    }

    // 6. Validate similarity scores
    const similarityErrors = this.validateSimilarityScores(results);
    errors.push(...similarityErrors);

    // 7. Validate metadata presence
    const metadataErrors = this.validateMetadata(results);
    errors.push(...metadataErrors);

    // 8. Performance warnings
    if (searchStats.faiss_search_time_ms > 0.5) {
      warnings.push(
        `FAISS search time ${searchStats.faiss_search_time_ms.toFixed(3)}ms ` +
        `is approaching the 1ms limit`
      );
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
      metrics: {
        result_count: results.length,
        faiss_search_time_ms: searchStats.faiss_search_time_ms,
        total_search_time_ms: searchStats.total_search_time_ms,
        data_source: searchStats.data_source,
        fallback_used: searchStats.fallback_used,
        distance_range: results.length > 0 ? {
          min: Math.min(...results.map(r => r.distance)),
          max: Math.max(...results.map(r => r.distance))
        } : null,
        similarity_range: results.length > 0 ? {
          min: Math.min(...results.map(r => r.similarity_score)),
          max: Math.max(...results.map(r => r.similarity_score))
        } : null
      }
    };
  }

  /**
   * Validate distance monotonicity (distances should be non-decreasing)
   */
  private validateDistanceMonotonicity(results: FAISSSearchResult[]): string | null {
    if (results.length < 2) return null;

    for (let i = 1; i < results.length; i++) {
      if (results[i].distance < results[i - 1].distance) {
        return `Distance monotonicity violation at index ${i}: ` +
               `${results[i].distance} < ${results[i - 1].distance}`;
      }
    }

    return null;
  }

  /**
   * Validate similarity scores are within expected range
   */
  private validateSimilarityScores(results: FAISSSearchResult[]): string[] {
    const errors: string[] = [];

    results.forEach((result, index) => {
      if (result.similarity_score < this.MIN_SIMILARITY_SCORE || 
          result.similarity_score > this.MAX_SIMILARITY_SCORE) {
        errors.push(
          `Invalid similarity score at index ${index}: ` +
          `${result.similarity_score} (must be between ${this.MIN_SIMILARITY_SCORE} and ${this.MAX_SIMILARITY_SCORE})`
        );
      }
    });

    return errors;
  }

  /**
   * Validate metadata presence and structure
   */
  private validateMetadata(results: FAISSSearchResult[]): string[] {
    const errors: string[] = [];

    results.forEach((result, index) => {
      if (!result.metadata) {
        errors.push(`Missing metadata at index ${index}`);
      } else if (typeof result.metadata !== 'object') {
        errors.push(`Invalid metadata type at index ${index}: expected object, got ${typeof result.metadata}`);
      }
    });

    return errors;
  }

  /**
   * Validate FAISS health status
   */
  validateHealthStatus(healthStatus: FAISSHealthStatus): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // 1. Overall health status
    if (healthStatus.status !== 'healthy') {
      errors.push(`FAISS health status is '${healthStatus.status}', expected 'healthy'`);
    }

    // 2. Indices loaded
    if (healthStatus.indices_loaded === 0) {
      errors.push('No FAISS indices are loaded');
    }

    // 3. Memory usage (reasonable limits)
    if (healthStatus.memory_usage_mb > 8000) { // 8GB limit
      warnings.push(`High memory usage: ${healthStatus.memory_usage_mb}MB`);
    }

    // 4. Performance stats validation
    const perfStats = healthStatus.performance_stats;
    
    if (perfStats.p95_search_time_ms > this.FAISS_SEARCH_TIME_LIMIT_MS) {
      errors.push(
        `P95 search time ${perfStats.p95_search_time_ms.toFixed(3)}ms exceeds ` +
        `${this.FAISS_SEARCH_TIME_LIMIT_MS}ms limit`
      );
    }

    if (perfStats.fallback_rate > 0) {
      errors.push(`Fallback rate ${perfStats.fallback_rate} must be zero for TEST2 requirements`);
    }

    if (perfStats.total_searches === 0) {
      warnings.push('No search operations recorded in performance stats');
    }

    // 5. Individual index status
    healthStatus.indices_status?.forEach((indexStatus, i) => {
      if (indexStatus.status !== 'loaded') {
        errors.push(`Index ${indexStatus.horizon} status is '${indexStatus.status}', expected 'loaded'`);
      }
      
      if (indexStatus.size_mb === 0) {
        warnings.push(`Index ${indexStatus.horizon} has zero size`);
      }
    });

    return {
      valid: errors.length === 0,
      errors,
      warnings,
      metrics: {
        health_status: healthStatus.status,
        indices_loaded: healthStatus.indices_loaded,
        memory_usage_mb: healthStatus.memory_usage_mb,
        p95_search_time_ms: perfStats.p95_search_time_ms,
        average_search_time_ms: perfStats.average_search_time_ms,
        total_searches: perfStats.total_searches,
        fallback_rate: perfStats.fallback_rate,
        indices_count: healthStatus.indices_status?.length || 0
      }
    };
  }

  /**
   * Validate FAISS index performance over multiple operations
   */
  validateBatchPerformance(searchStats: FAISSSearchStats[]): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (searchStats.length === 0) {
      errors.push('No search operations to validate');
      return { valid: false, errors, warnings, metrics: {} };
    }

    // Extract FAISS search times
    const faissTimes = searchStats.map(stats => stats.faiss_search_time_ms);
    
    // Calculate percentiles
    const sortedTimes = [...faissTimes].sort((a, b) => a - b);
    const p50 = sortedTimes[Math.floor(sortedTimes.length * 0.5)];
    const p95 = sortedTimes[Math.floor(sortedTimes.length * 0.95)];
    const p99 = sortedTimes[Math.floor(sortedTimes.length * 0.99)];
    const mean = faissTimes.reduce((sum, time) => sum + time, 0) / faissTimes.length;

    // Validate P95 requirement
    if (p95 > this.FAISS_SEARCH_TIME_LIMIT_MS) {
      errors.push(`P95 FAISS search time ${p95.toFixed(3)}ms exceeds ${this.FAISS_SEARCH_TIME_LIMIT_MS}ms limit`);
    }

    // Check for fallback usage
    const fallbackUsage = searchStats.filter(stats => stats.fallback_used).length;
    if (fallbackUsage > 0) {
      errors.push(`${fallbackUsage} out of ${searchStats.length} operations used fallback (must be zero)`);
    }

    // Check for non-FAISS data sources
    const nonFaissOperations = searchStats.filter(stats => stats.data_source !== 'faiss').length;
    if (nonFaissOperations > 0) {
      errors.push(`${nonFaissOperations} out of ${searchStats.length} operations used non-FAISS data source`);
    }

    // Performance warnings
    if (p95 > 0.5) {
      warnings.push(`P95 FAISS search time ${p95.toFixed(3)}ms is approaching the 1ms limit`);
    }

    if (mean > 0.3) {
      warnings.push(`Mean FAISS search time ${mean.toFixed(3)}ms is higher than expected`);
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
      metrics: {
        total_operations: searchStats.length,
        p50_faiss_time_ms: p50,
        p95_faiss_time_ms: p95,
        p99_faiss_time_ms: p99,
        mean_faiss_time_ms: mean,
        max_faiss_time_ms: Math.max(...faissTimes),
        min_faiss_time_ms: Math.min(...faissTimes),
        fallback_operations: fallbackUsage,
        non_faiss_operations: nonFaissOperations,
        fallback_rate: fallbackUsage / searchStats.length,
        data_source_compliance_rate: (searchStats.length - nonFaissOperations) / searchStats.length
      }
    };
  }

  /**
   * Generate comprehensive FAISS validation report
   */
  generateValidationReport(
    searchResults: Array<{ results: FAISSSearchResult[]; stats: FAISSSearchStats }>,
    healthStatus?: FAISSHealthStatus
  ): any {
    const report = {
      timestamp: new Date().toISOString(),
      test_summary: {
        total_searches: searchResults.length,
        validation_passed: true,
        overall_errors: [] as string[],
        overall_warnings: [] as string[]
      },
      search_validation: [] as ValidationResult[],
      health_validation: null as ValidationResult | null,
      batch_performance: null as ValidationResult | null,
      recommendations: [] as string[]
    };

    // Validate individual search results
    searchResults.forEach((search, index) => {
      const validation = this.validateSearchResults(search.results, search.stats);
      report.search_validation.push(validation);
      
      if (!validation.valid) {
        report.test_summary.validation_passed = false;
        report.test_summary.overall_errors.push(`Search ${index + 1}: ${validation.errors.join(', ')}`);
      }
      
      report.test_summary.overall_warnings.push(...validation.warnings.map(w => `Search ${index + 1}: ${w}`));
    });

    // Validate health status if provided
    if (healthStatus) {
      report.health_validation = this.validateHealthStatus(healthStatus);
      if (!report.health_validation.valid) {
        report.test_summary.validation_passed = false;
        report.test_summary.overall_errors.push(...report.health_validation.errors);
      }
      report.test_summary.overall_warnings.push(...report.health_validation.warnings);
    }

    // Validate batch performance
    if (searchResults.length > 1) {
      report.batch_performance = this.validateBatchPerformance(searchResults.map(s => s.stats));
      if (!report.batch_performance.valid) {
        report.test_summary.validation_passed = false;
        report.test_summary.overall_errors.push(...report.batch_performance.errors);
      }
      report.test_summary.overall_warnings.push(...report.batch_performance.warnings);
    }

    // Generate recommendations
    if (!report.test_summary.validation_passed) {
      report.recommendations.push('Address all validation errors before proceeding to production');
    }

    if (report.test_summary.overall_warnings.length > 0) {
      report.recommendations.push('Review and address performance warnings to ensure optimal operation');
    }

    if (report.batch_performance?.metrics.p95_faiss_time_ms > 0.5) {
      report.recommendations.push('Consider optimizing FAISS index configuration to improve search performance');
    }

    return report;
  }
}