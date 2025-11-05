'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, X, Play, Pause, RotateCcw, CheckCircle } from 'lucide-react';
import { tours, type TourStep } from '@/lib/helpContent';

interface TourOverlayProps {
  isActive: boolean;
  currentStep: TourStep | null;
  onNext: () => void;
  onPrevious: () => void;
  onSkip: () => void;
  onComplete: () => void;
  stepIndex: number;
  totalSteps: number;
  tourTitle: string;
}

/**
 * Tour Overlay Component
 * Creates a spotlight effect and positions tour content
 */
function TourOverlay({
  isActive,
  currentStep,
  onNext,
  onPrevious,
  onSkip,
  onComplete,
  stepIndex,
  totalSteps,
  tourTitle
}: TourOverlayProps) {
  const [targetElement, setTargetElement] = useState<HTMLElement | null>(null);
  const [spotlightPosition, setSpotlightPosition] = useState({ x: 0, y: 0, width: 0, height: 0 });
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (!currentStep || !isActive) {
      setTargetElement(null);
      return;
    }

    const element = document.querySelector(currentStep.target) as HTMLElement;
    if (element) {
      setTargetElement(element);
      
      // Calculate spotlight position
      const rect = element.getBoundingClientRect();
      const padding = 8;
      setSpotlightPosition({
        x: rect.left - padding,
        y: rect.top - padding,
        width: rect.width + padding * 2,
        height: rect.height + padding * 2
      });

      // Calculate tooltip position
      const placement = currentStep.placement || 'bottom';
      let tooltipX = rect.left;
      let tooltipY = rect.bottom + 16;

      if (placement === 'top') {
        tooltipY = rect.top - 16;
      } else if (placement === 'left') {
        tooltipX = rect.left - 16;
        tooltipY = rect.top;
      } else if (placement === 'right') {
        tooltipX = rect.right + 16;
        tooltipY = rect.top;
      }

      // Ensure tooltip stays within viewport
      const tooltipWidth = 320;
      const tooltipHeight = 200;
      
      if (tooltipX + tooltipWidth > window.innerWidth - 16) {
        tooltipX = window.innerWidth - tooltipWidth - 16;
      }
      if (tooltipX < 16) tooltipX = 16;
      
      if (tooltipY + tooltipHeight > window.innerHeight - 16) {
        tooltipY = window.innerHeight - tooltipHeight - 16;
      }
      if (tooltipY < 16) tooltipY = 16;

      setTooltipPosition({ x: tooltipX, y: tooltipY });

      // Scroll element into view if needed
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      
      // Add highlight effect
      element.style.position = 'relative';
      element.style.zIndex = '9999';
    }
  }, [currentStep, isActive]);

  useEffect(() => {
    // Handle window resize
    const handleResize = () => {
      if (targetElement && currentStep) {
        const rect = targetElement.getBoundingClientRect();
        const padding = 8;
        setSpotlightPosition({
          x: rect.left - padding,
          y: rect.top - padding,
          width: rect.width + padding * 2,
          height: rect.height + padding * 2
        });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [targetElement, currentStep]);

  if (!isActive || !currentStep) return null;

  const isFirstStep = stepIndex === 0;
  const isLastStep = stepIndex === totalSteps - 1;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[9998]"
        style={{ pointerEvents: 'none' }}
      >
        {/* Dark overlay with spotlight cutout */}
        <div
          className="absolute inset-0 bg-black/75"
          style={{
            clipPath: targetElement 
              ? `polygon(0% 0%, 0% 100%, ${spotlightPosition.x}px 100%, ${spotlightPosition.x}px ${spotlightPosition.y}px, ${spotlightPosition.x + spotlightPosition.width}px ${spotlightPosition.y}px, ${spotlightPosition.x + spotlightPosition.width}px ${spotlightPosition.y + spotlightPosition.height}px, ${spotlightPosition.x}px ${spotlightPosition.y + spotlightPosition.height}px, ${spotlightPosition.x}px 100%, 100% 100%, 100% 0%)`
              : 'none'
          }}
        />

        {/* Spotlight ring */}
        {targetElement && (
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="absolute border-2 border-cyan-400 rounded-lg"
            style={{
              left: spotlightPosition.x,
              top: spotlightPosition.y,
              width: spotlightPosition.width,
              height: spotlightPosition.height,
              boxShadow: '0 0 0 4px rgba(34, 211, 238, 0.2), 0 0 20px rgba(34, 211, 238, 0.3)'
            }}
          />
        )}

        {/* Tour tooltip */}
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: -10 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: -10 }}
          className="absolute bg-[#0E1116] border border-[#2A2F3A] rounded-xl shadow-2xl max-w-sm"
          style={{
            left: tooltipPosition.x,
            top: tooltipPosition.y,
            pointerEvents: 'auto'
          }}
        >
          {/* Header */}
          <div className="p-4 border-b border-[#2A2F3A]">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-slate-200">{tourTitle}</div>
              <button
                onClick={onSkip}
                className="p-1 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X size={14} className="text-slate-400" />
              </button>
            </div>
            <div className="flex items-center gap-2 mt-2">
              <div className="flex gap-1">
                {Array.from({ length: totalSteps }).map((_, i) => (
                  <div
                    key={i}
                    className={`w-2 h-2 rounded-full ${
                      i === stepIndex ? 'bg-cyan-400' : 
                      i < stepIndex ? 'bg-green-500' : 'bg-slate-600'
                    }`}
                  />
                ))}
              </div>
              <span className="text-xs text-slate-500">
                {stepIndex + 1} of {totalSteps}
              </span>
            </div>
          </div>

          {/* Content */}
          <div className="p-4">
            <h3 className="text-base font-medium text-slate-100 mb-2">
              {currentStep.title}
            </h3>
            <p className="text-sm text-slate-300 leading-relaxed mb-4">
              {currentStep.content}
            </p>

            {/* Action hint */}
            {currentStep.action && (
              <div className="p-2 bg-[#1C1F26] border border-[#2A2F3A] rounded-lg mb-4">
                <div className="text-xs text-slate-400">
                  Try: <span className="text-cyan-400">{currentStep.action}</span> the highlighted element
                </div>
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between p-4 border-t border-[#2A2F3A]">
            <button
              onClick={onPrevious}
              disabled={isFirstStep}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft size={14} />
              Back
            </button>

            <div className="flex items-center gap-2">
              <button
                onClick={onSkip}
                className="px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors"
              >
                Skip Tour
              </button>
              {isLastStep ? (
                <button
                  onClick={onComplete}
                  className="flex items-center gap-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg transition-colors"
                >
                  <CheckCircle size={14} />
                  Complete
                </button>
              ) : (
                <button
                  onClick={onNext}
                  className="flex items-center gap-1 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-700 text-white text-sm rounded-lg transition-colors"
                >
                  Next
                  <ChevronRight size={14} />
                </button>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

interface GuidedTourProps {
  tourId?: string;
  isActive: boolean;
  onComplete: () => void;
  onSkip: () => void;
}

/**
 * Guided Tour Component
 * Orchestrates interactive tours with step-by-step guidance
 */
export function GuidedTour({ tourId = 'newUser', isActive, onComplete, onSkip }: GuidedTourProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  
  const tour = tours[tourId as keyof typeof tours];
  const currentStep = tour?.steps[currentStepIndex] || null;

  useEffect(() => {
    if (isActive) {
      setCurrentStepIndex(0);
      setCompletedSteps(new Set());
      setIsPaused(false);
    }
  }, [isActive, tourId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isActive) return;

      switch (e.key) {
        case 'Escape':
          onSkip();
          break;
        case 'ArrowRight':
          if (currentStepIndex < tour.steps.length - 1) {
            handleNext();
          }
          break;
        case 'ArrowLeft':
          if (currentStepIndex > 0) {
            handlePrevious();
          }
          break;
        case ' ':
          e.preventDefault();
          setIsPaused(!isPaused);
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isActive, currentStepIndex, isPaused, tour, onSkip]);

  const handleNext = () => {
    if (!currentStep) return;

    const newCompletedSteps = new Set(completedSteps);
    newCompletedSteps.add(currentStep.id);
    setCompletedSteps(newCompletedSteps);

    if (currentStepIndex < tour.steps.length - 1) {
      setCurrentStepIndex(currentStepIndex + 1);
    } else {
      handleComplete();
    }
  };

  const handlePrevious = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(currentStepIndex - 1);
    }
  };

  const handleComplete = () => {
    // Save tour completion to localStorage
    const completedTours = JSON.parse(localStorage.getItem('completedTours') || '[]');
    if (!completedTours.includes(tourId)) {
      completedTours.push(tourId);
      localStorage.setItem('completedTours', JSON.stringify(completedTours));
    }
    
    onComplete();
  };

  const handleSkip = () => {
    onSkip();
  };

  const handleRestart = () => {
    setCurrentStepIndex(0);
    setCompletedSteps(new Set());
    setIsPaused(false);
  };

  if (!tour || !isActive) return null;

  return (
    <>
      <TourOverlay
        isActive={isActive && !isPaused}
        currentStep={currentStep}
        onNext={handleNext}
        onPrevious={handlePrevious}
        onSkip={handleSkip}
        onComplete={handleComplete}
        stepIndex={currentStepIndex}
        totalSteps={tour.steps.length}
        tourTitle={tour.title}
      />

      {/* Tour controls */}
      {isActive && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          className="fixed bottom-6 left-6 bg-[#0E1116] border border-[#2A2F3A] rounded-xl shadow-2xl p-4 z-[9999]"
        >
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsPaused(!isPaused)}
              className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
            >
              {isPaused ? <Play size={16} /> : <Pause size={16} />}
            </button>
            <button
              onClick={handleRestart}
              className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              title="Restart tour"
            >
              <RotateCcw size={16} />
            </button>
            <div className="text-sm text-slate-400">
              {isPaused ? 'Tour paused' : `Step ${currentStepIndex + 1} of ${tour.steps.length}`}
            </div>
          </div>
        </motion.div>
      )}
    </>
  );
}

interface TourManagerProps {
  children: React.ReactNode;
}

/**
 * Tour Manager Component
 * Manages tour state and provides tour controls
 */
export function TourManager({ children }: TourManagerProps) {
  const [activeTour, setActiveTour] = useState<string | null>(null);
  const [isFirstVisit, setIsFirstVisit] = useState(false);

  useEffect(() => {
    // Check if this is the user's first visit
    const hasVisited = localStorage.getItem('hasVisited');
    const completedTours = JSON.parse(localStorage.getItem('completedTours') || '[]');
    
    if (!hasVisited && !completedTours.includes('newUser')) {
      setIsFirstVisit(true);
      // Start tour after a brief delay
      setTimeout(() => {
        setActiveTour('newUser');
      }, 1000);
    }
    
    localStorage.setItem('hasVisited', 'true');
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+/ to toggle tour mode
      if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        if (activeTour) {
          setActiveTour(null);
        } else {
          setActiveTour('newUser');
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [activeTour]);

  const startTour = (tourId: string) => {
    setActiveTour(tourId);
  };

  const stopTour = () => {
    setActiveTour(null);
  };

  return (
    <>
      {children}
      
      <GuidedTour
        tourId={activeTour || 'newUser'}
        isActive={!!activeTour}
        onComplete={stopTour}
        onSkip={stopTour}
      />

      {/* Global tour trigger (hidden, for programmatic access) */}
      <div 
        id="tour-manager"
        data-start-tour={(tourId: string) => startTour(tourId)}
        style={{ display: 'none' }}
      />
    </>
  );
}

// Export tour management functions for external use
export const tourManager = {
  startTour: (tourId: string) => {
    const element = document.getElementById('tour-manager') as any;
    if (element?.dataset?.startTour) {
      element.dataset.startTour(tourId);
    }
  },
  
  getAvailableTours: () => Object.keys(tours),
  
  isCompleted: (tourId: string) => {
    const completedTours = JSON.parse(localStorage.getItem('completedTours') || '[]');
    return completedTours.includes(tourId);
  },
  
  markCompleted: (tourId: string) => {
    const completedTours = JSON.parse(localStorage.getItem('completedTours') || '[]');
    if (!completedTours.includes(tourId)) {
      completedTours.push(tourId);
      localStorage.setItem('completedTours', JSON.stringify(completedTours));
    }
  }
};