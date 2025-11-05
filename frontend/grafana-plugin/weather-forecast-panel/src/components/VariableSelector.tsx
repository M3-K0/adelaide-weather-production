import React from 'react';
import { Checkbox, HorizontalGroup, Tooltip } from '@grafana/ui';
import { WeatherVariable } from '../types';

interface VariableSelectorProps {
  variables: WeatherVariable[];
  onToggle: (variable: WeatherVariable) => void;
}

export const VariableSelector: React.FC<VariableSelectorProps> = ({
  variables,
  onToggle
}) => {
  return (
    <HorizontalGroup spacing="sm">
      <div style={{ fontSize: '12px', color: '#666', alignSelf: 'center' }}>
        Variables:
      </div>
      {variables.map(variable => (
        <Tooltip key={variable.name} content={`${variable.label} (${variable.unit})`}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Checkbox
              value={variable.visible}
              onChange={() => onToggle(variable)}
            />
            <div style={{
              width: '12px',
              height: '12px',
              backgroundColor: variable.color,
              borderRadius: '2px',
              opacity: variable.visible ? 1 : 0.3
            }} />
            <span style={{
              fontSize: '11px',
              opacity: variable.visible ? 1 : 0.5
            }}>
              {variable.label}
            </span>
          </div>
        </Tooltip>
      ))}
    </HorizontalGroup>
  );
};