#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
export HF_HOME="$PWD/.runtime/huggingface"
.venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device='cpu')"
echo 'Setup complete. Run: bash scripts/run.sh'
