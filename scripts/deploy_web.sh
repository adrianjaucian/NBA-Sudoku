#!/usr/bin/env bash
# Deploy web/ to a free Netlify subdomain (anonymous drop).
set -euo pipefail
cd "$(dirname "$0")/../web"
npx --yes netlify-cli@latest deploy --dir=. --prod --allow-anonymous --message "${1:-TEAMMATE NBA Sudoku deploy}"
