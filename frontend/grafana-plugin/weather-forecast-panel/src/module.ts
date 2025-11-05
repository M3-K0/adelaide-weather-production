import { PanelPlugin } from '@grafana/data';
import { WeatherForecastPanel } from './components/WeatherForecastPanel';
import { WeatherPanelOptions, DEFAULT_OPTIONS } from './types';
import { panelOptionsBuilder } from './PanelOptions';

export const plugin = new PanelPlugin<WeatherPanelOptions>(WeatherForecastPanel)
  .setPanelOptions(panelOptionsBuilder)
  .setDefaults(DEFAULT_OPTIONS);