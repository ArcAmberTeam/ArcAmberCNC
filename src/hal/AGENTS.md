# HAL module boundaries

Follow the root `AGENT.md`.

`src/hal/` is the sole source owner for LinuxCNC HAL, including its core library, components, ClassicLadder, configuration tools, and user-space components. Organize existing C++ Python bindings, mixed C/C++ command tools, Python tools, and `.comp` definitions by function; do not split linked units by implementation language.

Public boundaries remain `hal.h`, existing installed headers, HAL pins/parameters, and command-line tools. `hal_priv.h` remains internal; do not export more of it. Access by upstream HAL tools and `src/rtapi/uspace_rtapi_app.cc` is a retained internal native-runtime exception, not an application-layer cross-layer interface.

Physical device-driver sources live in `drivers/`; user-space drivers and handwheels in `user_comps/`. Follow their respective `AGENTS.md`. All directories are actual source paths; builds, header exports, generators, and archives directly use the upstream structure without cross-root compatibility links or duplicate source.

`src/` is the build coordination entry point; Make, Meson, and source scanning directly access `src/hal/`. Retain functional directories, separating platform/CPU only for actual implementation differences. Do not copy common logic or create empty architecture directories.

Verification: run `.github/ci/test_native_layout.py` and affected native scopes through `.github/ci/native-check.sh` in a Debian 13 container. Builds must not load modules or access devices. README content is maintained by humans.
