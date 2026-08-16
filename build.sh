#!/usr/bin/env bash
# Build both frontends into frontend/dist/, ready for `wrangler deploy`.
#
# Existing trading-journal frontend  →  frontend/dist/
# New tej-capital frontend           →  frontend/dist/tej-capital/
#
# TEJ_CAPITAL_API_URL: baked into the tej-capital frontend at build time.
# Defaults to the Render service URL; override in Cloudflare Workers project
# settings (build vars) if Render assigned a different name.

set -euo pipefail
cd "$(dirname "$0")"

: "${TEJ_CAPITAL_API_URL:=https://tej-capital-api.onrender.com/api}"

echo "▶ Building trading-journal frontend"
(cd frontend && npm ci && npm run build)

echo "▶ Building tej-capital frontend"
(
  cd tej-capital/frontend
  npm ci
  VITE_TEJ_CAPITAL_API_URL="$TEJ_CAPITAL_API_URL" npm run build
)

echo "▶ Nesting tej-capital under /tej-capital/"
rm -rf frontend/dist/tej-capital
cp -r tej-capital/frontend/dist frontend/dist/tej-capital

echo "✔ frontend/dist ready"
