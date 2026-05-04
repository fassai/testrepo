#!/usr/bin/env bash
# MYDA auto-deploy installer
#
# After running once, the VPS will check GitHub every 60s and automatically
# re-run deploy-v2.sh whenever its content changes (i.e. whenever Claude
# pushes new site files or config to the branch).
#
# Idempotent. Safe to re-run.
#
# To uninstall:
#   systemctl disable --now myda-autodeploy.timer
#   rm /etc/systemd/system/myda-autodeploy.{service,timer}
#   rm /usr/local/bin/myda-autodeploy
#   systemctl daemon-reload

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

DEPLOY_URL="https://raw.githubusercontent.com/fassai/testrepo/claude/myda-studio-landing-6OtRj/myda/deploy-v2.sh"

echo "==> Writing /usr/local/bin/myda-autodeploy"
cat > /usr/local/bin/myda-autodeploy <<EOF
#!/usr/bin/env bash
# Re-run MYDA deploy if the upstream script has changed.
set -e
URL="$DEPLOY_URL"
CACHE="/var/lib/myda-autodeploy.sha"
mkdir -p "\$(dirname "\$CACHE")"
TMP=\$(mktemp)
trap 'rm -f "\$TMP"' EXIT
if ! curl -fsSL "\$URL" -o "\$TMP"; then
  echo "[myda] fetch failed, skipping this tick"
  exit 0
fi
NEW=\$(sha256sum "\$TMP" | awk '{print \$1}')
OLD=\$(cat "\$CACHE" 2>/dev/null || true)
if [ "\$NEW" = "\$OLD" ]; then
  exit 0
fi
echo "[myda] change detected (\$NEW), deploying..."
bash "\$TMP"
echo "\$NEW" > "\$CACHE"
echo "[myda] done"
EOF
chmod +x /usr/local/bin/myda-autodeploy

echo "==> Writing systemd service + timer"
cat > /etc/systemd/system/myda-autodeploy.service <<'EOF'
[Unit]
Description=MYDA auto-deploy from GitHub
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/myda-autodeploy
EOF

cat > /etc/systemd/system/myda-autodeploy.timer <<'EOF'
[Unit]
Description=Check GitHub every 60s for MYDA site changes

[Timer]
OnBootSec=30s
OnUnitActiveSec=60s
Unit=myda-autodeploy.service
AccuracySec=5s

[Install]
WantedBy=timers.target
EOF

echo "==> Enabling timer"
systemctl daemon-reload
systemctl enable --now myda-autodeploy.timer

echo
echo "================================================================"
echo "AUTO-DEPLOY ACTIVE."
echo
echo "From now on, when Claude pushes changes to the branch, this VPS"
echo "will pick them up and redeploy within ~60s. No further pastes."
echo
echo "Inspect:    systemctl status myda-autodeploy.timer"
echo "Last runs:  systemctl list-timers myda-autodeploy.timer"
echo "Logs:       journalctl -u myda-autodeploy.service -n 50 --no-pager"
echo "Trigger now: systemctl start myda-autodeploy.service"
echo "Disable:    systemctl disable --now myda-autodeploy.timer"
echo "================================================================"
