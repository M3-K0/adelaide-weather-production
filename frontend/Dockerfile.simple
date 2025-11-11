# Adelaide Weather Forecasting UI - Simple Production Dockerfile
# Uses pre-built application from local .next directory

FROM node:18-alpine AS production

# Create app user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Set work directory
WORKDIR /app

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copy pre-built application (using local successful build)
COPY .next/standalone ./
COPY .next/static ./.next/static
COPY public ./public

# Change ownership to nextjs user
RUN chown -R nextjs:nodejs /app

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Basic health check using Node.js (no external dependencies)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD node -e "const http = require('http'); const req = http.request('http://localhost:3000/api/health', res => process.exit(res.statusCode === 200 ? 0 : 1)); req.on('error', () => process.exit(1)); req.end();"

# Production command
CMD ["node", "server.js"]