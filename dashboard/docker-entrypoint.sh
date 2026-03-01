#!/bin/sh
set -e

# Write config.json with userId and teamId from environment variables
cat > /usr/share/caddy/config.json <<EOF
{
  "userId": "${ALPHATRION_DASHBOARD_USER_ID:-}",
  "teamId": "${ALPHATRION_DASHBOARD_TEAM_ID:-}"
}
EOF

echo "Created config.json with userId=${ALPHATRION_DASHBOARD_USER_ID:-} teamId=${ALPHATRION_DASHBOARD_TEAM_ID:-}"

# Start Caddy
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
