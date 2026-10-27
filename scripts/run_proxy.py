"""Start a native LiteLLM proxy using private local credentials, without Docker."""

import argparse
import os
import secrets
from pathlib import Path

import yaml

parser = argparse.ArgumentParser()
parser.add_argument("--runtime", type=Path, default=Path(".runtime/proxy-venv"))
parser.add_argument(
    "--fail-primary",
    action="store_true",
    help="Point primary at a closed local port to test real proxy failover",
)
args = parser.parse_args()
Path(".runtime").mkdir(exist_ok=True)
key_path = Path(".runtime/proxy.key")
if not key_path.exists():
    fd = os.open(key_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as file:
        file.write("sk-" + secrets.token_urlsafe(32))
os.environ["LITELLM_MASTER_KEY"] = key_path.read_text().strip()
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LITELLM_TELEMETRY"] = "False"
target = Path(".runtime/native-proxy.yaml")
config = yaml.safe_load(Path("config/litellm.yaml").read_text().replace("host.docker.internal", "127.0.0.1"))
if args.fail_primary:
    config["model_list"][0]["litellm_params"]["api_base"] = "http://127.0.0.1:1/v1"
target.write_text(yaml.safe_dump(config))
binary = args.runtime.resolve() / "bin/litellm"
os.execv(binary, [str(binary), "--config", str(target), "--host", "127.0.0.1", "--port", "4000"])
