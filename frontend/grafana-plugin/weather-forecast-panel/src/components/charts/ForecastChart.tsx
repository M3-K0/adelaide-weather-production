import React, { useMemo, useState } from 'react';
import { GrafanaTheme2 } from '@grafana/data';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  ComposedChart,
  ReferenceLine,
  Brush
} from 'recharts';
import { format, parseISO } from 'date-fns';
import {
  WeatherDataPoint,
  WeatherVariable,
  ForecastHorizon,
  AnalogPattern,
  UncertaintyBand,
  HistoricalEvent,
  AnimationState
} from '../../types';

interface ForecastChartProps {
  data: Array<WeatherDataPoint & { timestamp: number; horizon: number }>;
  variables: WeatherVariable[];
  selectedHorizon: ForecastHorizon;
  width: number;
  height: number;
  timeRange: any;
  theme: GrafanaTheme2;
  analogPatterns: AnalogPattern[];
  uncertaintyBands: UncertaintyBand[];
  historicalEvents: HistoricalEvent[];
  animationState: AnimationState;
}

export const ForecastChart: React.FC<ForecastChartProps> = ({
  data,
  variables,
  selectedHorizon,
  width,
  height,
  timeRange,
  theme,
  analogPatterns,
  uncertaintyBands,
  historicalEvents,
  animationState
}) => {
  const [selectedAnalog, setSelectedAnalog] = useState<AnalogPattern | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<any>(null);

  // Prepare chart data
  const chartData = useMemo(() => {
    // Group data by time and variable
    const groupedData = data.reduce((acc, point) => {
      const timeKey = point.timestamp;
      if (!acc[timeKey]) {
        acc[timeKey] = {
          timestamp: timeKey,
          time: point.time,
          horizon: point.horizon
        };
      }
      
      acc[timeKey][point.variable] = point.value;
      
      // Add uncertainty bands
      const uncertaintyForPoint = uncertaintyBands.find(
        band => 
          band.time.getTime() === point.time.getTime() && 
          band.variable === point.variable
      );
      
      if (uncertaintyForPoint) {
        acc[timeKey][`${point.variable}_lower`] = uncertaintyForPoint.lower;
        acc[timeKey][`${point.variable}_upper`] = uncertaintyForPoint.upper;
        acc[timeKey][`${point.variable}_confidence`] = uncertaintyForPoint.confidence;
      }
      
      return acc;
    }, {} as any);

    return Object.values(groupedData).sort((a: any, b: any) => a.timestamp - b.timestamp);
  }, [data, uncertaintyBands]);

  // Prepare analog pattern overlays
  const analogOverlays = useMemo(() => {
    if (!selectedAnalog) return [];
    
    return selectedAnalog.pattern.map((value, index) => ({
      timestamp: chartData[index]?.timestamp,
      analogValue: value,
      similarity: selectedAnalog.similarity
    })).filter(item => item.timestamp);
  }, [selectedAnalog, chartData]);

  // Animation frame data for horizon progression
  const animationFrameData = useMemo(() => {
    if (!animationState.isPlaying) return chartData;
    
    // Filter data based on current animation horizon
    const horizonLimit = animationState.currentHorizon;
    const now = Date.now();
    const cutoffTime = now + (horizonLimit * 60 * 60 * 1000);
    
    return chartData.filter((point: any) => point.timestamp <= cutoffTime);
  }, [chartData, animationState]);

  // Custom tooltip
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
          if (!variable || entry.dataKey.includes('_lower') || entry.dataKey.includes('_upper')) {
            return null;
          }
          
          return (
            <div key={index} style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: '4px',
              color: entry.color
            }}>
              <span>{variable.label}:</span>
              <span style={{ fontWeight: 'bold' }}>
                {entry.value?.toFixed(1)} {variable.unit}
              </span>
            </div>
          );
        })}
        
        {/* Show uncertainty information */}
        {payload.some((p: any) => p.payload[`${p.dataKey}_confidence`]) && (
          <div style={{
            marginTop: theme.spacing(1),
            paddingTop: theme.spacing(1),
            borderTop: `1px solid ${theme.colors.border.medium}`,
            fontSize: '12px',
            color: theme.colors.text.secondary
          }}>
            Confidence bands available
          </div>
        )}
      </div>
    );
  };

  // Format time axis
  const formatXAxis = (tickItem: any) => {
    return format(new Date(tickItem), 'HH:mm');
  };

  // Handle analog pattern selection
  const handleAnalogSelect = (pattern: AnalogPattern) => {
    setSelectedAnalog(pattern === selectedAnalog ? null : pattern);
  };

  return (
    <div style={{ width, height, position: 'relative' }}>
      {/* Analog patterns selector */}
      {analogPatterns.length > 0 && (
        <div style={{
          position: 'absolute',
          top: theme.spacing(1),
          left: theme.spacing(1),
          zIndex: 10,
          display: 'flex',
          gap: theme.spacing(1),
          flexWrap: 'wrap',
          maxWidth: width - theme.spacing(4)
        }}>
          {analogPatterns.map((pattern, index) => (
            <motion.button
              key={pattern.id}
              onClick={() => handleAnalogSelect(pattern)}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              style={{
                padding: theme.spacing(0.5, 1),
                background: selectedAnalog?.id === pattern.id
                  ? theme.colors.primary.main
                  : theme.colors.background.secondary,
                color: selectedAnalog?.id === pattern.id
                  ? theme.colors.primary.contrastText
                  : theme.colors.text.primary,
                border: `1px solid ${theme.colors.border.medium}`,
                borderRadius: theme.shape.borderRadius(),
                fontSize: '11px',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              Analog {index + 1} ({(pattern.similarity * 100).toFixed(0)}%)
            </motion.button>
          ))}
        </div>
      )}

      {/* Historical events indicators */}
      {historicalEvents.length > 0 && (
        <div style={{
          position: 'absolute',
          top: theme.spacing(1),
          right: theme.spacing(1),
          zIndex: 10,
          maxWidth: '200px'
        }}>
          {historicalEvents.slice(0, 3).map((event, index) => (
            <motion.div
              key={event.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              style={{
                padding: theme.spacing(0.5, 1),
                background: theme.colors.warning.transparent,
                color: theme.colors.warning.text,
                border: `1px solid ${theme.colors.warning.border}`,
                borderRadius: theme.shape.borderRadius(),
                fontSize: '10px',
                marginBottom: '2px',
                cursor: 'pointer'
              }}
              title={event.description}
            >
              ⚠ {event.type} ({format(event.date, 'MM/dd')})
            </motion.div>
          ))}
        </div>
      )}

      {/* Main chart */}
      <ResponsiveContainer width={width} height={height - 60}>
        <ComposedChart
          data={animationFrameData}
          margin={{
            top: 60,
            right: 30,
            left: 20,
            bottom: 20,
          }}
          onMouseMove={(e) => setHoveredPoint(e?.activePayload)}
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

          {/* Uncertainty bands */}
          {variables.filter(v => v.visible).map((variable) => (
            uncertaintyBands.some(band => band.variable === variable.name) && (
              <Area
                key={`${variable.name}_uncertainty`}
                dataKey={variable.name}
                stroke="none"
                fill={variable.color}
                fillOpacity={0.1}
                connectNulls={false}
              />
            )
          ))}

          {/* Main forecast lines */}
          {variables.filter(v => v.visible).map((variable) => (
            <Line
              key={variable.name}
              type="monotone"
              dataKey={variable.name}
              stroke={variable.color}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              animationDuration={animationState.isPlaying ? animationState.speed : 0}
            />
          ))}

          {/* Analog pattern overlay */}
          {selectedAnalog && (
            <Line
              type="monotone"
              dataKey="analogValue"
              stroke={theme.colors.secondary.main}
              strokeWidth={3}
              strokeDasharray="5 5"
              dot={false}
              connectNulls={false}
              name={`Analog Pattern (${(selectedAnalog.similarity * 100).toFixed(0)}%)`}
            />
          )}

          {/* Animation progress indicator */}
          {animationState.isPlaying && (
            <ReferenceLine
              x={Date.now() + (animationState.currentHorizon * 60 * 60 * 1000)}
              stroke={theme.colors.primary.main}
              strokeWidth={2}
              strokeDasharray="3 3"
            />
          )}

          {/* Brush for time selection */}
          <Brush
            dataKey="timestamp"
            height={30}
            stroke={theme.colors.primary.main}
            fill={theme.colors.background.secondary}
            tickFormatter={formatXAxis}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Animation state overlay */}
      <AnimatePresence>
        {animationState.isPlaying && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: 'absolute',
              bottom: theme.spacing(1),
              left: theme.spacing(1),
              padding: theme.spacing(1),
              background: theme.colors.success.transparent,
              color: theme.colors.success.text,
              border: `1px solid ${theme.colors.success.border}`,
              borderRadius: theme.shape.borderRadius(),
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: theme.spacing(1)
            }}
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            >
              ⟳
            </motion.div>
            <span>
              Animating through {selectedHorizon.label} forecast horizon
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};