# Adelaide Weather Frontend - Dependency Resolution Plan

## Executive Summary
The Adelaide Weather frontend has critical dependency conflicts preventing Docker builds. This plan resolves immediate blockers while establishing long-term dependency management practices.

## Critical Issues Identified

### 🚨 TIER 1 - BUILD BLOCKERS (Immediate Action Required)

#### 1. Bundle Analyzer Version Incompatibility
- **Current**: `@next/bundle-analyzer": "^16.0.1"`
- **Next.js**: `"next": "14.2.33"`
- **Problem**: Major version mismatch causing webpack build failures
- **Solution**: Downgrade to `"@next/bundle-analyzer": "^14.2.33"`

#### 2. ESLint Config Drift  
- **Current**: `"eslint-config-next": "14.0.3"`
- **Solution**: Update to `"eslint-config-next": "14.2.33"`

#### 3. Docker Build Strategy Flaw
- **Problem**: Dockerfile installs production-only deps but needs dev deps for build
- **Current**: `RUN npm ci --only=production` then `RUN npm run build` (FAILS)
- **Solution**: Multi-stage build with full dependencies in build stage

### ⚡ TIER 2 - HIGH PRIORITY (Stability & Security)

#### 4. Playwright Docker Compatibility
- **Current**: `"@playwright/test": "1.40.1"` (known Alpine issues)
- **Solution**: `"@playwright/test": "^1.45.0"` (last verified stable on Node 18-alpine)

#### 5. TypeScript ESLint Security Risk
- **Current**: `"@typescript-eslint/*": "^6.21.0"` (2 major versions behind)
- **Solution**: `"@typescript-eslint/*": "^7.18.0"`

#### 6. TypeScript Version Update
- **Current**: `"typescript": "5.3.3"`
- **Solution**: `"typescript": "5.6.3"` (better React 18 support)

### 📊 TIER 3 - PERFORMANCE & FEATURES

#### 7. Animation Library Optimization
- **Current**: `"framer-motion": "^10.16.4"`
- **Solution**: `"framer-motion": "^11.11.0"` (better performance, smaller bundle)

#### 8. React Query Updates
- **Current**: `"@tanstack/react-query": "^5.8.4"`
- **Solution**: `"@tanstack/react-query": "^5.90.7"`

## Implementation Strategy

### Phase 1: Critical Fixes (Day 1)
1. Update bundle analyzer and ESLint config
2. Implement multi-stage Dockerfile
3. Test Docker build process

### Phase 2: Security & Stability (Week 1)
1. Update Playwright and TypeScript toolchain
2. Run security audit and fix vulnerabilities
3. Update CI/CD pipeline

### Phase 3: Performance Optimization (Week 2)
1. Update animation and state management libraries
2. Bundle analysis and optimization
3. Performance baseline establishment

## Docker Build Fix

### Current (Broken) Dockerfile
```dockerfile
FROM node:18-alpine as base
ENV NODE_ENV=production
COPY package*.json ./
RUN npm ci --only=production --ignore-scripts  # Missing dev deps needed for build
COPY . .
RUN npm run build  # FAILS - Tailwind, PostCSS, TS types not available
```

### Fixed Multi-Stage Dockerfile
```dockerfile
# Build stage - includes all dependencies
FROM node:18-alpine AS build
WORKDIR /app

# Install all dependencies (including dev deps for build)
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Prune dev dependencies for production
RUN npm prune --production

# Production stage - optimized runtime image
FROM node:18-alpine AS production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

WORKDIR /app

# Copy only production artifacts
COPY --from=build --chown=nextjs:nodejs /app/.next ./.next
COPY --from=build --chown=nextjs:nodejs /app/public ./public
COPY --from=build --chown=nextjs:nodejs /app/package*.json ./
COPY --from=build --chown=nextjs:nodejs /app/node_modules ./node_modules

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

CMD ["npm", "start"]
```

## Long-Term Recommendations

### 1. Dependency Management Automation
```json
// Add to package.json
"renovate.json": {
  "extends": ["config:base"],
  "schedule": ["before 9am on monday"],
  "groupName": "Next.js ecosystem",
  "matchPackagePatterns": ["^@next/", "^next", "^eslint-config-next"]
}
```

### 2. Node.js Version Planning
- **Current**: Node 18 (entering maintenance mode Oct 2024)
- **Recommendation**: Plan migration to Node 20 LTS by Q1 2025
- **Consideration**: Switch from Alpine to Debian slim for better compatibility

### 3. Security Hardening
```javascript
// next.config.js - Enforce production secrets
env: {
  API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:8000',
  API_TOKEN: process.env.NODE_ENV === 'production' 
    ? process.env.API_TOKEN || (() => { throw new Error('API_TOKEN required in production') })()
    : process.env.API_TOKEN || 'dev-token-change-in-production'
}
```

### 4. CI/CD Optimization
- Move extensive analysis scripts to weekly scheduled jobs
- Keep core pipeline: lint, test, type-check, build
- Add automated dependency vulnerability scanning

## Risk Assessment

### High Risk (Immediate)
- Build failures blocking deployments
- Security vulnerabilities in outdated packages
- CI/CD pipeline instability

### Medium Risk (Short-term)
- Performance degradation from outdated libraries
- Developer experience issues
- Bundle size growth

### Low Risk (Long-term)
- Node.js version end-of-life
- Framework migration needs
- Technical debt accumulation

## Success Metrics

### Build Stability
- [ ] Docker build success rate: 100%
- [ ] CI/CD pipeline reliability: >99%
- [ ] Build time optimization: <30% reduction

### Security Posture
- [ ] Zero high/critical CVEs in dependencies
- [ ] Automated vulnerability scanning
- [ ] Regular dependency updates

### Performance
- [ ] Bundle size reduction: >15%
- [ ] First contentful paint improvement
- [ ] Lighthouse performance score: >90

## Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| 1 | 1-2 days | Critical dependency fixes, Docker build working |
| 2 | 1 week | Security updates, stable CI/CD |
| 3 | 1-2 weeks | Performance optimization, monitoring |

## Next Steps

1. **Immediate**: Apply Tier 1 fixes and test Docker build
2. **Day 2**: Implement multi-stage Dockerfile
3. **Week 1**: Complete security updates and establish monitoring
4. **Week 2**: Performance optimization and documentation

This plan ensures the Adelaide Weather frontend becomes build-stable while establishing practices to prevent future dependency conflicts.