import { useState, useEffect, useCallback, useRef } from 'react';
import { ForecastHorizon, AnimationState } from '../types';

interface UseAnimationProps {
  horizons: ForecastHorizon[];
  speed: number;
  onHorizonChange: (horizon: ForecastHorizon) => void;
}

interface UseAnimationReturn {
  animationState: AnimationState;
  startAnimation: () => void;
  stopAnimation: () => void;
  setHorizon: (horizon: ForecastHorizon) => void;
  setSpeed: (speed: number) => void;
}

export const useAnimation = ({
  horizons,
  speed,
  onHorizonChange
}: UseAnimationProps): UseAnimationReturn => {
  const [animationState, setAnimationState] = useState<AnimationState>({
    isPlaying: false,
    currentHorizon: horizons[0]?.hours || 6,
    speed: speed,
    direction: 'forward'
  });

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentIndexRef = useRef(0);

  // Start animation
  const startAnimation = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    setAnimationState(prev => ({ ...prev, isPlaying: true }));

    intervalRef.current = setInterval(() => {
      setAnimationState(prev => {
        let nextIndex = currentIndexRef.current;
        
        if (prev.direction === 'forward') {
          nextIndex++;
          if (nextIndex >= horizons.length) {
            nextIndex = horizons.length - 1;
            // Reverse direction at the end
            return {
              ...prev,
              direction: 'backward'
            };
          }
        } else {
          nextIndex--;
          if (nextIndex < 0) {
            nextIndex = 0;
            // Reverse direction at the beginning
            return {
              ...prev,
              direction: 'forward'
            };
          }
        }

        currentIndexRef.current = nextIndex;
        const newHorizon = horizons[nextIndex];
        
        // Notify parent component of horizon change
        onHorizonChange(newHorizon);

        return {
          ...prev,
          currentHorizon: newHorizon.hours
        };
      });
    }, animationState.speed);
  }, [horizons, onHorizonChange, animationState.speed]);

  // Stop animation
  const stopAnimation = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    setAnimationState(prev => ({ ...prev, isPlaying: false }));
  }, []);

  // Set specific horizon (stops animation)
  const setHorizon = useCallback((horizon: ForecastHorizon) => {
    stopAnimation();
    
    const index = horizons.findIndex(h => h.hours === horizon.hours);
    if (index !== -1) {
      currentIndexRef.current = index;
      setAnimationState(prev => ({
        ...prev,
        currentHorizon: horizon.hours,
        isPlaying: false
      }));
    }
  }, [horizons, stopAnimation]);

  // Set animation speed
  const setSpeed = useCallback((newSpeed: number) => {
    setAnimationState(prev => ({ ...prev, speed: newSpeed }));
    
    // Restart animation with new speed if currently playing
    if (animationState.isPlaying) {
      stopAnimation();
      setTimeout(() => startAnimation(), 50);
    }
  }, [animationState.isPlaying, startAnimation, stopAnimation]);

  // Update speed when prop changes
  useEffect(() => {
    setAnimationState(prev => ({ ...prev, speed }));
  }, [speed]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Progressive animation with smooth transitions
  const createProgressiveAnimation = useCallback((targetHorizon: ForecastHorizon) => {
    const currentIndex = currentIndexRef.current;
    const targetIndex = horizons.findIndex(h => h.hours === targetHorizon.hours);
    
    if (targetIndex === -1 || currentIndex === targetIndex) return;

    const step = targetIndex > currentIndex ? 1 : -1;
    const steps = Math.abs(targetIndex - currentIndex);
    
    let stepCount = 0;
    const stepInterval = setInterval(() => {
      stepCount++;
      const nextIndex = currentIndex + (step * stepCount);
      
      if (nextIndex >= 0 && nextIndex < horizons.length) {
        currentIndexRef.current = nextIndex;
        const nextHorizon = horizons[nextIndex];
        
        setAnimationState(prev => ({
          ...prev,
          currentHorizon: nextHorizon.hours
        }));
        
        onHorizonChange(nextHorizon);
      }
      
      if (stepCount >= steps) {
        clearInterval(stepInterval);
      }
    }, animationState.speed / 4); // Faster steps for smooth transition
  }, [horizons, onHorizonChange, animationState.speed]);

  // Enhanced animation with easing
  const startSmoothAnimation = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    setAnimationState(prev => ({ ...prev, isPlaying: true }));

    let progress = 0;
    const totalDuration = animationState.speed * horizons.length;
    const frameRate = 60; // 60 FPS
    const frameInterval = 1000 / frameRate;

    intervalRef.current = setInterval(() => {
      progress += frameInterval;
      const normalizedProgress = (progress % totalDuration) / totalDuration;
      
      // Easing function for smooth animation
      const easedProgress = 0.5 * (1 - Math.cos(normalizedProgress * Math.PI * 2));
      const horizonIndex = Math.floor(easedProgress * horizons.length);
      
      if (horizonIndex !== currentIndexRef.current && horizonIndex < horizons.length) {
        currentIndexRef.current = horizonIndex;
        const newHorizon = horizons[horizonIndex];
        
        setAnimationState(prev => ({
          ...prev,
          currentHorizon: newHorizon.hours
        }));
        
        onHorizonChange(newHorizon);
      }
    }, frameInterval);
  }, [horizons, onHorizonChange, animationState.speed]);

  return {
    animationState,
    startAnimation,
    stopAnimation,
    setHorizon,
    setSpeed
  };
};