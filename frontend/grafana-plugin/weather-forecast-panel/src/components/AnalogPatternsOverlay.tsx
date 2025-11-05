import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { format } from 'date-fns';
import { AnalogPattern, SynopticOverlay } from '../types';

interface AnalogPatternsOverlayProps {
  patterns: AnalogPattern[];
  currentSynopticSituation: SynopticOverlay | null;
  maxCount: number;
  onPatternSelect: (pattern: AnalogPattern) => void;
}

export const AnalogPatternsOverlay: React.FC<AnalogPatternsOverlayProps> = ({
  patterns,
  currentSynopticSituation,
  maxCount,
  onPatternSelect
}) => {
  const [selectedPattern, setSelectedPattern] = useState<AnalogPattern | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const displayPatterns = patterns.slice(0, maxCount);

  const handlePatternClick = (pattern: AnalogPattern) => {
    setSelectedPattern(pattern === selectedPattern ? null : pattern);
    onPatternSelect(pattern);
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      style={{
        position: 'absolute',
        top: '60px',
        left: '10px',
        zIndex: 20,
        background: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(10px)',
        borderRadius: '8px',
        padding: '12px',
        minWidth: '250px',
        maxWidth: '350px',
        color: 'white'
      }}
    >
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '8px'
      }}>
        <h4 style={{ margin: 0, fontSize: '14px' }}>
          📊 Analog Patterns
        </h4>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'white',
            cursor: 'pointer',
            padding: '2px'
          }}
        >
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            {displayPatterns.map((pattern, index) => (
              <motion.div
                key={pattern.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                onClick={() => handlePatternClick(pattern)}
                style={{
                  padding: '8px',
                  margin: '4px 0',
                  background: selectedPattern?.id === pattern.id
                    ? 'rgba(0, 217, 255, 0.2)'
                    : 'rgba(255, 255, 255, 0.1)',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  border: selectedPattern?.id === pattern.id
                    ? '1px solid #00D9FF'
                    : '1px solid transparent',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span style={{ fontSize: '12px', fontWeight: 'bold' }}>
                    Pattern #{index + 1}
                  </span>
                  <span style={{
                    fontSize: '11px',
                    background: `rgba(0, 255, 0, ${pattern.similarity})`,
                    padding: '2px 6px',
                    borderRadius: '10px'
                  }}>
                    {(pattern.similarity * 100).toFixed(0)}%
                  </span>
                </div>
                
                <div style={{ fontSize: '11px', marginTop: '4px' }}>
                  📅 {format(pattern.date, 'MMM dd, yyyy')}
                </div>
                
                <div style={{ fontSize: '10px', color: '#ccc', marginTop: '2px' }}>
                  {pattern.metadata.synopticSituation}
                </div>
                
                {selectedPattern?.id === pattern.id && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    style={{
                      marginTop: '8px',
                      paddingTop: '8px',
                      borderTop: '1px solid rgba(255, 255, 255, 0.2)',
                      fontSize: '10px'
                    }}
                  >
                    <div><strong>Outcome:</strong> {pattern.metadata.weatherOutcome}</div>
                    <div><strong>Confidence:</strong> {(pattern.confidence * 100).toFixed(0)}%</div>
                  </motion.div>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {currentSynopticSituation && (
        <div style={{
          marginTop: '12px',
          paddingTop: '8px',
          borderTop: '1px solid rgba(255, 255, 255, 0.2)',
          fontSize: '10px'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
            Current Situation
          </div>
          <div>
            Matches: {currentSynopticSituation.analogMatches.length} patterns
          </div>
        </div>
      )}
    </motion.div>
  );
};