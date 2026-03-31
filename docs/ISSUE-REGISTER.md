# Issue Register — Adelaide Weather Forecasting System

**Audit Date:** 2026-03-31
**Status:** Verified against source code. 34 confirmed issues, 6 false positives dismissed.

---

## Critical (4) — System won't work correctly

### C1: Missing `await` on Async Forecast Call
- **Files:** `api/main.py:702`, `api/main.py:707`
- **Description:** `forecast_adapter.forecast_with_uncertainty()` is `async def` but called without `await`. Returns a coroutine object instead of a dict. The `/forecast` endpoint is broken — `if var in forecast_result:` fails.
- **Fix:** Add `await` to both call sites. Verify calling function is already `async def`.
- **Assigned:** backend-fixer

### C2: Import Path Error in Exception Handlers
- **Files:** `api/main.py:1067`, `api/main.py:1117`
- **Description:** `from security_middleware import SecurityMiddleware` should be `from api.security_middleware import SecurityMiddleware`. The project root is on sys.path (line 51), not `api/`. Crashes on any HTTPException or unhandled exception.
- **Fix:** Change import path to `from api.security_middleware import SecurityMiddleware` at both locations.
- **Assigned:** backend-fixer

### C3: Variable Count Mismatch (9 vs 11)
- **Files:** `core/model_loader.py:185`, `core/real_time_embedder.py:48`, `core/analog_forecaster.py:75-85`, `core/model_loader.py:490`
- **Description:** CNN model initialized with `num_variables=11` but embedder uses `num_variables=9` and forecaster lists 9 variables. Passing 9-channel tensor to 11-channel conv layer crashes with shape error. Test function at `model_loader.py:490` also uses 9 channels against 11-channel model.
- **Fix:** Trace full pipeline to determine ground truth (9 or 11). Align all files. Update test function.
- **Assigned:** ml-engineer

### C4: Unsafe Pickle Loading
- **Files:** `core/model_loader.py:361-365`
- **Description:** `torch.load(model_path, map_location='cpu', weights_only=False)` allows arbitrary code execution. Lines 361-362 add `ProductionTrainingConfig` to `sys.modules` to handle unpickling.
- **Fix:** Use `weights_only=True` if possible. If checkpoint requires custom classes, gate `weights_only=False` behind explicit env var and document the risk.
- **Assigned:** ml-engineer

---

## High (6) — Wrong results or security gaps

### H1: Hardcoded Mock Hashes and Dates
- **Files:** `api/main.py:604`, `api/main.py:800-804`, `api/main.py:912-920`
- **Description:** Hash values `a7c3f92`, `2e8b4d1`, `d4f8a91` and `most_similar_date="2023-03-15T12:00:00Z"` are static strings in both `/forecast` and `/health` responses. Never reflect actual system state.
- **Fix:** Replace with computed values from model checkpoint info, or mark clearly as TODO placeholders that don't pretend to be real.
- **Assigned:** backend-fixer

### H2: No SSL/TLS in Nginx
- **Files:** `nginx/nginx.conf:209-223`
- **Description:** Entire HTTPS server block is commented out. Server only listens on port 80.
- **Fix:** Uncomment and configure HTTPS block with TLS 1.2+ and strong ciphers. Add cert path placeholders with operator instructions. Add HTTP-to-HTTPS redirect.
- **Note:** Actual certificate provisioning requires operator action.
- **Assigned:** security-auditor

### H3: Wildcard CORS in Nginx
- **Files:** `nginx/nginx.conf:120, 127-128, 158-159`
- **Description:** `Access-Control-Allow-Origin "*"` on all API routes overrides FastAPI's restricted CORS middleware (`CORS_ORIGINS` env var at `main.py:152`).
- **Fix:** Remove nginx-level CORS headers and let FastAPI handle CORS, OR make nginx read from the same `CORS_ORIGINS` config.
- **Assigned:** security-auditor

### H4: Health Check Leaks Exception Details
- **Files:** `api/main.py:940`
- **Description:** `raise HTTPException(500, f"Health check failed: {str(e)}")` includes raw exception string. The `/forecast` endpoint correctly checks `ENVIRONMENT != "production"` (line 822) but `/health` doesn't.
- **Fix:** Apply same environment-gated error sanitization as `/forecast`.
- **Assigned:** backend-fixer

### H5: Humidity Conversion Scientifically Wrong
- **Files:** `api/forecast_adapter.py:286-294`
- **Description:** Uses `conversion_factor = 15000` (flat multiplier) to convert specific humidity (kg/kg) to relative humidity (%). Physically meaningless. Correct method requires Bolton/Tetens formula with temperature and pressure.
- **Fix:** Implement proper q -> RH conversion using saturation vapour pressure. Use t850 as temperature input if available.
- **Assigned:** meteorologist

### H6: MSL Pressure is a Placeholder
- **Files:** `api/forecast_adapter.py:296-312`
- **Description:** Derives MSL from z500 with linear scaling `-(point_value - 5500) * 0.1`. Code comments say "placeholder." Hardcoded +/-5 hPa uncertainty.
- **Fix:** Implement hypsometric equation or clearly document as unavailable if required variables are missing.
- **Assigned:** meteorologist

---

## Medium (8) — Degraded quality or maintainability

### M1: Bare `except:` Blocks in Token Manager
- **Files:** `api/enhanced_token_manager.py:187`, `api/enhanced_token_manager.py:213`
- **Description:** Bare `except:` catches SystemExit, KeyboardInterrupt, etc. Should be `except Exception:`.
- **Assigned:** backend-fixer

### M2: Token First-8-Chars Logged
- **Files:** `api/main.py:233`, `api/main.py:250`, `api/main.py:263`
- **Description:** Logs `credentials.credentials[:8] + "..."`. Reveals 25% of a 32-char token.
- **Fix:** Replace with hashed hint: `hashlib.sha256(token.encode()).hexdigest()[:12]`.
- **Assigned:** backend-fixer

### M3: FAISS Health Monitor Memory Leak
- **Files:** `api/services/faiss_health_monitoring.py:120`
- **Description:** `self._completed_queries: List[FAISSQueryMetrics] = []` is appended to but never pruned. `_latency_samples` at line 132 IS bounded (`_max_samples = 1000`) but `_completed_queries` was missed.
- **Fix:** Add max size and pruning, matching the pattern used for `_latency_samples`.
- **Assigned:** backend-fixer

### M4: Inconsistent Variable Validation
- **Files:** `api/variables.py:264`, `api/security_middleware.py:47`
- **Description:** Two implementations: chain of 11 `.replace()` calls vs clean regex `^[a-zA-Z0-9_]{1,20}$`. Both validate the same thing differently.
- **Fix:** Consolidate to one shared validation approach (the regex).
- **Assigned:** security-auditor

### M5: Spatial Expansion Broadcasts Scalar to Grid
- **Files:** `core/real_time_embedder.py:140-146`
- **Description:** Broadcasts single scalar to 16x16 grid. Comment says "Real implementation would use spatial interpolation." CNN trained on spatial patterns will produce degraded embeddings.
- **Fix:** Document limitation clearly. If spatial data is available, implement interpolation. Otherwise add TODO with explanation.
- **Assigned:** ml-engineer

### M6: Prometheus CIDR Too Broad
- **Files:** `nginx/nginx.conf:183`
- **Description:** `allow 172.0.0.0/8` covers 16.7M addresses. Docker typically uses `172.17.0.0/16`.
- **Fix:** Restrict to `172.16.0.0/12` (Docker's allocated range) or specific deployment subnet.
- **Assigned:** security-auditor

### M7: Mock Analog Fallback Not Surfaced to Clients
- **Files:** `api/forecast_adapter.py:176-215`
- **Description:** When FAISS is unavailable, generates random indices. Metadata tags `fallback_mode: True` but this flag isn't in the API response — clients can't tell they're getting random data.
- **Fix:** Surface `fallback_mode` in the API response so clients can distinguish real from mock forecasts.
- **Assigned:** backend-fixer

### M8: No Distance-Based Analog Quality Cutoff
- **Files:** `core/analog_forecaster.py:265-269`
- **Description:** Takes top-N analogs without distance cutoff. Softmax weighting mitigates but doesn't eliminate outlier contribution.
- **Fix:** Add optional distance-based filter before weighting. Keep soft weighting as primary mechanism.
- **Assigned:** meteorologist

---

## Low (6) — Minor quality or theoretical risk

### L1: Thread Limits Set at Import Time
- **Files:** `core/real_time_embedder.py:33-34`
- **Description:** `os.environ['OMP_NUM_THREADS'] = '2'` runs at import, overriding container/user settings.
- **Note:** Performance-only impact. Low priority.
- **Assigned:** ml-engineer (alongside M5 work in same file)

### L2: Cache Has No Max Size
- **Files:** `api/performance_middleware.py:20-76`
- **Description:** `ForecastCache` has no max entries. Small keyspace limits practical risk.
- **Assigned:** security-auditor (during M4 pass)

### L3: CSP Allows `unsafe-inline` for Styles
- **Files:** `api/security_middleware.py:79`
- **Description:** `style-src 'self' 'unsafe-inline'` in CSP. No practical effect on JSON API.
- **Assigned:** security-auditor

### L4: SQL Injection Regex Could False-Positive
- **Files:** `api/security_middleware.py:51-55`
- **Description:** Flags words like "select" in any input. No legitimate weather API input would trigger this.
- **Note:** Document as known limitation. Low priority.
- **Assigned:** security-auditor

### L5: Quantile Staircase Method Lacks Interpolation
- **Files:** `core/analog_forecaster.py:183-192`
- **Description:** Standard staircase method. Interpolation would improve smoothness marginally with ~50 analogs.
- **Assigned:** meteorologist

### L6: Emojis in Production Logs
- **Files:** `api/main.py:432-498`
- **Description:** Log messages use emojis. Structured logging systems may not render correctly.
- **Assigned:** backend-fixer

---

## Infrastructure (10)

### I1: `.env.production` Tracked in Git
- **Description:** Contains placeholder secrets (`API_TOKEN=your-secure-production-token-here-change-this`). Pattern encourages committing real values.
- **Fix:** Add to `.gitignore`. Ensure `.env.example` has all keys with placeholder values.
- **Assigned:** infra-reviewer

### I2: CI/CD Pre-Deployment Gates Are No-Ops
- **Files:** `.github/workflows/production-deployment.yml:99, 109, 189`
- **Description:** Security validation, performance baseline, and capacity checks are `echo "passed"` stubs with "In real implementation" comments.
- **Fix:** Either implement properly or remove and document as TODO.
- **Assigned:** infra-reviewer

### I3: No Centralized Logging
- **Description:** Prometheus/Grafana for metrics only. No log aggregation (ELK/Loki/Datadog). Application logs go to stdout with no collection.
- **Fix:** Document requirement. Suggest pragmatic option (e.g. Loki + Promtail in docker-compose). Requires human decision on stack choice.
- **Assigned:** infra-reviewer (deferred — needs human input)

### I4: DR Plan Documented but Unvalidated
- **Files:** `ops/production-readiness/disaster-recovery-validation.md`
- **Description:** RTO 4h / RPO 1h documented. Claims "PRODUCTION READY." Not tested.
- **Fix:** Flag as unvalidated. No code change needed.
- **Assigned:** infra-reviewer (document-only)

### I5: Production Runs Older Images Than Staging
- **Description:** nginx 1.24 vs 1.25, prometheus 2.40 vs 2.45, grafana 9.3 vs 10.0.
- **Fix:** Standardize to latest stable version across all docker-compose files.
- **Assigned:** infra-reviewer

### I6: Helm Chart Has No Templates
- **Files:** `helm/adelaide-weather-forecast/`
- **Description:** Only Chart.yaml + values.yaml. No templates/ directory. Chart is unusable.
- **Fix:** Either add minimal templates or document as aspirational/future work.
- **Assigned:** infra-reviewer

### I7: Redis Prometheus Scrape Misconfigured
- **Files:** `monitoring/prometheus.yml:35-37`
- **Description:** Targets `redis:6379` directly. Redis doesn't expose Prometheus metrics. Needs redis_exporter sidecar.
- **Fix:** Add redis_exporter to docker-compose monitoring stack, update prometheus scrape target.
- **Assigned:** infra-reviewer

### I8: 21 of 24 Core Modules Untested
- **Description:** Only config_drift_detector, resource_guardrails, and secure_credential_manager have any tests. model_loader, analog_forecaster, real_time_embedder, device_manager, etc. have none.
- **Fix:** test-writer agent creates regression tests after fixes are applied.
- **Assigned:** test-writer

### I9: No Python Lock File, Mixed Version Pinning
- **Files:** `requirements.txt`, `api/requirements.txt`, `monitoring/synthetic/requirements.txt`
- **Description:** Main uses `>=`, api uses `==`. Duplicate `prometheus-client` in api/requirements.txt (lines 13 and 33). Version mismatch in monitoring (0.17.1 vs 0.19.0).
- **Fix:** Consolidate to exact pins. Remove duplicates. Align versions.
- **Assigned:** infra-reviewer

### I10: python-jose 3.3.0 (6 Years Old)
- **Files:** `api/requirements.txt:10`
- **Description:** `python-jose[cryptography]==3.3.0` released June 2020. Effectively unmaintained. Handles JWT authentication.
- **Fix:** Evaluate replacement (PyJWT or authlib). Flag as TODO if migration is non-trivial.
- **Assigned:** infra-reviewer

---

## False Positives (Dismissed)

| # | Claimed Issue | Why Dismissed |
|---|--------------|---------------|
| F1 | Zero filtering for temperature (analog_forecaster.py:158) | Correct for Kelvin — 0K is absolute zero |
| F2 | L2 normalization of zero vectors (model_loader.py:276) | PyTorch F.normalize has default eps=1e-12 |
| F3 | SeasonalEmbedding dimension fragility (model_loader.py:141) | Hardcoded 32, 32//2=16 each, consistent |
| F4 | LeadTimeEmbedding max too low (model_loader.py:115) | Max 72h > forecast max 48h, clamped |
| F5 | MD5 for cache keys (performance_middleware.py:34) | Fine for non-security cache key hashing |
| F6 | Rate limiting applied after auth (main.py:625) | SlowAPI middleware runs before endpoint body |
