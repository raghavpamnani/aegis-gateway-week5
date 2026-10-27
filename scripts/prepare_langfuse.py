"""Fetch official Compose at a recorded commit, create private localhost-only config."""

import json
import os
import secrets
import urllib.request
from pathlib import Path

import yaml

home = Path(".runtime/langfuse")
home.mkdir(parents=True, exist_ok=True)
request = urllib.request.Request(
    "https://api.github.com/repos/langfuse/langfuse/commits/main", headers={"User-Agent": "Aegis-Bootcamp"}
)
commit = json.load(urllib.request.urlopen(request, timeout=30))["sha"]
base = f"https://raw.githubusercontent.com/langfuse/langfuse/{commit}/"
raw = urllib.request.urlopen(base + "docker-compose.yml", timeout=30).read()
config = yaml.safe_load(raw)
for service in config["services"].values():
    # Keep every published port on localhost, including upstream web/media defaults.
    ports = []
    for port in service.get("ports", []):
        if not isinstance(port, str):
            raise ValueError("Review upstream Compose port format before proceeding")
        fields = port.split(":")
        ports.append("127.0.0.1:" + ":".join(fields[-2:]))
    service["ports"] = ports
(home / "compose.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
(home / "UPSTREAM.txt").write_text(
    f"Source: {base}docker-compose.yml\nCommit: {commit}\nLocal change: bind published ports to 127.0.0.1.\n"
)
secret_file = home / ".env"
if not secret_file.exists():
    password = secrets.token_hex(24)
    public = "pk-lf-" + secrets.token_hex(16)
    secret = "sk-lf-" + secrets.token_hex(24)
    values = {
        "NEXTAUTH_SECRET": secrets.token_hex(32),
        "SALT": secrets.token_hex(32),
        "ENCRYPTION_KEY": secrets.token_hex(32),
        "REDIS_AUTH": secrets.token_hex(24),
        "POSTGRES_PASSWORD": password,
        "DATABASE_URL": f"postgresql://postgres:{password}@postgres:5432/postgres",
        "MINIO_ROOT_PASSWORD": secrets.token_hex(24),
        "LANGFUSE_INIT_ORG_ID": "aegis-lab",
        "LANGFUSE_INIT_ORG_NAME": "Aegis Lab",
        "LANGFUSE_INIT_PROJECT_ID": "aegis-gateway",
        "LANGFUSE_INIT_PROJECT_NAME": "Aegis Gateway",
        "LANGFUSE_INIT_PROJECT_PUBLIC_KEY": public,
        "LANGFUSE_INIT_PROJECT_SECRET_KEY": secret,
        "LANGFUSE_INIT_USER_EMAIL": "operator@aegis.example",
        "LANGFUSE_INIT_USER_NAME": "Local Operator",
        "LANGFUSE_INIT_USER_PASSWORD": secrets.token_urlsafe(24),
        "TELEMETRY_ENABLED": "false",
    }
    values["LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY"] = values["MINIO_ROOT_PASSWORD"]
    values["LANGFUSE_S3_BATCH_EXPORT_SECRET_ACCESS_KEY"] = values["MINIO_ROOT_PASSWORD"]
    values["LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY"] = values["MINIO_ROOT_PASSWORD"]
    fd = os.open(secret_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as file:
        file.write("\n".join(k + "=" + v for k, v in values.items()) + "\n")
    fd = os.open(home / "app.env", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as file:
        file.write(
            f"LANGFUSE_BASE_URL=http://localhost:3000\nLANGFUSE_PUBLIC_KEY={public}\nLANGFUSE_SECRET_KEY={secret}\n"
        )
print("Prepared", home, "at official commit", commit)
print("Review generated Compose and UPSTREAM.txt, then run the command in docs/INTEGRATIONS.md.")
