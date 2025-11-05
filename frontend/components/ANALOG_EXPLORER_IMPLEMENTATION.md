# AnalogExplorer Component Implementation

## Overview

The AnalogExplorer component is an interactive visualization tool that displays the top 5 most similar historical weather patterns to current conditions. It features a timeline scrubber, detailed pattern analysis, outcome narratives, and data export functionality.

## Features

### 🎯 Core Functionality
- **Pattern Ranking**: Displays top 5 historical analogs ranked by similarity score
- **Interactive Timeline**: Smooth timeline scrubbing with play/pause controls
- **Real-time Visualization**: Live chart updates as timeline position changes
- **Detailed Analysis**: Expandable cards with pattern details and outcomes
- **Export Capabilities**: CSV and JSON export functionality

### 🎨 User Experience
- **Responsive Design**: Adapts to different screen sizes
- **Smooth Animations**: Framer Motion powered transitions
- **Keyboard Navigation**: Full keyboard accessibility support
- **Loading States**: Skeleton loading and error states
- **Performance Optimized**: Efficient rendering and data handling

### 📊 Data Visualization
- **Line Charts**: Interactive Recharts timeline visualization
- **Trend Indicators**: Temperature and pressure trend arrows
- **Variable Selection**: Switch between different weather variables
- **Reference Lines**: Current timeline position indicator

## Component Architecture

### Main Component: `AnalogExplorer`
```typescript
interface AnalogExplorerProps {
  data: AnalogExplorerData;
  horizon: ForecastHorizon;
  loading?: boolean;
  error?: string | null;
  onAnalogSelect?: (analog: AnalogPattern) => void;
  className?: string;
}
```

### Sub-components

#### `TimelineControls`
- Play/pause controls
- Reset functionality
- Position indicator
- Timeline scrubber

#### `AnalogCard`
- Pattern summary display
- Similarity score badge
- Expandable details
- Location information

#### `TimelineEvents`
- Event display at current timeline position
- Trend indicators
- Weather event lists

#### `CurrentPointInfo`
- Current timeline position details
- Active events at selected time
- Chart reference line

## Data Flow

### 1. Data Fetching
```typescript
// Custom hook for data management
const { data, loading, error, refetch } = useAnalogData(horizon, {
  autoFetch: true,
  cacheDuration: 10 * 60 * 1000, // 10 minutes
  retryOnError: true,
  maxRetries: 3
});
```

### 2. State Management
```typescript
// Component state
const [selectedAnalogIndex, setSelectedAnalogIndex] = useState<number>(0);
const [timelinePosition, setTimelinePosition] = useState<number>(0);
const [isPlaying, setIsPlaying] = useState<boolean>(false);
const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set([0]));
const [selectedVariable, setSelectedVariable] = useState<WeatherVariable>('t2m');
```

### 3. Timeline Animation
```typescript
// Animation timer for smooth playback
useEffect(() => {
  if (isPlaying) {
    const interval = setInterval(() => {
      setTimelinePosition(prev => {
        const next = prev + (0.005 * playbackSpeed);
        if (next >= 1) {
          setIsPlaying(false);
          return 1;
        }
        return next;
      });
    }, 50);
    
    setAnimationTimer(interval);
    return () => clearInterval(interval);
  }
}, [isPlaying, playbackSpeed]);
```

## API Integration

### Endpoints
- `GET /api/analogs?horizon={horizon}` - Fetch analog data

### Data Types
```typescript
interface AnalogExplorerData {
  forecast_horizon: ForecastHorizon;
  top_analogs: AnalogPattern[];
  ensemble_stats: {
    mean_outcomes: Record<WeatherVariable, number | null>;
    outcome_uncertainty: Record<WeatherVariable, number | null>;
    common_events: string[];
  };
  generated_at: string;
}

interface AnalogPattern {
  date: string;
  similarity_score: number;
  initial_conditions: Record<WeatherVariable, number | null>;
  timeline: AnalogTimelinePoint[];
  outcome_narrative: string;
  location?: {
    latitude: number;
    longitude: number;
    name?: string;
  };
  season_info: {
    month: number;
    season: 'summer' | 'autumn' | 'winter' | 'spring';
  };
}
```

## Performance Optimizations

### 1. Memoization
```typescript
// Expensive calculations are memoized
const chartData = useMemo(() => {
  if (!data.top_analogs.length) return [];
  
  const selectedAnalog = data.top_analogs[selectedAnalogIndex];
  const currentPoint = getCurrentTimelineData(selectedAnalog, timelinePosition);
  
  return selectedAnalog.timeline.map(point => ({
    hours: point.hours_offset,
    value: point.values[selectedVariable] || null,
    isCurrentPoint: point.hours_offset === currentPoint.hours_offset
  }));
}, [data.top_analogs, selectedAnalogIndex, selectedVariable, timelinePosition]);
```

### 2. Caching
- In-memory cache with configurable expiration
- Smart cache invalidation on refetch
- Preloading capabilities

### 3. Efficient Rendering
- Component-level optimizations
- Conditional rendering based on data availability
- Smooth animations with reduced DOM manipulation

## Export Functionality

### CSV Export
```typescript
function generateCSVContent(data: AnalogExplorerData): string {
  const headers = [
    'Date', 'Similarity_Score', 'Season', 'Outcome_Narrative',
    'Location_Name', 'Latitude', 'Longitude'
  ];
  
  const rows = data.top_analogs.map(analog => [
    analog.date,
    analog.similarity_score.toFixed(4),
    analog.season_info.season,
    `"${analog.outcome_narrative.replace(/"/g, '""')}"`,
    analog.location?.name || '',
    analog.location?.latitude.toFixed(6) || '',
    analog.location?.longitude.toFixed(6) || ''
  ]);
  
  return [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
}
```

### JSON Export
- Full data structure export
- Formatted JSON with proper indentation
- Complete analog pattern data including timeline points

## Accessibility Features

### Keyboard Navigation
- Timeline scrubber supports arrow keys
- Tab navigation through all interactive elements
- Proper focus management

### Screen Reader Support
```typescript
// ARIA labels and roles
<div
  role="article"
  aria-label={`Forecast for ${horizon}: analog patterns with ${confidencePct}% similarity`}
  tabIndex={0}
>
```

### Visual Accessibility
- High contrast color schemes
- Clear focus indicators
- Descriptive text for all visual elements

## Styling and Theming

### CSS Classes
```css
/* Timeline slider styling */
.timeline-slider {
  @apply appearance-none bg-slate-700 rounded-lg cursor-pointer h-2;
}

.timeline-slider::-webkit-slider-thumb {
  @apply appearance-none w-4 h-4 rounded-full cursor-pointer;
  background: #22d3ee;
  box-shadow: 0 2px 8px rgba(34, 211, 238, 0.3);
  transition: all 0.2s ease;
}

/* Multi-line text truncation */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
```

### Color Scheme
- **Primary**: Cyan (#22d3ee) for interactive elements
- **Background**: Dark slate (#0E1116, #0A0D12)
- **Borders**: Muted slate (#1C1F26, #2A2F3A)
- **Text**: Light slate (#e2e8f0, #94a3b8, #64748b)
- **Similarity Colors**: 
  - High (80%+): Emerald (#10b981)
  - Medium (60-79%): Cyan (#22d3ee)
  - Low (40-59%): Yellow (#f59e0b)
  - Poor (<40%): Orange (#f97316)

## Testing Strategy

### Unit Tests
- Component rendering with different props
- State management and user interactions
- Timeline controls and animations
- Export functionality
- Error handling

### Integration Tests
- API data fetching and error states
- Cache behavior and invalidation
- Timeline synchronization
- Chart interactions

### Accessibility Tests
- Keyboard navigation
- Screen reader compatibility
- Focus management
- ARIA attributes

## Usage Examples

### Basic Usage
```typescript
import { AnalogExplorer } from '@/components';
import { useAnalogData } from '@/lib/useAnalogData';

function MyComponent() {
  const { data, loading, error } = useAnalogData('24h');
  
  return (
    <AnalogExplorer
      data={data!}
      horizon="24h"
      loading={loading}
      error={error}
      onAnalogSelect={(analog) => console.log('Selected:', analog)}
    />
  );
}
```

### With Custom Options
```typescript
const { data, loading, error, refetch } = useAnalogData('48h', {
  autoFetch: false,
  cacheDuration: 5 * 60 * 1000, // 5 minutes
  retryOnError: false
});

// Manual trigger
await refetch();
```

### Preloading Data
```typescript
import { preloadAnalogData } from '@/lib/useAnalogData';

// Preload data for faster loading
await preloadAnalogData('24h');
```

## Future Enhancements

### Planned Features
1. **Comparison Mode**: Side-by-side analog comparison
2. **Map Integration**: Geographic visualization of analog locations
3. **Advanced Filtering**: Filter analogs by season, similarity threshold
4. **Custom Variables**: User-defined variable combinations
5. **Bookmarking**: Save interesting analog patterns
6. **Sharing**: Share specific analog patterns via URL

### Performance Improvements
1. **Virtual Scrolling**: For large analog datasets
2. **Web Workers**: Heavy calculations in background threads
3. **Progressive Loading**: Lazy load timeline data
4. **WebGL Charts**: For high-performance visualization

### Accessibility Enhancements
1. **Voice Navigation**: Voice commands for timeline control
2. **Haptic Feedback**: Tactile feedback for mobile users
3. **Audio Descriptions**: Audio descriptions of chart data
4. **High Contrast Mode**: Dedicated high contrast theme

## Dependencies

### Core Dependencies
- `react` - Component framework
- `framer-motion` - Smooth animations
- `recharts` - Chart visualization
- `lucide-react` - Icons
- `date-fns` - Date formatting

### Development Dependencies
- `@testing-library/react` - Component testing
- `@testing-library/user-event` - User interaction testing
- `jest` - Test runner

## Browser Support

### Minimum Requirements
- **Chrome**: 88+
- **Firefox**: 85+
- **Safari**: 14+
- **Edge**: 88+

### Features Used
- ES2020 features
- CSS Grid and Flexbox
- Web APIs: Fetch, URL, Blob
- Modern JavaScript: async/await, destructuring

## Deployment Considerations

### Production Optimizations
1. **Code Splitting**: Lazy load component for better performance
2. **Tree Shaking**: Remove unused code
3. **Bundle Analysis**: Monitor bundle size impact
4. **CDN Assets**: Serve static assets from CDN

### Environment Variables
```bash
# API configuration
API_BASE_URL=https://api.weather.adelaide.com
API_TOKEN=your_api_token_here

# Feature flags
ENABLE_ANALOG_EXPLORER=true
ANALOG_CACHE_DURATION=600000  # 10 minutes
```

### Monitoring
- Performance metrics tracking
- Error reporting and logging
- User interaction analytics
- API usage monitoring

This implementation provides a comprehensive, production-ready analog pattern explorer with excellent user experience, performance, and accessibility characteristics.