"""Interactive configuration on the deployment host; generate secrets without printing them."""

import os
import re
import secrets
from pathlib import Path


def configure():
    destination = Path(".env.production")
    if destination.exists():
        raise SystemExit(
            ".env.production already exists. Edit it explicitly; existing secrets are preserved."
        )
    values = {}
    prompts = {
        "DOMAIN": "Domain pointing to this server (e.g. geo.your-domain.com)",
        "ACME_EMAIL": "Email for TLS certificate notices",
        "FIREBASE_PROJECT_ID": "Firebase project ID",
        "NEXT_PUBLIC_FIREBASE_API_KEY": "Firebase web app apiKey (public configuration)",
        "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN": "Firebase web app authDomain",
    }
    for key, prompt in prompts.items():
        value = input(f"{prompt}: ").strip()
        if not value or not re.fullmatch(r"[A-Za-z0-9@._-]+", value):
            raise SystemExit(
                f"Invalid {key}; use a plain hostname, project identifier or configuration value."
            )
        values[key] = value
    values["POSTGRES_PASSWORD"] = secrets.token_hex(32)
    values["DOWNLOAD_SECRET"] = secrets.token_hex(48)
    # O_EXCL avoids clobbering another configuration. Restrictive permissions on Unix hosts.
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as target:
        target.write("".join(f"{key}={value}\n" for key, value in values.items()))
    print("Created .env.production with fresh secrets. Do not commit or share this file.")


if __name__ == "__main__":
    configure()
