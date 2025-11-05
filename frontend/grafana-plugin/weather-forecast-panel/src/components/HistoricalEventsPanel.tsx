import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { format } from 'date-fns';
import { HistoricalEvent } from '../types';

interface HistoricalEventsPanelProps {
  events: HistoricalEvent[];
  onEventSelect: (event: HistoricalEvent) => void;
}

export const HistoricalEventsPanel: React.FC<HistoricalEventsPanelProps> = ({
  events,
  onEventSelect
}) => {
  const [selectedEvent, setSelectedEvent] = useState<HistoricalEvent | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const severityColors = {
    low: '#4CAF50',
    medium: '#FF9800',
    high: '#F44336',
    extreme: '#9C27B0'
  };

  const severityIcons = {
    low: '🟢',
    medium: '🟡',
    high: '🔴',
    extreme: '🟣'
  };

  const handleEventClick = (event: HistoricalEvent) => {
    setSelectedEvent(event === selectedEvent ? null : event);
    onEventSelect(event);
  };

  if (events.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      style={{
        position: 'absolute',
        top: '60px',
        right: '10px',
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
          📚 Historical Events
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

      <div style={{ fontSize: '11px', color: '#ccc', marginBottom: '8px' }}>
        {events.length} similar event{events.length !== 1 ? 's' : ''} found
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            {events.map((event, index) => (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                onClick={() => handleEventClick(event)}
                style={{
                  padding: '8px',
                  margin: '4px 0',
                  background: selectedEvent?.id === event.id
                    ? 'rgba(255, 193, 7, 0.2)'
                    : 'rgba(255, 255, 255, 0.1)',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  border: selectedEvent?.id === event.id
                    ? '1px solid #FFC107'
                    : '1px solid transparent',
                  borderLeft: `3px solid ${severityColors[event.severity]}`,
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}>
                    <span>{severityIcons[event.severity]}</span>
                    <span style={{ fontSize: '12px', fontWeight: 'bold' }}>
                      {event.type}
                    </span>
                  </div>
                  <span style={{
                    fontSize: '11px',
                    background: `rgba(255, 255, 255, ${event.similarity})`,
                    color: 'black',
                    padding: '2px 6px',
                    borderRadius: '10px'
                  }}>
                    {(event.similarity * 100).toFixed(0)}%
                  </span>
                </div>
                
                <div style={{ fontSize: '11px', marginTop: '4px' }}>
                  📅 {format(event.date, 'MMM dd, yyyy HH:mm')}
                </div>
                
                <div style={{ 
                  fontSize: '10px', 
                  color: '#ccc', 
                  marginTop: '2px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: selectedEvent?.id === event.id ? 'normal' : 'nowrap'
                }}>
                  {event.description}
                </div>
                
                {selectedEvent?.id === event.id && (
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
                    <div style={{ marginBottom: '4px' }}>
                      <strong>Severity:</strong> {event.severity.toUpperCase()}
                    </div>
                    <div style={{ marginBottom: '4px' }}>
                      <strong>Analog Patterns:</strong> {event.analogPatterns.length}
                    </div>
                    
                    {event.analogPatterns.length > 0 && (
                      <div style={{
                        marginTop: '6px',
                        padding: '4px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        borderRadius: '2px'
                      }}>
                        <div style={{ fontWeight: 'bold', marginBottom: '2px' }}>
                          Top Analog Pattern:
                        </div>
                        <div>
                          Similarity: {(event.analogPatterns[0].similarity * 100).toFixed(0)}%
                        </div>
                        <div>
                          Situation: {event.analogPatterns[0].metadata.synopticSituation}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        style={{
          marginTop: '8px',
          paddingTop: '8px',
          borderTop: '1px solid rgba(255, 255, 255, 0.2)',
          fontSize: '10px',
          color: '#ccc'
        }}
      >
        <div>Quick access to similar events</div>
        <div>Click for detailed analysis</div>
      </motion.div>
    </motion.div>
  );
};