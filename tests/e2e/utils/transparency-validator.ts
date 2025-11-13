/**
 * Transparency Validator for E2E Testing
 * 
 * Validates transparency and explainability requirements for:
 * - Model version tracking
 * - Confidence intervals
 * - Quality scores
 * - Uncertainty quantification
 * - Search method transparency
 * - Analog quality assessment
 */

export interface TransparencyData {
  model_version?: string;
  search_method?: string;
  confidence_intervals?: any;
  quality_scores?: any;
  uncertainty_quantification?: any;
  analog_quality?: any;
  data_lineage?: any;
  processing_pipeline?: any;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  metrics: any;
}

export class TransparencyValidator {
  private readonly REQUIRED_FIELDS = [
    'model_version',
    'search_method'
  ];

  private readonly OPTIONAL_FIELDS = [
    'confidence_intervals',
    'quality_scores',
    'uncertainty_quantification',
    'analog_quality',
    'data_lineage',
    'processing_pipeline'
  ];

  /**
   * Validate transparency data structure and content
   */
  validateTransparencyData(
    transparencyData: TransparencyData,
    context: 'analog' | 'forecast' = 'analog'
  ): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // 1. Validate required fields
    const requiredFieldErrors = this.validateRequiredFields(transparencyData);
    errors.push(...requiredFieldErrors);

    // 2. Validate model version format
    const modelVersionErrors = this.validateModelVersion(transparencyData.model_version);
    errors.push(...modelVersionErrors);

    // 3. Validate search method
    const searchMethodErrors = this.validateSearchMethod(transparencyData.search_method);
    errors.push(...searchMethodErrors);

    // 4. Context-specific validation
    if (context === 'analog') {
      const analogErrors = this.validateAnalogTransparency(transparencyData);
      errors.push(...analogErrors);
      
      const analogWarnings = this.getAnalogTransparencyWarnings(transparencyData);
      warnings.push(...analogWarnings);
    } else {
      const forecastErrors = this.validateForecastTransparency(transparencyData);
      errors.push(...forecastErrors);
      
      const forecastWarnings = this.getForecastTransparencyWarnings(transparencyData);
      warnings.push(...forecastWarnings);
    }

    // 5. Data quality assessment
    const qualityMetrics = this.assessTransparencyQuality(transparencyData);
    if (qualityMetrics.completeness < 0.7) {
      warnings.push(`Transparency data completeness is ${(qualityMetrics.completeness * 100).toFixed(1)}% (recommended: >70%)`);
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
      metrics: {
        ...qualityMetrics,
        context,
        validation_timestamp: new Date().toISOString()
      }
    };
  }

  /**
   * Validate required fields are present
   */
  private validateRequiredFields(data: TransparencyData): string[] {
    const errors: string[] = [];

    this.REQUIRED_FIELDS.forEach(field => {
      if (!data[field as keyof TransparencyData]) {
        errors.push(`Required transparency field '${field}' is missing`);
      }
    });

    return errors;
  }

  /**
   * Validate model version format and content
   */
  private validateModelVersion(modelVersion?: string): string[] {
    const errors: string[] = [];

    if (!modelVersion) {
      return errors; // Already caught by required fields validation
    }

    // Check version format (semantic versioning or timestamp-based)
    const semanticVersionRegex = /^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$/;
    const timestampVersionRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/;
    const hashVersionRegex = /^[a-f0-9]{7,40}$/i;

    if (!semanticVersionRegex.test(modelVersion) && 
        !timestampVersionRegex.test(modelVersion) && 
        !hashVersionRegex.test(modelVersion)) {
      errors.push(`Invalid model version format: '${modelVersion}'. Expected semantic version, timestamp, or git hash`);
    }

    return errors;
  }

  /**
   * Validate search method
   */
  private validateSearchMethod(searchMethod?: string): string[] {
    const errors: string[] = [];
    const validSearchMethods = ['faiss', 'exact', 'approximate', 'hybrid'];

    if (!searchMethod) {
      return errors; // Already caught by required fields validation
    }

    if (!validSearchMethods.includes(searchMethod.toLowerCase())) {
      errors.push(`Invalid search method: '${searchMethod}'. Expected one of: ${validSearchMethods.join(', ')}`);
    }

    // For TEST2, must be FAISS
    if (searchMethod.toLowerCase() !== 'faiss') {
      errors.push(`Search method must be 'faiss' for TEST2 requirements, got '${searchMethod}'`);
    }

    return errors;
  }

  /**
   * Validate analog-specific transparency data
   */
  private validateAnalogTransparency(data: TransparencyData): string[] {
    const errors: string[] = [];

    // Validate confidence intervals structure
    if (data.confidence_intervals) {
      const ciErrors = this.validateConfidenceIntervals(data.confidence_intervals);
      errors.push(...ciErrors);
    }

    // Validate quality scores
    if (data.quality_scores) {
      const qualityErrors = this.validateQualityScores(data.quality_scores);
      errors.push(...qualityErrors);
    }

    return errors;
  }

  /**
   * Validate forecast-specific transparency data
   */
  private validateForecastTransparency(data: TransparencyData): string[] {
    const errors: string[] = [];

    // Validate uncertainty quantification
    if (data.uncertainty_quantification) {
      const uqErrors = this.validateUncertaintyQuantification(data.uncertainty_quantification);
      errors.push(...uqErrors);
    }

    // Validate analog quality assessment
    if (data.analog_quality) {
      const aqErrors = this.validateAnalogQuality(data.analog_quality);
      errors.push(...aqErrors);
    }

    return errors;
  }

  /**
   * Validate confidence intervals structure
   */
  private validateConfidenceIntervals(confidenceIntervals: any): string[] {
    const errors: string[] = [];

    if (typeof confidenceIntervals !== 'object' || confidenceIntervals === null) {
      errors.push('Confidence intervals must be an object');
      return errors;
    }

    // Check for expected confidence levels
    const expectedLevels = ['0.5', '0.8', '0.9', '0.95'];
    const hasValidLevels = expectedLevels.some(level => 
      confidenceIntervals[level] !== undefined
    );

    if (!hasValidLevels) {
      errors.push(`Confidence intervals should include at least one of: ${expectedLevels.join(', ')}`);
    }

    // Validate interval structure
    Object.entries(confidenceIntervals).forEach(([level, interval]: [string, any]) => {
      const numericLevel = parseFloat(level);
      if (isNaN(numericLevel) || numericLevel <= 0 || numericLevel >= 1) {
        errors.push(`Invalid confidence level: ${level} (must be between 0 and 1)`);
      }

      if (typeof interval === 'object' && interval !== null) {
        if (typeof interval.lower !== 'number' || typeof interval.upper !== 'number') {
          errors.push(`Confidence interval for level ${level} must have numeric 'lower' and 'upper' bounds`);
        } else if (interval.lower >= interval.upper) {
          errors.push(`Confidence interval for level ${level}: lower bound must be less than upper bound`);
        }
      }
    });

    return errors;
  }

  /**
   * Validate quality scores structure
   */
  private validateQualityScores(qualityScores: any): string[] {
    const errors: string[] = [];

    if (typeof qualityScores !== 'object' || qualityScores === null) {
      errors.push('Quality scores must be an object');
      return errors;
    }

    const expectedScores = ['similarity', 'relevance', 'temporal_proximity', 'meteorological_consistency'];
    
    expectedScores.forEach(scoreType => {
      if (qualityScores[scoreType] !== undefined) {
        const score = qualityScores[scoreType];
        if (typeof score !== 'number' || score < 0 || score > 1) {
          errors.push(`Quality score '${scoreType}' must be a number between 0 and 1, got ${score}`);
        }
      }
    });

    return errors;
  }

  /**
   * Validate uncertainty quantification structure
   */
  private validateUncertaintyQuantification(uq: any): string[] {
    const errors: string[] = [];

    if (typeof uq !== 'object' || uq === null) {
      errors.push('Uncertainty quantification must be an object');
      return errors;
    }

    // Check for expected UQ components
    const expectedComponents = ['aleatory', 'epistemic', 'total'];
    
    expectedComponents.forEach(component => {
      if (uq[component] !== undefined) {
        if (typeof uq[component] !== 'number' || uq[component] < 0) {
          errors.push(`Uncertainty component '${component}' must be a non-negative number, got ${uq[component]}`);
        }
      }
    });

    // Validate uncertainty sources if present
    if (uq.sources && Array.isArray(uq.sources)) {
      uq.sources.forEach((source: any, index: number) => {
        if (typeof source !== 'object' || !source.name || typeof source.contribution !== 'number') {
          errors.push(`Uncertainty source at index ${index} must have 'name' and numeric 'contribution'`);
        }
      });
    }

    return errors;
  }

  /**
   * Validate analog quality assessment
   */
  private validateAnalogQuality(analogQuality: any): string[] {
    const errors: string[] = [];

    if (typeof analogQuality !== 'object' || analogQuality === null) {
      errors.push('Analog quality must be an object');
      return errors;
    }

    // Check for expected quality metrics
    const expectedMetrics = ['spatial_consistency', 'temporal_relevance', 'meteorological_similarity', 'ensemble_diversity'];
    
    expectedMetrics.forEach(metric => {
      if (analogQuality[metric] !== undefined) {
        const value = analogQuality[metric];
        if (typeof value !== 'number' || value < 0 || value > 1) {
          errors.push(`Analog quality metric '${metric}' must be a number between 0 and 1, got ${value}`);
        }
      }
    });

    return errors;
  }

  /**
   * Get warnings for analog transparency data
   */
  private getAnalogTransparencyWarnings(data: TransparencyData): string[] {
    const warnings: string[] = [];

    if (!data.confidence_intervals) {
      warnings.push('Confidence intervals not provided - uncertainty assessment may be incomplete');
    }

    if (!data.quality_scores) {
      warnings.push('Quality scores not provided - analog relevance cannot be assessed');
    }

    return warnings;
  }

  /**
   * Get warnings for forecast transparency data
   */
  private getForecastTransparencyWarnings(data: TransparencyData): string[] {
    const warnings: string[] = [];

    if (!data.uncertainty_quantification) {
      warnings.push('Uncertainty quantification not provided - forecast reliability cannot be assessed');
    }

    if (!data.analog_quality) {
      warnings.push('Analog quality assessment not provided - forecast basis quality unknown');
    }

    if (!data.data_lineage) {
      warnings.push('Data lineage not provided - forecast traceability limited');
    }

    return warnings;
  }

  /**
   * Assess overall transparency quality
   */
  private assessTransparencyQuality(data: TransparencyData): any {
    const totalFields = this.REQUIRED_FIELDS.length + this.OPTIONAL_FIELDS.length;
    const presentFields = this.REQUIRED_FIELDS.concat(this.OPTIONAL_FIELDS)
      .filter(field => data[field as keyof TransparencyData] !== undefined).length;

    const completeness = presentFields / totalFields;

    // Calculate richness score based on data depth
    let richness = 0;
    if (data.confidence_intervals && typeof data.confidence_intervals === 'object') {
      richness += 0.2;
    }
    if (data.quality_scores && typeof data.quality_scores === 'object') {
      richness += 0.2;
    }
    if (data.uncertainty_quantification && typeof data.uncertainty_quantification === 'object') {
      richness += 0.2;
    }
    if (data.analog_quality && typeof data.analog_quality === 'object') {
      richness += 0.2;
    }
    if (data.data_lineage && typeof data.data_lineage === 'object') {
      richness += 0.2;
    }

    // Calculate transparency score (combination of completeness and richness)
    const transparencyScore = (completeness * 0.6) + (richness * 0.4);

    return {
      completeness,
      richness,
      transparency_score: transparencyScore,
      present_fields: presentFields,
      total_fields: totalFields,
      required_fields_present: this.REQUIRED_FIELDS.every(field => 
        data[field as keyof TransparencyData] !== undefined
      ),
      optional_fields_present: this.OPTIONAL_FIELDS.filter(field => 
        data[field as keyof TransparencyData] !== undefined
      ).length
    };
  }

  /**
   * Generate comprehensive transparency validation report
   */
  generateTransparencyReport(
    analogTransparency?: TransparencyData,
    forecastTransparency?: TransparencyData
  ): any {
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        analog_validation: null as ValidationResult | null,
        forecast_validation: null as ValidationResult | null,
        overall_valid: true,
        total_errors: 0,
        total_warnings: 0
      },
      recommendations: [] as string[]
    };

    // Validate analog transparency
    if (analogTransparency) {
      report.summary.analog_validation = this.validateTransparencyData(analogTransparency, 'analog');
      if (!report.summary.analog_validation.valid) {
        report.summary.overall_valid = false;
      }
      report.summary.total_errors += report.summary.analog_validation.errors.length;
      report.summary.total_warnings += report.summary.analog_validation.warnings.length;
    }

    // Validate forecast transparency
    if (forecastTransparency) {
      report.summary.forecast_validation = this.validateTransparencyData(forecastTransparency, 'forecast');
      if (!report.summary.forecast_validation.valid) {
        report.summary.overall_valid = false;
      }
      report.summary.total_errors += report.summary.forecast_validation.errors.length;
      report.summary.total_warnings += report.summary.forecast_validation.warnings.length;
    }

    // Generate recommendations
    if (!report.summary.overall_valid) {
      report.recommendations.push('Address all transparency validation errors to ensure explainability compliance');
    }

    if (report.summary.total_warnings > 0) {
      report.recommendations.push('Consider implementing suggested transparency enhancements to improve explainability');
    }

    if (analogTransparency && report.summary.analog_validation?.metrics.transparency_score < 0.8) {
      report.recommendations.push('Enhance analog transparency data to improve explainability score');
    }

    if (forecastTransparency && report.summary.forecast_validation?.metrics.transparency_score < 0.8) {
      report.recommendations.push('Enhance forecast transparency data to improve explainability score');
    }

    return report;
  }
}