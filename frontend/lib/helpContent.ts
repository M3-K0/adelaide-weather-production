/**
 * Help Content Library for Adelaide Weather Forecasting System
 * Centralized repository for all help text, tooltips, tours, and documentation
 */

export interface HelpTooltip {
  id: string;
  title: string;
  content: string;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  shortcut?: string;
}

export interface TourStep {
  id: string;
  target: string;
  title: string;
  content: string;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  action?: 'click' | 'hover' | 'focus';
  delay?: number;
}

export interface HelpArticle {
  id: string;
  title: string;
  category: string;
  content: string;
  tags: string[];
  lastUpdated: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
}

export interface FAQ {
  id: string;
  question: string;
  answer: string;
  category: string;
  tags: string[];
}

// Contextual tooltips for UI elements
export const tooltips: Record<string, HelpTooltip> = {
  // Navigation tooltips
  'nav-dashboard': {
    id: 'nav-dashboard',
    title: 'Dashboard',
    content: 'View all forecast horizons and system status at a glance. This is your main operational view.',
    placement: 'right',
    shortcut: '1'
  },
  'nav-details': {
    id: 'nav-details',
    title: 'Forecast Details',
    content: 'Detailed analysis of forecast models, uncertainty bands, and analog patterns.',
    placement: 'right',
    shortcut: '2'
  },
  'nav-status': {
    id: 'nav-status',
    title: 'System Status',
    content: 'Monitor system health, model performance, and data availability.',
    placement: 'right',
    shortcut: '3'
  },
  'nav-about': {
    id: 'nav-about',
    title: 'About System',
    content: 'Learn about the analog ensemble methodology and system capabilities.',
    placement: 'right',
    shortcut: '4'
  },

  // Forecast card tooltips
  'forecast-horizon': {
    id: 'forecast-horizon',
    title: 'Forecast Horizon',
    content: 'Time ahead from now. Use the slider to adjust the forecast horizon between 1-48 hours.',
    placement: 'top'
  },
  'forecast-temperature': {
    id: 'forecast-temperature',
    title: 'Temperature Forecast',
    content: 'Central value from analog ensemble with uncertainty bounds (P05-P95 percentiles).',
    placement: 'top'
  },
  'forecast-confidence': {
    id: 'forecast-confidence',
    title: 'Forecast Confidence',
    content: 'Confidence percentage based on analog similarity and ensemble spread. Higher is better.',
    placement: 'top'
  },
  'forecast-wind': {
    id: 'forecast-wind',
    title: 'Wind Forecast',
    content: 'Wind speed and direction calculated from U/V components. Arrow shows direction.',
    placement: 'top'
  },
  'forecast-analogs': {
    id: 'forecast-analogs',
    title: 'Analog Matches',
    content: 'Number of historical patterns similar to current conditions. More analogs = higher confidence.',
    placement: 'top'
  },
  'forecast-latency': {
    id: 'forecast-latency',
    title: 'Response Time',
    content: 'API response time for this forecast. Lower latency indicates good system performance.',
    placement: 'top'
  },

  // Variable toggles
  'variable-toggle': {
    id: 'variable-toggle',
    title: 'Variable Display',
    content: 'Toggle additional meteorological variables on/off. Click the eye icon to show/hide.',
    placement: 'top'
  },
  'cape-badge': {
    id: 'cape-badge',
    title: 'CAPE (Convective Available Potential Energy)',
    content: 'Measure of atmospheric instability. Values >1000 J/kg indicate potential for thunderstorms.',
    placement: 'top'
  },

  // Status bar tooltips
  'status-model': {
    id: 'status-model',
    title: 'Model Version',
    content: 'Current analog ensemble model version hash. Used for reproducibility.',
    placement: 'top'
  },
  'status-index': {
    id: 'status-index',
    title: 'Index Version',
    content: 'Historical data index version. Updated when new analog patterns are added.',
    placement: 'top'
  },
  'status-dataset': {
    id: 'status-dataset',
    title: 'Dataset Version',
    content: 'Training dataset version used for analog matching.',
    placement: 'top'
  },
  'status-time': {
    id: 'status-time',
    title: 'Current Time',
    content: 'Local Adelaide time (ACDT/ACST) and last update timestamp.',
    placement: 'top'
  },

  // Keyboard shortcuts
  'shortcut-help': {
    id: 'shortcut-help',
    title: 'Help System',
    content: 'Press ? or F1 to open help. Esc to close dialogs. Arrow keys to navigate.',
    placement: 'top',
    shortcut: '? or F1'
  }
};

// Guided tour definitions
export const tours = {
  // New user onboarding
  newUser: {
    id: 'new-user',
    title: 'Welcome to Adelaide Weather Forecasting',
    description: 'Let\'s walk through the key features of your new forecasting system.',
    steps: [
      {
        id: 'welcome',
        target: 'body',
        title: 'Welcome to Adelaide Weather Forecasting',
        content: 'This system provides high-resolution analog ensemble weather forecasts for Adelaide using historical pattern matching. Let\'s explore the key features.',
        placement: 'bottom'
      },
      {
        id: 'navigation',
        target: '[data-tour="navigation"]',
        title: 'Navigation Panel',
        content: 'Use this sidebar to navigate between different views. Dashboard shows all forecasts, Details provides in-depth analysis.',
        placement: 'right'
      },
      {
        id: 'forecast-cards',
        target: '[data-tour="forecast-grid"]',
        title: 'Forecast Cards',
        content: 'Each card shows a different forecast horizon. You can see temperature, wind, and confidence levels at a glance.',
        placement: 'top'
      },
      {
        id: 'horizon-control',
        target: '[data-tour="horizon-slider"]',
        title: 'Horizon Control',
        content: 'Adjust the forecast horizon using this slider. Range from 1 to 48 hours ahead.',
        placement: 'top'
      },
      {
        id: 'variables',
        target: '[data-tour="variable-toggles"]',
        title: 'Additional Variables',
        content: 'Toggle additional meteorological variables like wind, pressure, and CAPE on/off for detailed analysis.',
        placement: 'top'
      },
      {
        id: 'analog-info',
        target: '[data-tour="analog-count"]',
        title: 'Analog Information',
        content: 'This shows how many historical patterns match current conditions. More analogs typically mean higher confidence.',
        placement: 'top'
      },
      {
        id: 'status-bar',
        target: '[data-tour="status-bar"]',
        title: 'System Status',
        content: 'Monitor system health, model versions, and update times in the status bar.',
        placement: 'top'
      }
    ] as TourStep[]
  },

  // Feature discovery tour
  features: {
    id: 'features',
    title: 'Advanced Features Tour',
    description: 'Discover powerful features for detailed analysis and system monitoring.',
    steps: [
      {
        id: 'uncertainty-bands',
        target: '[data-tour="uncertainty-display"]',
        title: 'Uncertainty Quantification',
        content: 'Uncertainty bands (P05-P95) show the range of possible values. Narrower bands indicate higher confidence.',
        placement: 'top'
      },
      {
        id: 'analog-explorer',
        target: '[data-tour="analog-button"]',
        title: 'Analog Pattern Explorer',
        content: 'Click here to explore historical patterns that match current conditions. Great for understanding forecast basis.',
        placement: 'top'
      },
      {
        id: 'cape-analysis',
        target: '[data-tour="cape-badge"]',
        title: 'CAPE Analysis',
        content: 'Convective Available Potential Energy helps assess thunderstorm potential. Color-coded for quick assessment.',
        placement: 'top'
      },
      {
        id: 'performance-metrics',
        target: '[data-tour="latency-display"]',
        title: 'Performance Monitoring',
        content: 'Response time and analog count help you assess system performance and forecast quality.',
        placement: 'top'
      }
    ] as TourStep[]
  },

  // Best practices guidance
  bestPractices: {
    id: 'best-practices',
    title: 'Forecasting Best Practices',
    description: 'Learn how to interpret and use forecasts effectively.',
    steps: [
      {
        id: 'confidence-interpretation',
        target: '[data-tour="confidence-badge"]',
        title: 'Interpreting Confidence',
        content: 'Confidence above 70% is generally reliable. Below 50% suggests high uncertainty - consider ensemble spread.',
        placement: 'top'
      },
      {
        id: 'horizon-reliability',
        target: '[data-tour="forecast-grid"]',
        title: 'Horizon Reliability',
        content: 'Shorter horizons (+6h, +12h) are more reliable than longer ones (+24h, +48h). Use accordingly.',
        placement: 'top'
      },
      {
        id: 'analog-assessment',
        target: '[data-tour="analog-count"]',
        title: 'Analog Assessment',
        content: 'More than 30 analogs is good, 20-30 is moderate, below 20 suggests rare conditions.',
        placement: 'top'
      },
      {
        id: 'uncertainty-usage',
        target: '[data-tour="uncertainty-display"]',
        title: 'Using Uncertainty Information',
        content: 'Always consider the uncertainty range (P05-P95) for risk assessment, not just the central value.',
        placement: 'top'
      }
    ] as TourStep[]
  }
};

// Help articles
export const helpArticles: HelpArticle[] = [
  {
    id: 'analog-ensemble-basics',
    title: 'Understanding Analog Ensemble Forecasting',
    category: 'methodology',
    content: `# Analog Ensemble Forecasting

Analog ensemble forecasting identifies historical weather patterns similar to current conditions and uses them to predict future weather.

## How It Works

1. **Pattern Matching**: The system compares current atmospheric conditions to historical data
2. **Similarity Ranking**: Similar patterns (analogs) are ranked by similarity score
3. **Ensemble Creation**: Top analogs form an ensemble of possible outcomes
4. **Statistical Analysis**: Uncertainty is quantified using ensemble spread

## Key Advantages

- **Physical Consistency**: Uses real observed weather patterns
- **Uncertainty Quantification**: Provides probability distributions, not just single values
- **Local Optimization**: Specifically calibrated for Adelaide conditions
- **Rare Event Handling**: Can capture unusual weather patterns in the historical record

## Interpreting Results

- **Central Value**: Most likely outcome based on analog ensemble
- **Uncertainty Bounds**: P05-P95 percentiles show range of possibilities
- **Confidence**: Higher analog similarity = higher confidence
- **Analog Count**: More matching patterns = more robust forecast`,
    tags: ['analog', 'ensemble', 'methodology', 'basics'],
    lastUpdated: '2024-01-15',
    difficulty: 'beginner'
  },
  {
    id: 'forecast-interpretation',
    title: 'How to Read Weather Forecasts',
    category: 'usage',
    content: `# Reading Weather Forecasts

Understanding how to interpret the forecasts is crucial for effective decision-making.

## Temperature Forecasts

- **Central Value**: The most likely temperature
- **P05/P95 Bounds**: 5th and 95th percentiles (90% confidence interval)
- **Confidence %**: Based on analog similarity and ensemble spread

## Wind Information

- **Speed**: Calculated from U/V wind components
- **Direction**: Wind direction in degrees (0° = North)
- **Gusts**: Peak wind speeds (when available)

## Confidence Interpretation

| Confidence | Interpretation | Recommended Use |
|------------|----------------|-----------------|
| 80-100% | Very High | Operational decisions |
| 60-79% | High | Planning with contingency |
| 40-59% | Moderate | Monitor closely |
| 20-39% | Low | Consider alternatives |
| 0-19% | Very Low | Seek additional information |

## Best Practices

1. Always check uncertainty bounds, not just central values
2. Shorter horizons are more reliable than longer ones
3. More analogs generally mean higher confidence
4. Consider local effects not captured in the model`,
    tags: ['interpretation', 'usage', 'confidence', 'best-practices'],
    lastUpdated: '2024-01-15',
    difficulty: 'beginner'
  },
  {
    id: 'cape-analysis',
    title: 'CAPE and Convective Potential',
    category: 'meteorology',
    content: `# CAPE: Convective Available Potential Energy

CAPE measures the amount of energy available for convection in the atmosphere.

## Understanding CAPE Values

| CAPE (J/kg) | Potential | Thunderstorm Likelihood |
|-------------|-----------|------------------------|
| 0-1000 | Low | Minimal |
| 1000-2500 | Moderate | Isolated storms possible |
| 2500-4000 | High | Scattered storms likely |
| 4000+ | Extreme | Severe storms possible |

## Color Coding in the System

- **Gray**: CAPE < 500 J/kg (Stable)
- **Green**: 500-1500 J/kg (Weak instability)
- **Yellow**: 1500-3000 J/kg (Moderate instability)
- **Orange**: 3000-4500 J/kg (Strong instability)
- **Red**: 4500+ J/kg (Extreme instability)

## Important Considerations

1. High CAPE doesn't guarantee storms - triggering mechanisms are also needed
2. CAPE values change rapidly during the day
3. Local topography can enhance or suppress convection
4. Combine CAPE with wind shear analysis for complete picture

## Using CAPE in Operations

- Monitor CAPE trends throughout the day
- Consider backup plans when CAPE exceeds 2500 J/kg
- Coordinate with local weather services for severe weather watches`,
    tags: ['cape', 'convection', 'thunderstorms', 'meteorology'],
    lastUpdated: '2024-01-15',
    difficulty: 'intermediate'
  }
];

// Frequently Asked Questions
export const faqs: FAQ[] = [
  {
    id: 'analog-count-low',
    question: 'What does it mean when the analog count is low?',
    answer: 'Low analog count (typically below 20) indicates that current atmospheric conditions are unusual or rare in the historical record. This may result in lower forecast confidence. Consider seeking additional meteorological guidance for important decisions.',
    category: 'interpretation',
    tags: ['analogs', 'confidence', 'rare-events']
  },
  {
    id: 'confidence-dropped',
    question: 'Why did forecast confidence suddenly drop?',
    answer: 'Confidence can drop due to: 1) Changing atmospheric patterns that are harder to match historically, 2) Transition periods between weather systems, 3) Rare meteorological conditions, or 4) Model uncertainty in current conditions. Check analog count and uncertainty bounds.',
    category: 'troubleshooting',
    tags: ['confidence', 'uncertainty', 'model-behavior']
  },
  {
    id: 'horizon-accuracy',
    question: 'Which forecast horizons are most accurate?',
    answer: 'Generally, shorter horizons (+6h, +12h) are more accurate than longer ones (+24h, +48h). The 6-hour forecast typically has the highest confidence and smallest uncertainty bounds. Use longer horizons for planning purposes with appropriate uncertainty consideration.',
    category: 'usage',
    tags: ['accuracy', 'horizons', 'reliability']
  },
  {
    id: 'cape-no-storms',
    question: 'CAPE is high but no storms developed. Why?',
    answer: 'High CAPE indicates atmospheric instability but storms need triggering mechanisms like convergence, lifting, or frontal boundaries. CAPE alone doesn\'t guarantee storm development. Other factors include wind shear, atmospheric moisture, and local topographic effects.',
    category: 'meteorology',
    tags: ['cape', 'thunderstorms', 'triggers']
  },
  {
    id: 'uncertainty-bands',
    question: 'How should I interpret the uncertainty bands?',
    answer: 'P05-P95 bands represent a 90% confidence interval. There\'s a 5% chance the actual value will be below P05 and 5% chance above P95. Wider bands indicate higher uncertainty. Use these for risk assessment rather than relying only on the central forecast.',
    category: 'interpretation',
    tags: ['uncertainty', 'confidence-intervals', 'risk-assessment']
  },
  {
    id: 'system-updates',
    question: 'How often does the system update forecasts?',
    answer: 'Forecasts update automatically every minute for the web interface. The underlying model runs every 6 hours with new observational data. Model and dataset versions are shown in the status bar and update when improvements are deployed.',
    category: 'system',
    tags: ['updates', 'frequency', 'data-refresh']
  }
];

// Keyboard shortcuts
export const keyboardShortcuts = {
  'general': [
    { key: '?', description: 'Show help and keyboard shortcuts', category: 'general' },
    { key: 'F1', description: 'Open help system', category: 'general' },
    { key: 'Esc', description: 'Close dialogs and overlays', category: 'general' },
    { key: 'Ctrl+/', description: 'Toggle tour mode', category: 'general' }
  ],
  'navigation': [
    { key: '1', description: 'Go to Dashboard', category: 'navigation' },
    { key: '2', description: 'Go to Details', category: 'navigation' },
    { key: '3', description: 'Go to System Status', category: 'navigation' },
    { key: '4', description: 'Go to About', category: 'navigation' }
  ],
  'forecast': [
    { key: 'Space', description: 'Toggle variable display', category: 'forecast' },
    { key: 'Arrow Left/Right', description: 'Navigate between cards', category: 'forecast' },
    { key: 'Ctrl+R', description: 'Refresh forecasts', category: 'forecast' },
    { key: 'A', description: 'Open analog explorer', category: 'forecast' }
  ]
};

// Help system configuration
export const helpConfig = {
  enableTooltips: true,
  enableTours: true,
  enableKeyboardShortcuts: true,
  defaultTooltipDelay: 500,
  tourAutoAdvance: false,
  tourShowProgress: true,
  feedbackEnabled: true,
  analyticsEnabled: true,
  contextualHelp: true
};

// Search functionality for help content
export function searchHelpContent(query: string): Array<{
  type: 'tooltip' | 'article' | 'faq' | 'tour';
  id: string;
  title: string;
  content: string;
  relevance: number;
}> {
  const results: Array<{
    type: 'tooltip' | 'article' | 'faq' | 'tour';
    id: string;
    title: string;
    content: string;
    relevance: number;
  }> = [];
  
  const searchTerms = query.toLowerCase().split(' ');
  
  // Search tooltips
  Object.values(tooltips).forEach(tooltip => {
    const text = `${tooltip.title} ${tooltip.content}`.toLowerCase();
    const relevance = searchTerms.reduce((score, term) => {
      return score + (text.includes(term) ? 1 : 0);
    }, 0) / searchTerms.length;
    
    if (relevance > 0) {
      results.push({
        type: 'tooltip',
        id: tooltip.id,
        title: tooltip.title,
        content: tooltip.content,
        relevance
      });
    }
  });
  
  // Search articles
  helpArticles.forEach(article => {
    const text = `${article.title} ${article.content} ${article.tags.join(' ')}`.toLowerCase();
    const relevance = searchTerms.reduce((score, term) => {
      return score + (text.includes(term) ? 1 : 0);
    }, 0) / searchTerms.length;
    
    if (relevance > 0) {
      results.push({
        type: 'article',
        id: article.id,
        title: article.title,
        content: article.content.substring(0, 200) + '...',
        relevance
      });
    }
  });
  
  // Search FAQs
  faqs.forEach(faq => {
    const text = `${faq.question} ${faq.answer} ${faq.tags.join(' ')}`.toLowerCase();
    const relevance = searchTerms.reduce((score, term) => {
      return score + (text.includes(term) ? 1 : 0);
    }, 0) / searchTerms.length;
    
    if (relevance > 0) {
      results.push({
        type: 'faq',
        id: faq.id,
        title: faq.question,
        content: faq.answer,
        relevance
      });
    }
  });
  
  return results.sort((a, b) => b.relevance - a.relevance);
}