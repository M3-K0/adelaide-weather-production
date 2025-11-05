'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BookOpen, 
  MessageCircle, 
  Star, 
  ThumbsUp, 
  ThumbsDown, 
  Send,
  Video,
  FileText,
  Search,
  Filter,
  Clock,
  Tag,
  ChevronDown,
  ExternalLink
} from 'lucide-react';
import { 
  helpArticles, 
  faqs, 
  searchHelpContent,
  type HelpArticle,
  type FAQ 
} from '@/lib/helpContent';

interface HelpSystemProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: 'articles' | 'faq' | 'videos' | 'feedback';
}

interface FeedbackData {
  type: 'bug' | 'feature' | 'content' | 'general';
  rating: number;
  message: string;
  email?: string;
  page: string;
  timestamp: string;
}

/**
 * Main Help System Component
 * Comprehensive help interface with articles, FAQs, videos, and feedback
 */
export function HelpSystem({ isOpen, onClose, initialTab = 'articles' }: HelpSystemProps) {
  const [activeTab, setActiveTab] = useState(initialTab);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');
  const [expandedFAQ, setExpandedFAQ] = useState<string | null>(null);
  const [helpfulFeedback, setHelpfulFeedback] = useState<Record<string, boolean>>({});
  const [contentRatings, setContentRatings] = useState<Record<string, number>>({});

  // Feedback form state
  const [feedbackForm, setFeedbackForm] = useState({
    type: 'general' as FeedbackData['type'],
    rating: 0,
    message: '',
    email: ''
  });
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  // Filter and search functionality
  useEffect(() => {
    if (searchQuery.length > 0) {
      const results = searchHelpContent(searchQuery);
      setSearchResults(results);
    } else {
      setSearchResults([]);
    }
  }, [searchQuery]);

  // Load saved feedback state
  useEffect(() => {
    const savedFeedback = localStorage.getItem('helpFeedback');
    const savedRatings = localStorage.getItem('contentRatings');
    
    if (savedFeedback) {
      setHelpfulFeedback(JSON.parse(savedFeedback));
    }
    if (savedRatings) {
      setContentRatings(JSON.parse(savedRatings));
    }
  }, []);

  // Filter articles and FAQs
  const filteredArticles = helpArticles.filter(article => {
    const categoryMatch = selectedCategory === 'all' || article.category === selectedCategory;
    const difficultyMatch = selectedDifficulty === 'all' || article.difficulty === selectedDifficulty;
    return categoryMatch && difficultyMatch;
  });

  const filteredFAQs = faqs.filter(faq => {
    const categoryMatch = selectedCategory === 'all' || faq.category === selectedCategory;
    return categoryMatch;
  });

  const categories = ['all', ...Array.from(new Set(helpArticles.map(a => a.category)))];
  const difficulties = ['all', 'beginner', 'intermediate', 'advanced'];

  const handleFeedbackSubmit = () => {
    const feedback: FeedbackData = {
      ...feedbackForm,
      page: window.location.pathname,
      timestamp: new Date().toISOString()
    };

    // In a real app, this would be sent to an API
    console.log('Feedback submitted:', feedback);
    
    // Save to localStorage for demo
    const existingFeedback = JSON.parse(localStorage.getItem('submittedFeedback') || '[]');
    existingFeedback.push(feedback);
    localStorage.setItem('submittedFeedback', JSON.stringify(existingFeedback));

    setFeedbackSubmitted(true);
    setTimeout(() => {
      setFeedbackSubmitted(false);
      setFeedbackForm({ type: 'general', rating: 0, message: '', email: '' });
    }, 3000);
  };

  const handleHelpfulClick = (id: string, helpful: boolean) => {
    const newFeedback = { ...helpfulFeedback, [id]: helpful };
    setHelpfulFeedback(newFeedback);
    localStorage.setItem('helpFeedback', JSON.stringify(newFeedback));
  };

  const handleRating = (id: string, rating: number) => {
    const newRatings = { ...contentRatings, [id]: rating };
    setContentRatings(newRatings);
    localStorage.setItem('contentRatings', JSON.stringify(newRatings));
  };

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
          className="bg-[#0E1116] border border-[#2A2F3A] rounded-xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Sidebar */}
          <div className="w-64 bg-[#1C1F26] border-r border-[#2A2F3A] flex flex-col">
            <div className="p-6 border-b border-[#2A2F3A]">
              <h2 className="text-xl font-semibold text-slate-100">Help Center</h2>
              <p className="text-sm text-slate-400 mt-1">Find answers and get support</p>
            </div>

            <nav className="flex-1 p-4">
              <div className="space-y-2">
                {[
                  { id: 'articles', label: 'Help Articles', icon: BookOpen, count: filteredArticles.length },
                  { id: 'faq', label: 'FAQ', icon: MessageCircle, count: filteredFAQs.length },
                  { id: 'videos', label: 'Video Guides', icon: Video, count: 3 },
                  { id: 'feedback', label: 'Feedback', icon: Send, count: null }
                ].map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                        activeTab === tab.id
                          ? 'bg-cyan-600 text-white'
                          : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800'
                      }`}
                    >
                      <Icon size={18} />
                      <span className="flex-1">{tab.label}</span>
                      {tab.count !== null && (
                        <span className="text-xs bg-slate-700 px-2 py-1 rounded">
                          {tab.count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </nav>

            {/* Quick Actions */}
            <div className="p-4 border-t border-[#2A2F3A]">
              <div className="space-y-2">
                <button className="w-full text-left text-sm text-slate-400 hover:text-slate-300 transition-colors">
                  Start Guided Tour
                </button>
                <button className="w-full text-left text-sm text-slate-400 hover:text-slate-300 transition-colors">
                  Keyboard Shortcuts
                </button>
                <button className="w-full text-left text-sm text-slate-400 hover:text-slate-300 transition-colors">
                  Contact Support
                </button>
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 flex flex-col">
            {/* Header with Search and Filters */}
            <div className="p-6 border-b border-[#2A2F3A]">
              <div className="flex items-center gap-4 mb-4">
                <div className="relative flex-1">
                  <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search help content..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 bg-[#1C1F26] border border-[#2A2F3A] rounded-lg text-slate-100 placeholder-slate-400 focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-slate-800 transition-colors"
                >
                  ✕
                </button>
              </div>

              {(activeTab === 'articles' || activeTab === 'faq') && (
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Filter size={14} className="text-slate-400" />
                    <select
                      value={selectedCategory}
                      onChange={(e) => setSelectedCategory(e.target.value)}
                      className="bg-[#1C1F26] border border-[#2A2F3A] rounded px-3 py-1 text-sm text-slate-200"
                    >
                      {categories.map(cat => (
                        <option key={cat} value={cat}>{cat === 'all' ? 'All Categories' : cat}</option>
                      ))}
                    </select>
                  </div>
                  {activeTab === 'articles' && (
                    <select
                      value={selectedDifficulty}
                      onChange={(e) => setSelectedDifficulty(e.target.value)}
                      className="bg-[#1C1F26] border border-[#2A2F3A] rounded px-3 py-1 text-sm text-slate-200"
                    >
                      {difficulties.map(diff => (
                        <option key={diff} value={diff}>{diff === 'all' ? 'All Levels' : diff}</option>
                      ))}
                    </select>
                  )}
                </div>
              )}
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Search Results */}
              {searchQuery && searchResults.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-slate-200 mb-3">
                    Search Results ({searchResults.length})
                  </h3>
                  <div className="space-y-3">
                    {searchResults.map((result, index) => (
                      <div key={index} className="p-4 bg-[#1C1F26] border border-[#2A2F3A] rounded-lg hover:bg-slate-800 transition-colors cursor-pointer">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="text-sm font-medium text-slate-200">{result.title}</div>
                            <div className="text-xs text-slate-400 mt-1">{result.content}</div>
                          </div>
                          <span className="text-xs text-slate-500 bg-slate-700 px-2 py-1 rounded ml-2">
                            {result.type}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Help Articles */}
              {activeTab === 'articles' && (
                <div className="space-y-4">
                  <h3 className="text-lg font-medium text-slate-200">Help Articles</h3>
                  {filteredArticles.map((article) => (
                    <div key={article.id} className="bg-[#1C1F26] border border-[#2A2F3A] rounded-lg p-6">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <h4 className="text-base font-medium text-slate-100 mb-2">{article.title}</h4>
                          <div className="flex items-center gap-3 text-xs text-slate-400">
                            <span className="flex items-center gap-1">
                              <Tag size={12} />
                              {article.category}
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock size={12} />
                              {article.lastUpdated}
                            </span>
                            <span className={`px-2 py-1 rounded ${
                              article.difficulty === 'beginner' ? 'bg-green-900 text-green-300' :
                              article.difficulty === 'intermediate' ? 'bg-yellow-900 text-yellow-300' :
                              'bg-red-900 text-red-300'
                            }`}>
                              {article.difficulty}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="prose prose-invert prose-sm max-w-none mb-4">
                        <div className="text-slate-300 text-sm leading-relaxed">
                          {article.content.substring(0, 300)}...
                        </div>
                      </div>

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-slate-500">Was this helpful?</span>
                          <button
                            onClick={() => handleHelpfulClick(article.id, true)}
                            className={`p-1 rounded ${
                              helpfulFeedback[article.id] === true 
                                ? 'bg-green-600 text-white' 
                                : 'text-slate-400 hover:text-green-400'
                            }`}
                          >
                            <ThumbsUp size={12} />
                          </button>
                          <button
                            onClick={() => handleHelpfulClick(article.id, false)}
                            className={`p-1 rounded ${
                              helpfulFeedback[article.id] === false 
                                ? 'bg-red-600 text-white' 
                                : 'text-slate-400 hover:text-red-400'
                            }`}
                          >
                            <ThumbsDown size={12} />
                          </button>
                        </div>

                        <div className="flex items-center gap-1">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              onClick={() => handleRating(article.id, star)}
                              className={`${
                                (contentRatings[article.id] || 0) >= star
                                  ? 'text-yellow-400'
                                  : 'text-slate-600'
                              } hover:text-yellow-400 transition-colors`}
                            >
                              <Star size={12} fill="currentColor" />
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* FAQ Section */}
              {activeTab === 'faq' && (
                <div className="space-y-4">
                  <h3 className="text-lg font-medium text-slate-200">Frequently Asked Questions</h3>
                  {filteredFAQs.map((faq) => (
                    <div key={faq.id} className="bg-[#1C1F26] border border-[#2A2F3A] rounded-lg">
                      <button
                        onClick={() => setExpandedFAQ(expandedFAQ === faq.id ? null : faq.id)}
                        className="w-full p-4 text-left flex items-center justify-between hover:bg-slate-800 transition-colors"
                      >
                        <span className="font-medium text-slate-200">{faq.question}</span>
                        <ChevronDown
                          size={16}
                          className={`text-slate-400 transition-transform ${
                            expandedFAQ === faq.id ? 'rotate-180' : ''
                          }`}
                        />
                      </button>
                      <AnimatePresence>
                        {expandedFAQ === faq.id && (
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: 'auto' }}
                            exit={{ height: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="p-4 pt-0 border-t border-[#2A2F3A]">
                              <p className="text-slate-300 text-sm leading-relaxed mb-3">
                                {faq.answer}
                              </p>
                              <div className="flex items-center justify-between">
                                <div className="flex flex-wrap gap-1">
                                  {faq.tags.map((tag) => (
                                    <span
                                      key={tag}
                                      className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded"
                                    >
                                      {tag}
                                    </span>
                                  ))}
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-xs text-slate-500">Helpful?</span>
                                  <button
                                    onClick={() => handleHelpfulClick(faq.id, true)}
                                    className={`p-1 rounded ${
                                      helpfulFeedback[faq.id] === true 
                                        ? 'bg-green-600 text-white' 
                                        : 'text-slate-400 hover:text-green-400'
                                    }`}
                                  >
                                    <ThumbsUp size={12} />
                                  </button>
                                  <button
                                    onClick={() => handleHelpfulClick(faq.id, false)}
                                    className={`p-1 rounded ${
                                      helpfulFeedback[faq.id] === false 
                                        ? 'bg-red-600 text-white' 
                                        : 'text-slate-400 hover:text-red-400'
                                    }`}
                                  >
                                    <ThumbsDown size={12} />
                                  </button>
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  ))}
                </div>
              )}

              {/* Video Guides */}
              {activeTab === 'videos' && (
                <div className="space-y-4">
                  <h3 className="text-lg font-medium text-slate-200">Video Guides</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[
                      {
                        title: 'Getting Started with Adelaide Weather',
                        duration: '5:32',
                        thumbnail: '/video-thumbnails/getting-started.jpg',
                        description: 'Complete walkthrough of the forecasting system interface and basic features.'
                      },
                      {
                        title: 'Understanding Analog Ensemble Forecasts',
                        duration: '8:15',
                        thumbnail: '/video-thumbnails/analog-ensemble.jpg',
                        description: 'Deep dive into analog ensemble methodology and how to interpret results.'
                      },
                      {
                        title: 'Advanced Features and Troubleshooting',
                        duration: '12:04',
                        thumbnail: '/video-thumbnails/advanced.jpg',
                        description: 'Expert tips for using advanced features and solving common issues.'
                      }
                    ].map((video, index) => (
                      <div key={index} className="bg-[#1C1F26] border border-[#2A2F3A] rounded-lg overflow-hidden">
                        <div className="aspect-video bg-slate-800 flex items-center justify-center">
                          <Video size={32} className="text-slate-600" />
                        </div>
                        <div className="p-4">
                          <div className="flex items-start justify-between mb-2">
                            <h4 className="font-medium text-slate-200">{video.title}</h4>
                            <span className="text-xs text-slate-500 bg-slate-700 px-2 py-1 rounded">
                              {video.duration}
                            </span>
                          </div>
                          <p className="text-sm text-slate-400 mb-3">{video.description}</p>
                          <button className="flex items-center gap-2 text-cyan-400 hover:text-cyan-300 text-sm">
                            <ExternalLink size={14} />
                            Watch Video
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Feedback Form */}
              {activeTab === 'feedback' && (
                <div className="max-w-2xl">
                  <h3 className="text-lg font-medium text-slate-200 mb-4">Feedback & Support</h3>
                  
                  {feedbackSubmitted ? (
                    <div className="bg-green-900/50 border border-green-700 rounded-lg p-6 text-center">
                      <div className="text-green-400 mb-2">Thank you for your feedback!</div>
                      <div className="text-green-300 text-sm">
                        We appreciate your input and will use it to improve the system.
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      <div>
                        <label className="block text-sm font-medium text-slate-200 mb-2">
                          Feedback Type
                        </label>
                        <select
                          value={feedbackForm.type}
                          onChange={(e) => setFeedbackForm(prev => ({ ...prev, type: e.target.value as any }))}
                          className="w-full bg-[#1C1F26] border border-[#2A2F3A] rounded-lg px-3 py-2 text-slate-200"
                        >
                          <option value="general">General Feedback</option>
                          <option value="bug">Bug Report</option>
                          <option value="feature">Feature Request</option>
                          <option value="content">Documentation Issue</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-200 mb-2">
                          Overall Rating
                        </label>
                        <div className="flex items-center gap-1">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              onClick={() => setFeedbackForm(prev => ({ ...prev, rating: star }))}
                              className={`${
                                feedbackForm.rating >= star
                                  ? 'text-yellow-400'
                                  : 'text-slate-600'
                              } hover:text-yellow-400 transition-colors`}
                            >
                              <Star size={24} fill="currentColor" />
                            </button>
                          ))}
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-200 mb-2">
                          Message
                        </label>
                        <textarea
                          value={feedbackForm.message}
                          onChange={(e) => setFeedbackForm(prev => ({ ...prev, message: e.target.value }))}
                          placeholder="Tell us about your experience, report a bug, or suggest an improvement..."
                          rows={6}
                          className="w-full bg-[#1C1F26] border border-[#2A2F3A] rounded-lg px-3 py-2 text-slate-200 placeholder-slate-400 focus:border-cyan-500 focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-200 mb-2">
                          Email (optional)
                        </label>
                        <input
                          type="email"
                          value={feedbackForm.email}
                          onChange={(e) => setFeedbackForm(prev => ({ ...prev, email: e.target.value }))}
                          placeholder="your.email@example.com"
                          className="w-full bg-[#1C1F26] border border-[#2A2F3A] rounded-lg px-3 py-2 text-slate-200 placeholder-slate-400 focus:border-cyan-500 focus:outline-none"
                        />
                      </div>

                      <button
                        onClick={handleFeedbackSubmit}
                        disabled={!feedbackForm.message.trim()}
                        className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                      >
                        <Send size={16} />
                        Submit Feedback
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}