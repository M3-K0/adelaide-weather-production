import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { PanelProps } from '@grafana/data';
import { useTheme2 } from '@grafana/ui';
import { 
  WeatherPanelOptions, 
  PanelState, 
  DEFAULT_HORIZONS, 
  DEFAULT_VARIABLES,
  ForecastHorizon,
  WeatherVariable,
  AnimationState
} from '../types';
import { SplitView } from './SplitView';
import { AnimationControls } from './AnimationControls';
import { VariableSelector } from './VariableSelector';
import { HorizonSelector } from './HorizonSelector';
import { AnalogPatternsOverlay } from './AnalogPatternsOverlay';
import { UncertaintyBandsDisplay } from './UncertaintyBandsDisplay';
import { HistoricalEventsPanel } from './HistoricalEventsPanel';
import { useDataQuery } from '../hooks/useDataQuery';
import { useAnimation } from '../hooks/useAnimation';

interface Props extends PanelProps<WeatherPanelOptions> {}

export const WeatherForecastPanel: React.FC<Props> = ({ 
  options, 
  data, 
  width, 
  height,
  timeRange,
  onChangeTimeRange,
  replaceVariables
}) => {
  const theme = useTheme2();
  
  // Panel state
  const [state, setState] = useState<PanelState>({
    selectedHorizon: DEFAULT_HORIZONS[0],
    visibleVariables: DEFAULT_VARIABLES.filter(v => v.visible),
    analogPatterns: [],
    uncertaintyBands: [],
    historicalEvents: [],
    animationState: {
      isPlaying: false,
      currentHorizon: 6,
      speed: options.animationSpeed || 1000,
      direction: 'forward'
    },
    synopticOverlay: null,
    isLoading: false,
    error: null
  });

  // Data fetching
  const { 
    queryData, 
    isLoading: dataLoading, 
    error: dataError 
  } = useDataQuery({
    timeRange,
    selectedHorizon: state.selectedHorizon,
    variables: state.visibleVariables,
    options
  });

  // Animation control
  const { 
    animationState, 
    startAnimation, 
    stopAnimation, 
    setHorizon 
  } = useAnimation({
    horizons: DEFAULT_HORIZONS,
    speed: options.animationSpeed,
    onHorizonChange: (horizon) => {
      setState(prev => ({ 
        ...prev, 
        selectedHorizon: horizon 
      }));
    }
  });

  // Update state when data changes
  useEffect(() => {
    if (queryData) {
      setState(prev => ({
        ...prev,
        analogPatterns: queryData.analogs,
        uncertaintyBands: queryData.uncertainty,
        historicalEvents: queryData.historical,
        isLoading: false,
        error: null
      }));
    }
  }, [queryData]);

  // Update loading and error states
  useEffect(() => {
    setState(prev => ({
      ...prev,
      isLoading: dataLoading,
      error: dataError
    }));
  }, [dataLoading, dataError]);

  // Handlers
  const handleHorizonChange = useCallback((horizon: ForecastHorizon) => {
    setState(prev => ({ 
      ...prev, 
      selectedHorizon: horizon 
    }));
    setHorizon(horizon);
  }, [setHorizon]);

  const handleVariableToggle = useCallback((variable: WeatherVariable) => {
    setState(prev => ({
      ...prev,
      visibleVariables: prev.visibleVariables.map(v =>
        v.name === variable.name ? { ...v, visible: !v.visible } : v
      )
    }));
  }, []);

  const handleAnimationToggle = useCallback(() => {
    if (animationState.isPlaying) {
      stopAnimation();
    } else {
      startAnimation();
    }
  }, [animationState.isPlaying, startAnimation, stopAnimation]);

  // Prepare chart data
  const chartData = useMemo(() => {
    if (!queryData) return { observations: [], forecasts: [] };
    
    return {
      observations: queryData.observations.filter(d => 
        state.visibleVariables.some(v => v.name === d.variable && v.visible)
      ),
      forecasts: queryData.forecasts.filter(d => 
        state.visibleVariables.some(v => v.name === d.variable && v.visible) &&
        d.horizon === state.selectedHorizon.hours
      )
    };
  }, [queryData, state.visibleVariables, state.selectedHorizon]);

  // Panel styles
  const panelStyles = {
    container: {
      width: width,
      height: height,
      background: theme.colors.background.primary,
      border: `1px solid ${theme.colors.border.medium}`,
      borderRadius: theme.shape.borderRadius(),
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column' as const,
    },
    header: {
      padding: theme.spacing(1, 2),
      borderBottom: `1px solid ${theme.colors.border.medium}`,
      background: theme.colors.background.secondary,
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      flexShrink: 0,
    },
    controls: {
      display: 'flex',
      gap: theme.spacing(2),
      alignItems: 'center',
    },
    content: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column' as const,
      overflow: 'hidden',
    },
    error: {
      padding: theme.spacing(2),
      color: theme.colors.error.text,
      background: theme.colors.error.transparent,
      border: `1px solid ${theme.colors.error.border}`,
      borderRadius: theme.shape.borderRadius(),
      margin: theme.spacing(1),
    },
    loading: {
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100%',
      color: theme.colors.text.secondary,
    }
  };

  if (state.error) {
    return (
      <div style={panelStyles.container}>
        <div style={panelStyles.error}>
          <strong>Error:</strong> {state.error}
        </div>
      </div>
    );
  }

  return (
    <div style={panelStyles.container}>
      {/* Header with controls */}
      <div style={panelStyles.header}>
        <div style={panelStyles.controls}>
          <HorizonSelector
            horizons={DEFAULT_HORIZONS}
            selected={state.selectedHorizon}
            onChange={handleHorizonChange}
            animationState={animationState}
          />
          <VariableSelector
            variables={state.visibleVariables}
            onToggle={handleVariableToggle}
          />
          <AnimationControls
            animationState={animationState}
            onToggle={handleAnimationToggle}
            onSpeedChange={(speed) => 
              setState(prev => ({
                ...prev,
                animationState: { ...prev.animationState, speed }
              }))
            }
          />
        </div>
        
        {state.isLoading && (
          <div style={{ color: theme.colors.text.secondary }}>
            Loading...
          </div>
        )}
      </div>

      {/* Main content */}
      <div style={panelStyles.content}>
        {state.isLoading ? (
          <div style={panelStyles.loading}>
            Loading weather data...
          </div>
        ) : (
          <SplitView
            observationsData={chartData.observations}
            forecastData={chartData.forecasts}
            variables={state.visibleVariables}
            selectedHorizon={state.selectedHorizon}
            splitRatio={options.splitViewRatio}
            showObservations={options.showObservations}
            showForecast={options.showForecast}
            timeRange={timeRange}
            width={width}
            height={height - 60} // Account for header
            theme={theme}
            
            // Analog patterns overlay
            analogPatterns={options.showAnalogPatterns ? state.analogPatterns : []}
            maxAnalogCount={options.maxAnalogCount}
            
            // Uncertainty bands
            uncertaintyBands={options.showUncertaintyBands ? state.uncertaintyBands : []}
            confidenceThreshold={options.confidenceThreshold}
            
            // Historical events
            historicalEvents={options.enableHistoricalEvents ? state.historicalEvents : []}
            
            // Synoptic overlay
            synopticOverlay={state.synopticOverlay}
            
            // Animation state
            animationState={animationState}
          />
        )}
      </div>

      {/* Overlays */}
      {options.showAnalogPatterns && state.analogPatterns.length > 0 && (
        <AnalogPatternsOverlay
          patterns={state.analogPatterns}
          currentSynopticSituation={state.synopticOverlay}
          maxCount={options.maxAnalogCount}
          onPatternSelect={(pattern) => {
            // Handle analog pattern selection
            console.log('Selected analog pattern:', pattern);
          }}
        />
      )}

      {options.showUncertaintyBands && state.uncertaintyBands.length > 0 && (
        <UncertaintyBandsDisplay
          bands={state.uncertaintyBands}
          variables={state.visibleVariables}
          threshold={options.confidenceThreshold}
        />
      )}

      {options.enableHistoricalEvents && state.historicalEvents.length > 0 && (
        <HistoricalEventsPanel
          events={state.historicalEvents}
          onEventSelect={(event) => {
            // Handle historical event selection
            console.log('Selected historical event:', event);
          }}
        />
      )}
    </div>
  );
};