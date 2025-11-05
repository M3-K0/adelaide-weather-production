import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { GrafanaTheme2 } from '@grafana/data';
import { SynopticOverlay, AnalogPattern, AnimationState } from '../../types';

interface SynopticMapOverlayProps {
  synopticData: SynopticOverlay;
  analogPatterns: AnalogPattern[];
  width: number;
  height: number;
  theme: GrafanaTheme2;
  animationState: AnimationState;
}

export const SynopticMapOverlay: React.FC<SynopticMapOverlayProps> = ({
  synopticData,
  analogPatterns,
  width,
  height,
  theme,
  animationState
}) => {
  // Generate contour lines from pressure data
  const contourLines = useMemo(() => {
    if (!synopticData.patterns.pressure) return [];
    
    const pressure = synopticData.patterns.pressure;
    const contours = [];
    const contourLevels = [1000, 1005, 1010, 1015, 1020, 1025, 1030];
    
    // Simplified contour generation
    for (const level of contourLevels) {
      const points = [];
      for (let i = 0; i < pressure.length; i++) {
        for (let j = 0; j < pressure[i].length; j++) {
          if (Math.abs(pressure[i][j] - level) < 2.5) {
            points.push({
              x: (j / pressure[i].length) * width,
              y: (i / pressure.length) * height,
              value: pressure[i][j]
            });
          }
        }
      }
      
      if (points.length > 0) {
        contours.push({
          level,
          points,
          color: level < 1013 ? '#FF6B6B' : '#4ECDC4'
        });
      }
    }
    
    return contours;
  }, [synopticData.patterns.pressure, width, height]);

  // Generate wind vectors
  const windVectors = useMemo(() => {
    if (!synopticData.patterns.wind.u || !synopticData.patterns.wind.v) return [];
    
    const vectors = [];
    const stepSize = 20; // Show every 20th grid point
    
    for (let i = 0; i < synopticData.patterns.wind.u.length; i += stepSize) {
      for (let j = 0; j < synopticData.patterns.wind.u[i].length; j += stepSize) {
        const u = synopticData.patterns.wind.u[i][j];
        const v = synopticData.patterns.wind.v[i][j];
        const speed = Math.sqrt(u * u + v * v);
        
        if (speed > 1) { // Only show significant winds
          vectors.push({
            x: (j / synopticData.patterns.wind.u[i].length) * width,
            y: (i / synopticData.patterns.wind.u.length) * height,
            u,
            v,
            speed,
            angle: Math.atan2(v, u) * 180 / Math.PI
          });
        }
      }
    }
    
    return vectors;
  }, [synopticData.patterns.wind, width, height]);

  // Temperature contours with color gradient
  const temperatureContours = useMemo(() => {
    if (!synopticData.patterns.temperature) return [];
    
    const temp = synopticData.patterns.temperature;
    const tempContours = [];
    
    // Create temperature gradient background
    for (let i = 0; i < temp.length; i++) {
      for (let j = 0; j < temp[i].length; j++) {
        const temperature = temp[i][j];
        const hue = Math.max(0, Math.min(240, 240 - (temperature + 10) * 8)); // Blue to red gradient
        
        tempContours.push({
          x: (j / temp[i].length) * width,
          y: (i / temp.length) * height,
          temperature,
          color: `hsl(${hue}, 70%, 50%)`
        });
      }
    }
    
    return tempContours;
  }, [synopticData.patterns.temperature, width, height]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 0.7 }}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width,
        height,
        pointerEvents: 'none',
        zIndex: 5
      }}
    >
      <svg width={width} height={height}>
        {/* Temperature background gradient */}
        <defs>
          <radialGradient id="temperatureGradient">
            <stop offset="0%" stopColor="rgba(255, 107, 107, 0.3)" />
            <stop offset="50%" stopColor="rgba(78, 205, 196, 0.2)" />
            <stop offset="100%" stopColor="rgba(69, 183, 209, 0.1)" />
          </radialGradient>
        </defs>

        {/* Temperature field visualization */}
        {temperatureContours.map((point, index) => (
          <motion.circle
            key={`temp_${index}`}
            cx={point.x}
            cy={point.y}
            r="3"
            fill={point.color}
            opacity="0.4"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: index * 0.001 }}
          />
        ))}

        {/* Pressure contour lines */}
        {contourLines.map((contour, index) => (
          <g key={`contour_${contour.level}`}>
            {contour.points.map((point, pointIndex) => (
              <motion.circle
                key={`point_${pointIndex}`}
                cx={point.x}
                cy={point.y}
                r="1"
                fill={contour.color}
                opacity="0.8"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.8 }}
                transition={{ delay: index * 0.1 + pointIndex * 0.01 }}
              />
            ))}
            
            {/* Contour line label */}
            {contour.points.length > 0 && (
              <text
                x={contour.points[0].x + 10}
                y={contour.points[0].y - 5}
                fill={contour.color}
                fontSize="10"
                fontWeight="bold"
              >
                {contour.level}
              </text>
            )}
          </g>
        ))}

        {/* Wind vectors */}
        {windVectors.map((vector, index) => (
          <motion.g
            key={`wind_${index}`}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.02 }}
          >
            <line
              x1={vector.x}
              y1={vector.y}
              x2={vector.x + vector.u * 3}
              y2={vector.y + vector.v * 3}
              stroke="#FFF"
              strokeWidth={Math.min(3, vector.speed / 5)}
              strokeOpacity="0.8"
              markerEnd="url(#windArrowhead)"
            />
            
            {/* Wind speed circles for stronger winds */}
            {vector.speed > 10 && (
              <circle
                cx={vector.x}
                cy={vector.y}
                r={vector.speed / 5}
                fill="none"
                stroke="#FFF"
                strokeWidth="1"
                opacity="0.5"
              />
            )}
          </motion.g>
        ))}

        {/* Arrow marker for wind vectors */}
        <defs>
          <marker
            id="windArrowhead"
            markerWidth="6"
            markerHeight="4"
            refX="6"
            refY="2"
            orient="auto"
          >
            <polygon
              points="0 0, 6 2, 0 4"
              fill="#FFF"
              opacity="0.8"
            />
          </marker>
        </defs>

        {/* Analog pattern highlights */}
        {analogPatterns.slice(0, 3).map((pattern, index) => (
          <motion.g
            key={`analog_${pattern.id}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.6 }}
            transition={{ delay: index * 0.2 }}
          >
            <circle
              cx={width * (0.2 + index * 0.3)}
              cy={height * 0.1}
              r="20"
              fill="none"
              stroke="#FFD700"
              strokeWidth="2"
              strokeDasharray="5,5"
            />
            <text
              x={width * (0.2 + index * 0.3)}
              y={height * 0.1 + 5}
              textAnchor="middle"
              fill="#FFD700"
              fontSize="12"
              fontWeight="bold"
            >
              A{index + 1}
            </text>
          </motion.g>
        ))}

        {/* Animation progress indicator */}
        {animationState.isPlaying && (
          <motion.g
            animate={{
              opacity: [0.3, 1, 0.3],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          >
            <rect
              x={width - 100}
              y={10}
              width="80"
              height="20"
              fill="rgba(0, 0, 0, 0.7)"
              rx="10"
            />
            <text
              x={width - 60}
              y={25}
              textAnchor="middle"
              fill="#00D9FF"
              fontSize="12"
            >
              Animating
            </text>
          </motion.g>
        )}
      </svg>

      {/* Synoptic pattern info overlay */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          position: 'absolute',
          bottom: '10px',
          left: '10px',
          background: 'rgba(0, 0, 0, 0.8)',
          color: 'white',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '11px',
          backdropFilter: 'blur(5px)'
        }}
      >
        <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
          Synoptic Analysis
        </div>
        <div>Analog Matches: {synopticData.analogMatches.length}</div>
        <div>Time: {synopticData.time.toLocaleTimeString()}</div>
      </motion.div>
    </motion.div>
  );
};