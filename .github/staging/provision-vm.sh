#!/bin/bash
# Run as root to provision or upgrade the dedicated Debian 13 Web staging VM.
# /etc/frp/frpc.toml and its pinned server.crt must already be provisioned.
set -euo pipefail
# shellcheck disable=SC1091 # Provided by the target Debian system.
[[ $EUID == 0 && $(. /etc/os-release; printf '%s' "$VERSION_ID") == 13 ]]
[[ $(dpkg --print-architecture) == amd64 ]]
script_directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
[[ -f $script_directory/install.sh && -f $script_directory/web_release.py ]]
# Prevent a newly installed nginx package from briefly opening its default port 80.
systemctl stop nginx.service 2>/dev/null || true
systemctl mask --runtime nginx.service
export DEBIAN_FRONTEND=noninteractive
apt-get update -o APT::Update::Error-Mode=any
apt-get install -y --no-install-recommends qemu-guest-agent \
  sudo curl ca-certificates openssl xfce4 xfce4-terminal dbus-x11 \
  tigervnc-standalone-server tigervnc-tools novnc websockify \
  chromium nginx python3 xauth fonts-dejavu-core
getent passwd frp >/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin frp
getent passwd novnc >/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin novnc
usermod -aG video,render linuxcnc
install -d -m 755 -o root -g root /srv/betterlinuxcnc-web /srv/betterlinuxcnc-web/releases
install -d -m 700 -o deploy -g deploy /srv/betterlinuxcnc-web/incoming
install -d -m 755 -o root -g root /usr/local/lib/betterlinuxcnc
install -m 644 -o root -g root "$script_directory/web_release.py" /usr/local/lib/betterlinuxcnc/web_release.py
install -m 755 -o root -g root "$script_directory/install.sh" /usr/local/sbin/betterlinuxcnc-deploy-web
# Revoke the obsolete package installer during the one-time migration.
rm -f /etc/sudoers.d/betterlinuxcnc-deploy /usr/local/sbin/betterlinuxcnc-deploy
cat > /etc/sudoers.d/betterlinuxcnc-deploy-web <<'EOF'
deploy ALL=(root) NOPASSWD: /usr/local/sbin/betterlinuxcnc-deploy-web
EOF
chmod 440 /etc/sudoers.d/betterlinuxcnc-deploy-web
visudo -cf /etc/sudoers.d/betterlinuxcnc-deploy-web
# Dedicated staging nginx configuration: no includes can reopen a public listener.
cat > /etc/nginx/nginx.conf <<'EOF'
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;
events { worker_connections 256; }
http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
    sendfile on;
    server_tokens off;
    server {
        listen 127.0.0.1:8080;
        server_name localhost;
        root /srv/betterlinuxcnc-web/current;
        index index.html;
        add_header Cache-Control "no-cache" always;
        add_header X-Content-Type-Options "nosniff" always;
        location / { try_files $uri $uri/ /index.html; }
        location = /build-info.json { try_files $uri =404; }
        location ~ /\. { deny all; }
    }
}
EOF
nginx -t
systemctl unmask --runtime nginx.service
chown -R root:frp /etc/frp
chmod 750 /etc/frp
chmod 640 /etc/frp/frpc.toml /etc/frp/server.crt
chmod 755 /usr/local/bin/frpc
cat > /etc/systemd/system/frpc-xamber.service <<'EOF'
[Unit]
Description=BetterLinuxCNC staging FRP tunnels
After=network-online.target
Wants=network-online.target
[Service]
User=frp
Group=frp
ExecStart=/usr/local/bin/frpc -c /etc/frp/frpc.toml
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
[Install]
WantedBy=multi-user.target
EOF
install -d -m 700 -o linuxcnc -g linuxcnc \
  /home/linuxcnc/.config /home/linuxcnc/.config/tigervnc
install -d -m 700 /root/staging-credentials
if [[ ! -f /home/linuxcnc/.config/tigervnc/passwd ]]; then
  umask 077
  openssl rand -base64 6 > /root/staging-credentials/novnc-password
  tigervncpasswd -f < /root/staging-credentials/novnc-password \
    > /home/linuxcnc/.config/tigervnc/passwd
  chown linuxcnc:linuxcnc /home/linuxcnc/.config/tigervnc/passwd
fi
cat > /home/linuxcnc/.config/tigervnc/xstartup <<'EOF'
#!/bin/sh
unset SESSION_MANAGER DBUS_SESSION_BUS_ADDRESS
exec dbus-run-session -- startxfce4
EOF
chmod 755 /home/linuxcnc/.config/tigervnc/xstartup
chown linuxcnc:linuxcnc /home/linuxcnc/.config/tigervnc/xstartup
install -d -m 750 -o root -g novnc /etc/novnc
if [[ ! -f /etc/novnc/server.key ]]; then
  openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 825 \
    -keyout /etc/novnc/server.key -out /etc/novnc/server.crt \
    -subj /CN=linuxcnc-staging -addext 'subjectAltName=IP:45.192.97.209' \
    >/dev/null 2>&1
fi
chown root:novnc /etc/novnc/server.*
chmod 640 /etc/novnc/server.*
cat > /etc/systemd/system/linuxcnc-desktop.service <<'EOF'
[Unit]
Description=BetterLinuxCNC Web staging XFCE desktop
After=network.target
[Service]
Type=simple
User=linuxcnc
Group=linuxcnc
PAMName=login
WorkingDirectory=/home/linuxcnc
Environment=HOME=/home/linuxcnc
ExecStart=/usr/bin/tigervncserver :1 -fg -localhost yes -geometry 1440x900 -depth 24 -SecurityTypes VncAuth -PasswordFile /home/linuxcnc/.config/tigervnc/passwd -xstartup /home/linuxcnc/.config/tigervnc/xstartup
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/linuxcnc-novnc.service <<'EOF'
[Unit]
Description=HTTPS noVNC for BetterLinuxCNC Web staging
After=linuxcnc-desktop.service
Requires=linuxcnc-desktop.service
[Service]
User=novnc
Group=novnc
ExecStart=/usr/bin/websockify --ssl-only --cert=/etc/novnc/server.crt --key=/etc/novnc/server.key --web=/usr/share/novnc 127.0.0.1:6080 127.0.0.1:5901
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
[Install]
WantedBy=multi-user.target
EOF
install -d -o linuxcnc -g linuxcnc /home/linuxcnc/Desktop
rm -f /home/linuxcnc/Desktop/linuxcnc.desktop
cat > /home/linuxcnc/Desktop/betterlinuxcnc-web.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=BetterLinuxCNC Web
Comment=Open the deployed Web interface
Exec=chromium --app=http://127.0.0.1:8080/
Icon=chromium
Terminal=false
EOF
chown linuxcnc:linuxcnc /home/linuxcnc/Desktop/betterlinuxcnc-web.desktop
chmod 755 /home/linuxcnc/Desktop/betterlinuxcnc-web.desktop
/usr/local/bin/frpc verify -c /etc/frp/frpc.toml
systemctl daemon-reload
systemctl enable --now nginx frpc-xamber linuxcnc-desktop linuxcnc-novnc
systemctl start qemu-guest-agent
printf 'noVNC HTTPS certificate: '
openssl x509 -in /etc/novnc/server.crt -noout -fingerprint -sha256
echo 'Web staging is ready at http://127.0.0.1:8080/ after the first successful Web deployment.'
