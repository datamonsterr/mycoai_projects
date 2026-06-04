# syntax=docker/dockerfile:1

# =============================================================================
# MycoAI Frontend — Multi-stage Dockerfile
# =============================================================================
# Targets:
#   deps  → installs node_modules via pnpm (shared cache layer)
#   dev   → Vite dev server with HMR (default for compose)
#   prod  → nginx serving built static files
#
# Build:
#   docker build -t mycoai-frontend:dev --target dev frontend/
#   docker build -t mycoai-frontend:prod --target prod frontend/
# =============================================================================

# ---- Dependencies layer (shared) --------------------------------------------
FROM node:25-alpine AS deps
RUN npm install -g pnpm
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile


# ---- Development (Vite HMR) -------------------------------------------------
FROM node:25-alpine AS dev
RUN npm install -g pnpm
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 5173
CMD ["pnpm", "dev", "--host", "0.0.0.0"]


# ---- Build (production assets) ----------------------------------------------
FROM node:25-alpine AS build
RUN npm install -g pnpm
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build


# ---- Production (nginx) -----------------------------------------------------
FROM nginx:1.27-alpine AS prod

RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup && \
    touch /var/run/nginx.pid && \
    chown -R appuser:appgroup /var/run/nginx.pid \
                              /var/cache/nginx \
                              /var/log/nginx

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

USER 1001
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
