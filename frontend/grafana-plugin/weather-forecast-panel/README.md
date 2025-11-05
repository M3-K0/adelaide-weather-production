# Weather Forecast Panel - Grafana Plugin

A custom Grafana panel plugin designed for meteorologists with advanced weather forecasting capabilities, analog pattern analysis, and interactive animations.

## Features

### 🌟 Core Features
- **Split View Interface**: Side-by-side display of observations and forecasts
- **Multi-Horizon Animation**: Smooth animations through 6h/12h/24h/48h forecast horizons
- **Analog Pattern Overlay**: Display similar historical weather patterns on current synoptic situation
- **Uncertainty Visualization**: Confidence bands for forecast uncertainty quantification
- **Historical Event Access**: Quick access to similar weather events from the past

### 📊 Data Integration
- **Prometheus Metrics**: Real-time metrics from weather monitoring systems
- **TimescaleDB**: Historical weather data and analog pattern storage
- **Multi-variable Support**: Temperature, pressure, CAPE, wind speed, and more
- **Quality Indicators**: Data quality and confidence metrics

### 🎮 Interactive Controls
- **Animation Controls**: Play/pause with configurable speed settings
- **Variable Selection**: Toggle visibility of different weather parameters
- **Horizon Selection**: Switch between forecast horizons with visual indicators
- **Pattern Selection**: Click analog patterns for detailed comparison

### 🎨 Visualization Features
- **Synoptic Map Overlay**: Pressure contours, wind vectors, temperature fields
- **Confidence Bands**: Visual uncertainty representation
- **Color-coded Variables**: Intuitive color schemes for different parameters
- **Responsive Design**: Adapts to different panel sizes and screen resolutions

## Installation

### Prerequisites
- Grafana 9.0.0 or higher
- Node.js 18.x or higher
- npm 9.x or higher

### Build from Source
```bash
# Clone the plugin
cd /path/to/grafana/plugins
git clone <repository-url> weather-forecast-panel

# Install dependencies
cd weather-forecast-panel
npm install

# Build the plugin
npm run build

# Restart Grafana
sudo systemctl restart grafana-server
```

### Development Mode
```bash
# Watch for changes during development
npm run dev

# Run tests
npm run test
```

## Configuration

### Panel Options

#### View Settings
- **Show Observations**: Toggle observation data display
- **Show Forecast**: Toggle forecast data display
- **Split View Ratio**: Adjust the split between observations and forecast panels (0.2 - 0.8)
- **Default Horizon**: Set the initial forecast horizon (6h, 12h, 24h, 48h)

#### Animation Settings
- **Animation Speed**: Control animation timing (250ms - 5000ms)

#### Data Settings
- **Show Uncertainty Bands**: Enable/disable confidence interval visualization
- **Enable Historical Events**: Show similar historical weather events
- **Confidence Threshold**: Minimum confidence level for displaying uncertainty (0.1 - 1.0)

#### Analog Pattern Settings
- **Show Analog Patterns**: Enable analog pattern overlay
- **Maximum Analog Count**: Number of analog patterns to display (1-10)

### Data Sources

#### Prometheus Queries
Configure these metrics in your Prometheus datasource:

```promql
# Observations
weather_observation{variable="temperature"}
weather_observation{variable="pressure"}
weather_observation{variable="cape"}

# Forecasts
weather_forecast{variable="temperature",horizon="6h"}
weather_forecast{variable="pressure",horizon="12h"}

# Analog patterns
analog_similarity_score{horizon="6h"}
ensemble_spread_current{horizon="6h"}
```

#### TimescaleDB Integration
The plugin expects these database tables:
- `historical_weather_events`: Historical weather event data
- `analog_patterns`: Analog pattern storage with similarity scores
- `forecast_verification`: Forecast accuracy and error metrics

## Usage

### Basic Setup
1. Add the Weather Forecast Panel to your dashboard
2. Configure your Prometheus and TimescaleDB data sources
3. Set up the appropriate queries for your weather variables
4. Customize the panel options to match your preferences

### Interactive Features

#### Animation Controls
- Click the **Play** button to start horizon animation
- Use **Speed** dropdown to adjust animation timing
- Animation automatically cycles through available horizons

#### Variable Selection
- Toggle weather variables on/off using checkboxes
- Color indicators show variable colors used in charts
- Changes apply to both observation and forecast views

#### Analog Pattern Analysis
- Analog patterns appear as overlay buttons when available
- Click patterns to overlay historical data on current chart
- Pattern similarity percentages indicate quality of match
- Detailed metadata shows synoptic situation and outcomes

#### Historical Events
- Historical events panel shows similar past events
- Click events for detailed analysis and associated analog patterns
- Severity indicators (🟢🟡🔴🟣) show event significance
- Events include similarity scores and pattern matching

### Advanced Features

#### Synoptic Map Overlay
- Pressure contour lines with labeled isobars
- Wind vector visualization with speed indicators
- Temperature field gradients
- Analog pattern highlight markers

#### Uncertainty Visualization
- Confidence bands around forecast lines
- Quality indicators for observation data
- Threshold-based filtering for reliability
- Statistical uncertainty metrics

## Data Format

### Expected Metrics Format
```typescript
// Observations
{
  time: Date,
  variable: "temperature" | "pressure" | "cape" | "wind_speed",
  value: number,
  confidence?: number
}

// Forecasts
{
  time: Date,
  variable: string,
  value: number,
  horizon: number, // hours
  uncertainty?: {
    lower: number,
    upper: number
  }
}

// Analog Patterns
{
  id: string,
  similarity: number, // 0-1
  date: Date,
  pattern: number[],
  metadata: {
    synopticSituation: string,
    weatherOutcome: string
  }
}
```

## Troubleshooting

### Common Issues

#### No Data Displayed
- Verify Prometheus and TimescaleDB connections
- Check query syntax and metric names
- Ensure time range includes available data
- Verify variable names match configuration

#### Animation Not Working
- Check that multiple horizons have data
- Verify animation speed settings
- Ensure forecast data exists for all horizons

#### Analog Patterns Missing
- Verify TimescaleDB analog_patterns table exists
- Check similarity threshold settings
- Ensure analog calculation service is running

#### Performance Issues
- Reduce number of analog patterns displayed
- Adjust confidence thresholds to filter data
- Consider shorter time ranges for complex queries

### Debug Mode
Enable debug logging in Grafana configuration:
```ini
[log]
level = debug
filters = plugin.weather-forecast-panel:debug
```

## Contributing

### Development Setup
```bash
# Fork and clone the repository
git clone <your-fork-url>
cd weather-forecast-panel

# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm run test

# Lint code
npm run lint
```

### Code Structure
```
src/
├── components/           # React components
│   ├── charts/          # Chart visualizations
│   ├── overlays/        # Map and pattern overlays
│   └── WeatherForecastPanel.tsx
├── hooks/               # Custom React hooks
├── types.ts             # TypeScript definitions
├── PanelOptions.tsx     # Panel configuration
└── module.ts            # Plugin entry point
```

### Testing
```bash
# Unit tests
npm run test

# E2E tests (requires Grafana instance)
npm run test:e2e

# Coverage report
npm run test:coverage
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Contact the Adelaide Weather Team

## Acknowledgments

- Built with Grafana Plugin SDK
- Uses Recharts for visualization
- Framer Motion for animations
- Integrates with Prometheus and TimescaleDB