import React from 'react';
import { PanelOptionsEditorBuilder, StandardEditorProps } from '@grafana/data';
import { Switch, Select, Slider, HorizontalGroup } from '@grafana/ui';
import { WeatherPanelOptions } from './types';

export const panelOptionsBuilder = (builder: PanelOptionsEditorBuilder<WeatherPanelOptions>) => {
  return builder
    .addCustomEditor({
      id: 'viewSettings',
      path: '',
      name: 'View Settings',
      editor: ViewSettingsEditor,
    })
    .addCustomEditor({
      id: 'animationSettings',
      path: '',
      name: 'Animation Settings',
      editor: AnimationSettingsEditor,
    })
    .addCustomEditor({
      id: 'dataSettings',
      path: '',
      name: 'Data Settings',
      editor: DataSettingsEditor,
    })
    .addCustomEditor({
      id: 'analogSettings',
      path: '',
      name: 'Analog Pattern Settings',
      editor: AnalogSettingsEditor,
    });
};

const ViewSettingsEditor: React.FC<StandardEditorProps<any, any, WeatherPanelOptions>> = ({ 
  value, 
  onChange 
}) => {
  const options = value as WeatherPanelOptions;

  return (
    <div>
      <HorizontalGroup>
        <Switch
          label="Show Observations"
          value={options.showObservations}
          onChange={(checked) => onChange({ ...options, showObservations: checked })}
        />
        <Switch
          label="Show Forecast"
          value={options.showForecast}
          onChange={(checked) => onChange({ ...options, showForecast: checked })}
        />
      </HorizontalGroup>
      
      <div style={{ marginTop: '12px' }}>
        <label>Split View Ratio</label>
        <Slider
          min={0.2}
          max={0.8}
          step={0.1}
          value={options.splitViewRatio}
          onChange={(ratio) => onChange({ ...options, splitViewRatio: ratio })}
        />
      </div>

      <div style={{ marginTop: '12px' }}>
        <Select
          label="Default Horizon"
          value={options.defaultHorizon}
          options={[
            { label: '6 hours', value: '6h' },
            { label: '12 hours', value: '12h' },
            { label: '24 hours', value: '24h' },
            { label: '48 hours', value: '48h' }
          ]}
          onChange={(selection) => onChange({ ...options, defaultHorizon: selection.value! })}
        />
      </div>
    </div>
  );
};

const AnimationSettingsEditor: React.FC<StandardEditorProps<any, any, WeatherPanelOptions>> = ({ 
  value, 
  onChange 
}) => {
  const options = value as WeatherPanelOptions;

  return (
    <div>
      <div style={{ marginBottom: '12px' }}>
        <label>Animation Speed (ms)</label>
        <Slider
          min={250}
          max={5000}
          step={250}
          value={options.animationSpeed}
          onChange={(speed) => onChange({ ...options, animationSpeed: speed })}
        />
      </div>
    </div>
  );
};

const DataSettingsEditor: React.FC<StandardEditorProps<any, any, WeatherPanelOptions>> = ({ 
  value, 
  onChange 
}) => {
  const options = value as WeatherPanelOptions;

  return (
    <div>
      <HorizontalGroup>
        <Switch
          label="Show Uncertainty Bands"
          value={options.showUncertaintyBands}
          onChange={(checked) => onChange({ ...options, showUncertaintyBands: checked })}
        />
        <Switch
          label="Enable Historical Events"
          value={options.enableHistoricalEvents}
          onChange={(checked) => onChange({ ...options, enableHistoricalEvents: checked })}
        />
      </HorizontalGroup>

      <div style={{ marginTop: '12px' }}>
        <label>Confidence Threshold</label>
        <Slider
          min={0.1}
          max={1.0}
          step={0.1}
          value={options.confidenceThreshold}
          onChange={(threshold) => onChange({ ...options, confidenceThreshold: threshold })}
        />
      </div>
    </div>
  );
};

const AnalogSettingsEditor: React.FC<StandardEditorProps<any, any, WeatherPanelOptions>> = ({ 
  value, 
  onChange 
}) => {
  const options = value as WeatherPanelOptions;

  return (
    <div>
      <Switch
        label="Show Analog Patterns"
        value={options.showAnalogPatterns}
        onChange={(checked) => onChange({ ...options, showAnalogPatterns: checked })}
      />

      <div style={{ marginTop: '12px' }}>
        <label>Maximum Analog Count</label>
        <Slider
          min={1}
          max={10}
          step={1}
          value={options.maxAnalogCount}
          onChange={(count) => onChange({ ...options, maxAnalogCount: count })}
        />
      </div>
    </div>
  );
};