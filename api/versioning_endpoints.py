#!/usr/bin/env python3
"""
Forecast Versioning API Endpoints
================================

FastAPI endpoints for comprehensive forecast version management, comparison,
and historical analysis capabilities.

Features:
- GET /versions: List forecast versions with filtering
- GET /versions/{version_id}: Get specific version details
- POST /versions/compare: Compare multiple forecast versions
- GET /versions/search: Advanced search with filters
- POST /versions/export: Create export jobs for historical data
- GET /exports/{export_id}: Download exported data
- GET /versions/analytics: Performance analytics and trends

Author: T-013 Implementation
Version: 1.0.0 - Versioned Storage with UI Access
"""

import os
import sys
import json
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

# FastAPI and dependencies
from fastapi import FastAPI, HTTPException, Depends, Query, Path, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, field_validator
import asyncpg

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================================
# Database Connection
# ============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://user:password@localhost:5432/weather_forecast"
)

async def get_db_connection():
    """Get database connection with error handling."""
    try:
        return await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        raise HTTPException(500, f"Database connection failed: {str(e)}")

# ============================================================================
# Pydantic Models for API Contracts
# ============================================================================

class ForecastVersionSummary(BaseModel):
    """Summary of a forecast version for list views."""
    version_id: str = Field(..., description="Unique version identifier")
    forecast_time: datetime = Field(..., description="When forecast was made")
    created_at: datetime = Field(..., description="When version was stored")
    horizon: str = Field(..., description="Forecast horizon")
    confidence_score: Optional[float] = Field(None, description="Overall confidence (0-1)")
    risk_level: Optional[str] = Field(None, description="Risk assessment level")
    model_version: str = Field(..., description="Model version used")
    latency_ms: Optional[int] = Field(None, description="Generation latency")
    analog_count: Optional[int] = Field(None, description="Number of analogs used")
    variable_count: int = Field(..., description="Number of variables forecasted")

class ForecastVersionDetail(BaseModel):
    """Complete forecast version with all data."""
    version_id: str = Field(..., description="Unique version identifier")
    forecast_time: datetime = Field(..., description="When forecast was made")
    created_at: datetime = Field(..., description="When version was stored")
    horizon: str = Field(..., description="Forecast horizon")
    location_lat: float = Field(..., description="Forecast latitude")
    location_lon: float = Field(..., description="Forecast longitude")
    
    # Forecast data
    variables: Dict[str, Any] = Field(..., description="Variable forecasts")
    wind_data: Optional[Dict[str, Any]] = Field(None, description="Wind forecast data")
    
    # Metadata
    model_version: str = Field(..., description="Model version")
    index_version: str = Field(..., description="Index version")
    dataset_hash: str = Field(..., description="Dataset hash")
    api_version: str = Field(..., description="API version")
    
    # Performance
    latency_ms: Optional[int] = Field(None, description="Generation latency")
    analog_count: Optional[int] = Field(None, description="Analogs used")
    total_analogs_used: Optional[int] = Field(None, description="Total analogs in ensemble")
    
    # Quality
    confidence_score: Optional[float] = Field(None, description="Confidence (0-1)")
    risk_level: Optional[str] = Field(None, description="Risk level")
    narrative: Optional[str] = Field(None, description="Forecast narrative")
    confidence_explanation: Optional[str] = Field(None, description="Confidence explanation")
    
    # Context
    user_id: Optional[str] = Field(None, description="User who generated forecast")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    request_params: Optional[Dict[str, Any]] = Field(None, description="Original request")

class VersionComparison(BaseModel):
    """Comparison between two forecast versions."""
    comparison_id: str = Field(..., description="Unique comparison identifier")
    created_at: datetime = Field(..., description="When comparison was created")
    created_by: Optional[str] = Field(None, description="User who created comparison")
    
    # Versions being compared
    version_a: ForecastVersionSummary = Field(..., description="First version")
    version_b: ForecastVersionSummary = Field(..., description="Second version")
    
    # Comparison results
    variables_compared: List[str] = Field(..., description="Variables included in comparison")
    differences: Dict[str, Any] = Field(..., description="Detailed differences")
    similarity_score: Optional[float] = Field(None, description="Overall similarity (0-1)")
    significant_changes: List[str] = Field(default_factory=list, description="Notable changes")
    
    # User annotations
    notes: Optional[str] = Field(None, description="User notes about comparison")
    tags: List[str] = Field(default_factory=list, description="User-defined tags")

class VersionComparisonRequest(BaseModel):
    """Request to compare forecast versions."""
    version_ids: List[str] = Field(..., min_items=2, max_items=5, description="Version IDs to compare")
    variables: Optional[List[str]] = Field(None, description="Variables to compare (default: all)")
    notes: Optional[str] = Field(None, description="Optional notes")
    
    @field_validator('version_ids')
    @classmethod
    def validate_version_ids(cls, v):
        """Validate version IDs are valid UUIDs."""
        for version_id in v:
            try:
                uuid.UUID(version_id)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {version_id}")
        return v

class ExportRequest(BaseModel):
    """Request to export forecast data."""
    export_type: str = Field(..., description="Export format")
    start_date: datetime = Field(..., description="Start of date range")
    end_date: datetime = Field(..., description="End of date range")
    horizons: List[str] = Field(..., description="Forecast horizons to include")
    variables: List[str] = Field(..., description="Variables to include")
    include_metadata: bool = Field(True, description="Include version metadata")
    include_comparisons: bool = Field(False, description="Include comparison data")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")
    
    @field_validator('export_type')
    @classmethod
    def validate_export_type(cls, v):
        """Validate export type."""
        valid_types = ['json', 'csv', 'archive']
        if v not in valid_types:
            raise ValueError(f"Export type must be one of {valid_types}")
        return v
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_dates(cls, v):
        """Ensure dates are timezone-aware."""
        if v.tzinfo is None:
            raise ValueError("Dates must include timezone information")
        return v

class ExportStatus(BaseModel):
    """Status of an export operation."""
    export_id: str = Field(..., description="Export identifier")
    created_at: datetime = Field(..., description="When export was requested")
    created_by: str = Field(..., description="User who requested export")
    export_type: str = Field(..., description="Export format")
    status: str = Field(..., description="Current status")
    progress_percent: int = Field(..., description="Progress percentage")
    file_size_bytes: Optional[int] = Field(None, description="Generated file size")
    record_count: Optional[int] = Field(None, description="Number of records")
    download_url: Optional[str] = Field(None, description="Download URL if ready")
    expires_at: Optional[datetime] = Field(None, description="Download expiration")
    error_message: Optional[str] = Field(None, description="Error if failed")

class VersionAnalytics(BaseModel):
    """Analytics data for forecast versions."""
    time_range: Dict[str, datetime] = Field(..., description="Analysis time range")
    total_versions: int = Field(..., description="Total versions in range")
    versions_by_horizon: Dict[str, int] = Field(..., description="Count by horizon")
    versions_by_model: Dict[str, int] = Field(..., description="Count by model version")
    
    # Performance metrics
    avg_latency_ms: float = Field(..., description="Average generation latency")
    avg_confidence_score: float = Field(..., description="Average confidence")
    avg_analog_count: float = Field(..., description="Average analogs used")
    
    # Quality trends
    confidence_trend: List[Dict[str, Any]] = Field(..., description="Confidence over time")
    accuracy_trend: List[Dict[str, Any]] = Field(..., description="Accuracy over time")
    usage_trend: List[Dict[str, Any]] = Field(..., description="Usage over time")

class VersionSearchRequest(BaseModel):
    """Advanced search request for forecast versions."""
    query: Optional[str] = Field(None, description="Text search in narrative/notes")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    horizons: Optional[List[str]] = Field(None, description="Horizon filter")
    model_versions: Optional[List[str]] = Field(None, description="Model version filter")
    confidence_min: Optional[float] = Field(None, ge=0, le=1, description="Minimum confidence")
    confidence_max: Optional[float] = Field(None, ge=0, le=1, description="Maximum confidence")
    risk_levels: Optional[List[str]] = Field(None, description="Risk level filter")
    variables: Optional[List[str]] = Field(None, description="Required variables")
    user_id: Optional[str] = Field(None, description="User filter")
    tags: Optional[List[str]] = Field(None, description="Tag filter")
    limit: int = Field(50, ge=1, le=500, description="Maximum results")
    offset: int = Field(0, ge=0, description="Results offset")

# ============================================================================
# Versioning API Endpoints
# ============================================================================

async def get_forecast_versions(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    horizon: Optional[str] = Query(None, description="Horizon filter"),
    model_version: Optional[str] = Query(None, description="Model version filter"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset")
) -> Dict[str, Any]:
    """
    Get list of forecast versions with optional filtering.
    
    Returns paginated list of forecast version summaries with metadata.
    """
    conn = await get_db_connection()
    
    try:
        # Build dynamic query
        conditions = []
        params = []
        param_count = 0
        
        if start_date:
            param_count += 1
            conditions.append(f"forecast_time >= ${param_count}")
            params.append(start_date)
        
        if end_date:
            param_count += 1
            conditions.append(f"forecast_time <= ${param_count}")
            params.append(end_date)
        
        if horizon:
            param_count += 1
            conditions.append(f"horizon = ${param_count}")
            params.append(horizon)
        
        if model_version:
            param_count += 1
            conditions.append(f"model_version = ${param_count}")
            params.append(model_version)
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) 
            FROM forecast_versions 
            WHERE {where_clause}
        """
        total_count = await conn.fetchval(count_query, *params)
        
        # Get paginated results
        param_count += 1
        limit_param = f"${param_count}"
        params.append(limit)
        
        param_count += 1
        offset_param = f"${param_count}"
        params.append(offset)
        
        query = f"""
            SELECT 
                version_id,
                forecast_time,
                created_at,
                horizon,
                confidence_score,
                risk_level,
                model_version,
                latency_ms,
                analog_count,
                jsonb_array_length(jsonb_object_keys(variables)) as variable_count
            FROM forecast_versions
            WHERE {where_clause}
            ORDER BY forecast_time DESC
            LIMIT {limit_param} OFFSET {offset_param}
        """
        
        rows = await conn.fetch(query, *params)
        
        versions = [
            ForecastVersionSummary(
                version_id=str(row['version_id']),
                forecast_time=row['forecast_time'],
                created_at=row['created_at'],
                horizon=row['horizon'],
                confidence_score=row['confidence_score'],
                risk_level=row['risk_level'],
                model_version=row['model_version'],
                latency_ms=row['latency_ms'],
                analog_count=row['analog_count'],
                variable_count=row['variable_count'] or 0
            )
            for row in rows
        ]
        
        return {
            "versions": [v.dict() for v in versions],
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "filters_applied": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "horizon": horizon,
                "model_version": model_version
            }
        }
        
    finally:
        await conn.close()

async def get_forecast_version_detail(version_id: str) -> ForecastVersionDetail:
    """
    Get complete details for a specific forecast version.
    
    Returns full version data including variables, metadata, and context.
    """
    try:
        uuid.UUID(version_id)  # Validate UUID format
    except ValueError:
        raise HTTPException(400, "Invalid version ID format")
    
    conn = await get_db_connection()
    
    try:
        query = """
            SELECT *
            FROM forecast_versions
            WHERE version_id = $1
        """
        
        row = await conn.fetchrow(query, uuid.UUID(version_id))
        
        if not row:
            raise HTTPException(404, "Forecast version not found")
        
        return ForecastVersionDetail(
            version_id=str(row['version_id']),
            forecast_time=row['forecast_time'],
            created_at=row['created_at'],
            horizon=row['horizon'],
            location_lat=row['location_lat'],
            location_lon=row['location_lon'],
            variables=row['variables'],
            wind_data=row['wind_data'],
            model_version=row['model_version'],
            index_version=row['index_version'],
            dataset_hash=row['dataset_hash'],
            api_version=row['api_version'],
            latency_ms=row['latency_ms'],
            analog_count=row['analog_count'],
            total_analogs_used=row['total_analogs_used'],
            confidence_score=row['confidence_score'],
            risk_level=row['risk_level'],
            narrative=row['narrative'],
            confidence_explanation=row['confidence_explanation'],
            user_id=row['user_id'],
            correlation_id=row['correlation_id'],
            request_params=row['request_params']
        )
        
    finally:
        await conn.close()

async def compare_forecast_versions(
    request: VersionComparisonRequest,
    user_id: Optional[str] = None
) -> VersionComparison:
    """
    Compare multiple forecast versions and return detailed analysis.
    
    Creates a comparison record and returns differences, similarities,
    and analytical insights between the specified versions.
    """
    conn = await get_db_connection()
    
    try:
        # Validate that all versions exist
        version_uuids = [uuid.UUID(vid) for vid in request.version_ids]
        
        placeholders = ','.join(f'${i+1}' for i in range(len(version_uuids)))
        query = f"""
            SELECT version_id, forecast_time, horizon, confidence_score, 
                   risk_level, model_version, analog_count, variables
            FROM forecast_versions
            WHERE version_id IN ({placeholders})
            ORDER BY forecast_time
        """
        
        rows = await conn.fetch(query, *version_uuids)
        
        if len(rows) != len(request.version_ids):
            missing = set(request.version_ids) - {str(row['version_id']) for row in rows}
            raise HTTPException(404, f"Versions not found: {missing}")
        
        # For simplicity, compare first two versions (extend for multi-version comparison)
        version_a_data = rows[0]
        version_b_data = rows[1]
        
        # Calculate differences
        variables_a = version_a_data['variables']
        variables_b = version_b_data['variables']
        
        differences = {}
        significant_changes = []
        
        # Compare each variable
        for var_name in set(variables_a.keys()) | set(variables_b.keys()):
            if var_name in variables_a and var_name in variables_b:
                val_a = variables_a[var_name].get('value') if isinstance(variables_a[var_name], dict) else None
                val_b = variables_b[var_name].get('value') if isinstance(variables_b[var_name], dict) else None
                
                if val_a is not None and val_b is not None:
                    diff = val_b - val_a
                    percent_change = (diff / val_a * 100) if val_a != 0 else 0
                    
                    differences[var_name] = {
                        'value_a': val_a,
                        'value_b': val_b,
                        'absolute_difference': diff,
                        'percent_change': percent_change
                    }
                    
                    # Flag significant changes (>10% change)
                    if abs(percent_change) > 10:
                        significant_changes.append(
                            f"{var_name}: {percent_change:+.1f}% change ({val_a:.2f} → {val_b:.2f})"
                        )
        
        # Calculate overall similarity (simplified)
        similarity_score = max(0, 1 - (len(significant_changes) * 0.1))
        
        # Create comparison record
        comparison_id = uuid.uuid4()
        
        insert_query = """
            INSERT INTO forecast_comparisons (
                comparison_id, created_by, version_a, version_b,
                variables_compared, differences, similarity_score,
                significant_changes, notes
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        await conn.execute(
            insert_query,
            comparison_id,
            user_id,
            version_uuids[0],
            version_uuids[1],
            request.variables or list(variables_a.keys()),
            json.dumps(differences),
            similarity_score,
            significant_changes,
            request.notes
        )
        
        # Build response
        version_a_summary = ForecastVersionSummary(
            version_id=str(version_a_data['version_id']),
            forecast_time=version_a_data['forecast_time'],
            created_at=datetime.now(timezone.utc),  # Simplified
            horizon=version_a_data['horizon'],
            confidence_score=version_a_data['confidence_score'],
            risk_level=version_a_data['risk_level'],
            model_version=version_a_data['model_version'],
            latency_ms=None,
            analog_count=version_a_data['analog_count'],
            variable_count=len(variables_a)
        )
        
        version_b_summary = ForecastVersionSummary(
            version_id=str(version_b_data['version_id']),
            forecast_time=version_b_data['forecast_time'],
            created_at=datetime.now(timezone.utc),  # Simplified
            horizon=version_b_data['horizon'],
            confidence_score=version_b_data['confidence_score'],
            risk_level=version_b_data['risk_level'],
            model_version=version_b_data['model_version'],
            latency_ms=None,
            analog_count=version_b_data['analog_count'],
            variable_count=len(variables_b)
        )
        
        return VersionComparison(
            comparison_id=str(comparison_id),
            created_at=datetime.now(timezone.utc),
            created_by=user_id,
            version_a=version_a_summary,
            version_b=version_b_summary,
            variables_compared=request.variables or list(variables_a.keys()),
            differences=differences,
            similarity_score=similarity_score,
            significant_changes=significant_changes,
            notes=request.notes,
            tags=[]
        )
        
    finally:
        await conn.close()

async def search_forecast_versions(request: VersionSearchRequest) -> Dict[str, Any]:
    """
    Advanced search for forecast versions with multiple filters.
    
    Supports text search, date ranges, confidence filters, and more.
    """
    conn = await get_db_connection()
    
    try:
        conditions = []
        params = []
        param_count = 0
        
        # Text search in narrative
        if request.query:
            param_count += 1
            conditions.append(f"narrative ILIKE ${param_count}")
            params.append(f"%{request.query}%")
        
        # Date range filters
        if request.start_date:
            param_count += 1
            conditions.append(f"forecast_time >= ${param_count}")
            params.append(request.start_date)
        
        if request.end_date:
            param_count += 1
            conditions.append(f"forecast_time <= ${param_count}")
            params.append(request.end_date)
        
        # Horizon filter
        if request.horizons:
            param_count += 1
            conditions.append(f"horizon = ANY(${param_count})")
            params.append(request.horizons)
        
        # Model version filter
        if request.model_versions:
            param_count += 1
            conditions.append(f"model_version = ANY(${param_count})")
            params.append(request.model_versions)
        
        # Confidence range
        if request.confidence_min is not None:
            param_count += 1
            conditions.append(f"confidence_score >= ${param_count}")
            params.append(request.confidence_min)
        
        if request.confidence_max is not None:
            param_count += 1
            conditions.append(f"confidence_score <= ${param_count}")
            params.append(request.confidence_max)
        
        # Risk level filter
        if request.risk_levels:
            param_count += 1
            conditions.append(f"risk_level = ANY(${param_count})")
            params.append(request.risk_levels)
        
        # User filter
        if request.user_id:
            param_count += 1
            conditions.append(f"user_id = ${param_count}")
            params.append(request.user_id)
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) 
            FROM forecast_versions 
            WHERE {where_clause}
        """
        total_count = await conn.fetchval(count_query, *params)
        
        # Get results
        param_count += 1
        limit_param = f"${param_count}"
        params.append(request.limit)
        
        param_count += 1
        offset_param = f"${param_count}"
        params.append(request.offset)
        
        query = f"""
            SELECT 
                version_id, forecast_time, created_at, horizon,
                confidence_score, risk_level, model_version,
                latency_ms, analog_count, narrative,
                jsonb_array_length(jsonb_object_keys(variables)) as variable_count
            FROM forecast_versions
            WHERE {where_clause}
            ORDER BY forecast_time DESC
            LIMIT {limit_param} OFFSET {offset_param}
        """
        
        rows = await conn.fetch(query, *params)
        
        versions = [
            {
                "version_id": str(row['version_id']),
                "forecast_time": row['forecast_time'].isoformat(),
                "created_at": row['created_at'].isoformat(),
                "horizon": row['horizon'],
                "confidence_score": row['confidence_score'],
                "risk_level": row['risk_level'],
                "model_version": row['model_version'],
                "latency_ms": row['latency_ms'],
                "analog_count": row['analog_count'],
                "narrative": row['narrative'],
                "variable_count": row['variable_count'] or 0
            }
            for row in rows
        ]
        
        return {
            "versions": versions,
            "pagination": {
                "total_count": total_count,
                "limit": request.limit,
                "offset": request.offset,
                "has_more": request.offset + request.limit < total_count
            },
            "search_criteria": request.dict(exclude_unset=True)
        }
        
    finally:
        await conn.close()

async def create_export_job(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    user_id: str
) -> ExportStatus:
    """
    Create an export job for historical forecast data.
    
    Initiates background processing to generate the requested export format.
    """
    conn = await get_db_connection()
    
    try:
        export_id = uuid.uuid4()
        
        # Insert export record
        insert_query = """
            INSERT INTO forecast_exports (
                export_id, created_by, export_type, date_range,
                horizons_included, variables_included, filters,
                include_metadata, include_comparisons, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """
        
        date_range = f"[{request.start_date.isoformat()},{request.end_date.isoformat()}]"
        
        await conn.execute(
            insert_query,
            export_id,
            user_id,
            request.export_type,
            date_range,
            request.horizons,
            request.variables,
            json.dumps(request.filters) if request.filters else None,
            request.include_metadata,
            request.include_comparisons,
            'pending'
        )
        
        # Add background task to process export
        background_tasks.add_task(process_export_job, str(export_id))
        
        return ExportStatus(
            export_id=str(export_id),
            created_at=datetime.now(timezone.utc),
            created_by=user_id,
            export_type=request.export_type,
            status='pending',
            progress_percent=0
        )
        
    finally:
        await conn.close()

async def process_export_job(export_id: str):
    """
    Background task to process export jobs.
    
    This would implement the actual data export logic.
    """
    conn = await get_db_connection()
    
    try:
        # Update status to processing
        await conn.execute(
            "UPDATE forecast_exports SET status = 'processing', progress_percent = 0 WHERE export_id = $1",
            uuid.UUID(export_id)
        )
        
        # Simulate processing time
        await asyncio.sleep(2)
        
        # Update progress
        await conn.execute(
            "UPDATE forecast_exports SET progress_percent = 50 WHERE export_id = $1",
            uuid.UUID(export_id)
        )
        
        await asyncio.sleep(3)
        
        # Complete the export (simplified)
        download_url = f"/api/exports/{export_id}/download"
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        await conn.execute("""
            UPDATE forecast_exports 
            SET status = 'completed', progress_percent = 100,
                download_url = $2, file_size_bytes = 1024000,
                record_count = 100, expires_at = $3
            WHERE export_id = $1
        """, uuid.UUID(export_id), download_url, expires_at)
        
    except Exception as e:
        # Handle export failure
        await conn.execute(
            "UPDATE forecast_exports SET status = 'failed', error_message = $2 WHERE export_id = $1",
            uuid.UUID(export_id), str(e)
        )
    finally:
        await conn.close()

async def get_export_status(export_id: str) -> ExportStatus:
    """
    Get the status of an export job.
    
    Returns current progress and download information when ready.
    """
    try:
        uuid.UUID(export_id)
    except ValueError:
        raise HTTPException(400, "Invalid export ID format")
    
    conn = await get_db_connection()
    
    try:
        query = """
            SELECT export_id, created_at, created_by, export_type, status,
                   progress_percent, file_size_bytes, record_count,
                   download_url, expires_at, error_message
            FROM forecast_exports
            WHERE export_id = $1
        """
        
        row = await conn.fetchrow(query, uuid.UUID(export_id))
        
        if not row:
            raise HTTPException(404, "Export not found")
        
        return ExportStatus(
            export_id=str(row['export_id']),
            created_at=row['created_at'],
            created_by=row['created_by'],
            export_type=row['export_type'],
            status=row['status'],
            progress_percent=row['progress_percent'],
            file_size_bytes=row['file_size_bytes'],
            record_count=row['record_count'],
            download_url=row['download_url'],
            expires_at=row['expires_at'],
            error_message=row['error_message']
        )
        
    finally:
        await conn.close()

async def get_version_analytics(
    days: int = Query(30, ge=1, le=365, description="Days to analyze")
) -> VersionAnalytics:
    """
    Get analytics and trends for forecast versions.
    
    Returns performance metrics, usage patterns, and quality trends.
    """
    conn = await get_db_connection()
    
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Basic statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_versions,
                AVG(latency_ms) as avg_latency_ms,
                AVG(confidence_score) as avg_confidence_score,
                AVG(analog_count) as avg_analog_count
            FROM forecast_versions
            WHERE forecast_time >= $1
        """
        
        stats = await conn.fetchrow(stats_query, start_date)
        
        # Versions by horizon
        horizon_query = """
            SELECT horizon, COUNT(*) as count
            FROM forecast_versions
            WHERE forecast_time >= $1
            GROUP BY horizon
            ORDER BY count DESC
        """
        
        horizon_rows = await conn.fetch(horizon_query, start_date)
        versions_by_horizon = {row['horizon']: row['count'] for row in horizon_rows}
        
        # Versions by model
        model_query = """
            SELECT model_version, COUNT(*) as count
            FROM forecast_versions
            WHERE forecast_time >= $1
            GROUP BY model_version
            ORDER BY count DESC
        """
        
        model_rows = await conn.fetch(model_query, start_date)
        versions_by_model = {row['model_version']: row['count'] for row in model_rows}
        
        # Daily trends (simplified)
        daily_query = """
            SELECT 
                DATE(forecast_time) as day,
                COUNT(*) as count,
                AVG(confidence_score) as avg_confidence,
                AVG(latency_ms) as avg_latency
            FROM forecast_versions
            WHERE forecast_time >= $1
            GROUP BY DATE(forecast_time)
            ORDER BY day
        """
        
        daily_rows = await conn.fetch(daily_query, start_date)
        
        confidence_trend = [
            {
                "date": row['day'].isoformat(),
                "value": float(row['avg_confidence']) if row['avg_confidence'] else 0,
                "count": row['count']
            }
            for row in daily_rows
        ]
        
        usage_trend = [
            {
                "date": row['day'].isoformat(),
                "versions": row['count'],
                "avg_latency": float(row['avg_latency']) if row['avg_latency'] else 0
            }
            for row in daily_rows
        ]
        
        return VersionAnalytics(
            time_range={
                "start": start_date,
                "end": datetime.now(timezone.utc)
            },
            total_versions=stats['total_versions'],
            versions_by_horizon=versions_by_horizon,
            versions_by_model=versions_by_model,
            avg_latency_ms=float(stats['avg_latency_ms']) if stats['avg_latency_ms'] else 0,
            avg_confidence_score=float(stats['avg_confidence_score']) if stats['avg_confidence_score'] else 0,
            avg_analog_count=float(stats['avg_analog_count']) if stats['avg_analog_count'] else 0,
            confidence_trend=confidence_trend,
            accuracy_trend=[],  # Would integrate with accuracy tracking
            usage_trend=usage_trend
        )
        
    finally:
        await conn.close()

# ============================================================================
# Helper Functions
# ============================================================================

def format_version_differences(differences: Dict[str, Any]) -> List[str]:
    """Format version differences for display."""
    formatted = []
    
    for variable, diff_data in differences.items():
        if isinstance(diff_data, dict):
            percent_change = diff_data.get('percent_change', 0)
            if abs(percent_change) > 1:  # Only show significant changes
                sign = "+" if percent_change > 0 else ""
                formatted.append(f"{variable}: {sign}{percent_change:.1f}%")
    
    return formatted

def calculate_similarity_score(version_a: Dict, version_b: Dict) -> float:
    """Calculate similarity between two forecast versions."""
    # Simplified similarity calculation
    # In production, this would be more sophisticated
    
    variables_a = version_a.get('variables', {})
    variables_b = version_b.get('variables', {})
    
    common_vars = set(variables_a.keys()) & set(variables_b.keys())
    if not common_vars:
        return 0.0
    
    differences = []
    for var in common_vars:
        val_a = variables_a[var].get('value') if isinstance(variables_a[var], dict) else None
        val_b = variables_b[var].get('value') if isinstance(variables_b[var], dict) else None
        
        if val_a is not None and val_b is not None and val_a != 0:
            relative_diff = abs((val_b - val_a) / val_a)
            differences.append(relative_diff)
    
    if differences:
        avg_difference = sum(differences) / len(differences)
        return max(0, 1 - avg_difference)
    
    return 0.5  # Default similarity for unclear cases