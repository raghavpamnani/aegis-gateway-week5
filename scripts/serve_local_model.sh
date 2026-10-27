#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -n "${AEGIS_OLLAMA_BIN:-}" ]; then
  model_bin="$AEGIS_OLLAMA_BIN"
elif command -v ollama >/dev/null 2>&1; then
  model_bin="$(command -v ollama)"
elif [ -x "$HOME/Library/Caches/ProcureFlow/ollama/ollama" ]; then
  model_bin="$HOME/Library/Caches/ProcureFlow/ollama/ollama"
else
  echo 'Install Ollama from https://ollama.com/download, then rerun.' >&2
  exit 1
fi
export OLLAMA_HOST=127.0.0.1:11435
export OLLAMA_MODELS="$PWD/.runtime/ollama-models"
export OLLAMA_NO_CLOUD=1
mkdir -p "$OLLAMA_MODELS"
exec "$model_bin" serve
