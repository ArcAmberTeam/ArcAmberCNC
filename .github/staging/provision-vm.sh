#!/bin/bash
# Run as root on a fresh Debian 13 staging VM after cloud-init and frpc upload.
# /etc/frp/frpc.toml and its pinned server.crt must already be provisioned.
set -euo pipefail
# shellcheck disable=SC1091 # Provided by the target Debian system.
[[ $EUID == 0 && $(. /etc/os-release; printf '%s' "$VERSION_ID") == 13 ]]
[[ $(dpkg --print-architecture) == amd64 ]]
export DEBIAN_FRONTEND=noninteractive
apt-get update -o APT::Update::Error-Mode=any
apt-get install -y --no-install-recommends linux-image-rt-amd64 qemu-guest-agent \
  sudo curl ca-certificates openssl xfce4 xfce4-terminal dbus-x11 \
  tigervnc-standalone-server tigervnc-tools novnc websockify \
  linuxcnc-uspace xauth fonts-dejavu-core
getent passwd frp >/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin frp
getent passwd novnc >/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin novnc
getent group realtime >/dev/null || groupadd --system realtime
usermod -aG realtime,video,render linuxcnc
cat > /etc/security/limits.d/linuxcnc-staging.conf <<'EOF'
@realtime - rtprio 99
@realtime - memlock unlimited
EOF
install -d -m 755 /srv/betterlinuxcnc /srv/betterlinuxcnc/releases
install -d -m 700 -o deploy -g deploy /srv/betterlinuxcnc/incoming
cat > /etc/sudoers.d/betterlinuxcnc-deploy <<'EOF'
deploy ALL=(root) NOPASSWD: /usr/local/sbin/betterlinuxcnc-deploy
EOF
chmod 440 /etc/sudoers.d/betterlinuxcnc-deploy
visudo -cf /etc/sudoers.d/betterlinuxcnc-deploy
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
Description=LinuxCNC staging XFCE desktop
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
LimitRTPRIO=99
LimitMEMLOCK=infinity
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/linuxcnc-novnc.service <<'EOF'
[Unit]
Description=HTTPS noVNC for LinuxCNC staging
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
cat > /home/linuxcnc/Desktop/linuxcnc.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=LinuxCNC
Comment=Choose a simulation configuration
Exec=linuxcnc
Icon=linuxcnc
Terminal=false
EOF
chown linuxcnc:linuxcnc /home/linuxcnc/Desktop/linuxcnc.desktop
chmod 755 /home/linuxcnc/Desktop/linuxcnc.desktop
/usr/local/bin/frpc verify -c /etc/frp/frpc.toml
systemctl daemon-reload
systemctl enable --now frpc-xamber linuxcnc-desktop linuxcnc-novnc
systemctl start qemu-guest-agent
printf 'noVNC HTTPS certificate: '
openssl x509 -in /etc/novnc/server.crt -noout -fingerprint -sha256
echo 'Reboot into the installed RT kernel, then verify /sys/kernel/realtime = 1.'
