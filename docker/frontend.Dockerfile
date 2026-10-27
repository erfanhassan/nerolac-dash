# ==============================================================================
# Nerolac Operations Dashboard - Production Frontend Dockerfile
# Multi-Stage Build: Node 20-alpine | Next.js 15 Standalone | Non-Root User
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Dependency Installation
# ------------------------------------------------------------------------------
FROM node:20-alpine AS deps

# Install libc6-compat for Alpine compatibility with process bindings
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json ./

# Install clean, frozen dependencies
RUN npm ci

# ------------------------------------------------------------------------------
# Stage 2: Next.js Production Build
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy installed dependencies
COPY --from=deps /app/node_modules ./node_modules

# Copy full application source
COPY . .

# Environment flags for optimized production artifact compilation
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

# Compile Next.js 15 App Router into standalone build
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 3: Hardened Runtime Container
# ------------------------------------------------------------------------------
FROM node:20-alpine AS runner

LABEL maintainer="Nerolac DevOps Engineering <devops@nerolac.bd>"
LABEL description="Production Next.js 15 Frontend for Nerolac Operations Dashboard"
LABEL security.non-root="true"

WORKDIR /app

# Install wget for lightweight healthcheck probing
RUN apk add --no-cache wget

# Create non-root system group and user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Set runtime production environment
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

# Create public assets directory if needed
RUN mkdir -p /app/public && chown nextjs:nodejs /app/public

# Copy compiled Next.js standalone runtime with non-root ownership
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Enforce non-root execution
USER nextjs

# Expose Next.js server port
EXPOSE 3000

# Container liveness and readiness probe
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3000/ || exit 1

# Launch standalone Node.js server
CMD ["node", "server.js"]
