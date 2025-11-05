import React from 'react';
import { motion } from 'framer-motion';
import { UncertaintyBand, WeatherVariable } from '../types';

interface UncertaintyBandsDisplayProps {
  bands: UncertaintyBand[];
  variables: WeatherVariable[];
  threshold: number;
}

export const UncertaintyBandsDisplay: React.FC<UncertaintyBandsDisplayProps> = ({
  bands,
  variables,
  threshold
}) => {
  const visibleBands = bands.filter(band => 
    band.confidence >= threshold &&
    variables.some(v => v.name === band.variable && v.visible)
  );

  if (visibleBands.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        position: 'absolute',
        bottom: '10px',
        right: '10px',
        zIndex: 15,
        background: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(10px)',
        borderRadius: '8px',
        padding: '12px',
        minWidth: '200px',
        color: 'white'
      }}
    >
      <h4 style={{ margin: '0 0 8px 0', fontSize: '14px' }}>
        🎯 Uncertainty Bands
      </h4>

      {variables.filter(v => v.visible).map(variable => {
        const variableBands = visibleBands.filter(b => b.variable === variable.name);
        if (variableBands.length === 0) return null;

        const avgConfidence = variableBands.reduce((sum, b) => sum + b.confidence, 0) / variableBands.length;

        return (
          <div key={variable.name} style={{ marginBottom: '8px' }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '4px'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  background: variable.color,
                  borderRadius: '50%'
                }} />
                <span style={{ fontSize: '12px' }}>{variable.label}</span>
              </div>
              <span style={{
                fontSize: '10px',
                background: `rgba(0, 255, 0, ${avgConfidence})`,
                padding: '2px 6px',
                borderRadius: '10px'
              }}>
                {(avgConfidence * 100).toFixed(0)}%
              </span>
            </div>

            <div style={{ fontSize: '10px', color: '#ccc' }}>
              {variableBands.length} confidence intervals
            </div>
          </div>
        );
      })}

      <div style={{
        marginTop: '8px',
        paddingTop: '8px',
        borderTop: '1px solid rgba(255, 255, 255, 0.2)',
        fontSize: '10px',
        color: '#ccc'
      }}>
        Threshold: {(threshold * 100).toFixed(0)}% confidence
      </div>
    </motion.div>
  );
};