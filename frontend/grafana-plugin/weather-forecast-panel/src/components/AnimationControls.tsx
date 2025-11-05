import React from 'react';
import { IconButton, HorizontalGroup, Select, Slider } from '@grafana/ui';
import { AnimationState } from '../types';

interface AnimationControlsProps {
  animationState: AnimationState;
  onToggle: () => void;
  onSpeedChange: (speed: number) => void;
}

export const AnimationControls: React.FC<AnimationControlsProps> = ({
  animationState,
  onToggle,
  onSpeedChange
}) => {
  const speedOptions = [
    { label: '0.5x', value: 2000 },
    { label: '1x', value: 1000 },
    { label: '2x', value: 500 },
    { label: '4x', value: 250 }
  ];

  return (
    <HorizontalGroup spacing="sm">
      <IconButton
        name={animationState.isPlaying ? 'pause' : 'play'}
        variant="secondary"
        tooltip={animationState.isPlaying ? 'Pause animation' : 'Play animation'}
        onClick={onToggle}
      />
      
      <Select
        value={animationState.speed}
        options={speedOptions}
        onChange={(option) => onSpeedChange(option.value!)}
        width={8}
        placeholder="Speed"
      />
      
      <div style={{ minWidth: '60px', fontSize: '12px', color: '#666' }}>
        {animationState.isPlaying ? 'Playing' : 'Paused'}
      </div>
    </HorizontalGroup>
  );
};