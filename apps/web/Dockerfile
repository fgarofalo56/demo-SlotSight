# ═══════════════════════════════════════════════════════════════════════════
# SlotSight web — multi-stage build
#
# Stage 1 builds the Vite bundle; stage 2 serves the static output from nginx.
# The Node toolchain never reaches the runtime image.
# ═══════════════════════════════════════════════════════════════════════════

FROM node:26-alpine AS builder

RUN corepack enable

WORKDIR /build

# Dependency layer first so a source change does not re-install node_modules.
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile || pnpm install

COPY . .
RUN pnpm exec tsc --noEmit && pnpm exec vite build


# ═══════════════════════════════════════════════════════════════════════════
FROM nginx:1.27-alpine AS runtime

COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# nginx:alpine ships an unprivileged `nginx` user; use it.
RUN touch /var/run/nginx.pid \
    && chown -R nginx:nginx /var/run/nginx.pid /var/cache/nginx /usr/share/nginx/html

USER nginx

EXPOSE 8080

HEALTHCHECK --interval=20s --timeout=4s --start-period=8s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
