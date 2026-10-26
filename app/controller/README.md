# Local Python service

[Internal file responsibilities](src/betterlinuxcnc_service/README.md) · [Project module map](../../docs/module-map.md)

Currently provides a runnable Unix socket service accepting only `health` queries. It reports service reachability and always explicitly returns `machine_connected: false`; it has no LinuxCNC imports, motion commands, or HTTP listener.

## Development startup

Run from the repository root with Python 3.11 or later (Debian 13 defaults to Python 3.13):

```sh
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -e backend
backend/.venv/bin/python -m betterlinuxcnc_service
```

Keep that terminal running and start the desktop in another:

```sh
cd frontend
npm ci
npm run desktop:dev
```

Both use the same user and `XDG_RUNTIME_DIR`. The default address is `$XDG_RUNTIME_DIR/betterlinuxcnc/control.sock`; if unset, use `betterlinuxcnc/control.sock` under the system temporary directory. Python 3.11+ on macOS supports communication-layer development, not LinuxCNC execution on macOS. The desktop does not automatically start or install the service.

`--socket /path/to/control.sock` is only for server debugging/tests; the desktop UI cannot select arbitrary paths. The socket directory must belong to the current user with mode `0700`; socket mode is `0600`. Normal exit removes the socket created by this process. If a crash leaves a stale file, confirm no service owns it before cleanup. A second instance will not overwrite an existing endpoint.

## Protocol version 1

Transport is a four-byte unsigned big-endian length followed by UTF-8 JSON, with a 65536-byte frame limit, at most eight simultaneous clients, and two seconds for each complete request and response.

```json
{ "version": 1, "request_id": "example", "method": "health" }
```

```json
{
  "version": 1,
  "request_id": "example",
  "result": {
    "service": "betterlinuxcnc",
    "mode": "diagnostics-only",
    "machine_connected": false
  }
}
```

Errors preserve recognizable request IDs and express rejection through `error.code`. Unknown methods, extra/duplicate fields, nonstandard numbers, and mismatched versions are rejected. The service supports sequential queries on one connection; current Rust diagnostics opens a short connection for each query, without constructing unimplemented control sessions or state streams. Persistent control sessions and permission handshakes await machine integration.

Unix socket permissions restrict users but do not prove the client is Tauri. This diagnostic-only protocol cannot grant machine control.

## Checks and packaging

```sh
backend/.venv/bin/python -m pip install -r backend/requirements-ci.txt
backend/.venv/bin/ruff check backend
backend/.venv/bin/ruff format --check backend
backend/.venv/bin/python -m build --no-isolation backend
backend/.venv/bin/python -m pip install --force-reinstall --no-deps backend/dist/*.whl
backend/.venv/bin/python -m unittest discover -s backend/tests -v
```

CI builds wheels/source distributions on Python 3.11 and 3.13 and tests the installed service. The package has no third-party runtime dependencies. Rust tests also start real Python processes to verify message compatibility without connecting to a real machine.
