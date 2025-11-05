'use client';

import React, { useState, useEffect } from 'react';
import * as Tooltip from '@radix-ui/react-tooltip';
import { HelpCircle, Keyboard, Search, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  tooltips, 
  keyboardShortcuts, 
  searchHelpContent, 
  type HelpTooltip 
} from '@/lib/helpContent';

interface SmartTooltipProps {
  id: string;
  children: React.ReactNode;
  disabled?: boolean;
  className?: string;
}

/**
 * Smart Tooltip Component
 * Provides contextual help with keyboard navigation support
 */
export function SmartTooltip({ id, children, disabled = false, className }: SmartTooltipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const tooltipData = tooltips[id];

  if (!tooltipData || disabled) {
    return <>{children}</>;
  }

  return (
    <Tooltip.Provider delayDuration={500}>
      <Tooltip.Root open={isOpen} onOpenChange={setIsOpen}>
        <Tooltip.Trigger asChild className={className}>
          <div 
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setIsOpen(!isOpen);
              }
            }}
          >
            {children}
          </div>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            side={tooltipData.placement || 'top'}
            sideOffset={8}
            className="max-w-xs p-3 bg-slate-800 border border-slate-600 rounded-lg shadow-xl z-50"
          >
            <div className="space-y-2">
              <div className="font-medium text-slate-100 text-sm">
                {tooltipData.title}
              </div>
              <div className="text-slate-300 text-xs leading-relaxed">
                {tooltipData.content}
              </div>
              {tooltipData.shortcut && (
                <div className="flex items-center gap-1 pt-1 border-t border-slate-600">
                  <Keyboard size={10} className="text-slate-500" />
                  <span className="text-[10px] text-slate-500 font-mono">
                    {tooltipData.shortcut}
                  </span>
                </div>
              )}
            </div>
            <Tooltip.Arrow className="fill-slate-800" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

interface HelpPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Contextual Help Panel
 * Provides search, shortcuts, and quick help access
 */
export function HelpPanel({ isOpen, onClose }: HelpPanelProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [activeCategory, setActiveCategory] = useState<'shortcuts' | 'search' | 'quick'>('quick');

  useEffect(() => {
    if (searchQuery.length > 2) {
      const results = searchHelpContent(searchQuery);
      setSearchResults(results.slice(0, 8)); // Limit to 8 results
      setActiveCategory('search');
    } else {
      setSearchResults([]);
      if (activeCategory === 'search') {
        setActiveCategory('quick');
      }
    }
  }, [searchQuery, activeCategory]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-[#0E1116] border border-[#2A2F3A] rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-[#2A2F3A]">
            <div className="flex items-center gap-3">
              <HelpCircle size={20} className="text-cyan-400" />
              <h2 className="text-lg font-medium text-slate-100">Help & Support</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <X size={16} className="text-slate-400" />
            </button>
          </div>

          {/* Search */}
          <div className="p-6 border-b border-[#2A2F3A]">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search help content..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-[#1C1F26] border border-[#2A2F3A] rounded-lg text-slate-100 placeholder-slate-400 focus:border-cyan-500 focus:outline-none"
                autoFocus
              />
            </div>
          </div>

          {/* Category Tabs */}
          <div className="flex border-b border-[#2A2F3A]">
            {[
              { id: 'quick', label: 'Quick Help' },
              { id: 'shortcuts', label: 'Shortcuts' },
              { id: 'search', label: `Search${searchResults.length > 0 ? ` (${searchResults.length})` : ''}` }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveCategory(tab.id as any)}
                className={`px-6 py-3 text-sm font-medium transition-colors ${
                  activeCategory === tab.id
                    ? 'text-cyan-400 border-b-2 border-cyan-400'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="p-6 max-h-96 overflow-y-auto">
            {activeCategory === 'quick' && (
              <div className="space-y-4">
                <div>
                  <h3 className="text-sm font-medium text-slate-200 mb-2">Quick Actions</h3>
                  <div className="grid grid-cols-2 gap-2">
                    <button className="p-3 bg-[#1C1F26] border border-[#2A2F3A] rounded-lg text-left hover:bg-slate-800 transition-colors">
                      <div className="text-sm text-slate-200">Start Tour</div>
                      <div className="text-xs text-slate-400">New user guide</div>
                    </button>
                    <button className="p-3 bg-[#1C1F26] border border-[#2A2F3A] rounded-lg text-left hover:bg-slate-800 transition-colors">
                      <div className="text-sm text-slate-200">View Shortcuts</div>
                      <div className="text-xs text-slate-400">Keyboard commands</div>
                    </button>
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-slate-200 mb-2">Common Questions</h3>
                  <div className="space-y-2">
                    <div className="p-3 bg-[#1C1F26] border border-[#2A2F3A] rounded-lg">
                      <div className="text-sm text-slate-200">How do I interpret confidence levels?</div>
                      <div className="text-xs text-slate-400 mt-1">
                        Confidence above 70% is reliable, below 50% indicates high uncertainty.
                      </div>
                    </div>
                    <div className="p-3 bg-[#1C1F26] border border-[#2A2F3A] rounded-lg">
                      <div className="text-sm text-slate-200">What does analog count mean?</div>
                      <div className="text-xs text-slate-400 mt-1">
                        Number of historical patterns similar to current conditions.
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeCategory === 'shortcuts' && (
              <div className="space-y-4">
                {Object.entries(keyboardShortcuts).map(([category, shortcuts]) => (
                  <div key={category}>
                    <h3 className="text-sm font-medium text-slate-200 mb-2 capitalize">
                      {category}
                    </h3>
                    <div className="space-y-1">
                      {shortcuts.map((shortcut, index) => (
                        <div key={index} className="flex items-center justify-between p-2 bg-[#1C1F26] rounded-lg">
                          <span className="text-sm text-slate-300">{shortcut.description}</span>
                          <kbd className="px-2 py-1 bg-slate-700 text-slate-300 rounded text-xs font-mono">
                            {shortcut.key}
                          </kbd>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeCategory === 'search' && (
              <div className="space-y-2">
                {searchResults.length === 0 && searchQuery.length > 2 && (
                  <div className="text-center py-8 text-slate-400">
                    No results found for "{searchQuery}"
                  </div>
                )}
                {searchResults.length === 0 && searchQuery.length <= 2 && (
                  <div className="text-center py-8 text-slate-400">
                    Enter at least 3 characters to search
                  </div>
                )}
                {searchResults.map((result, index) => (
                  <div key={index} className="p-3 bg-[#1C1F26] border border-[#2A2F3A] rounded-lg hover:bg-slate-800 transition-colors cursor-pointer">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="text-sm text-slate-200 font-medium">{result.title}</div>
                        <div className="text-xs text-slate-400 mt-1 line-clamp-2">{result.content}</div>
                      </div>
                      <span className="text-xs text-slate-500 bg-slate-700 px-2 py-1 rounded ml-2">
                        {result.type}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

interface HelpButtonProps {
  onClick: () => void;
  className?: string;
}

/**
 * Help Button Component
 * Floating help button with keyboard shortcut support
 */
export function HelpButton({ onClick, className }: HelpButtonProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.key === '?' && !e.shiftKey) || e.key === 'F1') {
        e.preventDefault();
        onClick();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClick]);

  return (
    <button
      onClick={onClick}
      className={`fixed bottom-6 right-6 p-3 bg-cyan-600 hover:bg-cyan-700 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-200 z-40 ${className}`}
      title="Help & Support (Press ? or F1)"
    >
      <HelpCircle size={20} />
    </button>
  );
}

interface ProgressiveDisclosureProps {
  level: 'basic' | 'intermediate' | 'advanced';
  children: React.ReactNode;
  title: string;
  description?: string;
}

/**
 * Progressive Disclosure Component
 * Shows information based on user expertise level
 */
export function ProgressiveDisclosure({ level, children, title, description }: ProgressiveDisclosureProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [userLevel, setUserLevel] = useState<'basic' | 'intermediate' | 'advanced'>('basic');

  // In a real app, this would come from user preferences
  useEffect(() => {
    const savedLevel = localStorage.getItem('userExpertiseLevel') as any;
    if (savedLevel) {
      setUserLevel(savedLevel);
    }
  }, []);

  const shouldShowByDefault = () => {
    const levels = { basic: 0, intermediate: 1, advanced: 2 };
    return levels[userLevel] >= levels[level];
  };

  return (
    <div className="border border-[#2A2F3A] rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-3 bg-[#1C1F26] hover:bg-slate-800 transition-colors text-left flex items-center justify-between"
      >
        <div>
          <div className="text-sm font-medium text-slate-200">{title}</div>
          {description && (
            <div className="text-xs text-slate-400 mt-1">{description}</div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-1 rounded ${
            level === 'basic' ? 'bg-green-900 text-green-300' :
            level === 'intermediate' ? 'bg-yellow-900 text-yellow-300' :
            'bg-red-900 text-red-300'
          }`}>
            {level}
          </span>
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            ▼
          </motion.div>
        </div>
      </button>
      <AnimatePresence>
        {(isExpanded || shouldShowByDefault()) && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="p-3 bg-[#0E1116] border-t border-[#2A2F3A]">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}