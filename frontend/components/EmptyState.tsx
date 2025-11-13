/**
 * EmptyState Component
 * 
 * Reusable component for displaying empty states, no data scenarios,
 * and fallback indicators across the application.
 */

import React from 'react';
import { 
  AlertCircle, 
  Database,
  RefreshCw, 
  TrendingUp, 
  Cloud, 
  Activity,
  Search,
  Settings,
  Info
} from 'lucide-react';
import { motion } from 'framer-motion';

export type EmptyStateType = 
  | 'no-data' 
  | 'no-analogs' 
  | 'no-forecast' 
  | 'no-metrics' 
  | 'search-empty' 
  | 'error' 
  | 'loading-failed'
  | 'fallback-data'
  | 'service-unavailable';

export type EmptyStateSize = 'sm' | 'md' | 'lg';

interface EmptyStateProps {
  /** Type of empty state to display */
  type: EmptyStateType;
  /** Optional custom title */
  title?: string;
  /** Optional custom description */
  description?: string;
  /** Optional size variant */
  size?: EmptyStateSize;
  /** Show retry button */
  showRetry?: boolean;
  /** Retry button callback */
  onRetry?: () => void;
  /** Show contact support button */
  showSupport?: boolean;
  /** Optional additional actions */
  actions?: React.ReactNode;
  /** Custom className */
  className?: string;
  /** Disable animations */
  disableAnimations?: boolean;
  /** Data source indicator for transparency */
  dataSource?: 'faiss' | 'fallback' | 'error';
  /** Fallback reason if applicable */
  fallbackReason?: string;
}

interface EmptyStateConfig {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  description: string;
  color: string;
  bgColor: string;
  borderColor: string;
}

// Configuration for different empty state types
const emptyStateConfigs: Record<EmptyStateType, EmptyStateConfig> = {
  'no-data': {
    icon: Database,
    title: 'No Data Available',
    description: 'There is no data available for the selected parameters.',
    color: 'text-slate-400',
    bgColor: 'bg-slate-900/30',
    borderColor: 'border-slate-700'
  },
  'no-analogs': {
    icon: TrendingUp,
    title: 'No Analogs Available',
    description: 'No similar historical weather patterns were found for this forecast.',
    color: 'text-blue-400',
    bgColor: 'bg-blue-950/30',
    borderColor: 'border-blue-700'
  },
  'no-forecast': {
    icon: Cloud,
    title: 'No Forecast Available',
    description: 'Weather forecast data is not available for the selected time horizon.',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-950/30',
    borderColor: 'border-cyan-700'
  },
  'no-metrics': {
    icon: Activity,
    title: 'No Metrics Available',
    description: 'Performance metrics are not available for the selected time range.',
    color: 'text-green-400',
    bgColor: 'bg-green-950/30',
    borderColor: 'border-green-700'
  },
  'search-empty': {
    icon: Search,
    title: 'No Results Found',
    description: 'No results match your current search criteria.',
    color: 'text-purple-400',
    bgColor: 'bg-purple-950/30',
    borderColor: 'border-purple-700'
  },
  'error': {
    icon: AlertCircle,
    title: 'Error Loading Data',
    description: 'An error occurred while loading the requested data.',
    color: 'text-red-400',
    bgColor: 'bg-red-950/30',
    borderColor: 'border-red-700'
  },
  'loading-failed': {
    icon: RefreshCw,
    title: 'Loading Failed',
    description: 'Failed to load data. Please check your connection and try again.',
    color: 'text-orange-400',
    bgColor: 'bg-orange-950/30',
    borderColor: 'border-orange-700'
  },
  'fallback-data': {
    icon: Settings,
    title: 'Using Fallback Data',
    description: 'Real-time data unavailable. Showing cached or synthetic data.',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-950/30',
    borderColor: 'border-yellow-700'
  },
  'service-unavailable': {
    icon: Database,
    title: 'Service Unavailable',
    description: 'The backend service is temporarily unavailable.',
    color: 'text-red-400',
    bgColor: 'bg-red-950/30',
    borderColor: 'border-red-700'
  }
};

// Size configurations
const sizeConfigs = {
  sm: {
    container: 'p-4',
    icon: 24,
    title: 'text-sm font-medium',
    description: 'text-xs',
    button: 'px-3 py-1.5 text-xs'
  },
  md: {
    container: 'p-6',
    icon: 32,
    title: 'text-base font-semibold',
    description: 'text-sm',
    button: 'px-4 py-2 text-sm'
  },
  lg: {
    container: 'p-8',
    icon: 40,
    title: 'text-lg font-bold',
    description: 'text-base',
    button: 'px-6 py-3 text-base'
  }
};

export const EmptyState: React.FC<EmptyStateProps> = ({
  type,
  title,
  description,
  size = 'md',
  showRetry = false,
  onRetry,
  showSupport = false,
  actions,
  className = '',
  disableAnimations = false,
  dataSource,
  fallbackReason
}) => {
  const config = emptyStateConfigs[type];
  const sizeConfig = sizeConfigs[size];
  const Icon = config.icon;

  const displayTitle = title || config.title;
  const displayDescription = description || config.description;

  return (
    <motion.div
      className={`
        rounded-lg border ${config.borderColor} ${config.bgColor}
        ${sizeConfig.container} text-center
        ${className}
      `}
      initial={disableAnimations ? false : { opacity: 0, y: 20 }}
      animate={disableAnimations ? false : { opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Icon */}
      <motion.div
        className="flex justify-center mb-4"
        initial={disableAnimations ? false : { scale: 0.8 }}
        animate={disableAnimations ? false : { scale: 1 }}
        transition={{ delay: 0.1, duration: 0.3 }}
      >
        <Icon size={sizeConfig.icon} className={`${config.color} opacity-60`} />
      </motion.div>

      {/* Title */}
      <h3 className={`${sizeConfig.title} text-slate-200 mb-2`}>
        {displayTitle}
      </h3>

      {/* Description */}
      <p className={`${sizeConfig.description} text-slate-400 mb-4`}>
        {displayDescription}
      </p>

      {/* Data Source Indicator */}
      {dataSource && (
        <div className="mb-4">
          <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border ${
            dataSource === 'faiss' 
              ? 'bg-emerald-950/50 border-emerald-700 text-emerald-400'
              : dataSource === 'fallback'
                ? 'bg-orange-950/50 border-orange-700 text-orange-400'
                : 'bg-red-950/50 border-red-700 text-red-400'
          }`}>
            <Database size={10} />
            {dataSource === 'faiss' ? 'Real-time Data' : 
             dataSource === 'fallback' ? 'Fallback Mode' : 
             'Error State'}
          </div>
          {fallbackReason && (
            <p className="text-xs text-slate-500 mt-2">
              Reason: {fallbackReason}
            </p>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        {showRetry && onRetry && (
          <button
            onClick={onRetry}
            className={`
              inline-flex items-center gap-2 ${sizeConfig.button}
              bg-slate-700 hover:bg-slate-600 text-slate-200 hover:text-white
              border border-slate-600 hover:border-slate-500 rounded-lg
              transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500
            `}
          >
            <RefreshCw size={size === 'sm' ? 12 : 14} />
            Retry
          </button>
        )}

        {showSupport && (
          <button
            className={`
              inline-flex items-center gap-2 ${sizeConfig.button}
              bg-transparent hover:bg-slate-800 text-slate-400 hover:text-slate-200
              border border-slate-600 hover:border-slate-500 rounded-lg
              transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500
            `}
          >
            <Info size={size === 'sm' ? 12 : 14} />
            Contact Support
          </button>
        )}

        {actions}
      </div>
    </motion.div>
  );
};

export default EmptyState;