#!/bin/sh
# Create a self-signed certificate for https://localhost, for local development only.
# Staging and production put their real certificate in the same place (P0-OPS-01).
set -eu
cd "$(dirname "$0")"
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
    -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
    -keyout certs/server.key -out certs/server.crt
# Nginx runs as uid 101 inside its container and must be able to read the key.
chmod 644 certs/server.key certs/server.crt
echo "Created deploy/nginx/certs/server.crt and server.key"
