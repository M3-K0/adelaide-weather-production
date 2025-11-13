/**
 * LoadingState Component
 * 
 * Reusable loading component with different variants for various
 * loading scenarios across the application.
 */

import React from 'react';
import { RefreshCw, Cloud, TrendingUp, Activity, Database } from 'lucide-react';
import { motion } from 'framer-motion';

export type LoadingType = 
  | 'default'
  | 'forecast'
  | 'analogs' 
  | 'metrics'
  | 'data';

export type LoadingSize = 'sm' | 'md' | 'lg';

interface LoadingStateProps {
  /** Type of loading indicator */
  type?: LoadingType;
  /** Size variant */
  size?: LoadingSize;
  /** Custom loading message */
  message?: string;
  /** Show additional details */
  showDetails?: boolean;
  /** Custom className */
  className?: string;
  /** Disable animations */
  disableAnimations?: boolean;
  /** Show progress indicator */
  showProgress?: boolean;
  /** Progress percentage (0-100) */
  progress?: number;
}

interface LoadingConfig {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  message: string;
  details: string;
  color: string;
}

// Configuration for different loading types
const loadingConfigs: Record<LoadingType, LoadingConfig> = {
  default: {
    icon: RefreshCw,
    message: 'Loading...',
    details: 'Please wait while we fetch the data.',
    color: 'text-slate-400'
  },
  forecast: {
    icon: Cloud,
    message: 'Loading Forecast',
    details: 'Analyzing weather patterns and generating predictions...',
    color: 'text-cyan-400'
  },
  analogs: {
    icon: TrendingUp,
    message: 'Searching Analogs',
    details: 'Finding similar historical weather patterns...',
    color: 'text-blue-400'
  },
  metrics: {
    icon: Activity,
    message: 'Loading Metrics',
    details: 'Gathering performance and accuracy data...',
    color: 'text-green-400'
  },
  data: {
    icon: Database,
    message: 'Loading Data',
    details: 'Retrieving information from the database...',
    color: 'text-purple-400'
  }
};

// Size configurations
const sizeConfigs = {
  sm: {
    container: 'p-4',
    icon: 20,
    message: 'text-sm font-medium',
    details: 'text-xs',
    spinner: 'w-4 h-4'
  },
  md: {
    container: 'p-6',
    icon: 24,
    message: 'text-base font-semibold',
    details: 'text-sm',
    spinner: 'w-6 h-6'
  },
  lg: {
    container: 'p-8',
    icon: 32,
    message: 'text-lg font-bold',
    details: 'text-base',
    spinner: 'w-8 h-8'
  }
};

// Skeleton loading component for content placeholders
export const Skeleton: React.FC<{
  className?: string;
  width?: string | number;
  height?: string | number;
  count?: number;
}> = ({ className = '', width, height = '1rem', count = 1 }) => {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: count }, (_, i) => (
        <div
          key={i}
          className="bg-slate-700/50 rounded animate-pulse"
          style={{
            width: width || '100%',
            height
          }}
        />
      ))}
    </div>
  );
};

// Pulse animation for loading states
const PulseAnimation: React.FC<{ 
  size: number; 
  color: string; 
  disabled?: boolean 
}> = ({ size, color, disabled }) => {
  if (disabled) {
    return (
      <div className={`w-${size} h-${size} rounded-full bg-current opacity-50 ${color}`} />
    );
  }

  return (
    <motion.div
      className={`w-${size} h-${size} rounded-full bg-current ${color}`}
      animate={{
        scale: [1, 1.2, 1],
        opacity: [0.5, 1, 0.5]
      }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: "easeInOut"
      }}
    />
  );
};

export const LoadingState: React.FC<LoadingStateProps> = ({
  type = 'default',
  size = 'md',
  message,
  showDetails = true,
  className = '',
  disableAnimations = false,
  showProgress = false,
  progress = 0
}) => {
  const config = loadingConfigs[type];
  const sizeConfig = sizeConfigs[size];
  const Icon = config.icon;

  const displayMessage = message || config.message;

  return (
    <div className={`
      flex flex-col items-center justify-center text-center
      ${sizeConfig.container} ${className}
    `}>
      {/* Loading Icon/Spinner */}
      <motion.div
        className="flex justify-center mb-4"
        initial={disableAnimations ? false : { opacity: 0 }}
        animate={disableAnimations ? false : { opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <motion.div
          animate={disableAnimations ? false : { rotate: 360 }}
          transition={disableAnimations ? false : {
            duration: 2,
            repeat: Infinity,
            ease: "linear"
          }}
        >
          <Icon 
            size={sizeConfig.icon} 
            className={`${config.color} ${!disableAnimations ? 'animate-spin' : ''}`} 
          />
        </motion.div>
      </motion.div>

      {/* Loading Message */}
      <div className={`${sizeConfig.message} text-slate-200 mb-2`}>
        {displayMessage}
      </div>

      {/* Additional Details */}
      {showDetails && (
        <p className={`${sizeConfig.details} text-slate-400 mb-4 max-w-md`}>
          {config.details}
        </p>
      )}

      {/* Progress Bar */}
      {showProgress && (
        <div className="w-full max-w-xs mb-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-slate-400">Progress</span>
            <span className="text-xs text-slate-300 font-mono">{progress}%</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2">
            <motion.div
              className={`h-2 rounded-full ${
                progress >= 90 ? 'bg-green-500' :
                progress >= 70 ? 'bg-cyan-500' :
                progress >= 30 ? 'bg-blue-500' :
                'bg-slate-500'
              }`}
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>
      )}

      {/* Pulse Indicators */}
      <div className="flex items-center space-x-2">
        <PulseAnimation 
          size={2} 
          color={config.color} 
          disabled={disableAnimations}
        />
        <PulseAnimation 
          size={2} 
          color={config.color} 
          disabled={disableAnimations}
        />
        <PulseAnimation 
          size={2} 
          color={config.color} 
          disabled={disableAnimations}
        />
      </div>
    </div>
  );
};

// Specialized loading components
export const ForecastLoading: React.FC<Omit<LoadingStateProps, 'type'>> = (props) => (
  <LoadingState {...props} type="forecast" />
);

export const AnalogsLoading: React.FC<Omit<LoadingStateProps, 'type'>> = (props) => (
  <LoadingState {...props} type="analogs" />
);

export const MetricsLoading: React.FC<Omit<LoadingStateProps, 'type'>> = (props) => (
  <LoadingState {...props} type="metrics" />
);

export const DataLoading: React.FC<Omit<LoadingStateProps, 'type'>> = (props) => (
  <LoadingState {...props} type="data" />
);

export default LoadingState;