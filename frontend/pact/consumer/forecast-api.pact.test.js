/**
 * Pact Consumer Tests for Adelaide Weather Forecast API
 *
 * These tests define the contract between the frontend consumer and backend provider.
 * They generate a Pact contract file that can be used to validate the API implementation.
 *
 * Enhanced Schema Coverage:
 * - ForecastResponse with narrative and risk assessment
 * - VariableResult with uncertainty quantification
 * - WindResult with speed/direction/gust
 * - RiskAssessment for weather hazards
 * - AnalogsSummary for historical pattern matching
 * - Comprehensive error handling
 */

const { Pact, Matchers } = require('@pact-foundation/pact');
const path = require('path');

// Pact Matchers for type-safe contract definition
const { like, eachLike, term, iso8601DateTime } = Matchers;

describe('Adelaide Weather Forecast API', () => {
  let provider;

  beforeAll(() => {
    provider = new Pact({
      consumer: 'adelaide-weather-frontend',
      provider: 'adelaide-weather-api',
      port: 8089,
      log: path.resolve(process.cwd(), 'logs', 'pact.log'),
      dir: path.resolve(process.cwd(), 'pacts'),
      logLevel: 'INFO',
      spec: 2
    });

    return provider.setup();
  });

  afterAll(() => {
    return provider.finalize();
  });

  afterEach(() => {
    return provider.verify();
  });

  describe('GET /forecast', () => {
    describe('successful forecast request with enhanced schema', () => {
      beforeEach(() => {
        const expectedResponse = {
          horizon: like('24h'),
          generated_at: iso8601DateTime(),
          variables: {
            t2m: {
              value: like(20.5),
              p05: like(18.0),
              p95: like(23.0),
              confidence: like(85.5),
              available: like(true),
              analog_count: like(45)
            },
            u10: {
              value: like(3.2),
              p05: like(1.5),
              p95: like(5.8),
              confidence: like(78.2),
              available: like(true),
              analog_count: like(45)
            },
            v10: {
              value: like(-2.1),
              p05: like(-4.5),
              p95: like(0.8),
              confidence: like(78.2),
              available: like(true),
              analog_count: like(45)
            },
            msl: {
              value: like(101325.0),
              p05: like(101000.0),
              p95: like(101800.0),
              confidence: like(92.1),
              available: like(true),
              analog_count: like(48)
            }
          },
          wind10m: {
            speed: like(3.8),
            direction: like(235.7),
            gust: like(null),
            available: like(true)
          },
          narrative: like(
            'Forecast for 24h: mild conditions with temperature around 20.5°C, light winds at 3.8 m/s from 236°, normal pressure system (1013 hPa).'
          ),
          risk_assessment: {
            thunderstorm: like('low'),
            heat_stress: like('minimal'),
            wind_damage: like('minimal'),
            precipitation: like('low')
          },
          analogs_summary: {
            most_similar_date: like('2023-03-15T12:00:00Z'),
            similarity_score: like(0.82),
            analog_count: like(45),
            outcome_description: like(
              'Strong pattern match with typical seasonal conditions'
            ),
            confidence_explanation: like(
              'Based on 45 historical analog patterns'
            )
          },
          confidence_explanation: like(
            'Moderate confidence (82.0%) based on 45 analog patterns'
          ),
          versions: {
            model: like('v1.0.0'),
            index: like('v1.0.0'),
            datasets: like('v1.0.0'),
            api_schema: like('v1.1.0')
          },
          hashes: {
            model: like('a7c3f92'),
            index: like('2e8b4d1'),
            datasets: like('d4f8a91')
          },
          latency_ms: like(42.5)
        };

        return provider.addInteraction({
          state: 'forecast system is operational',
          uponReceiving: 'a request for 24h forecast with default variables',
          withRequest: {
            method: 'GET',
            path: '/forecast',
            query: {
              horizon: '24h',
              vars: 't2m,u10,v10,msl'
            },
            headers: {
              Authorization: term({
                matcher: 'Bearer .*',
                generate: 'Bearer test-api-token'
              }),
              'Content-Type': 'application/json'
            }
          },
          willRespondWith: {
            status: 200,
            headers: {
              'Content-Type': 'application/json'
            },
            body: expectedResponse
          }
        });
      });

      it('returns comprehensive forecast with enhanced schema', async () => {
        const api = setupApiClient('http://localhost:8089');

        const response = await api.get('/forecast', {
          params: { horizon: '24h', vars: 't2m,u10,v10,msl' },
          headers: { Authorization: 'Bearer test-api-token' }
        });

        expect(response.status).toBe(200);
        expect(response.data).toHaveProperty('horizon', '24h');
        expect(response.data).toHaveProperty('variables');
        expect(response.data).toHaveProperty('wind10m');
        expect(response.data).toHaveProperty('narrative');
        expect(response.data).toHaveProperty('risk_assessment');
        expect(response.data).toHaveProperty('analogs_summary');
        expect(response.data).toHaveProperty('confidence_explanation');

        // Validate variable structure
        const t2mVariable = response.data.variables.t2m;
        expect(t2mVariable).toHaveProperty('value');
        expect(t2mVariable).toHaveProperty('p05');
        expect(t2mVariable).toHaveProperty('p95');
        expect(t2mVariable).toHaveProperty('confidence');
        expect(t2mVariable).toHaveProperty('available');
        expect(t2mVariable).toHaveProperty('analog_count');

        // Validate wind structure
        expect(response.data.wind10m).toHaveProperty('speed');
        expect(response.data.wind10m).toHaveProperty('direction');
        expect(response.data.wind10m).toHaveProperty('available');

        // Validate risk assessment
        expect(response.data.risk_assessment).toHaveProperty('thunderstorm');
        expect(response.data.risk_assessment).toHaveProperty('heat_stress');
        expect(response.data.risk_assessment).toHaveProperty('wind_damage');
        expect(response.data.risk_assessment).toHaveProperty('precipitation');

        // Validate analogs summary
        expect(response.data.analogs_summary).toHaveProperty(
          'similarity_score'
        );
        expect(response.data.analogs_summary).toHaveProperty('analog_count');
        expect(response.data.analogs_summary).toHaveProperty(
          'outcome_description'
        );
      });
    });

    describe('forecast request with CAPE variable for thunderstorm risk', () => {
      beforeEach(() => {
        return provider.addInteraction({
          state: 'forecast system is operational with CAPE data',
          uponReceiving: 'a request for forecast including CAPE variable',
          withRequest: {
            method: 'GET',
            path: '/forecast',
            query: {
              horizon: '6h',
              vars: 't2m,cape,msl'
            },
            headers: {
              Authorization: 'Bearer test-api-token',
              'Content-Type': 'application/json'
            }
          },
          willRespondWith: {
            status: 200,
            headers: {
              'Content-Type': 'application/json'
            },
            body: {
              horizon: like('6h'),
              generated_at: iso8601DateTime(),
              variables: {
                t2m: {
                  value: like(32.5),
                  p05: like(30.0),
                  p95: like(35.0),
                  confidence: like(88.5),
                  available: like(true),
                  analog_count: like(38)
                },
                cape: {
                  value: like(1500.0),
                  p05: like(800.0),
                  p95: like(2200.0),
                  confidence: like(75.2),
                  available: like(true),
                  analog_count: like(32)
                },
                msl: {
                  value: like(100980.0),
                  p05: like(100500.0),
                  p95: like(101300.0),
                  confidence: like(91.0),
                  available: like(true),
                  analog_count: like(40)
                }
              },
              wind10m: null,
              narrative: like(
                'Forecast for 6h: warm conditions with temperature around 32.5°C, low pressure system (1010 hPa).'
              ),
              risk_assessment: {
                thunderstorm: like('high'),
                heat_stress: like('moderate'),
                wind_damage: like('minimal'),
                precipitation: like('moderate')
              },
              analogs_summary: {
                most_similar_date: like('2022-11-28T06:00:00Z'),
                similarity_score: like(0.76),
                analog_count: like(32),
                outcome_description: like(
                  'Similar patterns typically resulted in afternoon thunderstorms'
                ),
                confidence_explanation: like(
                  'Based on 32 historical analog patterns'
                )
              },
              confidence_explanation: like(
                'Moderate confidence (80.0%) based on 32 analog patterns'
              ),
              versions: {
                model: like('v1.0.0'),
                index: like('v1.0.0'),
                datasets: like('v1.0.0'),
                api_schema: like('v1.1.0')
              },
              hashes: {
                model: like('a7c3f92'),
                index: like('2e8b4d1'),
                datasets: like('d4f8a91')
              },
              latency_ms: like(38.2)
            }
          }
        });
      });

      it('returns forecast with elevated thunderstorm risk based on CAPE', async () => {
        const api = setupApiClient('http://localhost:8089');

        const response = await api.get('/forecast', {
          params: { horizon: '6h', vars: 't2m,cape,msl' },
          headers: { Authorization: 'Bearer test-api-token' }
        });

        expect(response.status).toBe(200);
        expect(response.data.variables).toHaveProperty('cape');
        expect(response.data.risk_assessment.thunderstorm).toBe('high');
        expect(response.data.risk_assessment.heat_stress).toBe('moderate');
        expect(typeof response.data.variables.cape.value).toBe('number');
        expect(response.data.variables.cape.value).toBeGreaterThan(0);
      });
    });

    describe('error scenarios', () => {
      describe('invalid horizon parameter', () => {
        beforeEach(() => {
          return provider.addInteraction({
            state: 'forecast system is operational',
            uponReceiving: 'a request with invalid horizon parameter',
            withRequest: {
              method: 'GET',
              path: '/forecast',
              query: {
                horizon: 'invalid',
                vars: 't2m'
              },
              headers: {
                Authorization: 'Bearer test-api-token',
                'Content-Type': 'application/json'
              }
            },
            willRespondWith: {
              status: 400,
              headers: {
                'Content-Type': 'application/json'
              },
              body: {
                error: {
                  code: like(400),
                  message: like(
                    'Invalid request parameters: Invalid horizon. Must be one of: 6h, 12h, 24h, 48h'
                  ),
                  timestamp: iso8601DateTime(),
                  correlation_id: like('req-12345')
                }
              }
            }
          });
        });

        it('returns 400 error with structured error response', async () => {
          const api = setupApiClient('http://localhost:8089');

          try {
            await api.get('/forecast', {
              params: { horizon: 'invalid', vars: 't2m' },
              headers: { Authorization: 'Bearer test-api-token' }
            });
            fail('Expected request to fail');
          } catch (error) {
            expect(error.response.status).toBe(400);
            expect(error.response.data.error).toHaveProperty('code', 400);
            expect(error.response.data.error).toHaveProperty('message');
            expect(error.response.data.error).toHaveProperty('timestamp');
            expect(error.response.data.error.message).toContain(
              'Invalid horizon'
            );
          }
        });
      });

      describe('authentication failure', () => {
        beforeEach(() => {
          return provider.addInteraction({
            state: 'forecast system is operational',
            uponReceiving: 'a request with invalid authentication token',
            withRequest: {
              method: 'GET',
              path: '/forecast',
              query: {
                horizon: '24h',
                vars: 't2m'
              },
              headers: {
                Authorization: 'Bearer invalid-token',
                'Content-Type': 'application/json'
              }
            },
            willRespondWith: {
              status: 401,
              headers: {
                'Content-Type': 'application/json',
                'WWW-Authenticate': 'Bearer'
              },
              body: {
                error: {
                  code: like(401),
                  message: like('Invalid authentication token'),
                  timestamp: iso8601DateTime(),
                  correlation_id: like('req-67890')
                }
              }
            }
          });
        });

        it('returns 401 error for invalid authentication', async () => {
          const api = setupApiClient('http://localhost:8089');

          try {
            await api.get('/forecast', {
              params: { horizon: '24h', vars: 't2m' },
              headers: { Authorization: 'Bearer invalid-token' }
            });
            fail('Expected request to fail');
          } catch (error) {
            expect(error.response.status).toBe(401);
            expect(error.response.data.error).toHaveProperty('code', 401);
            expect(error.response.headers).toHaveProperty(
              'www-authenticate',
              'Bearer'
            );
          }
        });
      });

      describe('system unavailable', () => {
        beforeEach(() => {
          return provider.addInteraction({
            state: 'forecast system is down',
            uponReceiving: 'a request when system is unavailable',
            withRequest: {
              method: 'GET',
              path: '/forecast',
              query: {
                horizon: '24h',
                vars: 't2m'
              },
              headers: {
                Authorization: 'Bearer test-api-token',
                'Content-Type': 'application/json'
              }
            },
            willRespondWith: {
              status: 503,
              headers: {
                'Content-Type': 'application/json'
              },
              body: {
                error: {
                  code: like(503),
                  message: like('Forecasting system not ready'),
                  timestamp: iso8601DateTime(),
                  correlation_id: like('req-503')
                }
              }
            }
          });
        });

        it('returns 503 error when system is unavailable', async () => {
          const api = setupApiClient('http://localhost:8089');

          try {
            await api.get('/forecast', {
              params: { horizon: '24h', vars: 't2m' },
              headers: { Authorization: 'Bearer test-api-token' }
            });
            fail('Expected request to fail');
          } catch (error) {
            expect(error.response.status).toBe(503);
            expect(error.response.data.error).toHaveProperty(
              'message',
              'Forecasting system not ready'
            );
          }
        });
      });
    });
  });
});

// Helper function to set up API client
function setupApiClient(baseURL) {
  // Simple HTTP client for testing
  const axios = require('axios');
  return axios.create({
    baseURL,
    timeout: 5000,
    headers: {
      'Content-Type': 'application/json'
    }
  });
}
