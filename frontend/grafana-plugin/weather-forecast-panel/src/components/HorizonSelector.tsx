import React from 'react';
import { RadioButtonGroup } from '@grafana/ui';
import { motion } from 'framer-motion';
import { ForecastHorizon, AnimationState } from '../types';

interface HorizonSelectorProps {
  horizons: ForecastHorizon[];
  selected: ForecastHorizon;
  onChange: (horizon: ForecastHorizon) => void;
  animationState: AnimationState;
}

export const HorizonSelector: React.FC<HorizonSelectorProps> = ({
  horizons,
  selected,
  onChange,
  animationState
}) => {
  const options = horizons.map(horizon => ({
    label: horizon.label,
    value: horizon.hours.toString(),
    description: `${horizon.hours} hour forecast`
  }));

  const handleChange = (value: string) => {
    const horizon = horizons.find(h => h.hours.toString() === value);
    if (horizon) {
      onChange(horizon);
    }
  };

  return (
    <div style={{ position: 'relative' }}>
      <RadioButtonGroup
        options={options}
        value={selected.hours.toString()}
        onChange={handleChange}
        size="sm"
      />
      
      {/* Animation progress indicator */}
      {animationState.isPlaying && (
        <motion.div
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{
            duration: animationState.speed / 1000,
            repeat: Infinity,
            ease: 'linear'
          }}
          style={{
            position: 'absolute',
            bottom: '-2px',
            left: 0,
            height: '2px',
            background: '#00D9FF',
            transformOrigin: 'left',
            borderRadius: '1px'
          }}
        />
      )}
    </div>
  );
};