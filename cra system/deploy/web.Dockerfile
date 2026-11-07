FROM node:24.22.2-bookworm-slim AS build

WORKDIR /build
COPY web/package.json web/package-lock.json ./
RUN npm ci --ignore-scripts
COPY web ./
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.29-alpine

COPY deploy/nginx.runtime.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/dist /usr/share/nginx/html

EXPOSE 8080
