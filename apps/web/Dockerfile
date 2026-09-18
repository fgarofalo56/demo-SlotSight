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

# A TEMPLATE, not a config. The nginx image substitutes ${API_URL} and
# ${DNS_RESOLVER} into it at container start and writes the result to
# /etc/nginx/conf.d/. That is what lets the same image work behind Docker
# Compose (upstream `api`) and in Azure Container Apps (an https FQDN).
COPY nginx.default.conf.template /etc/nginx/templates/default.conf.template

# Sourced by the nginx entrypoint before templates are rendered. Discovers the
# platform's real nameserver, because no single resolver IP works in both
# Docker and Container Apps. See the script for the full story.
COPY docker-entrypoint.d/10-set-dns-resolver.envsh /docker-entrypoint.d/10-set-dns-resolver.envsh

# Compose default. Azure Container Apps overrides it — see
# infra/modules/containerapps.bicep.
ENV API_URL=http://api:8000
# "auto" means: discover it from /etc/resolv.conf at start.
ENV DNS_RESOLVER=auto

RUN chmod +x /docker-entrypoint.d/10-set-dns-resolver.envsh \
    && touch /var/run/nginx.pid \
    && chown -R nginx:nginx /var/run/nginx.pid /var/cache/nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /etc/nginx/conf.d

USER nginx

EXPOSE 8080

HEALTHCHECK --interval=20s --timeout=4s --start-period=8s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
