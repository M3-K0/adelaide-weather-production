import React, { useMemo } from 'react';
import { GrafanaTheme2 } from '@grafana/data';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  WeatherDataPoint, 
  WeatherVariable, 
  ForecastHorizon,
  AnalogPattern,
  UncertaintyBand,
  HistoricalEvent,
  SynopticOverlay,
  AnimationState
} from '../types';
import { ObservationsChart } from './charts/ObservationsChart';
import { ForecastChart } from './charts/ForecastChart';
import { SynopticMapOverlay } from './overlays/SynopticMapOverlay';

interface SplitViewProps {
  observationsData: WeatherDataPoint[];
  forecastData: WeatherDataPoint[];
  variables: WeatherVariable[];
  selectedHorizon: ForecastHorizon;
  splitRatio: number;
  showObservations: boolean;
  showForecast: boolean;
  timeRange: any;
  width: number;
  height: number;
  theme: GrafanaTheme2;
  analogPatterns: AnalogPattern[];
  maxAnalogCount: number;
  uncertaintyBands: UncertaintyBand[];
  confidenceThreshold: number;
  historicalEvents: HistoricalEvent[];
  synopticOverlay: SynopticOverlay | null;
  animationState: AnimationState;
}

export const SplitView: React.FC<SplitViewProps> = ({
  observationsData,
  forecastData,
  variables,
  selectedHorizon,
  splitRatio,
  showObservations,
  showForecast,
  timeRange,
  width,
  height,
  theme,
  analogPatterns,
  maxAnalogCount,
  uncertaintyBands,
  confidenceThreshold,
  historicalEvents,
  synopticOverlay,
  animationState
}) => {
  // Calculate panel dimensions
  const observationsWidth = showObservations && showForecast 
    ? Math.floor(width * splitRatio) 
    : showObservations ? width : 0;
  
  const forecastWidth = showObservations && showForecast 
    ? width - observationsWidth 
    : showForecast ? width : 0;

  // Panel styles
  const panelStyles = {
    container: {
      display: 'flex',
      width: width,
      height: height,
      position: 'relative' as const,
      overflow: 'hidden',
    },
    observationsPanel: {
      width: observationsWidth,
      height: height,
      borderRight: showObservations && showForecast 
        ? `2px solid ${theme.colors.border.medium}` 
        : 'none',
      background: theme.colors.background.primary,
      position: 'relative' as const,
    },
    forecastPanel: {
      width: forecastWidth,
      height: height,
      background: theme.colors.background.primary,
      position: 'relative' as const,
    },
    panelHeader: {
      padding: theme.spacing(1, 2),
      background: theme.colors.background.secondary,
      borderBottom: `1px solid ${theme.colors.border.medium}`,
      fontSize: theme.typography.h6.fontSize,
      fontWeight: theme.typography.h6.fontWeight,
      color: theme.colors.text.primary,
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    panelContent: {
      height: height - 40, // Account for header
      overflow: 'hidden',
      position: 'relative' as const,
    },
    animationIndicator: {
      position: 'absolute' as const,
      top: theme.spacing(1),
      right: theme.spacing(1),
      padding: theme.spacing(0.5, 1),
      background: animationState.isPlaying 
        ? theme.colors.success.transparent 
        : theme.colors.info.transparent,
      color: animationState.isPlaying 
        ? theme.colors.success.text 
        : theme.colors.info.text,
      borderRadius: theme.shape.borderRadius(),
      fontSize: '12px',
      zIndex: 10,
    },
  };

  // Prepare data for charts
  const observationsChartData = useMemo(() => {
    return observationsData.map(point => ({
      ...point,
      timestamp: point.time.getTime(),
    }));
  }, [observationsData]);

  const forecastChartData = useMemo(() => {
    return forecastData.map(point => ({
      ...point,
      timestamp: point.time.getTime(),
      horizon: selectedHorizon.hours,
    }));
  }, [forecastData, selectedHorizon]);

  // Filter uncertainty bands for current horizon
  const currentUncertaintyBands = useMemo(() => {
    return uncertaintyBands.filter(band => 
      band.confidence >= confidenceThreshold
    );
  }, [uncertaintyBands, confidenceThreshold]);

  // Filter analog patterns by count
  const displayAnalogPatterns = useMemo(() => {
    return analogPatterns
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, maxAnalogCount);
  }, [analogPatterns, maxAnalogCount]);

  return (
    <div style={panelStyles.container}>
      {/* Animation state indicator */}
      <AnimatePresence>
        {animationState.isPlaying && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            style={panelStyles.animationIndicator}
          >
            ▶ Playing {selectedHorizon.label} Animation
          </motion.div>
        )}
      </AnimatePresence>

      {/* Observations Panel */}
      {showObservations && (
        <motion.div
          style={panelStyles.observationsPanel}
          initial={{ width: 0 }}
          animate={{ width: observationsWidth }}
          transition={{ duration: 0.3 }}
        >
          <div style={panelStyles.panelHeader}>
            <span>Observations</span>
            <span style={{ fontSize: '12px', color: theme.colors.text.secondary }}>
              Current Conditions
            </span>
          </div>
          
          <div style={panelStyles.panelContent}>
            <ObservationsChart
              data={observationsChartData}
              variables={variables}
              width={observationsWidth}
              height={height - 40}
              timeRange={timeRange}
              theme={theme}
              analogPatterns={displayAnalogPatterns}
              uncertaintyBands={currentUncertaintyBands}
            />
          </div>
        </motion.div>
      )}

      {/* Forecast Panel */}
      {showForecast && (
        <motion.div
          style={panelStyles.forecastPanel}
          initial={{ width: 0 }}
          animate={{ width: forecastWidth }}
          transition={{ duration: 0.3 }}
        >
          <div style={panelStyles.panelHeader}>
            <span>Forecast</span>
            <span style={{ fontSize: '12px', color: theme.colors.text.secondary }}>
              {selectedHorizon.label} Horizon
              {animationState.isPlaying && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  style={{ marginLeft: theme.spacing(1) }}
                >
                  ⟳
                </motion.span>
              )}
            </span>
          </div>
          
          <div style={panelStyles.panelContent}>
            <ForecastChart
              data={forecastChartData}
              variables={variables}
              selectedHorizon={selectedHorizon}
              width={forecastWidth}
              height={height - 40}
              timeRange={timeRange}
              theme={theme}
              analogPatterns={displayAnalogPatterns}
              uncertaintyBands={currentUncertaintyBands}
              historicalEvents={historicalEvents}
              animationState={animationState}
            />
            
            {/* Synoptic overlay */}
            {synopticOverlay && (
              <SynopticMapOverlay
                synopticData={synopticOverlay}
                analogPatterns={displayAnalogPatterns}
                width={forecastWidth}
                height={height - 40}
                theme={theme}
                animationState={animationState}
              />
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
};