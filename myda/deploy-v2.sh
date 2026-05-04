#!/usr/bin/env bash
# MYDA Studio — Traefik-aware deploy
#
# Mirrors the /opt/contentclinic-web pattern on this VPS:
#   - nginx:alpine container at /opt/myda-web, exposing a host port
#   - Traefik file-provider config at /docker/traefik/conf.d/myda.yml
#   - TLS via the existing 'letsencrypt' cert resolver
#
# Idempotent. Run as root. No-touch to existing services.

set -euo pipefail

DOMAIN="myda.contentclinic.co"
PROJECT_DIR="/opt/myda-web"
TRAEFIK_CONF_DIR="/docker/traefik/conf.d"
TRAEFIK_CONF="$TRAEFIK_CONF_DIR/myda.yml"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

# --- pick a free host port (start at 8083) ---
pick_port() {
  for p in 8083 8084 8085 8086 8087 8088 8089 8090; do
    if ! ss -tln | awk '{print $4}' | grep -qE "[:.]$p\$"; then
      echo "$p"; return 0
    fi
  done
  echo "No free port in 8083-8090" >&2; exit 2
}
HOST_PORT=$(pick_port)
echo "==> Using host port $HOST_PORT"

# --- write site files ---
echo "==> Writing site to $PROJECT_DIR/site"
mkdir -p "$PROJECT_DIR/site"
SITE_B64="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"
echo "$SITE_B64" | base64 -d | tar -xzf - -C "$PROJECT_DIR/site"
ls "$PROJECT_DIR/site" | head -10

# --- nginx.conf for the container ---
cat > "$PROJECT_DIR/nginx.conf" <<'NGX'
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ $uri.html =404;
    }

    location ~* \.(?:css|js|png|jpe?g|gif|svg|webp|ico|woff2?)$ {
        expires 7d;
        add_header Cache-Control "public, max-age=604800, immutable";
    }

    access_log /var/log/nginx/access.log;
    error_log  /var/log/nginx/error.log;
}
NGX

# --- docker-compose.yml ---
cat > "$PROJECT_DIR/docker-compose.yml" <<COMPOSE
# MYDA Studio — static site
# Traefik handles SSL + routing via file provider at $TRAEFIK_CONF
# This container exposes port $HOST_PORT on host; Traefik proxies to it.
services:
  myda-web:
    image: nginx:alpine
    container_name: myda-web
    restart: unless-stopped
    ports:
      - "$HOST_PORT:80"
    volumes:
      - ./site:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
COMPOSE

# --- Traefik file-provider route ---
echo "==> Writing Traefik route to $TRAEFIK_CONF"
mkdir -p "$TRAEFIK_CONF_DIR"
cat > "$TRAEFIK_CONF" <<TRAEFIK
# Auto-generated for $DOMAIN
http:
  routers:
    myda-secure:
      rule: "Host(\`$DOMAIN\`)"
      entryPoints:
        - websecure
      service: myda
      tls:
        certResolver: letsencrypt
    myda-http:
      rule: "Host(\`$DOMAIN\`)"
      entryPoints:
        - web
      service: myda
  services:
    myda:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:$HOST_PORT"
TRAEFIK

# --- bring up the container ---
echo "==> Starting container..."
cd "$PROJECT_DIR"
if command -v docker compose >/dev/null 2>&1 || docker compose version >/dev/null 2>&1; then
  docker compose up -d
else
  docker-compose up -d
fi

# --- give traefik a moment, then verify ---
sleep 3
echo
echo "==> Container status:"
docker ps --filter name=myda-web --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo
echo "==> Local origin check (should be 200):"
curl -sI "http://127.0.0.1:$HOST_PORT/" | head -1 || true

echo
echo "==> Through Traefik (HTTPS, should be 200 once cert issues — first hit may 4xx for ~30s while ACME runs):"
curl -skI "https://$DOMAIN/" | head -1 || true

echo
echo "================================================================"
echo "DONE."
echo "URL:  https://$DOMAIN"
echo "Port: $HOST_PORT (origin)"
echo "Site: $PROJECT_DIR/site"
echo "Route: $TRAEFIK_CONF"
echo
echo "If TLS cert isn't ready yet, watch the resolver:"
echo "  docker logs \$(docker ps -qf name=traefik) 2>&1 | grep -i acme | tail -20"
echo "================================================================"
