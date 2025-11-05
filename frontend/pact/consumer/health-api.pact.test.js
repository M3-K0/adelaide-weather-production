/**
 * Pact Consumer Tests for Health API Endpoint
 *
 * Tests the /health endpoint contract for system monitoring and status checks.
 * This endpoint is used by the frontend to display system status and operational readiness.
 */

const { Pact, Matchers } = require('@pact-foundation/pact');
const path = require('path');

const { like, eachLike, term, iso8601DateTime } = Matchers;

describe('Adelaide Weather Health API', () => {
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

  describe('GET /health', () => {
    describe('healthy system status', () => {
      beforeEach(() => {
        const expectedResponse = {
          ready: like(true),
          checks: eachLike(
            {
              name: like('startup_validation'),
              status: like('pass'),
              message: like('Expert startup validation passed')
            },
            { min: 2 }
          ),
          model: {
            version: like('v1.0.0'),
            hash: like('a7c3f92'),
            matched_ratio: like(1.0)
          },
          index: {
            ntotal: like(13148),
            dim: like(256),
            metric: like('L2'),
            hash: like('2e8b4d1'),
            dataset_hash: like('d4f8a91')
          },
          datasets: eachLike(
            {
              horizon: like('6h'),
              valid_pct_by_var: {
                t2m: like(99.5),
                u10: like(99.2),
                v10: like(99.2),
                msl: like(99.8),
                cape: like(95.1)
              },
              hash: like('d4f8a91'),
              schema_version: like('v1.0.0')
            },
            { min: 4 }
          ),
          deps: {
            fastapi: like('0.104.1'),
            torch: like('2.0.1'),
            faiss: like('1.7.4')
          },
          preprocessing_version: like('v1.0.0'),
          uptime_seconds: like(3600.5)
        };

        return provider.addInteraction({
          state: 'system is healthy and operational',
          uponReceiving: 'a request for system health status',
          withRequest: {
            method: 'GET',
            path: '/health'
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

      it('returns comprehensive health status when system is operational', async () => {
        const api = setupApiClient('http://localhost:8089');

        const response = await api.get('/health');

        expect(response.status).toBe(200);
        expect(response.data).toHaveProperty('ready', true);
        expect(response.data).toHaveProperty('checks');
        expect(response.data).toHaveProperty('model');
        expect(response.data).toHaveProperty('index');
        expect(response.data).toHaveProperty('datasets');
        expect(response.data).toHaveProperty('deps');
        expect(response.data).toHaveProperty('uptime_seconds');

        // Validate checks structure
        expect(Array.isArray(response.data.checks)).toBe(true);
        expect(response.data.checks.length).toBeGreaterThan(0);
        response.data.checks.forEach(check => {
          expect(check).toHaveProperty('name');
          expect(check).toHaveProperty('status');
          expect(check).toHaveProperty('message');
        });

        // Validate model info
        expect(response.data.model).toHaveProperty('version');
        expect(response.data.model).toHaveProperty('hash');
        expect(response.data.model).toHaveProperty('matched_ratio');

        // Validate index info
        expect(response.data.index).toHaveProperty('ntotal');
        expect(response.data.index).toHaveProperty('dim');
        expect(response.data.index).toHaveProperty('metric');

        // Validate datasets
        expect(Array.isArray(response.data.datasets)).toBe(true);
        response.data.datasets.forEach(dataset => {
          expect(dataset).toHaveProperty('horizon');
          expect(dataset).toHaveProperty('valid_pct_by_var');
          expect(dataset).toHaveProperty('hash');
          expect(dataset).toHaveProperty('schema_version');
        });
      });
    });

    describe('unhealthy system status', () => {
      beforeEach(() => {
        const expectedResponse = {
          ready: like(false),
          checks: eachLike(
            {
              name: like('startup_validation'),
              status: like('fail'),
              message: like('System not initialized')
            },
            { min: 1 }
          ),
          model: {
            version: like('unknown'),
            hash: like('unknown'),
            matched_ratio: like(0.0)
          },
          index: {
            ntotal: like(0),
            dim: like(0),
            metric: like('unknown'),
            hash: like('unknown'),
            dataset_hash: like('unknown')
          },
          datasets: [],
          deps: {},
          preprocessing_version: like('unknown'),
          uptime_seconds: like(0.0)
        };

        return provider.addInteraction({
          state: 'system is not ready',
          uponReceiving: 'a request for health status when system is not ready',
          withRequest: {
            method: 'GET',
            path: '/health'
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

      it('returns unhealthy status when system is not ready', async () => {
        const api = setupApiClient('http://localhost:8089');

        const response = await api.get('/health');

        expect(response.status).toBe(200);
        expect(response.data).toHaveProperty('ready', false);
        expect(
          response.data.checks.some(check => check.status === 'fail')
        ).toBe(true);
        expect(response.data.model.version).toBe('unknown');
        expect(response.data.index.ntotal).toBe(0);
        expect(response.data.datasets).toEqual([]);
      });
    });

    describe('rate limited health requests', () => {
      beforeEach(() => {
        return provider.addInteraction({
          state: 'health endpoint is rate limited',
          uponReceiving: 'too many health check requests',
          withRequest: {
            method: 'GET',
            path: '/health'
          },
          willRespondWith: {
            status: 429,
            headers: {
              'Content-Type': 'application/json',
              'Retry-After': '60'
            },
            body: {
              error: {
                code: like(429),
                message: like('Rate limit exceeded'),
                timestamp: iso8601DateTime(),
                correlation_id: like('req-rate-limit')
              }
            }
          }
        });
      });

      it('returns 429 when rate limit is exceeded', async () => {
        const api = setupApiClient('http://localhost:8089');

        try {
          await api.get('/health');
          fail('Expected request to fail with rate limit');
        } catch (error) {
          expect(error.response.status).toBe(429);
          expect(error.response.headers).toHaveProperty('retry-after', '60');
          expect(error.response.data.error).toHaveProperty('code', 429);
          expect(error.response.data.error.message).toContain('Rate limit');
        }
      });
    });
  });
});

// Helper function to set up API client
function setupApiClient(baseURL) {
  const axios = require('axios');
  return axios.create({
    baseURL,
    timeout: 5000,
    headers: {
      'Content-Type': 'application/json'
    }
  });
}
