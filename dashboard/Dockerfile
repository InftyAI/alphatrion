FROM node:24-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM caddy:2-alpine

# Create non-root user and set up directories
RUN adduser -D -u 1000 -g 1000 caddy && \
    mkdir -p /usr/share/caddy /config /data && \
    chown -R caddy:caddy /usr/share/caddy /config /data

# Copy index.html to root, assets to /static/assets
COPY --from=build /app/static/index.html /usr/share/caddy/
COPY --from=build /app/static/assets /usr/share/caddy/static/assets

COPY Caddyfile /etc/caddy/Caddyfile

# Switch to non-root user
USER caddy

EXPOSE 8080