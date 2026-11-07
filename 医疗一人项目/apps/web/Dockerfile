FROM node:22.23.4-alpine@sha256:fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914 AS builder

ARG NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL} \
    CI=true

RUN npm install --global pnpm@11.25.0
WORKDIR /app
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile

COPY apps/web apps/web
WORKDIR /app/apps/web
RUN pnpm build

FROM node:22.23.4-alpine@sha256:fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914 AS runner

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 10001 nodeapp \
    && adduser --system --uid 10001 --ingroup nodeapp nodeapp
WORKDIR /app

COPY --from=builder --chown=nodeapp:nodeapp /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nodeapp:nodeapp /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nodeapp:nodeapp /app/apps/web/public ./apps/web/public

USER nodeapp
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
