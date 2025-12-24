#!/usr/bin/env bash
set -euo pipefail

python scripts/gen_sample_traces.py

cd web
npm run build
npm run capture:screenshots
