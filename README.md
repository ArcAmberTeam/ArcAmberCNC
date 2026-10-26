Configuration file: `./launcher.json`, used for machine configuration and startup orchestration. Template: `./launcher.example.json`. Relative paths resolve against the configuration file's directory.

- `ini`: machine INI path; set `[DISPLAY] DISPLAY` to `betterlinuxcnc`.
- `startup_timeout`, `shutdown_timeout`: startup and shutdown wait times in seconds.
- `cam.host`, `cam.port`: machine TCP listen address and port; the default port is 6522.
- `cam.inbox`: G-code inbox directory.
- `cam.auto_run`: whether to submit machining when new G-code arrives; defaults to false.
- `cam.discovery.device_id`, `device_name`, `address`: stable device UUID, name, and broadcast address; UDP port 8421.
- Set `cam` to null to disable CAM integration.

Startup: after installation, run `betterlinuxcnc-launch` in the project directory. Run `betterlinuxcnc-launch --check` to check configuration, or `betterlinuxcnc-launch --config /project/path/launcher.json` to select a project configuration.

The default installed autostart project is `/opt/arcambercnc/launcher.json`. Set it at build time with `-DBETTERCNC_PROJECT_DIR=/project/path`. It starts automatically and is supervised after entering the desktop session; unattended boot requires system user autologin.

Manual stop: `systemctl --user stop betterlinuxcnc-launcher.service`, or kill the main launcher process; it will not restart automatically in this session. Run once without supervision: `betterlinuxcnc-launch --once`.
