import React, { useMemo, useState } from 'react';
import { GrafanaTheme2 } from '@grafana/data';
import { motion } from 'framer-motion';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Scatter,
  ComposedChart
} from 'recharts';
import { format } from 'date-fns';
import {
  WeatherDataPoint,
  WeatherVariable,
  AnalogPattern,
  UncertaintyBand
} from '../../types';

interface ObservationsChartProps {
  data: Array<WeatherDataPoint & { timestamp: number }>;
  variables: WeatherVariable[];
  width: number;
  height: number;
  timeRange: any;
  theme: GrafanaTheme2;
  analogPatterns: AnalogPattern[];
  uncertaintyBands: UncertaintyBand[];
}

export const ObservationsChart: React.FC<ObservationsChartProps> = ({
  data,
  variables,
  width,
  height,
  timeRange,
  theme,
  analogPatterns,
  uncertaintyBands
}) => {
  const [selectedVariable, setSelectedVariable] = useState<string | null>(null);
  const [hoveredAnalog, setHoveredAnalog] = useState<AnalogPattern | null>(null);

  // Prepare chart data
  const chartData = useMemo(() => {
    // Group data by time
    const groupedData = data.reduce((acc, point) => {
      const timeKey = point.timestamp;
      if (!acc[timeKey]) {
        acc[timeKey] = {
          timestamp: timeKey,
          time: point.time
        };
      }
      
      acc[timeKey][point.variable] = point.value;
      
      // Add quality indicators
      if (point.confidence !== undefined) {
        acc[timeKey][`${point.variable}_quality`] = point.confidence;
      }
      
      return acc;
    }, {} as any);

    return Object.values(groupedData).sort((a: any, b: any) => a.timestamp - b.timestamp);
  }, [data]);

  // Prepare analog comparison points
  const analogComparisonData = useMemo(() => {
    if (!hoveredAnalog || !chartData.length) return [];
    
    return hoveredAnalog.pattern.map((value, index) => ({
      timestamp: chartData[index]?.timestamp,
      analogValue: value,
      originalTime: hoveredAnalog.date.getTime() + (index * 60 * 60 * 1000) // Assuming hourly data
    })).filter(item => item.timestamp);
  }, [hoveredAnalog, chartData]);

  // Custom tooltip for observations
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;

    const time = new Date(label);
    
    return (
      <div style={{
        background: theme.colors.background.secondary,
        border: `1px solid ${theme.colors.border.medium}`,
        borderRadius: theme.shape.borderRadius(),
        padding: theme.spacing(1.5),
        boxShadow: theme.shadows.z2,
        minWidth: '200px'
      }}>
        <div style={{
          fontSize: '14px',
          fontWeight: 'bold',
          marginBottom: theme.spacing(1),
          color: theme.colors.text.primary
        }}>
          {format(time, 'MMM dd, HH:mm')}
        </div>
        
        {payload.map((entry: any, index: number) => {
          const variable = variables.find(v => v.name === entry.dataKey);
          if (!variable || entry.dataKey.includes('_quality')) {
            return null;
          }
          
          const qualityKey = `${entry.dataKey}_quality`;
          const quality = entry.payload[qualityKey];
          
          return (
            <div key={index} style={{ marginBottom: '8px' }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                color: entry.color
              }}>
                <span>{variable.label}:</span>
                <span style={{ fontWeight: 'bold' }}>
                  {entry.value?.toFixed(1)} {variable.unit}
                </span>
              </div>
              {quality !== undefined && (
                <div style={{
                  fontSize: '11px',
                  color: theme.colors.text.secondary,
                  textAlign: 'right'
                }}>
                  Quality: {(quality * 100).toFixed(0)}%
                </div>
              )}
            </div>
          );
        })}
        
        {/* Show nearest analog matches */}
        {analogPatterns.length > 0 && (
          <div style={{
            marginTop: theme.spacing(1),
            paddingTop: theme.spacing(1),
            borderTop: `1px solid ${theme.colors.border.medium}`,
            fontSize: '12px',
            color: theme.colors.text.secondary
          }}>
            Similar patterns: {analogPatterns.length}
          </div>
        )}
      </div>
    );
  };

  // Format time axis
  const formatXAxis = (tickItem: any) => {
    return format(new Date(tickItem), 'MMM dd\nHH:mm');
  };

  // Handle variable selection for highlighting
  const handleVariableClick = (variable: WeatherVariable) => {
    setSelectedVariable(
      selectedVariable === variable.name ? null : variable.name
    );
  };

  // Calculate data quality indicators
  const dataQualityStats = useMemo(() => {
    const stats = variables.reduce((acc, variable) => {
      const variableData = data.filter(d => d.variable === variable.name);
      const qualityValues = variableData
        .map(d => d.confidence)
        .filter(c => c !== undefined) as number[];
      
      if (qualityValues.length > 0) {
        acc[variable.name] = {
          avgQuality: qualityValues.reduce((sum, q) => sum + q, 0) / qualityValues.length,
          minQuality: Math.min(...qualityValues),
          dataPoints: variableData.length
        };
      }
      
      return acc;
    }, {} as any);
    
    return stats;
  }, [data, variables]);

  return (
    <div style={{ width, height, position: 'relative' }}>
      {/* Data quality indicators */}
      <div style={{
        position: 'absolute',
        top: theme.spacing(1),
        left: theme.spacing(1),
        zIndex: 10,
        display: 'flex',
        flexDirection: 'column',
        gap: theme.spacing(0.5),
        maxWidth: '200px'
      }}>
        {Object.entries(dataQualityStats).map(([variableName, stats]: any) => {
          const variable = variables.find(v => v.name === variableName);
          if (!variable?.visible) return null;
          
          return (
            <motion.div
              key={variableName}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              style={{
                padding: theme.spacing(0.5, 1),
                background: selectedVariable === variableName
                  ? theme.colors.primary.transparent
                  : theme.colors.background.secondary,
                border: `1px solid ${selectedVariable === variableName
                  ? theme.colors.primary.border
                  : theme.colors.border.medium}`,
                borderRadius: theme.shape.borderRadius(),
                fontSize: '11px',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
              onClick={() => handleVariableClick(variable)}
            >
              <div style={{ 
                color: variable.color, 
                fontWeight: 'bold',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <span>{variable.label}</span>
                <span style={{ 
                  width: '8px', 
                  height: '8px', 
                  background: variable.color, 
                  borderRadius: '50%' 
                }} />
              </div>
              <div style={{ 
                color: theme.colors.text.secondary,
                display: 'flex',
                justifyContent: 'space-between'
              }}>
                <span>Q: {(stats.avgQuality * 100).toFixed(0)}%</span>
                <span>N: {stats.dataPoints}</span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Analog patterns info */}
      {analogPatterns.length > 0 && (
        <div style={{
          position: 'absolute',
          top: theme.spacing(1),
          right: theme.spacing(1),
          zIndex: 10,
          maxWidth: '180px'
        }}>
          <div style={{
            padding: theme.spacing(1),
            background: theme.colors.info.transparent,
            color: theme.colors.info.text,
            border: `1px solid ${theme.colors.info.border}`,
            borderRadius: theme.shape.borderRadius(),
            fontSize: '12px'
          }}>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
              📊 Analog Patterns
            </div>
            <div>Found: {analogPatterns.length}</div>
            <div>
              Best match: {(analogPatterns[0]?.similarity * 100).toFixed(0)}%
            </div>
            <div style={{ 
              marginTop: '4px',
              fontSize: '10px',
              color: theme.colors.text.secondary
            }}>
              Hover chart to compare
            </div>
          </div>
        </div>
      )}

      {/* Main observations chart */}
      <ResponsiveContainer width={width} height={height - 20}>
        <ComposedChart
          data={chartData}
          margin={{
            top: 80,
            right: 30,
            left: 20,
            bottom: 20,
          }}
          onMouseMove={(e) => {
            if (analogPatterns.length > 0 && e?.activePayload) {
              // Find closest analog pattern based on current time
              const currentTime = e.activeLabel;
              // This would need actual analog pattern matching logic
              setHoveredAnalog(analogPatterns[0]);
            }
          }}
          onMouseLeave={() => setHoveredAnalog(null)}
        >
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke={theme.colors.border.weak}
          />
          <XAxis
            dataKey="timestamp"
            type="number"
            scale="time"
            domain={['dataMin', 'dataMax']}
            tickFormatter={formatXAxis}
            stroke={theme.colors.text.secondary}
            fontSize={12}
          />
          <YAxis
            stroke={theme.colors.text.secondary}
            fontSize={12}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />

          {/* Observation lines */}
          {variables.filter(v => v.visible).map((variable) => (
            <Line
              key={variable.name}
              type="monotone"
              dataKey={variable.name}
              stroke={variable.color}
              strokeWidth={selectedVariable === variable.name ? 3 : 2}
              strokeOpacity={selectedVariable && selectedVariable !== variable.name ? 0.3 : 1}
              dot={false}
              connectNulls={false}
              activeDot={{
                r: 4,
                fill: variable.color,
                stroke: theme.colors.background.primary,
                strokeWidth: 2
              }}
            />
          ))}

          {/* Analog pattern comparison overlay */}
          {hoveredAnalog && analogComparisonData.length > 0 && (
            <Line
              type="monotone"
              dataKey="analogValue"
              stroke={theme.colors.warning.main}
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              connectNulls={false}
              name={`Analog: ${format(hoveredAnalog.date, 'MMM dd, yyyy')}`}
              strokeOpacity={0.8}
            />
          )}

          {/* Current time reference line */}
          <ReferenceLine
            x={Date.now()}
            stroke={theme.colors.primary.main}
            strokeWidth={2}
            strokeDasharray="3 3"
            label={{ value: "Now", position: "top" }}
          />

          {/* Quality indicators as scatter points */}
          {variables.filter(v => v.visible && selectedVariable === v.name).map((variable) => (
            <Scatter
              key={`${variable.name}_quality`}
              dataKey={variable.name}
              fill={variable.color}
              fillOpacity={0.6}
              shape="circle"
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Analog pattern details overlay */}
      {hoveredAnalog && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            position: 'absolute',
            bottom: theme.spacing(1),
            left: theme.spacing(1),
            padding: theme.spacing(1.5),
            background: theme.colors.background.secondary,
            border: `1px solid ${theme.colors.border.medium}`,
            borderRadius: theme.shape.borderRadius(),
            boxShadow: theme.shadows.z2,
            fontSize: '12px',
            maxWidth: '250px'
          }}
        >
          <div style={{ 
            fontWeight: 'bold', 
            marginBottom: '4px',
            color: theme.colors.text.primary
          }}>
            📈 Analog Pattern Match
          </div>
          <div>Date: {format(hoveredAnalog.date, 'MMM dd, yyyy HH:mm')}</div>
          <div>Similarity: {(hoveredAnalog.similarity * 100).toFixed(1)}%</div>
          <div>Situation: {hoveredAnalog.metadata.synopticSituation}</div>
          <div style={{ 
            marginTop: '4px',
            color: theme.colors.text.secondary,
            fontSize: '11px'
          }}>
            {hoveredAnalog.metadata.weatherOutcome}
          </div>
        </motion.div>
      )}
    </div>
  );
};