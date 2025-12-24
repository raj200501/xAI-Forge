#!/usr/bin/env bash
set -euo pipefail

python -m xaiforge serve &
API_PID=$!

cd web
npm install
npm run dev &
WEB_PID=$!

trap 'kill ${API_PID} ${WEB_PID}' EXIT

wait
