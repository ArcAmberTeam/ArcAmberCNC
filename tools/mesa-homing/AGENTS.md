# Fixed Mesa homing build adapter

Follow the root AGENT.md. This directory owns the build and verification adapter,
not the homing algorithm or machine configuration. `vendor/cnc-mesa` is an
immutable, checksum-pinned upstream Release snapshot; never edit its files.

- Build only in GitHub CI. Copy native sources into a disposable writable tree,
  generate headers and halcompile from this repository, and compile only the
  fixed zhulong_homing module. Do not use distribution development headers.
- Run the upstream public HOMEMOD harness against these generated headers, with
  HAL allocation substitutes. Never load the module, start LinuxCNC, or touch
  hardware. Generator and HDL tests run on a disposable copy of the snapshot.
- Install only `/usr/lib/linuxcnc/modules/zhulong_homing.so`; place provenance
  under `/usr/share/betterlinuxcnc/homing`. Do not replace other native modules.
- Record vendor hashes, native revision, exported API and header hashes. Building
  against a revision does not prove compatibility with another installed core or
  physical homing behavior. Deployment must verify the intended core separately.
