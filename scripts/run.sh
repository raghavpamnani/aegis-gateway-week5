#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/private/tmp/aegis-week5-pycache}"
export HF_HOME="${HF_HOME:-$PWD/.runtime/huggingface}"
# Load only trusted operator-owned dotenv shell assignments. Never source uploads.
if [ -f .env ]; then set -a; . ./.env; set +a; fi
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
exec .venv/bin/python -m uvicorn aegis.app:create_app --factory --host 127.0.0.1 --port 8050
