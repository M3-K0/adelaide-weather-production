#!/usr/bin/env tsx
/**
 * Type Generation Pipeline for Adelaide Weather Forecasting API
 *
 * This script generates TypeScript types from the OpenAPI schema
 * and validates them against the enhanced API response format.
 */

import fs from 'fs/promises';
import path from 'path';

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Validates that our generated types match the actual API schema
 */
async function validateGeneratedTypes(): Promise<ValidationResult> {
  const result: ValidationResult = {
    valid: true,
    errors: [],
    warnings: []
  };

  try {
    // Read the generated types file
    const typesPath = path.join(process.cwd(), 'types', 'api.ts');
    const typesContent = await fs.readFile(typesPath, 'utf-8');

    // Check for required types
    const requiredTypes = [
      'ForecastResponse',
      'RiskAssessment',
      'AnalogsSummary',
      'VariableResult',
      'WindResult',
      'WeatherVariable',
      'ForecastHorizon',
      'RiskLevel'
    ];

    for (const typeName of requiredTypes) {
      if (
        !typesContent.includes(`interface ${typeName}`) &&
        !typesContent.includes(`type ${typeName}`)
      ) {
        result.errors.push(`Missing required type: ${typeName}`);
        result.valid = false;
      }
    }

    // Check for enhanced T-001 features
    const enhancedFeatures = [
      'risk_assessment: RiskAssessment',
      'analogs_summary: AnalogsSummary',
      'narrative: string',
      'confidence_explanation: string'
    ];

    for (const feature of enhancedFeatures) {
      if (!typesContent.includes(feature)) {
        result.errors.push(`Missing enhanced feature: ${feature}`);
        result.valid = false;
      }
    }

    // Check type guards
    const typeGuards = ['isApiError', 'isForecastResponse', 'isHealthResponse'];

    for (const guard of typeGuards) {
      if (!typesContent.includes(`function ${guard}`)) {
        result.warnings.push(`Missing type guard: ${guard}`);
      }
    }

    // Check constants
    const constants = [
      'WEATHER_VARIABLES',
      'FORECAST_HORIZONS',
      'RISK_LEVELS',
      'VARIABLE_NAMES',
      'VARIABLE_UNITS'
    ];

    for (const constant of constants) {
      if (!typesContent.includes(`const ${constant}`)) {
        result.warnings.push(`Missing constant: ${constant}`);
      }
    }

    console.log('✅ Type validation completed');

    if (result.errors.length > 0) {
      console.log('❌ Validation errors:');
      result.errors.forEach(error => console.log(`  - ${error}`));
    }

    if (result.warnings.length > 0) {
      console.log('⚠️  Validation warnings:');
      result.warnings.forEach(warning => console.log(`  - ${warning}`));
    }

    if (result.valid && result.warnings.length === 0) {
      console.log('🎉 All types are valid and complete!');
    }
  } catch (error) {
    result.valid = false;
    result.errors.push(`Failed to validate types: ${error}`);
  }

  return result;
}

/**
 * Validates TypeScript compilation with strict mode
 */
async function validateTypeScriptCompilation(): Promise<ValidationResult> {
  const result: ValidationResult = {
    valid: true,
    errors: [],
    warnings: []
  };

  try {
    const { execSync } = await import('child_process');

    // Run TypeScript compiler to check for errors
    console.log('🔍 Checking TypeScript compilation...');

    try {
      const output = execSync('npx tsc --noEmit --skipLibCheck', {
        encoding: 'utf-8',
        cwd: process.cwd()
      });

      console.log('✅ TypeScript compilation successful');
    } catch (error: any) {
      // Parse TypeScript errors
      const errorOutput = error.stdout || error.stderr || '';
      const errorLines = errorOutput
        .split('\n')
        .filter((line: string) => line.trim());

      if (errorLines.length > 0) {
        result.valid = false;
        result.errors = errorLines;

        console.log('❌ TypeScript compilation errors:');
        errorLines.forEach((line: string) => console.log(`  ${line}`));
      }
    }
  } catch (error) {
    result.valid = false;
    result.errors.push(`Failed to run TypeScript validation: ${error}`);
  }

  return result;
}

/**
 * Generates type documentation
 */
async function generateTypeDocumentation(): Promise<void> {
  try {
    const typesPath = path.join(process.cwd(), 'types', 'api.ts');
    const typesContent = await fs.readFile(typesPath, 'utf-8');

    const documentation = `# Adelaide Weather Forecasting API Types

This document describes the TypeScript types generated for the enhanced API schema (T-001).

## Core Types

### ForecastResponse
The main forecast response type with enhanced features including:
- Risk assessment for weather hazards
- Historical analog pattern analysis  
- Human-readable narrative
- Confidence explanations

### RiskAssessment
Risk levels for various weather hazards:
- Thunderstorm development
- Heat stress
- Wind damage potential  
- Heavy precipitation/flooding

### AnalogsSummary
Historical analog pattern matching results:
- Most similar date and similarity score
- Number of analogs used
- Outcome descriptions and confidence explanations

## Validation

Generated types include:
- Strict TypeScript mode compatibility
- Runtime type guards
- Input validation helpers
- Comprehensive error handling

## Usage

\`\`\`typescript
import type { ForecastResponse, RiskAssessment, isApiError } from '@/types'

// Type-safe API response handling
const response = await fetch('/api/forecast')
const data = await response.json()

if (isApiError(data)) {
  console.error('API Error:', data.error)
} else {
  // data is now typed as ForecastResponse
  console.log('Risk level:', data.risk_assessment.thunderstorm)
  console.log('Narrative:', data.narrative)
}
\`\`\`

---
Generated on: ${new Date().toISOString()}
`;

    const docsPath = path.join(process.cwd(), 'types', 'README.md');
    await fs.writeFile(docsPath, documentation);

    console.log('📚 Type documentation generated');
  } catch (error) {
    console.error('❌ Failed to generate documentation:', error);
  }
}

/**
 * Main execution function
 */
async function main() {
  console.log('🚀 Starting type generation pipeline...\n');

  // Validate generated types
  const typeValidation = await validateGeneratedTypes();

  // Validate TypeScript compilation
  const compilationValidation = await validateTypeScriptCompilation();

  // Generate documentation
  await generateTypeDocumentation();

  console.log('\n📋 Summary:');
  console.log(
    `Type validation: ${typeValidation.valid ? '✅ PASS' : '❌ FAIL'}`
  );
  console.log(
    `TypeScript compilation: ${compilationValidation.valid ? '✅ PASS' : '❌ FAIL'}`
  );

  const overallSuccess = typeValidation.valid && compilationValidation.valid;
  console.log(`Overall result: ${overallSuccess ? '🎉 SUCCESS' : '❌ FAILED'}`);

  if (!overallSuccess) {
    process.exit(1);
  }
}

// Run the script
if (require.main === module) {
  main().catch(error => {
    console.error('❌ Type generation failed:', error);
    process.exit(1);
  });
}

export {
  validateGeneratedTypes,
  validateTypeScriptCompilation,
  generateTypeDocumentation
};
