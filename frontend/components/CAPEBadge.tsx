'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Info, Zap, AlertTriangle, TrendingUp, Calendar } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import { clsx } from 'clsx';

// CAPE Risk level thresholds
const CAPE_THRESHOLDS = {
  LOW: { min: 0, max: 500, color: 'green', label: 'Low' },
  MODERATE: { min: 500, max: 1000, color: 'yellow', label: 'Moderate' },
  HIGH: { min: 1000, max: 2000, color: 'orange', label: 'High' },
  EXTREME: { min: 2000, max: Infinity, color: 'red', label: 'Extreme' }
} as const;

type RiskLevel = keyof typeof CAPE_THRESHOLDS;

interface CAPEBadgeProps {
  /** CAPE value in J/kg */
  value: number;
  /** Historical percentile for the current season (0-100) */
  percentile?: number;
  /** Season label (e.g., "Summer", "Winter") */
  season?: string;
  /** Optional size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether to show the info icon */
  showInfo?: boolean;
  /** Disable animations */
  disableAnimations?: boolean;
  /** Custom className */
  className?: string;
}

interface CAPEExplanationProps {
  riskLevel: RiskLevel;
  value: number;
  percentile?: number;
  season?: string;
}

// Lightning animation component for extreme levels
const LightningAnimation: React.FC<{ animate: boolean }> = ({ animate }) => {
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    if (!animate) return;

    const interval = setInterval(
      () => {
        setFlash(true);
        setTimeout(() => setFlash(false), 150);
      },
      2000 + Math.random() * 3000
    ); // Random interval between 2-5 seconds

    return () => clearInterval(interval);
  }, [animate]);

  return (
    <motion.div
      className='absolute inset-0 flex items-center justify-center pointer-events-none'
      initial={{ opacity: 0 }}
      animate={{ opacity: flash ? 1 : 0 }}
      transition={{ duration: 0.1 }}
    >
      <Zap
        size={12}
        className='text-yellow-200 drop-shadow-lg'
        style={{
          filter: flash ? 'drop-shadow(0 0 8px rgba(255, 255, 0, 0.8))' : 'none'
        }}
      />
    </motion.div>
  );
};

// CAPE explanation modal content
const CAPEExplanation: React.FC<CAPEExplanationProps> = ({
  riskLevel,
  value,
  percentile,
  season
}) => {
  const threshold = CAPE_THRESHOLDS[riskLevel];

  const getRiskDescription = (level: RiskLevel) => {
    switch (level) {
      case 'LOW':
        return {
          description:
            'Minimal convective potential. Thunderstorm development unlikely.',
          details: [
            'Stable atmospheric conditions',
            'Low vertical motion and instability',
            'Generally clear to partly cloudy skies',
            'Minimal risk of severe weather'
          ]
        };
      case 'MODERATE':
        return {
          description:
            'Weak to moderate convective potential. Isolated thunderstorms possible.',
          details: [
            'Some atmospheric instability present',
            'Possible development of isolated storms',
            'Generally non-severe conditions',
            'Low to moderate precipitation potential'
          ]
        };
      case 'HIGH':
        return {
          description:
            'Strong convective potential. Widespread thunderstorms likely.',
          details: [
            'Significant atmospheric instability',
            'Favorable conditions for storm development',
            'Possible severe weather including heavy rain',
            'Increased risk of strong winds and hail'
          ]
        };
      case 'EXTREME':
        return {
          description:
            'Very high convective potential. Severe thunderstorms highly likely.',
          details: [
            'Extreme atmospheric instability',
            'Very high risk of severe weather',
            'Potential for supercells and tornadoes',
            'Dangerous conditions: large hail, damaging winds'
          ]
        };
    }
  };

  const riskInfo = getRiskDescription(riskLevel);

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='space-y-2'>
        <div className='flex items-center gap-2'>
          <div
            className={clsx(
              'w-4 h-4 rounded-full',
              threshold.color === 'green' && 'bg-emerald-500',
              threshold.color === 'yellow' && 'bg-yellow-500',
              threshold.color === 'orange' && 'bg-orange-500',
              threshold.color === 'red' && 'bg-red-500'
            )}
          />
          <h3 className='text-lg font-semibold text-slate-50'>
            {threshold.label} Risk Level
          </h3>
        </div>
        <p className='text-sm text-slate-400'>
          CAPE: {value.toLocaleString()} J/kg
        </p>
      </div>

      {/* Risk Description */}
      <div className='space-y-3'>
        <p className='text-slate-200 text-sm leading-relaxed'>
          {riskInfo.description}
        </p>

        <div className='space-y-2'>
          <h4 className='text-sm font-medium text-slate-300 flex items-center gap-2'>
            <AlertTriangle size={14} />
            Conditions
          </h4>
          <ul className='space-y-1 text-xs text-slate-400'>
            {riskInfo.details.map((detail, index) => (
              <li key={index} className='flex items-start gap-2'>
                <span className='w-1 h-1 bg-slate-500 rounded-full mt-1.5 flex-shrink-0' />
                {detail}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Historical Context */}
      {percentile !== undefined && season && (
        <div className='bg-slate-800/30 rounded-lg p-4 space-y-3'>
          <h4 className='text-sm font-medium text-slate-300 flex items-center gap-2'>
            <TrendingUp size={14} />
            Historical Context
          </h4>

          <div className='space-y-2'>
            <div className='flex items-center justify-between text-sm'>
              <span className='text-slate-400'>{season} Percentile</span>
              <span className='text-slate-200 font-mono'>
                {percentile.toFixed(0)}%
              </span>
            </div>

            <div className='w-full bg-slate-700 rounded-full h-2 overflow-hidden'>
              <div
                className={clsx(
                  'h-full transition-all duration-300',
                  percentile >= 90 && 'bg-red-500',
                  percentile >= 75 && percentile < 90 && 'bg-orange-500',
                  percentile >= 50 && percentile < 75 && 'bg-yellow-500',
                  percentile < 50 && 'bg-emerald-500'
                )}
                style={{ width: `${percentile}%` }}
              />
            </div>

            <p className='text-xs text-slate-500'>
              {percentile >= 90
                ? 'Extremely high for this season'
                : percentile >= 75
                  ? 'Well above average for this season'
                  : percentile >= 50
                    ? 'Above average for this season'
                    : 'Below average for this season'}
            </p>
          </div>
        </div>
      )}

      {/* CAPE Scale Reference */}
      <div className='bg-slate-800/30 rounded-lg p-4 space-y-3'>
        <h4 className='text-sm font-medium text-slate-300 flex items-center gap-2'>
          <Calendar size={14} />
          CAPE Scale Reference
        </h4>

        <div className='space-y-2'>
          {Object.entries(CAPE_THRESHOLDS).map(([level, info]) => (
            <div
              key={level}
              className={clsx(
                'flex items-center justify-between p-2 rounded',
                riskLevel === level ? 'bg-slate-700/50' : 'bg-transparent'
              )}
            >
              <div className='flex items-center gap-2'>
                <div
                  className={clsx(
                    'w-2 h-2 rounded-full',
                    info.color === 'green' && 'bg-emerald-500',
                    info.color === 'yellow' && 'bg-yellow-500',
                    info.color === 'orange' && 'bg-orange-500',
                    info.color === 'red' && 'bg-red-500'
                  )}
                />
                <span
                  className={clsx(
                    'text-sm',
                    riskLevel === level
                      ? 'text-slate-100 font-medium'
                      : 'text-slate-400'
                  )}
                >
                  {info.label}
                </span>
              </div>
              <span
                className={clsx(
                  'text-xs font-mono',
                  riskLevel === level ? 'text-slate-200' : 'text-slate-500'
                )}
              >
                {info.min === 0 ? '0' : info.min.toLocaleString()}
                {info.max === Infinity
                  ? '+'
                  : `–${info.max.toLocaleString()}`}{' '}
                J/kg
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Main CAPE Badge component
export const CAPEBadge: React.FC<CAPEBadgeProps> = ({
  value,
  percentile,
  season,
  size = 'md',
  showInfo = true,
  disableAnimations = false,
  className
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Determine risk level based on CAPE value
  const getRiskLevel = useCallback((capeValue: number): RiskLevel => {
    if (capeValue >= CAPE_THRESHOLDS.EXTREME.min) return 'EXTREME';
    if (capeValue >= CAPE_THRESHOLDS.HIGH.min) return 'HIGH';
    if (capeValue >= CAPE_THRESHOLDS.MODERATE.min) return 'MODERATE';
    return 'LOW';
  }, []);

  const riskLevel = getRiskLevel(value);
  const threshold = CAPE_THRESHOLDS[riskLevel];
  const isExtreme = riskLevel === 'EXTREME';

  // Size variants
  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base'
  };

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16
  };

  // Color classes based on risk level
  const colorClasses = {
    green: {
      bg: 'bg-emerald-600/20 border-emerald-600/40',
      text: 'text-emerald-400',
      hover: 'hover:bg-emerald-600/30'
    },
    yellow: {
      bg: 'bg-yellow-600/20 border-yellow-600/40',
      text: 'text-yellow-400',
      hover: 'hover:bg-yellow-600/30'
    },
    orange: {
      bg: 'bg-orange-600/20 border-orange-600/40',
      text: 'text-orange-400',
      hover: 'hover:bg-orange-600/30'
    },
    red: {
      bg: 'bg-red-600/20 border-red-600/40',
      text: 'text-red-400',
      hover: 'hover:bg-red-600/30'
    }
  };

  const colors = colorClasses[threshold.color];

  const handleOpenModal = useCallback(() => {
    setIsModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
  }, []);

  return (
    <>
      <motion.div
        className={clsx(
          'inline-flex items-center gap-2 rounded-lg border font-medium relative overflow-hidden',
          sizeClasses[size],
          colors.bg,
          colors.text,
          showInfo && 'cursor-pointer',
          showInfo && colors.hover,
          'transition-all duration-200',
          className
        )}
        onClick={showInfo ? handleOpenModal : undefined}
        whileHover={
          !disableAnimations && showInfo ? { scale: 1.02 } : undefined
        }
        whileTap={!disableAnimations && showInfo ? { scale: 0.98 } : undefined}
        role={showInfo ? 'button' : undefined}
        tabIndex={showInfo ? 0 : undefined}
        onKeyDown={
          showInfo
            ? e => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleOpenModal();
                }
              }
            : undefined
        }
        aria-label={`CAPE risk level: ${threshold.label}, ${value} J/kg${percentile ? `, ${percentile}th percentile for ${season}` : ''}`}
      >
        {/* Lightning animation for extreme levels */}
        {isExtreme && !disableAnimations && (
          <LightningAnimation animate={true} />
        )}

        <span className='font-semibold'>{threshold.label}</span>

        <span className='font-mono text-xs opacity-80'>
          {value.toLocaleString()}
        </span>

        {showInfo && <Info size={iconSizes[size]} className='opacity-60' />}
      </motion.div>

      {/* Modal Dialog */}
      {showInfo && (
        <Dialog.Root open={isModalOpen} onOpenChange={setIsModalOpen}>
          <Dialog.Portal>
            <Dialog.Overlay
              className='fixed inset-0 bg-black/50 backdrop-blur-sm z-50'
              onClick={handleCloseModal}
            />
            <Dialog.Content className='fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg mx-4 bg-[#0E1116] border border-[#2A2F3A] rounded-xl shadow-2xl z-50 max-h-[90vh] overflow-y-auto'>
              <div className='p-6'>
                {/* Close button */}
                <Dialog.Close className='absolute top-4 right-4 p-2 rounded-lg hover:bg-slate-800/50 transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500'>
                  <span className='sr-only'>Close</span>
                  <svg
                    width='16'
                    height='16'
                    viewBox='0 0 16 16'
                    fill='none'
                    className='text-slate-400'
                  >
                    <path
                      d='M12 4L4 12M4 4L12 12'
                      stroke='currentColor'
                      strokeWidth='2'
                      strokeLinecap='round'
                    />
                  </svg>
                </Dialog.Close>

                <CAPEExplanation
                  riskLevel={riskLevel}
                  value={value}
                  percentile={percentile}
                  season={season}
                />
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      )}
    </>
  );
};

export default CAPEBadge;
