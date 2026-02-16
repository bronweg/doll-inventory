#!/bin/sh
set -e

# Generate runtime config from environment variables
# If VITE_API_BASE_URL is not set, construct it from window.location
cat > /app/dist/config.js << EOF
// Runtime configuration - generated from environment variables
(function() {
  var apiBaseUrl = '${VITE_API_BASE_URL:-}';

  // If API_BASE_URL is not set, use the current host with port 8000
  if (!apiBaseUrl) {
    var protocol = window.location.protocol;
    var hostname = window.location.hostname;
    apiBaseUrl = protocol + '//' + hostname + ':8000';
  }

  window.__RUNTIME_CONFIG__ = {
    API_BASE_URL: apiBaseUrl,
    BAGS_COUNT: ${VITE_BAGS_COUNT:-3}
  };
  window.__API_BASE_URL__ = window.__RUNTIME_CONFIG__.API_BASE_URL;
  window.__BAGS_COUNT__ = window.__RUNTIME_CONFIG__.BAGS_COUNT;
})();
EOF

echo "Generated runtime config:"
cat /app/dist/config.js

# Execute the main command
exec "$@"

