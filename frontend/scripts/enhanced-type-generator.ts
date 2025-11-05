#!/usr/bin/env tsx
/**
 * Enhanced TypeScript Type Generation Pipeline
 * ============================================
 * 
 * Automated TypeScript type generation from OpenAPI schema with:
 * - OpenAPI-to-TypeScript conversion
 * - Type validation and safety checks
 * - Pact contract integration
 * - CI/CD pipeline compatibility
 * - Error handling and reporting
 * - Incremental generation with change detection
 */

import fs from 'fs/promises';
import path from 'path';
import { execSync } from 'child_process';

interface GenerationConfig {
  openApiPath: string;
  outputDir: string;
  pactDir: string;
  validateTypes: boolean;
  generateDocs: boolean;
  ciMode: boolean;
}

interface GenerationResult {
  success: boolean;
  errors: string[];
  warnings: string[];
  filesGenerated: string[];
  schemaHash?: string;
  typesHash?: string;
}

interface TypeValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  coverage: {
    totalTypes: number;
    validatedTypes: number;
    missingTypes: string[];
  };
}

class EnhancedTypeGenerator {
  private config: GenerationConfig;
  private isCI: boolean;

  constructor(config: Partial<GenerationConfig> = {}) {
    this.isCI = process.env.CI === 'true';
    this.config = {
      openApiPath: config.openApiPath || 'openapi.json',
      outputDir: config.outputDir || 'types',
      pactDir: config.pactDir || 'pact',
      validateTypes: config.validateTypes ?? true,
      generateDocs: config.generateDocs ?? true,
      ciMode: config.ciMode ?? this.isCI,
      ...config
    };
  }

  /**
   * Main type generation pipeline
   */
  async generateTypes(): Promise<GenerationResult> {
    const result: GenerationResult = {
      success: false,
      errors: [],
      warnings: [],
      filesGenerated: []
    };

    try {
      if (this.isCI) {
        console.log('::group::TypeScript Type Generation');
      }

      console.log('🚀 Starting enhanced type generation...');
      console.log(`📂 OpenAPI Schema: ${this.config.openApiPath}`);
      console.log(`📁 Output Directory: ${this.config.outputDir}`);
      console.log(`🔍 Validation: ${this.config.validateTypes ? 'enabled' : 'disabled'}`);

      // Step 1: Validate OpenAPI schema exists and is valid
      const schemaValidation = await this.validateOpenAPISchema();
      if (!schemaValidation.success) {
        result.errors.push(...schemaValidation.errors);
        return result;
      }

      result.schemaHash = schemaValidation.hash;

      // Step 2: Check for changes (incremental generation)
      const hasChanges = await this.checkForChanges(result.schemaHash!);
      if (!hasChanges && !this.config.ciMode) {
        console.log('✨ No changes detected, skipping generation');
        result.success = true;
        return result;
      }

      // Step 3: Generate TypeScript types from OpenAPI
      const generationResult = await this.generateFromOpenAPI();
      if (!generationResult.success) {
        result.errors.push(...generationResult.errors);
        return result;
      }

      result.filesGenerated.push(...generationResult.files);

      // Step 4: Generate utility types and helpers
      const utilityResult = await this.generateUtilityTypes();
      if (utilityResult.success) {
        result.filesGenerated.push(...utilityResult.files);
      } else {
        result.warnings.push(...utilityResult.errors);
      }

      // Step 5: Validate generated types
      if (this.config.validateTypes) {
        const validationResult = await this.validateGeneratedTypes();
        if (!validationResult.valid) {
          result.errors.push(...validationResult.errors);
          result.warnings.push(...validationResult.warnings);
        }
      }

      // Step 6: Update Pact contracts with new types
      const pactResult = await this.updatePactContracts();
      if (!pactResult.success) {
        result.warnings.push(...pactResult.errors);
      }

      // Step 7: Generate documentation
      if (this.config.generateDocs) {
        const docsResult = await this.generateDocumentation();
        if (docsResult.success) {
          result.filesGenerated.push(...docsResult.files);
        }
      }

      // Step 8: Run TypeScript compilation check
      const compilationResult = await this.validateTypeScriptCompilation();
      if (!compilationResult.success) {
        result.errors.push(...compilationResult.errors);
        return result;
      }

      // Save generation metadata
      await this.saveGenerationMetadata(result);

      result.success = result.errors.length === 0;

      console.log(`\n📊 Generation Summary:`);
      console.log(`  ✅ Files Generated: ${result.filesGenerated.length}`);
      console.log(`  ❌ Errors: ${result.errors.length}`);
      console.log(`  ⚠️ Warnings: ${result.warnings.length}`);

      if (this.isCI) {
        console.log('::endgroup::');
      }

      return result;

    } catch (error) {
      result.errors.push(`Type generation failed: ${error}`);
      if (this.isCI) {
        console.log(`::error::Type generation failed: ${error}`);
        console.log('::endgroup::');
      }
      return result;
    }
  }

  /**
   * Validate OpenAPI schema file
   */
  private async validateOpenAPISchema(): Promise<{
    success: boolean;
    errors: string[];
    hash?: string;
  }> {
    try {
      const schemaPath = path.resolve(this.config.openApiPath);
      const schemaContent = await fs.readFile(schemaPath, 'utf-8');
      const schema = JSON.parse(schemaContent);

      const errors: string[] = [];

      // Basic OpenAPI validation
      if (!schema.openapi) {
        errors.push('Invalid OpenAPI schema: missing openapi version');
      }

      if (!schema.paths || Object.keys(schema.paths).length === 0) {
        errors.push('Invalid OpenAPI schema: no paths defined');
      }

      if (!schema.components?.schemas) {
        errors.push('Invalid OpenAPI schema: no component schemas defined');
      }

      // Calculate schema hash
      const hash = require('crypto')
        .createHash('sha256')
        .update(schemaContent)
        .digest('hex')
        .substring(0, 12);

      return {
        success: errors.length === 0,
        errors,
        hash
      };

    } catch (error) {
      return {
        success: false,
        errors: [`Failed to validate OpenAPI schema: ${error}`]
      };
    }
  }

  /**
   * Check if schema has changed since last generation
   */
  private async checkForChanges(currentHash: string): Promise<boolean> {
    try {
      const hashFile = path.join(this.config.outputDir, '.schema_hash');
      
      if (await this.fileExists(hashFile)) {
        const previousHash = await fs.readFile(hashFile, 'utf-8');
        return previousHash.trim() !== currentHash;
      }

      return true; // No previous hash, assume changes
    } catch {
      return true;
    }
  }

  /**
   * Generate TypeScript types from OpenAPI schema
   */
  private async generateFromOpenAPI(): Promise<{
    success: boolean;
    errors: string[];
    files: string[];
  }> {
    try {
      // Ensure output directory exists
      await fs.mkdir(this.config.outputDir, { recursive: true });

      // Use openapi-typescript to generate types
      const outputPath = path.join(this.config.outputDir, 'generated-api.ts');
      
      try {
        execSync(
          `npx openapi-typescript ${this.config.openApiPath} -o ${outputPath}`,
          { 
            stdio: this.isCI ? 'pipe' : 'inherit',
            cwd: process.cwd()
          }
        );
      } catch (error: any) {
        return {
          success: false,
          errors: [`Failed to generate types: ${error.message}`],
          files: []
        };
      }

      // Enhance generated types with custom utilities
      await this.enhanceGeneratedTypes(outputPath);

      return {
        success: true,
        errors: [],
        files: [outputPath]
      };

    } catch (error) {
      return {
        success: false,
        errors: [`Type generation failed: ${error}`],
        files: []
      };
    }
  }

  /**
   * Enhance generated types with custom utilities
   */
  private async enhanceGeneratedTypes(filePath: string): Promise<void> {
    try {
      let content = await fs.readFile(filePath, 'utf-8');

      // Add custom header
      const header = `/**
 * Auto-generated TypeScript types for Adelaide Weather Forecasting API
 * Generated on: ${new Date().toISOString()}
 * Schema Hash: ${await this.getSchemaHash()}
 * 
 * DO NOT EDIT MANUALLY - This file is auto-generated
 * To update types, run: npm run generate:types
 */

`;

      // Add utility type helpers
      const utilities = `
// Enhanced utility types for Adelaide Weather API
export type ApiResponse<T> = T | { error: string; details?: string };

export type AvailableVariables<T extends { variables: Record<string, any> }> = {
  [K in keyof T['variables']]: T['variables'][K]['available'] extends true ? K : never;
}[keyof T['variables']];

// Type guards for runtime safety
export function isApiError(response: unknown): response is { error: string } {
  return typeof response === 'object' && response !== null && 'error' in response;
}

export function isValidForecast(data: unknown): data is { horizon: string; variables: Record<string, any> } {
  return (
    typeof data === 'object' &&
    data !== null &&
    'horizon' in data &&
    'variables' in data
  );
}

`;

      content = header + content + utilities;
      await fs.writeFile(filePath, content);

    } catch (error) {
      console.warn(`Failed to enhance generated types: ${error}`);
    }
  }

  /**
   * Generate utility types and helpers
   */
  private async generateUtilityTypes(): Promise<{
    success: boolean;
    errors: string[];
    files: string[];
  }> {
    try {
      const utilityContent = `/**
 * Utility types and helpers for Adelaide Weather API
 * Auto-generated on: ${new Date().toISOString()}
 */

import type { components } from './generated-api';

// Extract useful types from OpenAPI components
export type ForecastResponse = components['schemas']['ForecastResponse'];
export type HealthResponse = components['schemas']['HealthResponse'];
export type VariableResult = components['schemas']['VariableResult'];
export type RiskAssessment = components['schemas']['RiskAssessment'];
export type AnalogsSummary = components['schemas']['AnalogsSummary'];

// Weather variable types
export type WeatherVariable = 
  | 't2m' | 'u10' | 'v10' | 'msl' | 'r850' 
  | 'tp6h' | 'cape' | 't850' | 'z500';

export type ForecastHorizon = '6h' | '12h' | '24h' | '48h';
export type RiskLevel = 'minimal' | 'low' | 'moderate' | 'high' | 'extreme';

// Constants for validation
export const WEATHER_VARIABLES: readonly WeatherVariable[] = [
  't2m', 'u10', 'v10', 'msl', 'r850', 'tp6h', 'cape', 't850', 'z500'
] as const;

export const FORECAST_HORIZONS: readonly ForecastHorizon[] = [
  '6h', '12h', '24h', '48h'
] as const;

export const RISK_LEVELS: readonly RiskLevel[] = [
  'minimal', 'low', 'moderate', 'high', 'extreme'
] as const;

// Enhanced type guards with runtime validation
export function isForecastResponse(data: unknown): data is ForecastResponse {
  if (typeof data !== 'object' || data === null) return false;
  
  const forecast = data as any;
  return (
    typeof forecast.horizon === 'string' &&
    typeof forecast.generated_at === 'string' &&
    typeof forecast.variables === 'object' &&
    typeof forecast.narrative === 'string' &&
    typeof forecast.risk_assessment === 'object' &&
    typeof forecast.analogs_summary === 'object'
  );
}

export function isHealthResponse(data: unknown): data is HealthResponse {
  if (typeof data !== 'object' || data === null) return false;
  
  const health = data as any;
  return (
    typeof health.ready === 'boolean' &&
    Array.isArray(health.checks) &&
    typeof health.model === 'object' &&
    typeof health.index === 'object'
  );
}

// Validation helpers
export function validateWeatherVariable(variable: string): variable is WeatherVariable {
  return WEATHER_VARIABLES.includes(variable as WeatherVariable);
}

export function validateForecastHorizon(horizon: string): horizon is ForecastHorizon {
  return FORECAST_HORIZONS.includes(horizon as ForecastHorizon);
}

export function validateRiskLevel(level: string): level is RiskLevel {
  return RISK_LEVELS.includes(level as RiskLevel);
}

// API request helpers
export interface ForecastRequestParams {
  horizon?: ForecastHorizon;
  vars?: string; // Comma-separated variable names
}

export interface ApiRequestConfig {
  baseURL?: string;
  timeout?: number;
  headers?: Record<string, string>;
}

// Error handling types
export interface ApiErrorResponse {
  error: {
    code: number;
    message: string;
    timestamp: string;
    correlation_id?: string;
  };
}

export function isApiErrorResponse(data: unknown): data is ApiErrorResponse {
  if (typeof data !== 'object' || data === null) return false;
  
  const error = data as any;
  return (
    typeof error.error === 'object' &&
    typeof error.error.code === 'number' &&
    typeof error.error.message === 'string' &&
    typeof error.error.timestamp === 'string'
  );
}
`;

      const utilityPath = path.join(this.config.outputDir, 'api-utilities.ts');
      await fs.writeFile(utilityPath, utilityContent);

      return {
        success: true,
        errors: [],
        files: [utilityPath]
      };

    } catch (error) {
      return {
        success: false,
        errors: [`Failed to generate utility types: ${error}`],
        files: []
      };
    }
  }

  /**
   * Validate generated TypeScript types
   */
  private async validateGeneratedTypes(): Promise<TypeValidationResult> {
    const result: TypeValidationResult = {
      valid: true,
      errors: [],
      warnings: [],
      coverage: {
        totalTypes: 0,
        validatedTypes: 0,
        missingTypes: []
      }
    };

    try {
      // Check if generated files exist
      const generatedPath = path.join(this.config.outputDir, 'generated-api.ts');
      const utilityPath = path.join(this.config.outputDir, 'api-utilities.ts');

      if (!(await this.fileExists(generatedPath))) {
        result.errors.push('Generated API types file not found');
        result.valid = false;
      }

      if (!(await this.fileExists(utilityPath))) {
        result.errors.push('Utility types file not found');
        result.valid = false;
      }

      // Validate type compilation
      try {
        execSync(
          'npx tsc --noEmit --skipLibCheck',
          {
            stdio: 'pipe',
            cwd: process.cwd()
          }
        );
        console.log('✅ TypeScript compilation validation passed');
      } catch (error: any) {
        result.errors.push(`TypeScript compilation failed: ${error.message}`);
        result.valid = false;
      }

      // Check for required types in generated files
      if (await this.fileExists(generatedPath)) {
        const content = await fs.readFile(generatedPath, 'utf-8');
        
        const requiredTypes = [
          'ForecastResponse',
          'HealthResponse',
          'VariableResult',
          'RiskAssessment',
          'AnalogsSummary'
        ];

        for (const typeName of requiredTypes) {
          if (!content.includes(typeName)) {
            result.coverage.missingTypes.push(typeName);
            result.warnings.push(`Missing expected type: ${typeName}`);
          } else {
            result.coverage.validatedTypes++;
          }
          result.coverage.totalTypes++;
        }
      }

    } catch (error) {
      result.errors.push(`Type validation failed: ${error}`);
      result.valid = false;
    }

    return result;
  }

  /**
   * Update Pact contracts with new types
   */
  private async updatePactContracts(): Promise<{
    success: boolean;
    errors: string[];
  }> {
    try {
      // Check if Pact tests exist
      const pactTestPath = path.join(this.config.pactDir, 'consumer');
      
      if (!(await this.directoryExists(pactTestPath))) {
        return {
          success: true,
          errors: ['Pact consumer tests not found - skipping validation']
        };
      }

      // Run Pact consumer tests to validate contract compatibility
      try {
        execSync(
          'npm run test:pact',
          {
            stdio: this.isCI ? 'pipe' : 'inherit',
            cwd: process.cwd()
          }
        );

        console.log('✅ Pact contract validation passed');
        return { success: true, errors: [] };

      } catch (error: any) {
        return {
          success: false,
          errors: [`Pact contract validation failed: ${error.message}`]
        };
      }

    } catch (error) {
      return {
        success: false,
        errors: [`Pact update failed: ${error}`]
      };
    }
  }

  /**
   * Generate type documentation
   */
  private async generateDocumentation(): Promise<{
    success: boolean;
    files: string[];
  }> {
    try {
      const documentation = `# Adelaide Weather API Types

Auto-generated TypeScript types for the Adelaide Weather Forecasting API.

## Generated Files

- \`generated-api.ts\` - Auto-generated types from OpenAPI schema
- \`api-utilities.ts\` - Utility types and helpers
- \`README.md\` - This documentation

## Usage

\`\`\`typescript
import type { ForecastResponse, WeatherVariable } from './api-utilities';
import { isForecastResponse, validateWeatherVariable } from './api-utilities';

// Type-safe API response handling
async function getForecast(horizon: string, variables: string[]) {
  // Validate inputs
  if (!validateForecastHorizon(horizon)) {
    throw new Error('Invalid forecast horizon');
  }

  for (const variable of variables) {
    if (!validateWeatherVariable(variable)) {
      throw new Error(\`Invalid weather variable: \${variable}\`);
    }
  }

  const response = await fetch('/api/forecast', {
    method: 'GET',
    params: { horizon, vars: variables.join(',') }
  });

  const data = await response.json();

  if (isForecastResponse(data)) {
    // data is now properly typed as ForecastResponse
    console.log('Risk level:', data.risk_assessment.thunderstorm);
    console.log('Narrative:', data.narrative);
    return data;
  } else {
    throw new Error('Invalid forecast response');
  }
}
\`\`\`

## Type Safety Features

- ✅ Runtime type guards for API responses
- ✅ Validation helpers for input parameters
- ✅ Comprehensive error handling types
- ✅ Auto-generated from OpenAPI schema
- ✅ Pact contract validation

## Regenerating Types

To regenerate types after API changes:

\`\`\`bash
npm run generate:types
\`\`\`

---
Generated on: ${new Date().toISOString()}
Schema Hash: ${await this.getSchemaHash()}
`;

      const docsPath = path.join(this.config.outputDir, 'README.md');
      await fs.writeFile(docsPath, documentation);

      return {
        success: true,
        files: [docsPath]
      };

    } catch (error) {
      console.warn(`Failed to generate documentation: ${error}`);
      return { success: false, files: [] };
    }
  }

  /**
   * Validate TypeScript compilation
   */
  private async validateTypeScriptCompilation(): Promise<{
    success: boolean;
    errors: string[];
  }> {
    try {
      execSync(
        'npx tsc --noEmit --skipLibCheck',
        {
          stdio: 'pipe',
          cwd: process.cwd()
        }
      );

      return { success: true, errors: [] };
    } catch (error: any) {
      return {
        success: false,
        errors: [`TypeScript compilation failed: ${error.message}`]
      };
    }
  }

  /**
   * Save generation metadata for CI/CD
   */
  private async saveGenerationMetadata(result: GenerationResult): Promise<void> {
    try {
      const metadata = {
        timestamp: new Date().toISOString(),
        schemaHash: result.schemaHash,
        typesHash: await this.calculateTypesHash(),
        filesGenerated: result.filesGenerated,
        success: result.success,
        errors: result.errors,
        warnings: result.warnings,
        generator: 'enhanced-type-generator',
        version: '1.0.0'
      };

      const metadataPath = path.join(this.config.outputDir, '.generation_metadata.json');
      await fs.writeFile(metadataPath, JSON.stringify(metadata, null, 2));

      // Save schema hash for next run
      if (result.schemaHash) {
        const hashPath = path.join(this.config.outputDir, '.schema_hash');
        await fs.writeFile(hashPath, result.schemaHash);
      }

      if (this.isCI) {
        console.log(`::set-output name=types_hash::${metadata.typesHash}`);
        console.log(`::set-output name=files_generated::${result.filesGenerated.length}`);
      }

    } catch (error) {
      console.warn(`Failed to save generation metadata: ${error}`);
    }
  }

  // Helper methods
  private async fileExists(filePath: string): Promise<boolean> {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  private async directoryExists(dirPath: string): Promise<boolean> {
    try {
      const stat = await fs.stat(dirPath);
      return stat.isDirectory();
    } catch {
      return false;
    }
  }

  private async getSchemaHash(): Promise<string> {
    try {
      const schemaContent = await fs.readFile(this.config.openApiPath, 'utf-8');
      return require('crypto')
        .createHash('sha256')
        .update(schemaContent)
        .digest('hex')
        .substring(0, 12);
    } catch {
      return 'unknown';
    }
  }

  private async calculateTypesHash(): Promise<string> {
    try {
      const generatedPath = path.join(this.config.outputDir, 'generated-api.ts');
      const utilityPath = path.join(this.config.outputDir, 'api-utilities.ts');
      
      let content = '';
      
      if (await this.fileExists(generatedPath)) {
        content += await fs.readFile(generatedPath, 'utf-8');
      }
      
      if (await this.fileExists(utilityPath)) {
        content += await fs.readFile(utilityPath, 'utf-8');
      }

      return require('crypto')
        .createHash('sha256')
        .update(content)
        .digest('hex')
        .substring(0, 12);
    } catch {
      return 'unknown';
    }
  }
}

// CLI Interface
async function main() {
  const args = process.argv.slice(2);
  const config: Partial<GenerationConfig> = {};

  // Parse command line arguments
  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--schema':
        config.openApiPath = args[++i];
        break;
      case '--output':
        config.outputDir = args[++i];
        break;
      case '--no-validate':
        config.validateTypes = false;
        break;
      case '--no-docs':
        config.generateDocs = false;
        break;
      case '--help':
        console.log(`
Enhanced TypeScript Type Generator for Adelaide Weather API

Usage: tsx enhanced-type-generator.ts [options]

Options:
  --schema PATH     OpenAPI schema file path (default: openapi.json)
  --output DIR      Output directory for generated types (default: types)
  --no-validate     Skip type validation
  --no-docs         Skip documentation generation
  --help            Show this help message

Environment Variables:
  CI                Set to 'true' for CI mode with enhanced logging
`);
        process.exit(0);
        break;
    }
  }

  const generator = new EnhancedTypeGenerator(config);
  const result = await generator.generateTypes();

  if (!result.success) {
    console.error('\n❌ Type generation failed:');
    result.errors.forEach(error => console.error(`  - ${error}`));
    process.exit(1);
  }

  console.log('\n🎉 Type generation completed successfully!');
  process.exit(0);
}

// Export for use as module
export { EnhancedTypeGenerator, type GenerationConfig, type GenerationResult };

// Run CLI if called directly
if (require.main === module) {
  main().catch(error => {
    console.error('❌ Type generation failed:', error);
    process.exit(1);
  });
}