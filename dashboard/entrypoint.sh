#!/bin/sh
set -e

# Generate runtime configuration file
# This allows runtime configuration of the backend API URL
cat > /usr/share/nginx/html/config.js <<EOF
window.ENV = {
  VITE_API_URL: "${VITE_API_URL:-}"
};
EOF

echo "Generated runtime config:"
cat /usr/share/nginx/html/config.js

# Start nginx
exec nginx -g 'daemon off;'
