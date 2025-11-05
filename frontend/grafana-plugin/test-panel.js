#!/usr/bin/env node

/**
 * Weather Forecast Panel Testing Script
 * 
 * This script tests the Grafana weather forecast panel functionality
 * including data integration, animations, and user interactions.
 */

const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

class WeatherPanelTester {
    constructor() {
        this.browser = null;
        this.page = null;
        this.testResults = [];
        this.config = {
            grafanaUrl: 'http://localhost:3000',
            username: 'admin',
            password: 'admin',
            timeout: 30000
        };
    }

    async initialize() {
        console.log('🚀 Initializing Weather Panel Tester...');
        
        this.browser = await puppeteer.launch({
            headless: false, // Set to true for CI environments
            defaultViewport: { width: 1920, height: 1080 },
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });

        this.page = await this.browser.newPage();
        
        // Set up console logging
        this.page.on('console', msg => {
            if (msg.type() === 'error') {
                console.error('❌ Browser Console Error:', msg.text());
            }
        });

        // Set up error handling
        this.page.on('pageerror', error => {
            console.error('❌ Page Error:', error.message);
        });
    }

    async loginToGrafana() {
        console.log('🔐 Logging into Grafana...');
        
        try {
            await this.page.goto(`${this.config.grafanaUrl}/login`);
            
            await this.page.waitForSelector('input[name="user"]', { timeout: this.config.timeout });
            await this.page.type('input[name="user"]', this.config.username);
            await this.page.type('input[name="password"]', this.config.password);
            
            await this.page.click('button[type="submit"]');
            await this.page.waitForNavigation();
            
            this.addTestResult('login', true, 'Successfully logged into Grafana');
            
        } catch (error) {
            this.addTestResult('login', false, `Login failed: ${error.message}`);
            throw error;
        }
    }

    async createTestDashboard() {
        console.log('📊 Creating test dashboard...');
        
        try {
            // Navigate to dashboard creation
            await this.page.goto(`${this.config.grafanaUrl}/dashboard/new`);
            await this.page.waitForSelector('[data-testid="dashboard-settings"]', { timeout: this.config.timeout });
            
            // Add new panel
            await this.page.click('[data-testid="dashboard-add-panel"]');
            await this.page.waitForSelector('[data-testid="add-panel"]');
            await this.page.click('[data-testid="add-panel"]');
            
            // Wait for panel editor
            await this.page.waitForSelector('[data-testid="panel-editor"]');
            
            this.addTestResult('dashboard_creation', true, 'Test dashboard created successfully');
            
        } catch (error) {
            this.addTestResult('dashboard_creation', false, `Dashboard creation failed: ${error.message}`);
            throw error;
        }
    }

    async selectWeatherForecastPanel() {
        console.log('🌦️  Selecting Weather Forecast Panel...');
        
        try {
            // Open visualization picker
            await this.page.click('[data-testid="panel-editor-tab-visualizations"]');
            
            // Look for weather forecast panel
            const panelSelector = '[data-testid="weather-forecast-panel"]';
            await this.page.waitForSelector(panelSelector, { timeout: this.config.timeout });
            await this.page.click(panelSelector);
            
            // Wait for panel to load
            await this.page.waitForTimeout(2000);
            
            this.addTestResult('panel_selection', true, 'Weather Forecast Panel selected successfully');
            
        } catch (error) {
            // Fallback: check if plugin is installed
            const pluginPresent = await this.page.$('[data-testid="weather-forecast-panel"]');
            if (!pluginPresent) {
                this.addTestResult('panel_selection', false, 'Weather Forecast Panel plugin not found - check installation');
            } else {
                this.addTestResult('panel_selection', false, `Panel selection failed: ${error.message}`);
            }
            throw error;
        }
    }

    async testPanelConfiguration() {
        console.log('⚙️  Testing panel configuration options...');
        
        try {
            // Open panel options
            await this.page.click('[data-testid="panel-editor-tab-options"]');
            
            const tests = [
                // Test view settings
                {
                    name: 'show_observations_toggle',
                    selector: '[data-testid="show-observations-switch"]',
                    action: 'click'
                },
                {
                    name: 'show_forecast_toggle', 
                    selector: '[data-testid="show-forecast-switch"]',
                    action: 'click'
                },
                {
                    name: 'split_view_ratio',
                    selector: '[data-testid="split-view-ratio-slider"]',
                    action: 'drag'
                },
                // Test animation settings
                {
                    name: 'animation_speed',
                    selector: '[data-testid="animation-speed-slider"]',
                    action: 'drag'
                },
                // Test data settings
                {
                    name: 'uncertainty_bands_toggle',
                    selector: '[data-testid="uncertainty-bands-switch"]',
                    action: 'click'
                },
                {
                    name: 'historical_events_toggle',
                    selector: '[data-testid="historical-events-switch"]', 
                    action: 'click'
                },
                // Test analog settings
                {
                    name: 'analog_patterns_toggle',
                    selector: '[data-testid="analog-patterns-switch"]',
                    action: 'click'
                },
                {
                    name: 'max_analog_count',
                    selector: '[data-testid="max-analog-count-slider"]',
                    action: 'drag'
                }
            ];

            for (const test of tests) {
                try {
                    const element = await this.page.$(test.selector);
                    if (element) {
                        if (test.action === 'click') {
                            await element.click();
                        } else if (test.action === 'drag') {
                            await element.hover();
                            await this.page.mouse.down();
                            await this.page.mouse.move(50, 0);
                            await this.page.mouse.up();
                        }
                        
                        this.addTestResult(`config_${test.name}`, true, `${test.name} configuration test passed`);
                    } else {
                        this.addTestResult(`config_${test.name}`, false, `${test.name} element not found`);
                    }
                } catch (error) {
                    this.addTestResult(`config_${test.name}`, false, `${test.name} test failed: ${error.message}`);
                }
            }
            
        } catch (error) {
            this.addTestResult('panel_configuration', false, `Configuration test failed: ${error.message}`);
        }
    }

    async testDataQueries() {
        console.log('📈 Testing data queries...');
        
        try {
            // Navigate to query tab
            await this.page.click('[data-testid="panel-editor-tab-queries"]');
            
            // Add Prometheus query for observations
            await this.page.click('[data-testid="query-add"]');
            await this.page.waitForSelector('[data-testid="query-editor"]');
            
            const observationQuery = 'weather_observation{location="adelaide"}';
            await this.page.type('[data-testid="query-field"]', observationQuery);
            
            // Add forecast query
            await this.page.click('[data-testid="query-add"]');
            const forecastQuery = 'weather_forecast{location="adelaide"}';
            await this.page.type('[data-testid="query-field"]:last-of-type', forecastQuery);
            
            // Run queries
            await this.page.click('[data-testid="query-run"]');
            await this.page.waitForTimeout(3000);
            
            this.addTestResult('data_queries', true, 'Data queries configured successfully');
            
        } catch (error) {
            this.addTestResult('data_queries', false, `Data query test failed: ${error.message}`);
        }
    }

    async testPanelInteractions() {
        console.log('🎮 Testing panel interactions...');
        
        try {
            // Switch back to panel view
            await this.page.click('[data-testid="panel-editor-tab-panel"]');
            await this.page.waitForTimeout(2000);
            
            const interactions = [
                // Test horizon selection
                {
                    name: 'horizon_selection',
                    selector: '[data-testid="horizon-6h"]',
                    description: 'Test 6h horizon selection'
                },
                {
                    name: 'horizon_selection_12h',
                    selector: '[data-testid="horizon-12h"]',
                    description: 'Test 12h horizon selection'
                },
                // Test variable toggles
                {
                    name: 'temperature_toggle',
                    selector: '[data-testid="variable-temperature"]',
                    description: 'Test temperature variable toggle'
                },
                {
                    name: 'pressure_toggle',
                    selector: '[data-testid="variable-pressure"]',
                    description: 'Test pressure variable toggle'
                },
                // Test animation controls
                {
                    name: 'animation_play',
                    selector: '[data-testid="animation-play"]',
                    description: 'Test animation play button'
                },
                {
                    name: 'animation_pause',
                    selector: '[data-testid="animation-pause"]',
                    description: 'Test animation pause button'
                }
            ];

            for (const interaction of interactions) {
                try {
                    const element = await this.page.$(interaction.selector);
                    if (element) {
                        await element.click();
                        await this.page.waitForTimeout(1000);
                        this.addTestResult(`interaction_${interaction.name}`, true, interaction.description);
                    } else {
                        this.addTestResult(`interaction_${interaction.name}`, false, `Element ${interaction.selector} not found`);
                    }
                } catch (error) {
                    this.addTestResult(`interaction_${interaction.name}`, false, `${interaction.description} failed: ${error.message}`);
                }
            }
            
        } catch (error) {
            this.addTestResult('panel_interactions', false, `Interaction test failed: ${error.message}`);
        }
    }

    async testAnimationFunctionality() {
        console.log('🎬 Testing animation functionality...');
        
        try {
            // Start animation
            const playButton = await this.page.$('[data-testid="animation-play"]');
            if (playButton) {
                await playButton.click();
                
                // Wait for animation to run
                await this.page.waitForTimeout(5000);
                
                // Check for animation indicators
                const animationIndicator = await this.page.$('[data-testid="animation-indicator"]');
                if (animationIndicator) {
                    this.addTestResult('animation_start', true, 'Animation started successfully');
                } else {
                    this.addTestResult('animation_start', false, 'Animation indicator not found');
                }
                
                // Test pause
                const pauseButton = await this.page.$('[data-testid="animation-pause"]');
                if (pauseButton) {
                    await pauseButton.click();
                    this.addTestResult('animation_pause', true, 'Animation paused successfully');
                }
                
            } else {
                this.addTestResult('animation_start', false, 'Animation play button not found');
            }
            
        } catch (error) {
            this.addTestResult('animation_functionality', false, `Animation test failed: ${error.message}`);
        }
    }

    async testAnalogPatterns() {
        console.log('📊 Testing analog pattern functionality...');
        
        try {
            // Look for analog pattern overlays
            const analogPatterns = await this.page.$$('[data-testid^="analog-pattern-"]');
            
            if (analogPatterns.length > 0) {
                // Click first analog pattern
                await analogPatterns[0].click();
                await this.page.waitForTimeout(2000);
                
                // Check for pattern details
                const patternDetails = await this.page.$('[data-testid="analog-pattern-details"]');
                if (patternDetails) {
                    this.addTestResult('analog_pattern_selection', true, 'Analog pattern selection works');
                } else {
                    this.addTestResult('analog_pattern_selection', false, 'Analog pattern details not shown');
                }
                
                this.addTestResult('analog_patterns_present', true, `Found ${analogPatterns.length} analog patterns`);
            } else {
                this.addTestResult('analog_patterns_present', false, 'No analog patterns found');
            }
            
        } catch (error) {
            this.addTestResult('analog_patterns', false, `Analog pattern test failed: ${error.message}`);
        }
    }

    async testResponsiveness() {
        console.log('📱 Testing panel responsiveness...');
        
        try {
            const viewports = [
                { width: 1920, height: 1080, name: 'desktop' },
                { width: 1024, height: 768, name: 'tablet' },
                { width: 375, height: 667, name: 'mobile' }
            ];

            for (const viewport of viewports) {
                await this.page.setViewport(viewport);
                await this.page.waitForTimeout(2000);
                
                // Check if panel is still visible and functional
                const panelElement = await this.page.$('[data-testid="weather-forecast-panel"]');
                if (panelElement) {
                    const boundingBox = await panelElement.boundingBox();
                    if (boundingBox && boundingBox.width > 0 && boundingBox.height > 0) {
                        this.addTestResult(`responsive_${viewport.name}`, true, `Panel responsive on ${viewport.name}`);
                    } else {
                        this.addTestResult(`responsive_${viewport.name}`, false, `Panel not visible on ${viewport.name}`);
                    }
                } else {
                    this.addTestResult(`responsive_${viewport.name}`, false, `Panel not found on ${viewport.name}`);
                }
            }
            
            // Reset to desktop view
            await this.page.setViewport({ width: 1920, height: 1080 });
            
        } catch (error) {
            this.addTestResult('responsiveness', false, `Responsiveness test failed: ${error.message}`);
        }
    }

    async testPerformance() {
        console.log('⚡ Testing panel performance...');
        
        try {
            // Measure panel load time
            const startTime = Date.now();
            
            await this.page.reload();
            await this.page.waitForSelector('[data-testid="weather-forecast-panel"]', { timeout: this.config.timeout });
            
            const loadTime = Date.now() - startTime;
            
            if (loadTime < 5000) {
                this.addTestResult('performance_load', true, `Panel loaded in ${loadTime}ms`);
            } else {
                this.addTestResult('performance_load', false, `Panel load time too slow: ${loadTime}ms`);
            }
            
            // Test memory usage
            const metrics = await this.page.metrics();
            const memoryUsage = metrics.JSHeapUsedSize / 1024 / 1024; // MB
            
            if (memoryUsage < 50) {
                this.addTestResult('performance_memory', true, `Memory usage: ${memoryUsage.toFixed(2)}MB`);
            } else {
                this.addTestResult('performance_memory', false, `High memory usage: ${memoryUsage.toFixed(2)}MB`);
            }
            
        } catch (error) {
            this.addTestResult('performance', false, `Performance test failed: ${error.message}`);
        }
    }

    async saveDashboard() {
        console.log('💾 Saving test dashboard...');
        
        try {
            // Save dashboard
            await this.page.click('[data-testid="dashboard-save"]');
            await this.page.waitForSelector('[data-testid="save-dashboard-modal"]');
            
            await this.page.type('[data-testid="dashboard-title"]', 'Weather Forecast Panel Test');
            await this.page.click('[data-testid="save-dashboard-button"]');
            
            await this.page.waitForTimeout(2000);
            this.addTestResult('save_dashboard', true, 'Test dashboard saved successfully');
            
        } catch (error) {
            this.addTestResult('save_dashboard', false, `Dashboard save failed: ${error.message}`);
        }
    }

    addTestResult(testName, passed, message) {
        this.testResults.push({
            test: testName,
            passed,
            message,
            timestamp: new Date().toISOString()
        });
        
        const status = passed ? '✅' : '❌';
        console.log(`${status} ${testName}: ${message}`);
    }

    generateTestReport() {
        console.log('\n📋 Test Report Summary');
        console.log('========================');
        
        const totalTests = this.testResults.length;
        const passedTests = this.testResults.filter(r => r.passed).length;
        const failedTests = totalTests - passedTests;
        
        console.log(`Total Tests: ${totalTests}`);
        console.log(`Passed: ${passedTests}`);
        console.log(`Failed: ${failedTests}`);
        console.log(`Success Rate: ${((passedTests / totalTests) * 100).toFixed(1)}%`);
        
        console.log('\n📊 Detailed Results:');
        console.log('=====================');
        
        this.testResults.forEach(result => {
            const status = result.passed ? '✅' : '❌';
            console.log(`${status} ${result.test}: ${result.message}`);
        });
        
        // Save report to file
        const reportPath = path.join(__dirname, 'test-report.json');
        fs.writeFileSync(reportPath, JSON.stringify({
            summary: {
                total: totalTests,
                passed: passedTests,
                failed: failedTests,
                successRate: (passedTests / totalTests) * 100
            },
            results: this.testResults,
            timestamp: new Date().toISOString()
        }, null, 2));
        
        console.log(`\n💾 Detailed report saved to: ${reportPath}`);
        
        return passedTests === totalTests;
    }

    async cleanup() {
        if (this.browser) {
            await this.browser.close();
        }
    }

    async runAllTests() {
        try {
            await this.initialize();
            await this.loginToGrafana();
            await this.createTestDashboard();
            await this.selectWeatherForecastPanel();
            await this.testPanelConfiguration();
            await this.testDataQueries();
            await this.testPanelInteractions();
            await this.testAnimationFunctionality();
            await this.testAnalogPatterns();
            await this.testResponsiveness();
            await this.testPerformance();
            await this.saveDashboard();
            
            const allTestsPassed = this.generateTestReport();
            
            if (allTestsPassed) {
                console.log('\n🎉 All tests passed! Weather Forecast Panel is working correctly.');
                return 0;
            } else {
                console.log('\n⚠️  Some tests failed. Check the report for details.');
                return 1;
            }
            
        } catch (error) {
            console.error('❌ Test suite failed:', error.message);
            return 1;
        } finally {
            await this.cleanup();
        }
    }
}

// Main execution
async function main() {
    const tester = new WeatherPanelTester();
    const exitCode = await tester.runAllTests();
    process.exit(exitCode);
}

if (require.main === module) {
    main().catch(error => {
        console.error('❌ Fatal error:', error);
        process.exit(1);
    });
}

module.exports = WeatherPanelTester;