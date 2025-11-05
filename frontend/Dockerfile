# Adelaide Weather Forecasting UI - Production Dockerfile
FROM node:18-alpine as base

# Set environment variables
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV CI=true

# Install system dependencies
RUN apk update && apk add --no-cache curl

# Create app user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Set work directory
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production --ignore-scripts

# Copy application code
COPY . .

# Generate TypeScript types if needed
RUN npm run generate-types || true

# Build application
RUN npm run build

# Set ownership and permissions
RUN chown -R nextjs:nodejs /app
USER nextjs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

# Expose port
EXPOSE 3000

# Production command
CMD ["npm", "start"]